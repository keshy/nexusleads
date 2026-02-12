"""Billing router – credit balance, transactions, and usage."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, OrgBilling, CreditTransaction, UsageEvent

router = APIRouter()


@router.get("/balance")
async def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Get current credit balance for the org."""
    billing = db.query(OrgBilling).filter(OrgBilling.org_id == org_id).first()
    if not billing:
        return {
            "credit_balance": 0.0,
            "lifetime_credits_purchased": 0.0,
            "lifetime_credits_used": 0.0,
            "free_grant_applied": False,
            "auto_reload_enabled": False,
            "auto_reload_threshold": None,
            "auto_reload_amount": None,
        }
    return {
        "credit_balance": float(billing.credit_balance),
        "lifetime_credits_purchased": float(billing.lifetime_credits_purchased),
        "lifetime_credits_used": float(billing.lifetime_credits_used),
        "free_grant_applied": billing.free_grant_applied,
        "auto_reload_enabled": billing.auto_reload_enabled,
        "auto_reload_threshold": float(billing.auto_reload_threshold) if billing.auto_reload_threshold else None,
        "auto_reload_amount": float(billing.auto_reload_amount) if billing.auto_reload_amount else None,
    }


@router.get("/transactions")
async def list_transactions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """List credit transactions for the org."""
    txns = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.org_id == org_id)
        .order_by(desc(CreditTransaction.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(t.id),
            "type": t.type,
            "amount": float(t.amount),
            "balance_after": float(t.balance_after) if t.balance_after is not None else None,
            "description": t.description,
            "reference_id": t.reference_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]


@router.get("/usage")
async def get_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Get usage summary for the org."""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    total_events = (
        db.query(func.count(UsageEvent.id))
        .filter(UsageEvent.org_id == org_id)
        .scalar()
        or 0
    )
    recent_events = (
        db.query(func.count(UsageEvent.id))
        .filter(UsageEvent.org_id == org_id, UsageEvent.created_at >= thirty_days_ago)
        .scalar()
        or 0
    )
    total_credits_used = (
        db.query(func.sum(UsageEvent.credits))
        .filter(UsageEvent.org_id == org_id)
        .scalar()
        or 0.0
    )

    return {
        "total_events": total_events,
        "events_last_30_days": recent_events,
        "total_credits_used": float(total_credits_used),
    }


@router.put("/auto-reload")
async def update_auto_reload(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Update auto-reload settings."""
    billing = db.query(OrgBilling).filter(OrgBilling.org_id == org_id).first()
    if not billing:
        billing = OrgBilling(org_id=org_id)
        db.add(billing)

    if "enabled" in data:
        billing.auto_reload_enabled = bool(data["enabled"])
    if "threshold" in data:
        billing.auto_reload_threshold = data["threshold"]
    if "amount" in data:
        billing.auto_reload_amount = data["amount"]

    db.commit()
    return {"status": "ok"}
