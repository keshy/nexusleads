"""Shared org-context helpers used by all routers."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user
from models import User, OrgMember


async def require_org(
    x_org_id: str = Header(None, alias="X-Org-Id"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Resolve and validate the org from X-Org-Id header."""
    if not x_org_id:
        # Fall back to user's first org
        member = db.query(OrgMember).filter(OrgMember.user_id == current_user.id).first()
        if not member:
            raise HTTPException(status_code=400, detail="No organization found for user")
        return member.org_id

    # Validate user belongs to this org
    member = db.query(OrgMember).filter(
        OrgMember.user_id == current_user.id,
        OrgMember.org_id == x_org_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return member.org_id


async def require_org_admin(
    x_org_id: str = Header(None, alias="X-Org-Id"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Require org membership with owner or admin role."""
    if not x_org_id:
        member = db.query(OrgMember).filter(OrgMember.user_id == current_user.id).first()
        if not member:
            raise HTTPException(status_code=400, detail="No organization found for user")
        x_org_id = str(member.org_id)

    member = db.query(OrgMember).filter(
        OrgMember.user_id == current_user.id,
        OrgMember.org_id == x_org_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin or owner role required")
    return member.org_id
