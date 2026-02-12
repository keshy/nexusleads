"""Repositories router."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, Repository, Project, SourcingJob
from schemas import RepositoryCreate, RepositoryUpdate, RepositoryResponse, SimilarRepoSearch, SimilarRepoResult
import re
from github import Github, GithubException
from settings_service import get_setting

router = APIRouter()


def parse_github_url(url: str) -> tuple:
    """Parse GitHub URL to extract owner and repo name."""
    # Support various GitHub URL formats
    patterns = [
        r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
        r'github\.com/([^/]+)/([^/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            repo = repo.replace('.git', '')
            return owner, repo
    
    raise ValueError("Invalid GitHub URL format")


@router.post("/similar", response_model=list[SimilarRepoResult])
async def search_similar_repositories(
    search: SimilarRepoSearch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Search for similar repositories on GitHub."""
    github_token = get_setting(db, 'GITHUB_TOKEN', org_id=org_id)
    if not github_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub token not configured. Set it in Settings > API Keys."
        )

    client = Github(github_token)
    try:
        results = client.search_repositories(query=search.query, sort='stars', order='desc')[:search.limit]
    except GithubException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub search failed: {e.data.get('message') if hasattr(e, 'data') else str(e)}"
        )

    return [
        SimilarRepoResult(
            full_name=repo.full_name,
            description=repo.description,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            language=repo.language,
            topics=repo.get_topics(),
            url=repo.html_url
        )
        for repo in results
    ]


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_data: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Add a new repository to a project."""
    project = db.query(Project).filter(
        Project.id == repo_data.project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Parse GitHub URL
    try:
        owner, repo_name = parse_github_url(repo_data.github_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    full_name = f"{owner}/{repo_name}"
    
    # Check if repository already exists in project
    existing_repo = db.query(Repository).filter(
        Repository.project_id == repo_data.project_id,
        Repository.github_url == repo_data.github_url
    ).first()
    
    if existing_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository already exists in this project"
        )
    
    # Calculate next sourcing time
    interval_days = {
        'daily': 1,
        'weekly': 7,
        'monthly': 30
    }
    next_sourcing = datetime.utcnow() + timedelta(days=interval_days[repo_data.sourcing_interval])
    
    # Create repository
    new_repo = Repository(
        project_id=repo_data.project_id,
        github_url=repo_data.github_url,
        full_name=full_name,
        owner=owner,
        repo_name=repo_name,
        sourcing_interval=repo_data.sourcing_interval,
        next_sourcing_at=next_sourcing
    )
    
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)
    
    # Create initial sourcing job
    sourcing_job = SourcingJob(
        project_id=repo_data.project_id,
        repository_id=new_repo.id,
        job_type='repository_sourcing',
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    
    return new_repo


@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(
    project_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List repositories."""
    query = db.query(Repository).join(Project).filter(
        Project.org_id == org_id
    )
    
    if project_id:
        query = query.filter(Repository.project_id == project_id)
    
    repositories = query.offset(skip).limit(limit).all()
    return repositories


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get a specific repository."""
    repository = db.query(Repository).join(Project).filter(
        Repository.id == repository_id,
        Project.org_id == org_id
    ).first()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    return repository


@router.put("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: UUID,
    repo_data: RepositoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Update a repository."""
    repository = db.query(Repository).join(Project).filter(
        Repository.id == repository_id,
        Project.org_id == org_id
    ).first()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    # Update fields
    if repo_data.sourcing_interval is not None:
        repository.sourcing_interval = repo_data.sourcing_interval
        # Recalculate next sourcing time
        interval_days = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30
        }
        repository.next_sourcing_at = datetime.utcnow() + timedelta(
            days=interval_days[repo_data.sourcing_interval]
        )
    
    if repo_data.is_active is not None:
        repository.is_active = repo_data.is_active
    
    db.commit()
    db.refresh(repository)
    
    return repository


@router.post("/{repository_id}/source-now")
async def trigger_sourcing(
    repository_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger immediate sourcing for a repository."""
    repository = db.query(Repository).join(Project).filter(
        Repository.id == repository_id,
        Project.org_id == org_id
    ).first()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    # Check for existing pending/running jobs
    existing_job = db.query(SourcingJob).filter(
        SourcingJob.repository_id == repository_id,
        SourcingJob.status.in_(['pending', 'running'])
    ).first()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A sourcing job is already in progress for this repository"
        )
    
    # Create new sourcing job
    sourcing_job = SourcingJob(
        project_id=repository.project_id,
        repository_id=repository.id,
        job_type='repository_sourcing',
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    db.refresh(sourcing_job)
    
    return {"message": "Sourcing job created", "job_id": str(sourcing_job.id)}


@router.post("/{repository_id}/analyze-stargazers")
async def trigger_stargazer_analysis(
    repository_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger stargazer analysis for a repository."""
    repository = db.query(Repository).join(Project).filter(
        Repository.id == repository_id,
        Project.org_id == org_id
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    existing_job = db.query(SourcingJob).filter(
        SourcingJob.repository_id == repository_id,
        SourcingJob.job_type == 'stargazer_analysis',
        SourcingJob.status.in_(['pending', 'running'])
    ).first()

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A stargazer analysis job is already in progress for this repository"
        )

    sourcing_job = SourcingJob(
        project_id=repository.project_id,
        repository_id=repository.id,
        job_type='stargazer_analysis',
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    db.refresh(sourcing_job)

    return {"message": "Stargazer analysis job created", "job_id": str(sourcing_job.id)}


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Delete a repository."""
    repository = db.query(Repository).join(Project).filter(
        Repository.id == repository_id,
        Project.org_id == org_id
    ).first()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    db.delete(repository)
    db.commit()
    
    return None
