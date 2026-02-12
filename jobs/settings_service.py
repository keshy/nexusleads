"""Service for reading app settings from DB with env var fallback (jobs module).

Org-aware: when an org_id is provided the lookup chain is:
  org_settings → app_settings → env var → default
"""
import os
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from models import AppSetting, OrgSetting, OrgMember

logger = logging.getLogger(__name__)


def get_setting(db: Session, key: str, default: str = "", *, org_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> str:
    """Get a setting value.

    Lookup order:
      1. org_settings (if org_id provided)
      2. app_settings (global)
      3. Environment variable
      4. default
    """
    # 1. Org-level override
    if org_id:
        try:
            row = db.query(OrgSetting).filter(
                OrgSetting.org_id == org_id,
                OrgSetting.key == key,
            ).first()
            if row and row.value:
                return row.value
        except Exception as e:
            logger.warning(f"Failed to read org setting {key} for org {org_id}: {e}")

    # 2. Global app_settings
    try:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row and row.value:
            return row.value
    except Exception as e:
        logger.warning(f"Failed to read setting {key} from DB: {e}")

    # 3. Env var / default
    return os.getenv(key, default)


def get_user_org_id(db: Session, user_id: UUID) -> Optional[UUID]:
    """Resolve the org_id for a given user (first membership)."""
    try:
        membership = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
        if membership:
            return membership.org_id
    except Exception as e:
        logger.warning(f"Failed to resolve org for user {user_id}: {e}")
    return None
