"""Lightweight billing helper for jobs metering."""
import logging
import os
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import OrgMember

logger = logging.getLogger(__name__)


def _enrichment_cost() -> Decimal:
    raw = os.getenv("ENRICHMENT_CREDIT_COST", "0.01")
    try:
        return Decimal(raw)
    except Exception:
        return Decimal("0.01")


def get_user_org_id(db: Session, user_id: UUID) -> Optional[UUID]:
    """Resolve org membership for a user."""
    member = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
    return member.org_id if member else None


def check_and_deduct(
    db: Session,
    org_id: UUID,
    job_id: UUID,
    contributor_id: UUID,
) -> Tuple[bool, Optional[float]]:
    """Deduct enrichment credits if billing rows exist.

    Fail-open behavior:
    - If billing tables/rows are not initialized yet, allow processing.
    - If metering write fails unexpectedly, allow processing and log warning.
    """
    cost = _enrichment_cost()

    try:
        row = db.execute(
            text(
                """
                SELECT credit_balance, COALESCE(is_byok, false) AS is_byok, COALESCE(is_enterprise, false) AS is_enterprise
                FROM org_billing
                WHERE org_id = :org_id
                FOR UPDATE
                """
            ),
            {"org_id": str(org_id)},
        ).mappings().first()

        if not row:
            # No billing account yet: don't block jobs.
            return True, None

        balance = Decimal(str(row["credit_balance"] or 0))
        if row["is_byok"] or row["is_enterprise"]:
            return True, float(balance)

        if balance < cost:
            db.rollback()
            return False, float(balance)

        new_balance = balance - cost

        db.execute(
            text(
                """
                UPDATE org_billing
                SET credit_balance = :new_balance,
                    total_credits_used = COALESCE(total_credits_used, 0) + :cost,
                    total_enrichments = COALESCE(total_enrichments, 0) + 1,
                    updated_at = NOW()
                WHERE org_id = :org_id
                """
            ),
            {
                "org_id": str(org_id),
                "new_balance": str(new_balance),
                "cost": str(cost),
            },
        )

        # Best-effort journaling; ignore if older schemas don't have these columns yet.
        try:
            db.execute(
                text(
                    """
                    INSERT INTO credit_transactions (
                      org_id, type, amount, balance_after, description, job_id, contributor_id
                    ) VALUES (
                      :org_id, 'deduction', :amount, :balance_after, :description, :job_id, :contributor_id
                    )
                    """
                ),
                {
                    "org_id": str(org_id),
                    "amount": str(-cost),
                    "balance_after": str(new_balance),
                    "description": "Lead enrichment credit deduction",
                    "job_id": str(job_id),
                    "contributor_id": str(contributor_id),
                },
            )
        except Exception:
            db.rollback()
            db.execute(
                text(
                    """
                    UPDATE org_billing
                    SET credit_balance = :new_balance,
                        total_credits_used = COALESCE(total_credits_used, 0) + :cost,
                        total_enrichments = COALESCE(total_enrichments, 0) + 1,
                        updated_at = NOW()
                    WHERE org_id = :org_id
                    """
                ),
                {
                    "org_id": str(org_id),
                    "new_balance": str(new_balance),
                    "cost": str(cost),
                },
            )

        try:
            db.execute(
                text(
                    """
                    INSERT INTO usage_events (
                      org_id, event_type, cost, job_id, contributor_id, is_byok
                    ) VALUES (
                      :org_id, 'enrichment', :cost, :job_id, :contributor_id, false
                    )
                    """
                ),
                {
                    "org_id": str(org_id),
                    "cost": str(cost),
                    "job_id": str(job_id),
                    "contributor_id": str(contributor_id),
                },
            )
        except Exception:
            pass

        db.commit()
        return True, float(new_balance)
    except Exception as exc:
        db.rollback()
        logger.warning("Billing metering failed (allowing job): %s", exc)
        return True, None
