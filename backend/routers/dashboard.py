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
    User, Project, Repository, Contributor, LeadScore, 
    SocialContext, SourcingJob, ContributorStats
)
from schemas import DashboardStats, RepositoryLeadStats

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
    
    # Total repositories
    total_repositories = db.query(func.count(Repository.id)).join(Project).filter(
        Project.org_id == org_id,
        Repository.is_active == True
    ).scalar() or 0
    
    # Total contributors (unique across all projects)
    total_contributors = db.query(func.count(func.distinct(LeadScore.contributor_id))).join(Project).filter(
        Project.org_id == org_id
    ).scalar() or 0
    
    # Qualified leads (classified as DECISION_MAKER, KEY_CONTRIBUTOR, or HIGH_IMPACT)
    qualified_leads = db.query(func.count(func.distinct(SocialContext.contributor_id))).join(
        LeadScore, LeadScore.contributor_id == SocialContext.contributor_id
    ).join(Project).filter(
        Project.org_id == org_id,
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    ).scalar() or 0
    
    # Get classification counts
    decision_makers = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.contributor_id == SocialContext.contributor_id
    ).join(Project).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'DECISION_MAKER'
    ).scalar() or 0
    
    key_contributors = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.contributor_id == SocialContext.contributor_id
    ).join(Project).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'KEY_CONTRIBUTOR'
    ).scalar() or 0
    
    high_impact = db.query(func.count(SocialContext.id)).join(
        LeadScore, LeadScore.contributor_id == SocialContext.contributor_id
    ).join(Project).filter(
        Project.org_id == org_id,
        SocialContext.classification == 'HIGH_IMPACT'
    ).scalar() or 0
    
    # Job statistics
    active_jobs = db.query(func.count(SourcingJob.id)).join(Project).filter(
        Project.org_id == org_id,
        SourcingJob.status.in_(['pending', 'running'])
    ).scalar() or 0
    
    pending_jobs = db.query(func.count(SourcingJob.id)).join(Project).filter(
        Project.org_id == org_id,
        SourcingJob.status == 'pending'
    ).scalar() or 0
    
    today = datetime.utcnow().date()
    completed_jobs_today = db.query(func.count(SourcingJob.id)).join(Project).filter(
        Project.org_id == org_id,
        SourcingJob.status == 'completed',
        func.date(SourcingJob.completed_at) == today
    ).scalar() or 0
    
    return DashboardStats(
        total_projects=total_projects,
        total_repositories=total_repositories,
        total_contributors=total_contributors,
        qualified_leads=qualified_leads,
        decision_makers=decision_makers,
        key_contributors=key_contributors,
        high_impact=high_impact,
        active_jobs=active_jobs,
        pending_jobs=pending_jobs,
        completed_jobs_today=completed_jobs_today
    )


@router.get("/repositories/stats", response_model=List[RepositoryLeadStats])
async def get_repository_stats(
    project_id: UUID = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get lead statistics by repository."""
    
    # Build query
    query = db.query(Repository).join(Project).filter(
        Project.org_id == org_id,
        Repository.is_active == True
    )
    
    if project_id:
        query = query.filter(Repository.project_id == project_id)
    
    repositories = query.order_by(desc(Repository.stars)).limit(limit).all()
    
    result = []
    for repo in repositories:
        # Total contributors for this repo
        total_contributors = db.query(func.count(func.distinct(ContributorStats.contributor_id))).filter(
            ContributorStats.repository_id == repo.id
        ).scalar() or 0
        
        # Get qualified leads through project
        qualified_leads = db.query(func.count(func.distinct(LeadScore.contributor_id))).join(
            ContributorStats, LeadScore.contributor_id == ContributorStats.contributor_id
        ).filter(
            ContributorStats.repository_id == repo.id,
            LeadScore.project_id == repo.project_id,
            LeadScore.is_qualified_lead == True
        ).scalar() or 0
        
        # Classification counts
        decision_makers = db.query(func.count(func.distinct(SocialContext.contributor_id))).join(
            ContributorStats, SocialContext.contributor_id == ContributorStats.contributor_id
        ).filter(
            ContributorStats.repository_id == repo.id,
            SocialContext.classification == 'DECISION_MAKER'
        ).scalar() or 0
        
        key_contributors_count = db.query(func.count(func.distinct(SocialContext.contributor_id))).join(
            ContributorStats, SocialContext.contributor_id == ContributorStats.contributor_id
        ).filter(
            ContributorStats.repository_id == repo.id,
            SocialContext.classification == 'KEY_CONTRIBUTOR'
        ).scalar() or 0
        
        high_impact_count = db.query(func.count(func.distinct(SocialContext.contributor_id))).join(
            ContributorStats, SocialContext.contributor_id == ContributorStats.contributor_id
        ).filter(
            ContributorStats.repository_id == repo.id,
            SocialContext.classification == 'HIGH_IMPACT'
        ).scalar() or 0
        
        result.append(RepositoryLeadStats(
            repository_id=repo.id,
            repository_name=repo.full_name,
            total_contributors=total_contributors,
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
    recent_jobs = db.query(SourcingJob).join(Project).filter(
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
            "repository_id": str(job.repository_id) if job.repository_id else None
        }
        
        if job.repository_id:
            repo = db.query(Repository).filter(Repository.id == job.repository_id).first()
            if repo:
                activity["repository_name"] = repo.full_name
        
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
    
    query = db.query(LeadScore, Contributor, SocialContext, Project.name).join(
        Contributor, LeadScore.contributor_id == Contributor.id
    ).join(
        SocialContext, SocialContext.contributor_id == Contributor.id
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
            Contributor.id.in_(
                db.query(ContributorStats.contributor_id).join(Repository).filter(
                    ContributorStats.source == source
                )
            )
        )
    
    results = query.order_by(desc(LeadScore.overall_score)).limit(limit).all()
    
    leads = []
    for lead_score, contributor, social_context, project_name in results:
        lead = {
            "id": str(contributor.id),
            "username": contributor.username,
            "full_name": contributor.full_name,
            "company": contributor.company,
            "bio": contributor.bio,
            "avatar_url": contributor.avatar_url,
            "email": contributor.email,
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
            "current_company": social_context.current_company if social_context else contributor.company,
            "industry": social_context.industry if social_context else None,
            "linkedin_url": social_context.linkedin_url if social_context else None,
            "linkedin_profile_photo_url": social_context.linkedin_profile_photo_url if social_context else None,
            "source": (db.query(ContributorStats.source).join(Repository).filter(
                Repository.project_id == lead_score.project_id,
                ContributorStats.contributor_id == contributor.id
            ).first() or ('commit',))[0],
        }
        leads.append(lead)
    
    return leads
