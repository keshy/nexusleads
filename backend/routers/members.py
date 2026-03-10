"""Members router (generalized from contributors)."""
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, or_
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import (
    User, Member, MemberActivity, SocialContext,
    LeadScore, Project, CommunitySource, CommunityMember,
    ClayPushLog
)
from schemas import (
    MemberResponse, LeadDetail, MemberActivityResponse,
    SocialContextResponse, LeadScoreResponse
)
from datetime import datetime
from settings_service import get_excluded_organizations

router = APIRouter()

def apply_value_filter(query, column, values: list[str] | None, mode: Literal["include", "exclude"]):
    if not values:
        return query
    if mode == "exclude":
        return query.filter((column.is_(None)) | (~column.in_(values)))
    return query.filter(column.in_(values))


def apply_excluded_org_filter(query, email_column, company_column, excluded_domains: list[str]):
    if not excluded_domains:
        return query

    exclude_conditions = []
    for domain in excluded_domains:
        exclude_conditions.append(func.coalesce(email_column, '').ilike(f'%@{domain}'))
        exclude_conditions.append(func.coalesce(company_column, '').ilike(f'%{domain.split(".")[0]}%'))
    return query.filter(~or_(*exclude_conditions))

def aggregate_activity_rows(member_id: UUID, activity_rows: List[MemberActivity]) -> MemberActivityResponse | None:
    """Aggregate member activity across sources."""
    if not activity_rows:
        return None

    aggregated = {
        "total_commits": 0,
        "commits_last_3_months": 0,
        "commits_last_6_months": 0,
        "commits_last_year": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "pull_requests": 0,
        "issues_opened": 0,
        "issues_closed": 0,
        "code_reviews": 0,
        "is_maintainer": False,
        "is_core_team": False,
        "first_commit_date": None,
        "last_commit_date": None,
        "calculated_at": None,
    }

    for row in activity_rows:
        aggregated["total_commits"] += row.total_commits or 0
        aggregated["commits_last_3_months"] += row.commits_last_3_months or 0
        aggregated["commits_last_6_months"] += row.commits_last_6_months or 0
        aggregated["commits_last_year"] += row.commits_last_year or 0
        aggregated["lines_added"] += row.lines_added or 0
        aggregated["lines_deleted"] += row.lines_deleted or 0
        aggregated["pull_requests"] += row.pull_requests or 0
        aggregated["issues_opened"] += row.issues_opened or 0
        aggregated["issues_closed"] += row.issues_closed or 0
        aggregated["code_reviews"] += row.code_reviews or 0
        aggregated["is_maintainer"] = aggregated["is_maintainer"] or bool(row.is_maintainer)
        aggregated["is_core_team"] = aggregated["is_core_team"] or bool(row.is_core_team)
        if row.first_commit_date:
            aggregated["first_commit_date"] = min(aggregated["first_commit_date"], row.first_commit_date) if aggregated["first_commit_date"] else row.first_commit_date
        if row.last_commit_date:
            aggregated["last_commit_date"] = max(aggregated["last_commit_date"], row.last_commit_date) if aggregated["last_commit_date"] else row.last_commit_date
        if row.calculated_at:
            aggregated["calculated_at"] = max(aggregated["calculated_at"], row.calculated_at) if aggregated["calculated_at"] else row.calculated_at

    final_calculated_at = aggregated.pop("calculated_at") or datetime.utcnow()
    return MemberActivityResponse(
        id=None,
        source_id=None,
        member_id=member_id,
        activity_type='commit',
        calculated_at=final_calculated_at,
        **aggregated
    )


@router.get("/by-project", response_model=List[dict])
async def get_leads_by_project(
    source: list[str] | None = Query(None),
    source_mode: Literal["include", "exclude"] = "include",
    classification: list[str] | None = Query(None),
    classification_mode: Literal["include", "exclude"] = "include",
    industry: list[str] | None = Query(None),
    industry_mode: Literal["include", "exclude"] = "include",
    company: list[str] | None = Query(None),
    company_mode: Literal["include", "exclude"] = "include",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get all leads organized by project."""
    excluded_domains = get_excluded_organizations(db, org_id)

    projects = db.query(Project).filter(
        Project.org_id == org_id,
        Project.is_active == True
    ).all()
    
    result = []
    for project in projects:
        # Get top leads for this project
        leads_query = db.query(Member, SocialContext, LeadScore)\
            .join(LeadScore, LeadScore.member_id == Member.id)\
            .join(SocialContext, SocialContext.member_id == Member.id)\
            .filter(
                LeadScore.project_id == project.id,
                SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
            )

        # Exclude members from excluded organizations
        leads_query = apply_excluded_org_filter(leads_query, Member.email, SocialContext.current_company, excluded_domains)

        if source:
            source_member_ids = db.query(MemberActivity.member_id).join(
                CommunitySource, MemberActivity.source_id == CommunitySource.id
            ).filter(
                CommunitySource.project_id == project.id,
                MemberActivity.source.in_(source)
            )
            leads_query = leads_query.filter(
                Member.id.in_(source_member_ids)
                if source_mode == "include"
                else ~Member.id.in_(source_member_ids)
            )

        leads_query = apply_value_filter(leads_query, SocialContext.classification, classification, classification_mode)
        leads_query = apply_value_filter(leads_query, SocialContext.industry, industry, industry_mode)
        leads_query = apply_value_filter(leads_query, func.coalesce(SocialContext.current_company, Member.company), company, company_mode)

        leads = leads_query.order_by(desc(LeadScore.overall_score))\
            .limit(50)\
            .all()
        
        # Helper to get source for a member in this project's sources
        def get_source(member_id):
            ma = db.query(MemberActivity.source).join(
                CommunitySource, MemberActivity.source_id == CommunitySource.id
            ).filter(
                CommunitySource.project_id == project.id,
                MemberActivity.member_id == member_id
            ).first()
            return ma[0] if ma else 'contributor'

        # Helper to check if a member was pushed to Clay
        def get_clay_pushed_at(member_id):
            log = db.query(ClayPushLog.pushed_at).filter(
                ClayPushLog.org_id == org_id,
                ClayPushLog.member_id == member_id,
                ClayPushLog.status == 'success'
            ).order_by(desc(ClayPushLog.pushed_at)).first()
            return log[0].isoformat() if log else None

        # Batch-load owners for this project's leads
        all_leads_and_others = list(leads)
        all_owner_ids = {ls.owner_id for _, _, ls in all_leads_and_others if ls.owner_id}

        # Build leads list
        leads_list = []
        for member, social_context, lead_score in leads:
            leads_list.append({
                "id": str(member.id),
                "lead_score_id": str(lead_score.id),
                "full_name": member.full_name,
                "username": member.username,
                "email": member.email,
                "avatar_url": member.avatar_url,
                "company": member.company,
                "bio": member.bio,
                "current_company": social_context.current_company if social_context else member.company,
                "current_position": social_context.current_position if social_context else None,
                "industry": social_context.industry if social_context else None,
                "linkedin_url": social_context.linkedin_url if social_context else None,
                "linkedin_profile_photo_url": social_context.linkedin_profile_photo_url if social_context else None,
                "classification": social_context.classification if social_context else None,
                "classification_reasoning": social_context.classification_reasoning if social_context else None,
                "overall_score": float(lead_score.overall_score) if lead_score and lead_score.overall_score else None,
                "activity_score": float(lead_score.activity_score) if lead_score and lead_score.activity_score else 0,
                "influence_score": float(lead_score.influence_score) if lead_score and lead_score.influence_score else 0,
                "position_score": float(lead_score.position_score) if lead_score and lead_score.position_score else 0,
                "engagement_score": float(lead_score.engagement_score) if lead_score and lead_score.engagement_score else 0,
                "source": get_source(member.id),
                "clay_pushed_at": get_clay_pushed_at(member.id),
                "owner_id": str(lead_score.owner_id) if lead_score.owner_id else None,
            })
        
        # Get other members (KEY_CONTRIBUTOR or unclassified)
        lead_member_ids = [l["id"] for l in leads_list]
        others_query = db.query(Member, SocialContext, LeadScore)\
            .join(LeadScore, LeadScore.member_id == Member.id)\
            .outerjoin(SocialContext, SocialContext.member_id == Member.id)\
            .filter(
                LeadScore.project_id == project.id,
                ~Member.id.in_([l["id"] for l in leads_list]) if leads_list else True
            )

        others_query = apply_excluded_org_filter(others_query, Member.email, SocialContext.current_company, excluded_domains)

        others_query = others_query.order_by(desc(LeadScore.overall_score))\
            .limit(100)\
            .all()

        contributors_list = []
        for member, social_context, lead_score in others_query:
            if str(member.id) in lead_member_ids:
                continue
            all_owner_ids.add(lead_score.owner_id) if lead_score.owner_id else None
            contributors_list.append({
                "id": str(member.id),
                "lead_score_id": str(lead_score.id),
                "full_name": member.full_name,
                "username": member.username,
                "email": member.email,
                "avatar_url": member.avatar_url,
                "company": member.company,
                "bio": member.bio,
                "current_company": social_context.current_company if social_context else member.company,
                "current_position": social_context.current_position if social_context else None,
                "industry": social_context.industry if social_context else None,
                "linkedin_url": social_context.linkedin_url if social_context else None,
                "linkedin_profile_photo_url": social_context.linkedin_profile_photo_url if social_context else None,
                "classification": social_context.classification if social_context else None,
                "classification_reasoning": social_context.classification_reasoning if social_context else None,
                "overall_score": float(lead_score.overall_score) if lead_score and lead_score.overall_score else 0,
                "activity_score": float(lead_score.activity_score) if lead_score and lead_score.activity_score else 0,
                "influence_score": float(lead_score.influence_score) if lead_score and lead_score.influence_score else 0,
                "position_score": float(lead_score.position_score) if lead_score and lead_score.position_score else 0,
                "engagement_score": float(lead_score.engagement_score) if lead_score and lead_score.engagement_score else 0,
                "source": get_source(member.id),
                "clay_pushed_at": get_clay_pushed_at(member.id),
                "owner_id": str(lead_score.owner_id) if lead_score.owner_id else None,
            })

        # Batch-load owner info for this project
        owner_map = {}
        if all_owner_ids:
            owners = db.query(User).filter(User.id.in_(all_owner_ids)).all()
            owner_map = {str(u.id): {"id": str(u.id), "username": u.username, "full_name": u.full_name} for u in owners}

        result.append({
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "leads": leads_list,
            "contributors": contributors_list,
            "owners": owner_map,
        })
    
    return result


@router.get("/", response_model=List[LeadDetail])
async def list_members(
    project_id: UUID = None,
    source_id: UUID = None,
    classification: str = Query(None),
    qualified_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List members with filtering options."""
    access_query = db.query(CommunityMember.id).join(
        CommunitySource, CommunityMember.source_id == CommunitySource.id
    ).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunityMember.member_id == Member.id,
        Project.org_id == org_id
    )
    
    # Filter by project
    if project_id:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.org_id == org_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        access_query = access_query.filter(CommunitySource.project_id == project_id)
    
    # Filter by source
    if source_id:
        access_query = access_query.filter(CommunitySource.id == source_id)

    query = db.query(Member).filter(access_query.exists())
    
    # Filter by classification
    if classification:
        query = query.join(SocialContext).filter(
            SocialContext.classification == classification
        )
    
    # Filter qualified leads
    lead_score_join = None
    if project_id:
        lead_score_join = and_(
            LeadScore.member_id == Member.id,
            LeadScore.project_id == project_id
        )
        query = query.outerjoin(LeadScore, lead_score_join)
        if qualified_only:
            query = query.filter(LeadScore.is_qualified_lead.is_(True))
    
    # Order by lead score if project specified
    if project_id:
        query = query.order_by(desc(LeadScore.overall_score))
    
    members = query.offset(skip).limit(limit).all()

    member_ids = [m.id for m in members]

    social_context_map = {
        sc.member_id: sc for sc in db.query(SocialContext).filter(
            SocialContext.member_id.in_(member_ids)
        ).all()
    } if member_ids else {}

    lead_score_map = {}
    if project_id and member_ids:
        lead_scores = db.query(LeadScore).filter(
            LeadScore.project_id == project_id,
            LeadScore.member_id.in_(member_ids)
        ).all()
        lead_score_map = {ls.member_id: ls for ls in lead_scores}

    activity_map: dict[UUID, MemberActivityResponse] = {}
    if member_ids:
        if source_id:
            activity_rows = db.query(MemberActivity).filter(
                MemberActivity.source_id == source_id,
                MemberActivity.member_id.in_(member_ids)
            ).all()
            activity_map = {row.member_id: MemberActivityResponse.from_orm(row) for row in activity_rows}
        else:
            activity_query = db.query(MemberActivity).join(
                CommunitySource, MemberActivity.source_id == CommunitySource.id
            ).join(
                Project, CommunitySource.project_id == Project.id
            ).filter(
                MemberActivity.member_id.in_(member_ids),
                Project.org_id == org_id
            )
            if project_id:
                activity_query = activity_query.filter(CommunitySource.project_id == project_id)
            activity_rows = activity_query.all()
            rows_by_member: dict[UUID, List[MemberActivity]] = {}
            for row in activity_rows:
                rows_by_member.setdefault(row.member_id, []).append(row)
            activity_map = {
                mid: aggregate_activity_rows(mid, rows)
                for mid, rows in rows_by_member.items()
            }

    # Build detailed response
    result = []
    for member in members:
        activity = activity_map.get(member.id)
        social_context = social_context_map.get(member.id)
        lead_score = lead_score_map.get(member.id)

        result.append(LeadDetail(
            member=MemberResponse.from_orm(member),
            stats=activity,
            social_context=SocialContextResponse.from_orm(social_context) if social_context else None,
            lead_score=LeadScoreResponse.from_orm(lead_score) if lead_score else None
        ))

    return result


@router.get("/{member_id}", response_model=LeadDetail)
async def get_member(
    member_id: UUID,
    project_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get detailed information about a member."""
    member = db.query(Member).filter(
        Member.id == member_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    access_query = db.query(CommunityMember).join(
        CommunitySource, CommunityMember.source_id == CommunitySource.id
    ).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunityMember.member_id == member_id,
        Project.org_id == org_id
    )
    if project_id:
        access_query = access_query.filter(Project.id == project_id)
    if not access_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    activity = None
    if project_id:
        activity_rows = db.query(MemberActivity).join(
            CommunitySource, MemberActivity.source_id == CommunitySource.id
        ).filter(
            CommunitySource.project_id == project_id,
            MemberActivity.member_id == member_id
        ).all()
        activity = aggregate_activity_rows(member_id, activity_rows)
    else:
        activity_rows = db.query(MemberActivity).join(
            CommunitySource, MemberActivity.source_id == CommunitySource.id
        ).join(
            Project, CommunitySource.project_id == Project.id
        ).filter(
            Project.org_id == org_id,
            MemberActivity.member_id == member_id
        ).all()
        activity = aggregate_activity_rows(member_id, activity_rows)
    
    # Get social context
    social_context = db.query(SocialContext).filter(
        SocialContext.member_id == member_id
    ).first()
    
    # Get lead score (if project specified)
    lead_score = None
    if project_id:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.org_id == org_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        lead_score = db.query(LeadScore).filter(
            LeadScore.member_id == member_id,
            LeadScore.project_id == project_id
        ).first()
    
    return LeadDetail(
        member=MemberResponse.from_orm(member),
        stats=activity,
        social_context=SocialContextResponse.from_orm(social_context) if social_context else None,
        lead_score=LeadScoreResponse.from_orm(lead_score) if lead_score else None
    )


@router.post("/{member_id}/enrich")
async def enrich_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger social enrichment for a member."""
    member = db.query(Member).filter(
        Member.id == member_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    access_query = db.query(CommunityMember).join(
        CommunitySource, CommunityMember.source_id == CommunitySource.id
    ).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunityMember.member_id == member_id,
        Project.org_id == org_id
    )
    if not access_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Create enrichment job
    from models import SourcingJob
    
    job = SourcingJob(
        job_type='social_enrichment',
        status='pending',
        job_metadata={'contributor_id': str(member_id)},
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {"message": "Enrichment job created", "job_id": str(job.id)}


@router.post("/assign-owner")
async def assign_lead_owner(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Assign an owner to one or more leads (lead_score records).
    
    Body: { "lead_score_ids": [uuid, ...], "owner_id": uuid | null }
    owner_id=null removes the assignment.
    """
    from models import OrgMember

    lead_score_ids = payload.get("lead_score_ids", [])
    owner_id = payload.get("owner_id")  # None = unassign

    if not lead_score_ids:
        raise HTTPException(status_code=400, detail="lead_score_ids is required")

    # Validate owner belongs to the org (if assigning)
    if owner_id:
        owner_member = db.query(OrgMember).filter(
            OrgMember.org_id == org_id,
            OrgMember.user_id == owner_id,
        ).first()
        if not owner_member:
            raise HTTPException(status_code=400, detail="Owner is not a member of this organization")

    # Update lead_scores — only those belonging to projects in the caller's org
    updated = db.query(LeadScore).filter(
        LeadScore.id.in_(lead_score_ids),
        LeadScore.project_id.in_(
            db.query(Project.id).filter(Project.org_id == org_id)
        )
    ).update({LeadScore.owner_id: owner_id}, synchronize_session="fetch")

    db.commit()
    return {"updated": updated}
