"""Settings API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User
from schemas import AppSettingResponse, AppSettingUpdate
from settings_service import (
    get_org_settings, upsert_org_setting, delete_org_setting,
    MANAGED_KEYS,
)

router = APIRouter()


@router.get("", response_model=List[AppSettingResponse])
async def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get all managed settings for the selected organization. Secrets are masked."""
    return get_org_settings(db, org_id)


@router.put("")
async def update_setting(
    data: AppSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Create or update a setting for the selected organization."""
    if data.key not in MANAGED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {data.key}")
    upsert_org_setting(db, org_id, data.key, data.value)
    return {"status": "ok", "key": data.key}


@router.delete("/{key}")
async def remove_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Delete an org setting, reverting to env var fallback."""
    if key not in MANAGED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
    delete_org_setting(db, org_id, key)
    return {"status": "ok", "key": key}
