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
            "total_credits_purchased": 0.0,
            "total_credits_used": 0.0,
            "free_grant_applied": False,
            "auto_reload_enabled": False,
            "auto_reload_threshold": None,
            "auto_reload_amount": None,
        }
    return {
        "credit_balance": float(billing.credit_balance),
        "total_credits_purchased": float(billing.total_credits_purchased),
        "total_credits_used": float(billing.total_credits_used),
        "free_grant_applied": False,
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
            "reference_id": t.stripe_session_id,
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
        db.query(func.sum(UsageEvent.cost))
        .filter(UsageEvent.org_id == org_id)
        .scalar()
        or 0.0
    )

    return {
        "total_events": total_events,
        "events_last_30_days": recent_events,
        "total_credits_used": float(total_credits_used),
    }


@router.post("/purchase")
async def purchase_credits(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Purchase credits (manual top-up). Creates a transaction and updates balance."""
    from decimal import Decimal

    amount = data.get("amount")
    if not amount or float(amount) < 10:
        raise HTTPException(status_code=400, detail="Minimum purchase is $10.00")

    amount_dec = Decimal(str(amount))

    billing = db.query(OrgBilling).filter(OrgBilling.org_id == org_id).first()
    if not billing:
        billing = OrgBilling(org_id=org_id, credit_balance=0, total_credits_purchased=0, total_credits_used=0)
        db.add(billing)
        db.flush()

    new_balance = billing.credit_balance + amount_dec
    billing.credit_balance = new_balance
    billing.total_credits_purchased = billing.total_credits_purchased + amount_dec

    txn = CreditTransaction(
        org_id=org_id,
        type="purchase",
        amount=amount_dec,
        balance_after=new_balance,
        description=f"Manual credit purchase (${amount_dec:.2f})",
    )
    db.add(txn)
    db.commit()

    return {
        "status": "ok",
        "credit_balance": float(new_balance),
        "transaction_id": str(txn.id),
    }


@router.post("/checkout")
async def create_checkout_session(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Create a Stripe checkout session for credit purchase."""
    import os

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    amount = data.get("amount", 10)

    if not stripe_key:
        # Stripe not configured — fall back to manual purchase
        raise HTTPException(status_code=400, detail="Stripe is not configured. Use manual purchase instead.")

    try:
        import stripe
        stripe.api_key = stripe_key

        success_url = data.get("success_url", "http://localhost:5173/app/settings?billing=success")
        cancel_url = data.get("cancel_url", "http://localhost:5173/app/settings?billing=cancel")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"NexusLeads Credits (${amount:.2f})"},
                    "unit_amount": int(float(amount) * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"org_id": str(org_id), "amount": str(amount)},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except ImportError:
        raise HTTPException(status_code=400, detail="Stripe SDK not installed. Use manual purchase.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
