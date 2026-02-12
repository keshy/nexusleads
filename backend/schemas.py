"""Pydantic schemas for API validation."""
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


# Project schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    external_urls: Optional[List[str]] = None
    sourcing_context: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    external_urls: Optional[List[str]] = None
    sourcing_context: Optional[str] = None
    is_active: Optional[bool] = None
    auto_export_clay_enabled: Optional[bool] = None
    auto_export_clay_min_score: Optional[int] = None
    auto_export_clay_classifications: Optional[List[str]] = None


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    is_active: bool
    auto_export_clay_enabled: bool = False
    auto_export_clay_min_score: Optional[int] = None
    auto_export_clay_classifications: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    total_repositories: int
    total_contributors: int
    qualified_leads: int
    active_jobs: int


class ProjectWithStats(ProjectResponse):
    stats: ProjectStats


# Repository schemas
class RepositoryBase(BaseModel):
    github_url: str = Field(..., max_length=500)
    sourcing_interval: str = Field(default="monthly", pattern="^(daily|weekly|monthly)$")


class RepositoryCreate(RepositoryBase):
    project_id: UUID


class RepositoryUpdate(BaseModel):
    sourcing_interval: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    is_active: Optional[bool] = None


class RepositoryResponse(RepositoryBase):
    id: UUID
    project_id: UUID
    full_name: str
    owner: str
    repo_name: str
    description: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    open_issues: Optional[int] = None
    language: Optional[str] = None
    topics: Optional[List[str]] = None
    last_sourced_at: Optional[datetime] = None
    next_sourcing_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Contributor schemas
class ContributorBase(BaseModel):
    username: str
    github_id: int


class ContributorResponse(ContributorBase):
    id: UUID
    full_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    avatar_url: Optional[str] = None
    github_url: Optional[str] = None
    public_repos: int
    followers: int
    following: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Contributor stats schemas
class ContributorStatsResponse(BaseModel):
    id: Optional[UUID] = None
    repository_id: Optional[UUID] = None
    contributor_id: UUID
    total_commits: int
    commits_last_3_months: int
    commits_last_6_months: int
    commits_last_year: int
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    lines_added: int
    lines_deleted: int
    pull_requests: int
    issues_opened: int
    issues_closed: int
    code_reviews: int
    is_maintainer: bool
    is_core_team: bool
    calculated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Social context schemas
class SocialContextResponse(BaseModel):
    id: UUID
    contributor_id: UUID
    linkedin_url: Optional[str] = None
    linkedin_profile_photo_url: Optional[str] = None
    linkedin_headline: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    position_level: Optional[str] = None
    years_of_experience: Optional[int] = None
    skills: List[str] = []
    classification: Optional[str] = None
    classification_confidence: Optional[Decimal] = None
    classification_reasoning: Optional[str] = None
    is_verified: bool
    last_enriched_at: datetime
    
    class Config:
        from_attributes = True


# Lead score schemas
class LeadScoreResponse(BaseModel):
    id: UUID
    project_id: UUID
    contributor_id: UUID
    overall_score: Decimal
    activity_score: Decimal
    influence_score: Decimal
    position_score: Decimal
    engagement_score: Decimal
    is_qualified_lead: bool
    priority: Optional[str] = None
    notes: Optional[str] = None
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class LeadDetail(BaseModel):
    """Detailed lead information combining contributor, stats, and social context."""
    contributor: ContributorResponse
    stats: Optional[ContributorStatsResponse] = None
    social_context: Optional[SocialContextResponse] = None
    lead_score: Optional[LeadScoreResponse] = None


# Job schemas
class SourcingJobCreate(BaseModel):
    project_id: Optional[UUID] = None
    repository_id: Optional[UUID] = None
    job_type: str = Field(..., pattern="^(repository_sourcing|social_enrichment|similar_repos)$")
    metadata: Optional[Dict[str, Any]] = None


class SourcingJobResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    repository_id: Optional[UUID] = None
    job_type: str
    status: str
    total_steps: int
    current_step: int
    progress_percentage: Decimal
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    job_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    project_name: Optional[str] = None
    repository_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobProgressResponse(BaseModel):
    id: UUID
    job_id: UUID
    step_number: int
    step_name: str
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SourcingJobWithProgress(SourcingJobResponse):
    progress_steps: List[JobProgressResponse] = []


# Dashboard schemas
class DashboardStats(BaseModel):
    total_projects: int
    total_repositories: int
    total_contributors: int
    qualified_leads: int
    decision_makers: int
    key_contributors: int
    high_impact: int
    active_jobs: int
    pending_jobs: int
    completed_jobs_today: int


class RepositoryLeadStats(BaseModel):
    repository_id: UUID
    repository_name: str
    total_contributors: int
    qualified_leads: int
    decision_makers: int
    key_contributors: int
    high_impact: int


# Search schemas
class SimilarRepoSearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class SimilarRepoResult(BaseModel):
    full_name: str
    description: Optional[str] = None
    stars: int
    forks: int
    language: Optional[str] = None
    topics: List[str] = []
    url: str


# Settings schemas
class AppSettingResponse(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_secret: bool = False
    is_set: bool = False
    source: str = "not_set"
    hint: str = ""
    help_url: str = ""
    required: bool = False
    placeholder: str = ""


class AppSettingUpdate(BaseModel):
    key: str
    value: str


# Organization schemas
class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrgMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime

class OrgAddMember(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")

class OrgWithRole(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    created_at: datetime


# Chat schemas
class ChatConversationCreate(BaseModel):
    title: Optional[str] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ChatConversationUpdate(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None


class ChatConversationResponse(BaseModel):
    id: UUID
    org_id: UUID
    user_id: UUID
    title: str
    messages: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatConversationListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
