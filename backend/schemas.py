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


# Classification & Scoring schemas
class ClassificationLabel(BaseModel):
    key: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)


class ScoringWeights(BaseModel):
    position: float = Field(0.35, ge=0, le=1)
    activity: float = Field(0.25, ge=0, le=1)
    influence: float = Field(0.20, ge=0, le=1)
    engagement: float = Field(0.20, ge=0, le=1)


# Scoring presets
SCORING_PRESETS = {
    "developer_community": {
        "label": "Developer Community",
        "description": "Optimized for open-source and developer communities (activity-heavy)",
        "weights": ScoringWeights(position=0.20, activity=0.35, influence=0.20, engagement=0.25),
    },
    "executive_network": {
        "label": "Executive Network",
        "description": "Optimized for identifying decision makers and buyers (position-heavy)",
        "weights": ScoringWeights(position=0.45, activity=0.15, influence=0.25, engagement=0.15),
    },
    "social_engagement": {
        "label": "Social Engagement",
        "description": "Optimized for social communities like Discord, Reddit, X (engagement-heavy)",
        "weights": ScoringWeights(position=0.15, activity=0.25, influence=0.25, engagement=0.35),
    },
    "balanced": {
        "label": "Balanced",
        "description": "Equal weighting across all dimensions",
        "weights": ScoringWeights(position=0.25, activity=0.25, influence=0.25, engagement=0.25),
    },
}

DEFAULT_SCORING_WEIGHTS = ScoringWeights(position=0.35, activity=0.25, influence=0.20, engagement=0.20)

DEFAULT_CLASSIFICATION_LABELS = [
    ClassificationLabel(key="DECISION_MAKER", label="Decision Maker", description="C-suite, VPs, Directors who can make purchasing decisions"),
    ClassificationLabel(key="KEY_CONTRIBUTOR", label="Key Contributor", description="Core team members, maintainers, architects with high influence"),
    ClassificationLabel(key="HIGH_IMPACT", label="High Impact", description="Active participants with significant recent activity"),
]


# Project schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    external_urls: Optional[List[str]] = None
    sourcing_context: Optional[str] = None


class ProjectCreate(ProjectBase):
    classification_labels: Optional[List[ClassificationLabel]] = None
    scoring_weights: Optional[ScoringWeights] = None
    scoring_preset: Optional[str] = None


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
    classification_labels: Optional[List[ClassificationLabel]] = None
    scoring_weights: Optional[ScoringWeights] = None
    scoring_preset: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    is_active: bool
    auto_export_clay_enabled: bool = False
    auto_export_clay_min_score: Optional[int] = None
    auto_export_clay_classifications: Optional[List[str]] = None
    classification_labels: Optional[List[ClassificationLabel]] = None
    scoring_weights: Optional[ScoringWeights] = None
    scoring_preset: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    total_sources: int
    total_members: int
    qualified_leads: int
    active_jobs: int


class ProjectWithStats(ProjectResponse):
    stats: ProjectStats


# Community Source schemas
class CommunitySourceBase(BaseModel):
    source_type: str = Field(default="github_repo")
    external_url: str = Field(..., max_length=500)
    sourcing_interval: str = Field(default="monthly", pattern="^(daily|weekly|monthly)$")
    source_config: Optional[Dict[str, Any]] = None


class CommunitySourceCreate(CommunitySourceBase):
    project_id: UUID


class CommunitySourceUpdate(BaseModel):
    sourcing_interval: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    is_active: Optional[bool] = None
    source_config: Optional[Dict[str, Any]] = None


class CommunitySourceResponse(CommunitySourceBase):
    id: UUID
    project_id: UUID
    full_name: str
    owner: Optional[str] = None
    repo_name: Optional[str] = None
    github_url: Optional[str] = None
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


# Member schemas
class MemberBase(BaseModel):
    username: str
    github_id: Optional[int] = None


class MemberResponse(MemberBase):
    id: UUID
    platform_identities: Optional[Dict[str, Any]] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    avatar_url: Optional[str] = None
    github_url: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


# Member activity schemas
class MemberActivityResponse(BaseModel):
    id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    member_id: UUID
    activity_type: str = 'commit'
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
    member_id: UUID
    linkedin_url: Optional[str] = None
    linkedin_profile_photo_url: Optional[str] = None
    linkedin_headline: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    position_level: Optional[str] = None
    years_of_experience: Optional[int] = None
    skills: Optional[List[str]] = []
    classification: Optional[str] = None
    classification_confidence: Optional[Decimal] = None
    classification_reasoning: Optional[str] = None
    is_verified: bool = False
    last_enriched_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Lead score schemas
class LeadScoreResponse(BaseModel):
    id: UUID
    project_id: UUID
    member_id: UUID
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
    """Detailed lead information combining member, activity, and social context."""
    member: MemberResponse
    stats: Optional[MemberActivityResponse] = None
    social_context: Optional[SocialContextResponse] = None
    lead_score: Optional[LeadScoreResponse] = None


# Job schemas
class SourcingJobCreate(BaseModel):
    project_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    job_type: str = Field(..., pattern="^(source_ingestion|social_enrichment|similar_sources|stargazer_analysis)$")
    metadata: Optional[Dict[str, Any]] = None


class SourcingJobResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
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
    source_name: Optional[str] = None
    
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
    total_sources: int
    total_members: int
    qualified_leads: int
    decision_makers: int
    key_contributors: int
    high_impact: int
    active_jobs: int
    pending_jobs: int
    completed_jobs_today: int


class SourceLeadStats(BaseModel):
    source_id: UUID
    source_name: str
    source_type: str = 'github_repo'
    total_members: int
    qualified_leads: int
    decision_makers: int
    key_contributors: int
    high_impact: int


# Search schemas
class SourceDiscoverySearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    source_type: str = Field(default="github_repo")
    limit: int = Field(default=10, ge=1, le=50)


class SourceDiscoveryResult(BaseModel):
    full_name: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    topics: List[str] = []
    url: str
    source_type: str = 'github_repo'


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
