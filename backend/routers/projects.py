"""Projects router."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, Project, CommunitySource, LeadScore, SourcingJob, SocialContext, OrgMember
from schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, 
    ProjectWithStats, ProjectStats, SCORING_PRESETS
)

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Create a new project."""
    # Resolve scoring preset if specified
    scoring_weights = None
    if project_data.scoring_preset and project_data.scoring_preset in SCORING_PRESETS:
        scoring_weights = SCORING_PRESETS[project_data.scoring_preset]["weights"].model_dump()
    elif project_data.scoring_weights:
        scoring_weights = project_data.scoring_weights.model_dump()

    classification_labels = None
    if project_data.classification_labels:
        classification_labels = [l.model_dump() for l in project_data.classification_labels]

    new_project = Project(
        user_id=current_user.id,
        org_id=org_id,
        name=project_data.name,
        description=project_data.description,
        tags=project_data.tags,
        external_urls=project_data.external_urls,
        sourcing_context=project_data.sourcing_context,
        classification_labels=classification_labels,
        scoring_weights=scoring_weights,
        scoring_preset=project_data.scoring_preset
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project


@router.get("", response_model=List[ProjectWithStats])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List all projects for the current org."""
    projects = db.query(Project).filter(
        Project.org_id == org_id
    ).offset(skip).limit(limit).all()

    project_ids = [p.id for p in projects]
    if not project_ids:
        return []

    source_counts = dict(db.query(
        CommunitySource.project_id, func.count(CommunitySource.id)
    ).filter(
        CommunitySource.project_id.in_(project_ids)
    ).group_by(CommunitySource.project_id).all())

    member_counts = dict(db.query(
        LeadScore.project_id, func.count(func.distinct(LeadScore.member_id))
    ).filter(
        LeadScore.project_id.in_(project_ids)
    ).group_by(LeadScore.project_id).all())

    qualified_counts = dict(db.query(
        LeadScore.project_id, func.count(func.distinct(SocialContext.member_id))
    ).join(
        SocialContext, SocialContext.member_id == LeadScore.member_id
    ).filter(
        LeadScore.project_id.in_(project_ids),
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    ).group_by(LeadScore.project_id).all())

    active_jobs_counts = dict(db.query(
        SourcingJob.project_id, func.count(SourcingJob.id)
    ).filter(
        SourcingJob.project_id.in_(project_ids),
        SourcingJob.status.in_(['pending', 'running'])
    ).group_by(SourcingJob.project_id).all())

    # Enrich with stats
    result = []
    for project in projects:
        stats = ProjectStats(
            total_sources=source_counts.get(project.id, 0),
            total_members=member_counts.get(project.id, 0),
            qualified_leads=qualified_counts.get(project.id, 0),
            active_jobs=active_jobs_counts.get(project.id, 0)
        )
        result.append(ProjectWithStats(**project.__dict__, stats=stats))

    return result


@router.get("/{project_id}", response_model=ProjectWithStats)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get a specific project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get stats
    total_sources = db.query(func.count(CommunitySource.id)).filter(
        CommunitySource.project_id == project.id
    ).scalar()
    
    total_members = db.query(func.count(func.distinct(LeadScore.member_id))).filter(
        LeadScore.project_id == project.id
    ).scalar()
    
    qualified_leads = db.query(func.count(func.distinct(SocialContext.member_id))).join(
        LeadScore, LeadScore.member_id == SocialContext.member_id
    ).filter(
        LeadScore.project_id == project.id,
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    ).scalar()
    
    active_jobs = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id == project.id,
        SourcingJob.status.in_(['pending', 'running'])
    ).scalar()
    
    stats = ProjectStats(
        total_sources=total_sources or 0,
        total_members=total_members or 0,
        qualified_leads=qualified_leads or 0,
        active_jobs=active_jobs or 0
    )
    
    return ProjectWithStats(**project.__dict__, stats=stats)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Update a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.tags is not None:
        project.tags = project_data.tags
    if project_data.external_urls is not None:
        project.external_urls = project_data.external_urls
    if project_data.sourcing_context is not None:
        project.sourcing_context = project_data.sourcing_context
    if project_data.is_active is not None:
        project.is_active = project_data.is_active
    if project_data.auto_export_clay_enabled is not None:
        project.auto_export_clay_enabled = project_data.auto_export_clay_enabled
    if project_data.auto_export_clay_min_score is not None:
        project.auto_export_clay_min_score = project_data.auto_export_clay_min_score
    if project_data.auto_export_clay_classifications is not None:
        project.auto_export_clay_classifications = project_data.auto_export_clay_classifications
    if project_data.classification_labels is not None:
        project.classification_labels = [l.model_dump() for l in project_data.classification_labels]
    if project_data.scoring_weights is not None:
        project.scoring_weights = project_data.scoring_weights.model_dump()
    if project_data.scoring_preset is not None:
        if project_data.scoring_preset in SCORING_PRESETS:
            project.scoring_weights = SCORING_PRESETS[project_data.scoring_preset]["weights"].model_dump()
        project.scoring_preset = project_data.scoring_preset
    
    db.commit()
    db.refresh(project)
    
    return project


@router.post("/{project_id}/source-all")
async def trigger_project_sourcing(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger sourcing for all repositories in a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get all active sources for this project
    sources = db.query(CommunitySource).filter(
        CommunitySource.project_id == project_id,
        CommunitySource.is_active == True
    ).all()
    
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active community sources found in this project"
        )
    
    # Create sourcing jobs for each source
    jobs_created = 0
    for src in sources:
        # Check if there's already a pending/running job for this source
        existing_job = db.query(SourcingJob).filter(
            SourcingJob.source_id == src.id,
            SourcingJob.status.in_(['pending', 'running'])
        ).first()
        
        if not existing_job:
            job_type = 'repository_sourcing' if src.source_type == 'github_repo' else 'source_ingestion'
            job = SourcingJob(
                project_id=project_id,
                source_id=src.id,
                job_type=job_type,
                status='pending',
                created_by=current_user.id
            )
            db.add(job)
            jobs_created += 1
    
    db.commit()
    
    return {
        "message": f"Created {jobs_created} sourcing job(s)",
        "total_sources": len(sources),
        "jobs_created": jobs_created
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Delete a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()
    
    return None
