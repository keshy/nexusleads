"""Database models for job processor."""
import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DECIMAL, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """User model (minimal, for foreign key resolution)."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)


class Organization(Base):
    """Organization model."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class OrgMember(Base):
    """Organization membership."""
    __tablename__ = "org_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(String(50), default="member")
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class OrgSetting(Base):
    """Per-org settings."""
    __tablename__ = "org_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Project(Base):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    auto_export_clay_enabled = Column(Boolean, default=False)
    auto_export_clay_min_score = Column(DECIMAL(5, 2), nullable=True)
    auto_export_clay_classifications = Column(ARRAY(Text), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Repository(Base):
    """Repository model."""
    __tablename__ = "repositories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
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


class Contributor(Base):
    """Contributor model."""
    __tablename__ = "contributors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
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


class RepositoryContributor(Base):
    """Repository-Contributor relationship."""
    __tablename__ = "repository_contributors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"))
    discovered_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ContributorStats(Base):
    """Contributor statistics."""
    __tablename__ = "contributor_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"))
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


class SocialContext(Base):
    """Social context for contributors."""
    __tablename__ = "social_context"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"))
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
    classification = Column(String(50))
    classification_confidence = Column(DECIMAL(3, 2))
    classification_reasoning = Column(Text)
    is_verified = Column(Boolean, default=False)
    last_enriched_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class LeadScore(Base):
    """Lead scoring."""
    __tablename__ = "lead_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    overall_score = Column(DECIMAL(5, 2), default=0.00)
    activity_score = Column(DECIMAL(5, 2), default=0.00)
    influence_score = Column(DECIMAL(5, 2), default=0.00)
    position_score = Column(DECIMAL(5, 2), default=0.00)
    engagement_score = Column(DECIMAL(5, 2), default=0.00)
    is_qualified_lead = Column(Boolean, default=False)
    priority = Column(String(50))
    notes = Column(Text)
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


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


class AppSetting(Base):
    """Application settings stored in DB."""
    __tablename__ = "app_settings"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False, default='')
    description = Column(Text)
    is_secret = Column(Boolean, default=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class JobProgress(Base):
    """Job progress tracking."""
    __tablename__ = "job_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sourcing_jobs.id", ondelete="CASCADE"))
    step_name = Column(String(255), nullable=False)
    step_number = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    message = Column(Text)
    details = Column(JSON)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)
    step_metadata = Column("metadata", JSON)  # Renamed to avoid SQLAlchemy reserved attribute
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
