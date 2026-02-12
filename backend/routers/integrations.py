"""Integrations router – Clay webhook and future integrations."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, OrgSetting, ClayPushLog, SourcingJob, Project
from settings_service import get_setting, upsert_org_setting, delete_org_setting

router = APIRouter()


# ── Clay webhook config ──────────────────────────────────────────────

@router.get("/clay/config")
async def get_clay_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Get Clay integration config for the org."""
    webhook_url = get_setting(db, "CLAY_WEBHOOK_URL", org_id=org_id) or ""
    return {"webhook_url": webhook_url, "connected": bool(webhook_url)}


@router.put("/clay/config")
async def update_clay_config(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Set or update the Clay webhook URL for the org."""
    webhook_url = (data.get("webhook_url") or "").strip()
    if webhook_url:
        upsert_org_setting(db, org_id, "CLAY_WEBHOOK_URL", webhook_url)
    else:
        delete_org_setting(db, org_id, "CLAY_WEBHOOK_URL")
    return {"status": "ok", "webhook_url": webhook_url}


@router.post("/clay/test")
async def test_clay_webhook(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Send a test payload to the Clay webhook."""
    import httpx, json
    webhook_url = get_setting(db, "CLAY_WEBHOOK_URL", org_id=org_id)
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Clay webhook URL not configured")

    test_payload = {
        "_meta": {"test": True, "org_id": str(org_id)},
        "contributor": {"username": "test-user", "email": "test@example.com"},
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=test_payload)
        return {"status": "ok", "http_status": resp.status_code, "response": resp.text[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Clay push logs ───────────────────────────────────────────────────

@router.get("/clay/activity")
async def get_clay_activity(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Get recent Clay push activity for the org."""
    logs = (
        db.query(ClayPushLog)
        .filter(ClayPushLog.org_id == org_id)
        .order_by(desc(ClayPushLog.pushed_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(log.id),
            "contributor_id": str(log.contributor_id),
            "project_id": str(log.project_id) if log.project_id else None,
            "status": log.status,
            "pushed_at": log.pushed_at.isoformat() if log.pushed_at else None,
            "error_message": log.error_message,
        }
        for log in logs
    ]


@router.get("/clay/stats")
async def get_clay_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Get aggregate Clay push stats for the org."""
    from sqlalchemy import func

    total = db.query(func.count(ClayPushLog.id)).filter(ClayPushLog.org_id == org_id).scalar() or 0
    success = (
        db.query(func.count(ClayPushLog.id))
        .filter(ClayPushLog.org_id == org_id, ClayPushLog.status == "success")
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(ClayPushLog.id))
        .filter(ClayPushLog.org_id == org_id, ClayPushLog.status == "failed")
        .scalar()
        or 0
    )
    return {"total": total, "success": success, "failed": failed}


# ── Clay push (single + bulk) ────────────────────────────────────────

@router.post("/clay/push")
async def push_leads_to_clay(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id=Depends(require_org),
):
    """Queue a clay_push job for the given contributor IDs."""
    contributor_ids = data.get("contributor_ids", [])
    project_id = data.get("project_id")
    if not contributor_ids:
        raise HTTPException(status_code=400, detail="No contributor_ids provided")

    job = SourcingJob(
        project_id=project_id,
        job_type="clay_push",
        status="pending",
        created_by=current_user.id,
        parameters={"contributor_ids": contributor_ids, "org_id": str(org_id)},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"status": "queued", "job_id": str(job.id)}
