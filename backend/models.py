"""SQLAlchemy models."""
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, TIMESTAMP, 
    ForeignKey, DECIMAL, ARRAY, JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tags = Column(ARRAY(Text))  # User-defined tags
    external_urls = Column(ARRAY(Text))  # Additional URLs to track
    sourcing_context = Column(Text)  # Context/criteria for lead sourcing
    is_active = Column(Boolean, default=True)
    auto_export_clay_enabled = Column(Boolean, default=False)
    auto_export_clay_min_score = Column(Integer)
    auto_export_clay_classifications = Column(ARRAY(Text))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="projects")
    repositories = relationship("Repository", back_populates="project", cascade="all, delete-orphan")
    sourcing_jobs = relationship("SourcingJob", back_populates="project")
    lead_scores = relationship("LeadScore", back_populates="project", cascade="all, delete-orphan")


class Repository(Base):
    """Repository model."""
    __tablename__ = "repositories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    github_url = Column(String(500), nullable=False)
    full_name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    repo_name = Column(String(255), nullable=False)
    description = Column(Text)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    language = Column(String(100))
    topics = Column(ARRAY(Text))
    last_sourced_at = Column(TIMESTAMP(timezone=True))
    sourcing_interval = Column(String(50), default="monthly")
    next_sourcing_at = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('project_id', 'github_url', name='unique_project_repo'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="repositories")
    repository_contributors = relationship("RepositoryContributor", back_populates="repository", cascade="all, delete-orphan")
    contributor_stats = relationship("ContributorStats", back_populates="repository", cascade="all, delete-orphan")
    sourcing_jobs = relationship("SourcingJob", back_populates="repository")


class Contributor(Base):
    """Contributor model (GitHub users)."""
    __tablename__ = "contributors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    email = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    bio = Column(Text)
    blog = Column(String(500))
    twitter_username = Column(String(255))
    avatar_url = Column(String(500))
    github_url = Column(String(500))
    public_repos = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    repository_contributors = relationship("RepositoryContributor", back_populates="contributor")
    contributor_stats = relationship("ContributorStats", back_populates="contributor")
    social_context = relationship("SocialContext", back_populates="contributor", uselist=False)
    lead_scores = relationship("LeadScore", back_populates="contributor")


class RepositoryContributor(Base):
    """Repository-Contributor relationship."""
    __tablename__ = "repository_contributors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False)
    discovered_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('repository_id', 'contributor_id', name='unique_repo_contributor'),
    )
    
    # Relationships
    repository = relationship("Repository", back_populates="repository_contributors")
    contributor = relationship("Contributor", back_populates="repository_contributors")


class ContributorStats(Base):
    """Contributor statistics."""
    __tablename__ = "contributor_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False)
    total_commits = Column(Integer, default=0)
    commits_last_3_months = Column(Integer, default=0)
    commits_last_6_months = Column(Integer, default=0)
    commits_last_year = Column(Integer, default=0)
    first_commit_date = Column(TIMESTAMP(timezone=True))
    last_commit_date = Column(TIMESTAMP(timezone=True))
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    pull_requests = Column(Integer, default=0)
    issues_opened = Column(Integer, default=0)
    issues_closed = Column(Integer, default=0)
    code_reviews = Column(Integer, default=0)
    is_maintainer = Column(Boolean, default=False)
    is_core_team = Column(Boolean, default=False)
    source = Column(String(50), default='commit')
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('repository_id', 'contributor_id', name='unique_repo_contributor_stats'),
    )
    
    # Relationships
    repository = relationship("Repository", back_populates="contributor_stats")
    contributor = relationship("Contributor", back_populates="contributor_stats")


class SocialContext(Base):
    """Social context for contributors."""
    __tablename__ = "social_context"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False, unique=True)
    linkedin_url = Column(String(500))
    linkedin_profile_photo_url = Column(String(500))
    linkedin_headline = Column(Text)
    current_company = Column(String(255))
    current_position = Column(String(255))
    position_level = Column(String(100))
    years_of_experience = Column(Integer)
    skills = Column(ARRAY(Text))
    search_results = Column(JSON)
    raw_data = Column(JSON)
    industry = Column(String(255))
    classification = Column(String(50))  # DECISION_MAKER, KEY_CONTRIBUTOR, HIGH_IMPACT
    classification_confidence = Column(DECIMAL(3, 2))
    classification_reasoning = Column(Text)
    is_verified = Column(Boolean, default=False)
    last_enriched_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    contributor = relationship("Contributor", back_populates="social_context")


class SourcingJob(Base):
    """Sourcing job tracking."""
    __tablename__ = "sourcing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    total_steps = Column(Integer, default=0)
    current_step = Column(Integer, default=0)
    progress_percentage = Column(DECIMAL(5, 2), default=0.00)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)
    job_metadata = Column("metadata", JSON)  # Renamed to avoid SQLAlchemy reserved attribute
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="sourcing_jobs")
    repository = relationship("Repository", back_populates="sourcing_jobs")
    progress_steps = relationship("JobProgress", back_populates="job", cascade="all, delete-orphan")


class JobProgress(Base):
    """Job progress tracking."""
    __tablename__ = "job_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sourcing_jobs.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    message = Column(Text)
    details = Column(JSON)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("SourcingJob", back_populates="progress_steps")


class AppSetting(Base):
    """Application settings stored in DB (API keys, config)."""
    __tablename__ = "app_settings"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False, default='')
    description = Column(Text)
    is_secret = Column(Boolean, default=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Organization(Base):
    """Organization model."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    members = relationship("OrgMember", back_populates="organization", cascade="all, delete-orphan")
    settings = relationship("OrgSetting", back_populates="organization", cascade="all, delete-orphan")


class OrgMember(Base):
    """Organization membership."""
    __tablename__ = "org_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, default="member")
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('org_id', 'user_id', name='unique_org_member'),
    )

    organization = relationship("Organization", back_populates="members")


class OrgSetting(Base):
    """Per-org settings (API keys scoped to organization)."""
    __tablename__ = "org_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default='')
    is_secret = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('org_id', 'key', name='unique_org_setting'),
    )

    organization = relationship("Organization", back_populates="settings")


class ChatConversation(Base):
    """Chat conversations persisted per user and org."""
    __tablename__ = "chat_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, default="New conversation")
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ClayPushLog(Base):
    """Track which leads have been pushed to Clay."""
    __tablename__ = "clay_push_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sourcing_jobs.id", ondelete="CASCADE"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)  # 'success', 'failed', 'skipped'
    error_message = Column(Text)
    clay_response_status = Column(Integer)
    pushed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class OrgBilling(Base):
    """Organization billing account."""
    __tablename__ = "org_billing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_customer_id = Column(String(255))
    credit_balance = Column(DECIMAL(10, 2), default=0.00)
    total_credits_purchased = Column(DECIMAL(10, 2), default=0.00)
    total_credits_used = Column(DECIMAL(10, 2), default=0.00)
    total_enrichments = Column(Integer, default=0)
    is_byok = Column(Boolean, default=False)
    is_enterprise = Column(Boolean, default=False)
    auto_reload_enabled = Column(Boolean, default=False)
    auto_reload_threshold = Column(DECIMAL(10, 2), default=1.00)
    auto_reload_amount = Column(DECIMAL(10, 2), default=10.00)
    stripe_payment_method_id = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization")


class CreditTransaction(Base):
    """Credit transactions (purchases, grants, deductions)."""
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # 'purchase', 'grant', 'deduction', 'refund'
    amount = Column(DECIMAL(10, 4), nullable=False)  # positive for credits in, negative for deductions
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text)
    stripe_session_id = Column(String(255))
    job_id = Column(UUID(as_uuid=True), ForeignKey("sourcing_jobs.id", ondelete="SET NULL"))
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class UsageEvent(Base):
    """Usage metering (per-enrichment tracking)."""
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sourcing_jobs.id", ondelete="CASCADE"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False, default='enrichment')
    cost = Column(DECIMAL(10, 4), nullable=False)
    is_byok = Column(Boolean, default=False)
    volume_tier = Column(String(50))  # '1-1000', '1001-5000', etc.
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class FeatureFlag(Base):
    """Feature flags."""
    __tablename__ = "feature_flags"

    key = Column(String(255), primary_key=True)
    enabled = Column(Boolean, default=False)
    description = Column(Text)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class LeadScore(Base):
    """Lead scoring."""
    __tablename__ = "lead_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(DECIMAL(5, 2), default=0.00)
    activity_score = Column(DECIMAL(5, 2), default=0.00)
    influence_score = Column(DECIMAL(5, 2), default=0.00)
    position_score = Column(DECIMAL(5, 2), default=0.00)
    engagement_score = Column(DECIMAL(5, 2), default=0.00)
    is_qualified_lead = Column(Boolean, default=False)
    priority = Column(String(50))
    notes = Column(Text)
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('project_id', 'contributor_id', name='unique_project_contributor_score'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="lead_scores")
    contributor = relationship("Contributor", back_populates="lead_scores")
