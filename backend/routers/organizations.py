"""Organizations router."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user
from org_context import require_org, require_org_admin
from models import User, Organization, OrgMember, OrgBilling, CreditTransaction
from schemas import OrgCreate, OrgResponse, OrgMemberResponse, OrgAddMember

router = APIRouter()


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new organization. The creator becomes the owner."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization slug already exists")

    org = Organization(name=data.name, slug=slug)
    db.add(org)
    db.flush()

    member = OrgMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(member)

    # $5 free grant for new organizations
    from decimal import Decimal
    free_grant = Decimal("5.00")
    billing = OrgBilling(
        org_id=org.id,
        credit_balance=free_grant,
        total_credits_purchased=free_grant,
        total_credits_used=Decimal("0"),
    )
    db.add(billing)
    db.flush()
    grant_txn = CreditTransaction(
        org_id=org.id,
        type="grant",
        amount=free_grant,
        balance_after=free_grant,
        description="Welcome grant — $5.00 free credits",
    )
    db.add(grant_txn)

    db.commit()
    db.refresh(org)

    return OrgResponse(id=str(org.id), name=org.name, slug=org.slug, created_at=org.created_at)


@router.get("", response_model=List[OrgResponse])
async def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List organizations the current user belongs to."""
    memberships = db.query(OrgMember).filter(OrgMember.user_id == current_user.id).all()
    org_ids = [m.org_id for m in memberships]
    if not org_ids:
        return []
    orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
    return [OrgResponse(id=str(o.id), name=o.name, slug=o.slug, created_at=o.created_at) for o in orgs]


@router.get("/{org_id}/members", response_model=List[OrgMemberResponse])
async def list_members(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List members of an organization."""
    # Verify membership
    membership = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_id == current_user.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    members = db.query(OrgMember, User).join(User, OrgMember.user_id == User.id).filter(
        OrgMember.org_id == org_id
    ).all()

    return [
        OrgMemberResponse(
            id=str(m.id),
            user_id=str(u.id),
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m, u in members
    ]


@router.post("/{org_id}/members", response_model=OrgMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    data: OrgAddMember,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a member to an organization (owner/admin only)."""
    caller = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_id == current_user.id,
        OrgMember.role.in_(["owner", "admin"]),
    ).first()
    if not caller:
        raise HTTPException(status_code=403, detail="Only owners/admins can add members")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found with that email")

    existing = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    member = OrgMember(org_id=org_id, user_id=user.id, role=data.role or "member")
    db.add(member)
    db.commit()
    db.refresh(member)

    return OrgMemberResponse(
        id=str(member.id),
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a member from an organization (owner/admin only)."""
    caller = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_id == current_user.id,
        OrgMember.role.in_(["owner", "admin"]),
    ).first()
    if not caller:
        raise HTTPException(status_code=403, detail="Only owners/admins can remove members")

    member = db.query(OrgMember).filter(
        OrgMember.id == member_id,
        OrgMember.org_id == org_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner")

    db.delete(member)
    db.commit()
    return None
