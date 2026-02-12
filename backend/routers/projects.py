"""Projects router."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, Project, Repository, LeadScore, SourcingJob, SocialContext, OrgMember
from schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, 
    ProjectWithStats, ProjectStats
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
    new_project = Project(
        user_id=current_user.id,
        org_id=org_id,
        name=project_data.name,
        description=project_data.description,
        tags=project_data.tags,
        external_urls=project_data.external_urls,
        sourcing_context=project_data.sourcing_context
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

    repo_counts = dict(db.query(
        Repository.project_id, func.count(Repository.id)
    ).filter(
        Repository.project_id.in_(project_ids)
    ).group_by(Repository.project_id).all())

    contributor_counts = dict(db.query(
        LeadScore.project_id, func.count(func.distinct(LeadScore.contributor_id))
    ).filter(
        LeadScore.project_id.in_(project_ids)
    ).group_by(LeadScore.project_id).all())

    qualified_counts = dict(db.query(
        LeadScore.project_id, func.count(func.distinct(SocialContext.contributor_id))
    ).join(
        SocialContext, SocialContext.contributor_id == LeadScore.contributor_id
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
            total_repositories=repo_counts.get(project.id, 0),
            total_contributors=contributor_counts.get(project.id, 0),
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
    total_repos = db.query(func.count(Repository.id)).filter(
        Repository.project_id == project.id
    ).scalar()
    
    total_contributors = db.query(func.count(func.distinct(LeadScore.contributor_id))).filter(
        LeadScore.project_id == project.id
    ).scalar()
    
    qualified_leads = db.query(func.count(func.distinct(SocialContext.contributor_id))).join(
        LeadScore, LeadScore.contributor_id == SocialContext.contributor_id
    ).filter(
        LeadScore.project_id == project.id,
        SocialContext.classification.in_(['DECISION_MAKER', 'HIGH_IMPACT'])
    ).scalar()
    
    active_jobs = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id == project.id,
        SourcingJob.status.in_(['pending', 'running'])
    ).scalar()
    
    stats = ProjectStats(
        total_repositories=total_repos or 0,
        total_contributors=total_contributors or 0,
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
    
    # Get all active repositories for this project
    repositories = db.query(Repository).filter(
        Repository.project_id == project_id,
        Repository.is_active == True
    ).all()
    
    if not repositories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active repositories found in this project"
        )
    
    # Create sourcing jobs for each repository
    jobs_created = 0
    for repo in repositories:
        # Check if there's already a pending/running job for this repo
        existing_job = db.query(SourcingJob).filter(
            SourcingJob.repository_id == repo.id,
            SourcingJob.status.in_(['pending', 'running'])
        ).first()
        
        if not existing_job:
            job = SourcingJob(
                project_id=project_id,
                repository_id=repo.id,
                job_type='repository_sourcing',
                status='pending',
                created_by=current_user.id
            )
            db.add(job)
            jobs_created += 1
    
    db.commit()
    
    return {
        "message": f"Created {jobs_created} sourcing job(s)",
        "total_repositories": len(repositories),
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
