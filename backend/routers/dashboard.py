"""Dashboard router."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
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

router = APIRouter()


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
    project_id: UUID = None,
    source: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get top leads by score across all projects."""
    
    # Subquery: best LeadScore per member (highest overall_score) to deduplicate
    best_score_sq = db.query(
        LeadScore.member_id,
        func.max(LeadScore.overall_score).label("max_score")
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id
    )
    if project_id:
        best_score_sq = best_score_sq.filter(LeadScore.project_id == project_id)
    best_score_sq = best_score_sq.group_by(LeadScore.member_id).subquery()

    query = db.query(LeadScore, Member, SocialContext, Project.name).join(
        best_score_sq,
        (LeadScore.member_id == best_score_sq.c.member_id) &
        (LeadScore.overall_score == best_score_sq.c.max_score)
    ).join(
        Member, LeadScore.member_id == Member.id
    ).join(
        SocialContext, SocialContext.member_id == Member.id
    ).join(
        Project, LeadScore.project_id == Project.id
    ).filter(
        Project.org_id == org_id,
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    )
    
    if project_id:
        query = query.filter(LeadScore.project_id == project_id)

    if source:
        query = query.filter(
            Member.id.in_(
                db.query(CommunityMember.member_id).join(
                    CommunitySource, CommunityMember.source_id == CommunitySource.id
                ).filter(
                    CommunityMember.role == source
                )
            )
        )
    
    results = query.order_by(desc(LeadScore.overall_score)).limit(limit).all()
    
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
            "source": (db.query(CommunityMember.role).join(
                CommunitySource, CommunityMember.source_id == CommunitySource.id
            ).filter(
                CommunitySource.project_id == lead_score.project_id,
                CommunityMember.member_id == member.id
            ).first() or ('commit',))[0],
        }
        leads.append(lead)
    
    return leads
