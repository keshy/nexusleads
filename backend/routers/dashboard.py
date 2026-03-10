"""Dashboard router."""
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import (
    User, Project, CommunitySource, Member, LeadScore, 
    SocialContext, SourcingJob, MemberActivity, CommunityMember
)
from schemas import DashboardStats, SourceLeadStats
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

    from sqlalchemy import or_

    exclude_conditions = []
    for domain in excluded_domains:
        exclude_conditions.append(func.coalesce(email_column, '').ilike(f'%@{domain}'))
        exclude_conditions.append(func.coalesce(company_column, '').ilike(f'%{domain.split(".")[0]}%'))
    return query.filter(~or_(*exclude_conditions))


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get overall dashboard statistics."""
    
    # Total projects
    total_projects = db.query(func.count(Project.id)).filter(
        Project.org_id == org_id,
        Project.is_active == True
    ).scalar() or 0
    
    # Total sources
    total_sources = db.query(func.count(CommunitySource.id)).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        CommunitySource.is_active == True
    ).scalar() or 0
    
    # Total members (unique across all projects)
    total_members = db.query(func.count(func.distinct(LeadScore.member_id))).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id
    ).scalar() or 0
    
    # Qualified leads (classified as DECISION_MAKER, KEY_CONTRIBUTOR, or HIGH_IMPACT)
    qualified_leads = db.query(func.count(func.distinct(SocialContext.member_id))).join(
        LeadScore, LeadScore.member_id == SocialContext.member_id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    ).scalar() or 0
    
    # Get classification counts
    decision_makers = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.member_id == SocialContext.member_id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'DECISION_MAKER'
    ).scalar() or 0
    
    key_contributors = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.member_id == SocialContext.member_id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'KEY_CONTRIBUTOR'
    ).scalar() or 0
    
    high_impact = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.member_id == SocialContext.member_id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'HIGH_IMPACT'
    ).scalar() or 0
    
    # Job statistics
    active_jobs = db.query(func.count(SourcingJob.id)).join(
        Project, SourcingJob.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SourcingJob.status.in_(['pending', 'running'])
    ).scalar() or 0
    
    pending_jobs = db.query(func.count(SourcingJob.id)).join(
        Project, SourcingJob.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SourcingJob.status == 'pending'
    ).scalar() or 0
    
    today = datetime.utcnow().date()
    completed_jobs_today = db.query(func.count(SourcingJob.id)).join(
        Project, SourcingJob.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SourcingJob.status == 'completed',
        func.date(SourcingJob.completed_at) == today
    ).scalar() or 0
    
    return DashboardStats(
        total_projects=total_projects,
        total_sources=total_sources,
        total_members=total_members,
        qualified_leads=qualified_leads,
        decision_makers=decision_makers,
        key_contributors=key_contributors,
        high_impact=high_impact,
        active_jobs=active_jobs,
        pending_jobs=pending_jobs,
        completed_jobs_today=completed_jobs_today
    )


@router.get("/sources/stats", response_model=List[SourceLeadStats])
async def get_source_stats(
    project_id: UUID = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get lead statistics by community source."""
    
    # Build query
    query = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        CommunitySource.is_active == True
    )
    
    if project_id:
        query = query.filter(CommunitySource.project_id == project_id)
    
    sources = query.order_by(desc(CommunitySource.stars)).limit(limit).all()
    
    result = []
    for src in sources:
        # Total members for this source
        total_members = db.query(func.count(func.distinct(MemberActivity.member_id))).filter(
            MemberActivity.source_id == src.id
        ).scalar() or 0
        
        # Get qualified leads through project
        qualified_leads = db.query(func.count(func.distinct(LeadScore.member_id))).join(
            MemberActivity, LeadScore.member_id == MemberActivity.member_id
        ).filter(
            MemberActivity.source_id == src.id,
            LeadScore.project_id == src.project_id,
            LeadScore.is_qualified_lead == True
        ).scalar() or 0
        
        # Classification counts
        decision_makers = db.query(func.count(func.distinct(SocialContext.member_id))).join(
            MemberActivity, SocialContext.member_id == MemberActivity.member_id
        ).filter(
            MemberActivity.source_id == src.id,
            SocialContext.classification == 'DECISION_MAKER'
        ).scalar() or 0
        
        key_contributors_count = db.query(func.count(func.distinct(SocialContext.member_id))).join(
            MemberActivity, SocialContext.member_id == MemberActivity.member_id
        ).filter(
            MemberActivity.source_id == src.id,
            SocialContext.classification == 'KEY_CONTRIBUTOR'
        ).scalar() or 0
        
        high_impact_count = db.query(func.count(func.distinct(SocialContext.member_id))).join(
            MemberActivity, SocialContext.member_id == MemberActivity.member_id
        ).filter(
            MemberActivity.source_id == src.id,
            SocialContext.classification == 'HIGH_IMPACT'
        ).scalar() or 0
        
        result.append(SourceLeadStats(
            source_id=src.id,
            source_name=src.full_name,
            source_type=src.source_type,
            total_members=total_members,
            qualified_leads=qualified_leads,
            decision_makers=decision_makers,
            key_contributors=key_contributors_count,
            high_impact=high_impact_count
        ))
    
    return result


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get recent activity feed."""
    
    # Get recent jobs
    recent_jobs = db.query(SourcingJob).join(
        Project, SourcingJob.project_id == Project.id
    ).filter(
        Project.org_id == org_id
    ).order_by(desc(SourcingJob.created_at)).limit(limit).all()
    
    activities = []
    for job in recent_jobs:
        activity = {
            "id": str(job.id),
            "type": job.job_type,
            "status": job.status,
            "timestamp": job.created_at.isoformat(),
            "progress": float(job.progress_percentage),
            "project_id": str(job.project_id) if job.project_id else None,
            "source_id": str(job.source_id) if job.source_id else None
        }
        
        if job.source_id:
            src = db.query(CommunitySource).filter(CommunitySource.id == job.source_id).first()
            if src:
                activity["source_name"] = src.full_name
                activity["source_type"] = src.source_type
        
        activities.append(activity)
    
    return activities


@router.get("/top-leads")
async def get_top_leads(
    project_id: list[UUID] | None = Query(None),
    project_mode: Literal["include", "exclude"] = "include",
    source: list[str] | None = Query(None),
    source_mode: Literal["include", "exclude"] = "include",
    classification: list[str] | None = Query(None),
    classification_mode: Literal["include", "exclude"] = "include",
    industry: list[str] | None = Query(None),
    industry_mode: Literal["include", "exclude"] = "include",
    company: list[str] | None = Query(None),
    company_mode: Literal["include", "exclude"] = "include",
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get top leads by score across all projects."""
    
    # Exclude members from excluded organizations
    excluded_domains = get_excluded_organizations(db, org_id)
    
    # Subquery: best LeadScore per member (highest overall_score) to deduplicate.
    # Use row_number to guarantee exactly one row per member.
    from sqlalchemy import over, literal_column
    from sqlalchemy.sql.expression import text as sql_text

    project_scope = db.query(Project.id).filter(Project.org_id == org_id)
    if project_id:
        if project_mode == "exclude":
            project_scope = project_scope.filter(~Project.id.in_(project_id))
        else:
            project_scope = project_scope.filter(Project.id.in_(project_id))

    base_q = db.query(
        LeadScore.id.label("ls_id"),
        func.row_number().over(
            partition_by=LeadScore.member_id,
            order_by=desc(LeadScore.overall_score)
        ).label("rn")
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        LeadScore.project_id.in_(project_scope)
    )
    best_sq = base_q.subquery()

    query = db.query(LeadScore, Member, SocialContext, Project.name).join(
        best_sq,
        (LeadScore.id == best_sq.c.ls_id) & (best_sq.c.rn == 1)
    ).join(
        Member, LeadScore.member_id == Member.id
    ).join(
        SocialContext, SocialContext.member_id == Member.id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        LeadScore.project_id.in_(project_scope),
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    )

    if source:
        source_member_ids = db.query(MemberActivity.member_id).join(
            CommunitySource, MemberActivity.source_id == CommunitySource.id
        ).filter(
            CommunitySource.project_id.in_(project_scope),
            MemberActivity.source.in_(source)
        )
        query = query.filter(
            Member.id.in_(source_member_ids)
            if source_mode == "include"
            else ~Member.id.in_(source_member_ids)
        )

    query = apply_value_filter(query, SocialContext.classification, classification, classification_mode)
    query = apply_value_filter(query, SocialContext.industry, industry, industry_mode)
    query = apply_value_filter(query, func.coalesce(SocialContext.current_company, Member.company), company, company_mode)
    
    # Exclude members from excluded organizations (match on email domain or company name)
    query = apply_excluded_org_filter(query, Member.email, SocialContext.current_company, excluded_domains)
    
    results = query.order_by(desc(LeadScore.overall_score)).limit(limit).all()
    
    # Batch-load owners for all results
    owner_ids = {ls.owner_id for ls, _, _, _ in results if ls.owner_id}
    owner_map = {}
    if owner_ids:
        owners = db.query(User).filter(User.id.in_(owner_ids)).all()
        owner_map = {u.id: {"id": str(u.id), "username": u.username, "full_name": u.full_name} for u in owners}

    leads = []
    for lead_score, member, social_context, project_name in results:
        lead = {
            "id": str(lead_score.id),
            "username": member.username,
            "full_name": member.full_name,
            "company": member.company,
            "bio": member.bio,
            "avatar_url": member.avatar_url,
            "email": member.email,
            "overall_score": float(lead_score.overall_score) if lead_score.overall_score else 0,
            "activity_score": float(lead_score.activity_score) if lead_score.activity_score else 0,
            "influence_score": float(lead_score.influence_score) if lead_score.influence_score else 0,
            "position_score": float(lead_score.position_score) if lead_score.position_score else 0,
            "engagement_score": float(lead_score.engagement_score) if lead_score.engagement_score else 0,
            "priority": lead_score.priority,
            "project_name": project_name,
            "classification": social_context.classification if social_context else None,
            "classification_reasoning": social_context.classification_reasoning if social_context else None,
            "current_position": social_context.current_position if social_context else None,
            "current_company": social_context.current_company if social_context else member.company,
            "industry": social_context.industry if social_context else None,
            "linkedin_url": social_context.linkedin_url if social_context else None,
            "linkedin_profile_photo_url": social_context.linkedin_profile_photo_url if social_context else None,
            "source": (db.query(MemberActivity.source).join(
                CommunitySource, MemberActivity.source_id == CommunitySource.id
            ).filter(
                CommunitySource.project_id == lead_score.project_id,
                MemberActivity.member_id == member.id
            ).first() or ('commit',))[0],
            "owner": owner_map.get(lead_score.owner_id),
        }
        leads.append(lead)
    
    return leads
