"""Community sources router (generalized from repositories)."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_active_user
from org_context import require_org
from models import User, CommunitySource, Project, SourcingJob
from schemas import (
    CommunitySourceCreate, CommunitySourceUpdate, CommunitySourceResponse,
    SourceDiscoverySearch, SourceDiscoveryResult
)
import re
from github import Github, GithubException
from settings_service import get_setting

router = APIRouter()


def parse_github_url(url: str) -> tuple:
    """Parse GitHub URL to extract owner and repo name."""
    patterns = [
        r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
        r'github\.com/([^/]+)/([^/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner, repo = match.groups()
            repo = repo.replace('.git', '')
            return owner, repo
    
    raise ValueError("Invalid GitHub URL format")


def detect_source_type(url: str) -> str:
    """Detect community source type from URL."""
    url_lower = url.lower()
    if 'github.com' in url_lower:
        return 'github_repo'
    elif 'discord.gg' in url_lower or 'discord.com' in url_lower:
        return 'discord_server'
    elif 'reddit.com/r/' in url_lower:
        return 'reddit_subreddit'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'x_account'
    elif 'stocktwits.com' in url_lower:
        return 'stock_forum'
    return 'custom'


def parse_source_url(url: str, source_type: str) -> dict:
    """Parse source URL and return metadata based on type."""
    if source_type == 'github_repo':
        owner, repo_name = parse_github_url(url)
        return {
            'full_name': f"{owner}/{repo_name}",
            'owner': owner,
            'repo_name': repo_name,
        }
    elif source_type == 'reddit_subreddit':
        match = re.search(r'reddit\.com/r/([^/]+)', url)
        if match:
            return {'full_name': f"r/{match.group(1)}"}
        raise ValueError("Invalid Reddit URL format")
    elif source_type == 'discord_server':
        return {'full_name': url.split('/')[-1]}
    elif source_type == 'x_account':
        match = re.search(r'(?:twitter|x)\.com/([^/]+)', url)
        if match:
            return {'full_name': f"@{match.group(1)}"}
        raise ValueError("Invalid X/Twitter URL format")
    else:
        return {'full_name': url}


@router.post("/discover", response_model=list[SourceDiscoveryResult])
async def discover_sources(
    search: SourceDiscoverySearch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Discover community sources (currently GitHub repos)."""
    if search.source_type != 'github_repo':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discovery not yet supported for source type: {search.source_type}"
        )

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
        SourceDiscoveryResult(
            full_name=repo.full_name,
            description=repo.description,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            language=repo.language,
            topics=repo.get_topics(),
            url=repo.html_url,
            source_type='github_repo'
        )
        for repo in results
    ]


@router.post("/", response_model=CommunitySourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    source_data: CommunitySourceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Add a new community source to a project."""
    project = db.query(Project).filter(
        Project.id == source_data.project_id,
        Project.org_id == org_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Auto-detect source type from URL.
    # If the user left the default ('github_repo') we always re-detect so
    # pasting a Discord / Reddit / X URL picks the right type automatically.
    source_type = source_data.source_type
    detected = detect_source_type(source_data.external_url)
    if detected != 'custom':
        source_type = detected

    # Parse URL based on source type
    try:
        parsed = parse_source_url(source_data.external_url, source_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Check if source already exists in project
    existing = db.query(CommunitySource).filter(
        CommunitySource.project_id == source_data.project_id,
        CommunitySource.external_url == source_data.external_url
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This source already exists in this project"
        )
    
    # Calculate next sourcing time
    interval_days = {'daily': 1, 'weekly': 7, 'monthly': 30}
    next_sourcing = datetime.utcnow() + timedelta(days=interval_days[source_data.sourcing_interval])
    
    # Create source
    new_source = CommunitySource(
        project_id=source_data.project_id,
        source_type=source_type,
        external_url=source_data.external_url,
        source_config=source_data.source_config,
        # GitHub backward compat fields
        github_url=source_data.external_url if source_type == 'github_repo' else None,
        full_name=parsed['full_name'],
        owner=parsed.get('owner'),
        repo_name=parsed.get('repo_name'),
        sourcing_interval=source_data.sourcing_interval,
        next_sourcing_at=next_sourcing
    )
    
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    # Create initial sourcing job for every source type.
    # GitHub repos use the legacy 'repository_sourcing' handler;
    # all other types go through the generic 'source_ingestion' handler
    # which will fail gracefully if no connector / token is configured.
    job_type = 'repository_sourcing' if source_type == 'github_repo' else 'source_ingestion'
    sourcing_job = SourcingJob(
        project_id=source_data.project_id,
        source_id=new_source.id,
        job_type=job_type,
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    
    return new_source


@router.get("/", response_model=List[CommunitySourceResponse])
async def list_sources(
    project_id: UUID = None,
    source_type: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """List community sources."""
    query = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        Project.org_id == org_id
    )
    
    if project_id:
        query = query.filter(CommunitySource.project_id == project_id)
    
    if source_type:
        query = query.filter(CommunitySource.source_type == source_type)
    
    sources = query.offset(skip).limit(limit).all()
    return sources


@router.get("/{source_id}", response_model=CommunitySourceResponse)
async def get_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Get a specific community source."""
    source = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunitySource.id == source_id,
        Project.org_id == org_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    return source


@router.put("/{source_id}", response_model=CommunitySourceResponse)
async def update_source(
    source_id: UUID,
    source_data: CommunitySourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Update a community source."""
    source = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunitySource.id == source_id,
        Project.org_id == org_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    if source_data.sourcing_interval is not None:
        source.sourcing_interval = source_data.sourcing_interval
        interval_days = {'daily': 1, 'weekly': 7, 'monthly': 30}
        source.next_sourcing_at = datetime.utcnow() + timedelta(
            days=interval_days[source_data.sourcing_interval]
        )
    
    if source_data.is_active is not None:
        source.is_active = source_data.is_active

    if source_data.source_config is not None:
        source.source_config = source_data.source_config
    
    db.commit()
    db.refresh(source)
    
    return source


@router.post("/{source_id}/source-now")
async def trigger_sourcing(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger immediate sourcing for a community source."""
    source = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunitySource.id == source_id,
        Project.org_id == org_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Check for existing pending/running jobs
    existing_job = db.query(SourcingJob).filter(
        SourcingJob.source_id == source_id,
        SourcingJob.status.in_(['pending', 'running'])
    ).first()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A sourcing job is already in progress for this source"
        )
    
    # Determine job type based on source type
    job_type = 'repository_sourcing' if source.source_type == 'github_repo' else 'source_ingestion'

    sourcing_job = SourcingJob(
        project_id=source.project_id,
        source_id=source.id,
        job_type=job_type,
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    db.refresh(sourcing_job)
    
    return {"message": "Sourcing job created", "job_id": str(sourcing_job.id)}


@router.post("/{source_id}/analyze-stargazers")
async def trigger_stargazer_analysis(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Trigger stargazer/follower analysis for a source."""
    source = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunitySource.id == source_id,
        Project.org_id == org_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    if source.source_type != 'github_repo':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stargazer analysis is only supported for GitHub repositories"
        )

    existing_job = db.query(SourcingJob).filter(
        SourcingJob.source_id == source_id,
        SourcingJob.job_type == 'stargazer_analysis',
        SourcingJob.status.in_(['pending', 'running'])
    ).first()

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A stargazer analysis job is already in progress for this source"
        )

    sourcing_job = SourcingJob(
        project_id=source.project_id,
        source_id=source.id,
        job_type='stargazer_analysis',
        status='pending',
        created_by=current_user.id
    )
    db.add(sourcing_job)
    db.commit()
    db.refresh(sourcing_job)

    return {"message": "Stargazer analysis job created", "job_id": str(sourcing_job.id)}


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(require_org),
):
    """Delete a community source."""
    source = db.query(CommunitySource).join(
        Project, CommunitySource.project_id == Project.id
    ).filter(
        CommunitySource.id == source_id,
        Project.org_id == org_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    db.delete(source)
    db.commit()
    
    return None
