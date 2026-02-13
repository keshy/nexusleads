"""Contributors router."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import (
    User, Contributor, ContributorStats, SocialContext, 
    LeadScore, Project, Repository, RepositoryContributor,
    ClayPushLog
)
from schemas import (
    ContributorResponse, LeadDetail, ContributorStatsResponse,
    SocialContextResponse, LeadScoreResponse
)
from datetime import datetime

router = APIRouter()

def aggregate_stats_rows(contributor_id: UUID, stats_rows: List[ContributorStats]) -> ContributorStatsResponse | None:
    """Aggregate contributor stats across repositories."""
    if not stats_rows:
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

    for row in stats_rows:
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

    return ContributorStatsResponse(
        id=None,
        repository_id=None,
        contributor_id=contributor_id,
        calculated_at=aggregated["calculated_at"] or datetime.utcnow(),
        **aggregated
    )


@router.get("/by-project", response_model=List[dict])
async def get_leads_by_project(
    source: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get all leads organized by project."""
    # Get all user's projects
    projects = db.query(Project).filter(
        Project.org_id == org_id,
        Project.is_active == True
    ).all()
    
    result = []
    for project in projects:
        # Get top leads for this project
        leads_query = db.query(Contributor, SocialContext, LeadScore)\
            .join(LeadScore, LeadScore.contributor_id == Contributor.id)\
            .join(SocialContext, SocialContext.contributor_id == Contributor.id)\
            .filter(
                LeadScore.project_id == project.id,
                SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
            )

        if source:
            leads_query = leads_query.filter(
                Contributor.id.in_(
                    db.query(ContributorStats.contributor_id).join(Repository).filter(
                        Repository.project_id == project.id,
                        ContributorStats.source == source
                    )
                )
            )

        leads = leads_query.order_by(desc(LeadScore.overall_score))\
            .limit(50)\
            .all()
        
        # Helper to get source for a contributor in this project's repos
        def get_source(contributor_id):
            stat = db.query(ContributorStats.source).join(Repository).filter(
                Repository.project_id == project.id,
                ContributorStats.contributor_id == contributor_id
            ).first()
            return stat[0] if stat else 'commit'

        # Helper to check if a contributor was pushed to Clay
        def get_clay_pushed_at(contributor_id):
            log = db.query(ClayPushLog.pushed_at).filter(
                ClayPushLog.org_id == org_id,
                ClayPushLog.contributor_id == contributor_id,
                ClayPushLog.status == 'success'
            ).order_by(desc(ClayPushLog.pushed_at)).first()
            return log[0].isoformat() if log else None

        # Build leads list
        leads_list = []
        for contributor, social_context, lead_score in leads:
            leads_list.append({
                "id": str(contributor.id),
                "full_name": contributor.full_name,
                "username": contributor.username,
                "email": contributor.email,
                "avatar_url": contributor.avatar_url,
                "company": contributor.company,
                "bio": contributor.bio,
                "current_company": social_context.current_company if social_context else contributor.company,
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
                "source": get_source(contributor.id),
                "clay_pushed_at": get_clay_pushed_at(contributor.id)
            })
        
        # Get other contributors (KEY_CONTRIBUTOR or unclassified)
        lead_contributor_ids = [l["id"] for l in leads_list]
        others_query = db.query(Contributor, SocialContext, LeadScore)\
            .join(LeadScore, LeadScore.contributor_id == Contributor.id)\
            .outerjoin(SocialContext, SocialContext.contributor_id == Contributor.id)\
            .filter(
                LeadScore.project_id == project.id,
                ~Contributor.id.in_([l["id"] for l in leads_list]) if leads_list else True
            )\
            .order_by(desc(LeadScore.overall_score))\
            .limit(100)\
            .all()

        contributors_list = []
        for contributor, social_context, lead_score in others_query:
            if str(contributor.id) in lead_contributor_ids:
                continue
            contributors_list.append({
                "id": str(contributor.id),
                "full_name": contributor.full_name,
                "username": contributor.username,
                "email": contributor.email,
                "avatar_url": contributor.avatar_url,
                "company": contributor.company,
                "bio": contributor.bio,
                "current_company": social_context.current_company if social_context else contributor.company,
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
                "source": get_source(contributor.id),
                "clay_pushed_at": get_clay_pushed_at(contributor.id)
            })

        result.append({
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "leads": leads_list,
            "contributors": contributors_list
        })
    
    return result


@router.get("/", response_model=List[LeadDetail])
async def list_contributors(
    project_id: UUID = None,
    repository_id: UUID = None,
    classification: str = Query(None, pattern="^(DECISION_MAKER|KEY_CONTRIBUTOR|HIGH_IMPACT)$"),
    qualified_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List contributors with filtering options."""
    access_query = db.query(RepositoryContributor.id).join(Repository).join(Project).filter(
        RepositoryContributor.contributor_id == Contributor.id,
        Project.org_id == org_id
    )
    
    # Filter by project
    if project_id:
        # Verify project ownership
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.org_id == org_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        access_query = access_query.filter(Repository.project_id == project_id)
    
    # Filter by repository
    if repository_id:
        access_query = access_query.filter(Repository.id == repository_id)

    query = db.query(Contributor).filter(access_query.exists())
    
    # Filter by classification
    if classification:
        query = query.join(SocialContext).filter(
            SocialContext.classification == classification
        )
    
    # Filter qualified leads
    lead_score_join = None
    if project_id:
        lead_score_join = and_(
            LeadScore.contributor_id == Contributor.id,
            LeadScore.project_id == project_id
        )
        query = query.outerjoin(LeadScore, lead_score_join)
        if qualified_only:
            query = query.filter(LeadScore.is_qualified_lead.is_(True))
    
    # Order by lead score if project specified
    if project_id:
        query = query.order_by(desc(LeadScore.overall_score))
    
    contributors = query.offset(skip).limit(limit).all()

    contributor_ids = [c.id for c in contributors]

    social_context_map = {
        sc.contributor_id: sc for sc in db.query(SocialContext).filter(
            SocialContext.contributor_id.in_(contributor_ids)
        ).all()
    } if contributor_ids else {}

    lead_score_map = {}
    if project_id and contributor_ids:
        lead_scores = db.query(LeadScore).filter(
            LeadScore.project_id == project_id,
            LeadScore.contributor_id.in_(contributor_ids)
        ).all()
        lead_score_map = {ls.contributor_id: ls for ls in lead_scores}

    stats_map: dict[UUID, ContributorStatsResponse] = {}
    if contributor_ids:
        if repository_id:
            stats_rows = db.query(ContributorStats).filter(
                ContributorStats.repository_id == repository_id,
                ContributorStats.contributor_id.in_(contributor_ids)
            ).all()
            stats_map = {row.contributor_id: ContributorStatsResponse.from_orm(row) for row in stats_rows}
        else:
            stats_query = db.query(ContributorStats).join(Repository).join(Project).filter(
                ContributorStats.contributor_id.in_(contributor_ids),
                Project.org_id == org_id
            )
            if project_id:
                stats_query = stats_query.filter(Repository.project_id == project_id)
            stats_rows = stats_query.all()
            rows_by_contributor: dict[UUID, List[ContributorStats]] = {}
            for row in stats_rows:
                rows_by_contributor.setdefault(row.contributor_id, []).append(row)
            stats_map = {
                cid: aggregate_stats_rows(cid, rows)
                for cid, rows in rows_by_contributor.items()
            }

    # Build detailed response
    result = []
    for contributor in contributors:
        stats = stats_map.get(contributor.id)
        social_context = social_context_map.get(contributor.id)
        lead_score = lead_score_map.get(contributor.id)

        result.append(LeadDetail(
            contributor=ContributorResponse.from_orm(contributor),
            stats=stats,
            social_context=SocialContextResponse.from_orm(social_context) if social_context else None,
            lead_score=LeadScoreResponse.from_orm(lead_score) if lead_score else None
        ))

    return result


@router.get("/{contributor_id}", response_model=LeadDetail)
async def get_contributor(
    contributor_id: UUID,
    project_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get detailed information about a contributor."""
    contributor = db.query(Contributor).filter(
        Contributor.id == contributor_id
    ).first()
    
    if not contributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor not found"
        )

    access_query = db.query(RepositoryContributor).join(Repository).join(Project).filter(
        RepositoryContributor.contributor_id == contributor_id,
        Project.org_id == org_id
    )
    if project_id:
        access_query = access_query.filter(Project.id == project_id)
    if not access_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor not found"
        )
    
    stats = None
    if project_id:
        stats_rows = db.query(ContributorStats).join(Repository).filter(
            Repository.project_id == project_id,
            ContributorStats.contributor_id == contributor_id
        ).all()
        stats = aggregate_stats_rows(contributor_id, stats_rows)
    else:
        stats_rows = db.query(ContributorStats).join(Repository).join(Project).filter(
            Project.org_id == org_id,
            ContributorStats.contributor_id == contributor_id
        ).all()
        stats = aggregate_stats_rows(contributor_id, stats_rows)
    
    # Get social context
    social_context = db.query(SocialContext).filter(
        SocialContext.contributor_id == contributor_id
    ).first()
    
    # Get lead score (if project specified)
    lead_score = None
    if project_id:
        # Verify project ownership
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
            LeadScore.contributor_id == contributor_id,
            LeadScore.project_id == project_id
        ).first()
    
    return LeadDetail(
        contributor=ContributorResponse.from_orm(contributor),
        stats=stats,
        social_context=SocialContextResponse.from_orm(social_context) if social_context else None,
        lead_score=LeadScoreResponse.from_orm(lead_score) if lead_score else None
    )


@router.post("/{contributor_id}/enrich")
async def enrich_contributor(
    contributor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger social enrichment for a contributor."""
    contributor = db.query(Contributor).filter(
        Contributor.id == contributor_id
    ).first()
    
    if not contributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor not found"
        )

    access_query = db.query(RepositoryContributor).join(Repository).join(Project).filter(
        RepositoryContributor.contributor_id == contributor_id,
        Project.org_id == org_id
    )
    if not access_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributor not found"
        )
    
    # Create enrichment job
    from models import SourcingJob
    
    job = SourcingJob(
        job_type='social_enrichment',
        status='pending',
        job_metadata={'contributor_id': str(contributor_id)},
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {"message": "Enrichment job created", "job_id": str(job.id)}
