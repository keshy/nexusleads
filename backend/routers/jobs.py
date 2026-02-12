"""Jobs router."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, SourcingJob, JobProgress, Project, Repository
from schemas import SourcingJobResponse, SourcingJobWithProgress, JobProgressResponse

router = APIRouter()


@router.get("", response_model=List[SourcingJobResponse])
async def list_jobs(
    project_id: UUID = None,
    repository_id: UUID = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List sourcing jobs for the current org."""
    query = db.query(
        SourcingJob,
        Project.name.label("project_name"),
        Repository.full_name.label("repository_name")
    ).outerjoin(Project, SourcingJob.project_id == Project.id).outerjoin(Repository, SourcingJob.repository_id == Repository.id)
    
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
        
        query = query.filter(SourcingJob.project_id == project_id)
    else:
        # Only show jobs for org's projects
        org_project_ids = [p.id for p in db.query(Project).filter(
            Project.org_id == org_id
        ).all()]
        
        if org_project_ids:
            query = query.filter(
                SourcingJob.project_id.in_(org_project_ids)
            )
        else:
            query = query.filter(SourcingJob.project_id.is_(None))
    
    # Filter by repository
    if repository_id:
        query = query.filter(SourcingJob.repository_id == repository_id)
    
    # Filter by status
    if status_filter:
        query = query.filter(SourcingJob.status == status_filter)
    
    # Order by creation date
    jobs = query.order_by(desc(SourcingJob.created_at)).offset(skip).limit(limit).all()
    
    # Enrich with project and repository names
    result = []
    for job, project_name, repository_name in jobs:
        job_dict = {
            "id": job.id,
            "project_id": job.project_id,
            "repository_id": job.repository_id,
            "job_type": job.job_type,
            "status": job.status,
            "total_steps": job.total_steps,
            "current_step": job.current_step,
            "progress_percentage": job.progress_percentage,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message,
            "job_metadata": job.job_metadata,
            "created_at": job.created_at,
            "project_name": project_name,
            "repository_name": repository_name
        }

        result.append(SourcingJobResponse(**job_dict))
    
    return result


@router.get("/{job_id}", response_model=SourcingJobWithProgress)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get detailed job information with progress steps."""
    job = db.query(SourcingJob).filter(
        SourcingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify access via org
    if job.project_id:
        project = db.query(Project).filter(
            Project.id == job.project_id,
            Project.org_id == org_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get progress steps
    progress_steps = db.query(JobProgress).filter(
        JobProgress.job_id == job_id
    ).order_by(JobProgress.step_number).all()
    
    return SourcingJobWithProgress(
        **job.__dict__,
        progress_steps=[JobProgressResponse.from_orm(step) for step in progress_steps]
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Cancel a running or pending job."""
    job = db.query(SourcingJob).filter(
        SourcingJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify access via org
    if job.project_id:
        project = db.query(Project).filter(
            Project.id == job.project_id,
            Project.org_id == org_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Check if job can be cancelled
    if job.status not in ['pending', 'running']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    # Mark job as cancelled
    job.status = 'cancelled'
    job.completed_at = job.completed_at or datetime.utcnow()
    job.error_message = "Cancelled by user"
    db.commit()
    
    return {"message": "Job cancelled successfully"}


@router.get("/stats/summary")
async def get_job_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get job statistics summary."""
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    
    # Get jobs for org's projects
    user_project_ids = db.query(Project.id).filter(
        Project.org_id == org_id
    ).subquery()
    
    # Total jobs
    total_jobs = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id.in_(user_project_ids)
    ).scalar() or 0
    
    # Active jobs (pending or running)
    active_jobs = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id.in_(user_project_ids),
        SourcingJob.status.in_(['pending', 'running'])
    ).scalar() or 0
    
    # Completed jobs today
    today = datetime.utcnow().date()
    completed_today = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id.in_(user_project_ids),
        SourcingJob.status == 'completed',
        func.date(SourcingJob.completed_at) == today
    ).scalar() or 0
    
    # Failed jobs
    failed_jobs = db.query(func.count(SourcingJob.id)).filter(
        SourcingJob.project_id.in_(user_project_ids),
        SourcingJob.status == 'failed'
    ).scalar() or 0
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "completed_today": completed_today,
        "failed_jobs": failed_jobs
    }
