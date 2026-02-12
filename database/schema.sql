-- PLG Lead Sourcer Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (for authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[], -- User-defined tags for categorization
    external_urls TEXT[], -- Additional URLs to track (websites, docs, etc.)
    sourcing_context TEXT, -- Context/criteria for lead sourcing
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Repositories table
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    github_url VARCHAR(500) NOT NULL,
    full_name VARCHAR(255) NOT NULL, -- owner/repo
    owner VARCHAR(255) NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    description TEXT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    open_issues INTEGER DEFAULT 0,
    language VARCHAR(100),
    topics TEXT[], -- Array of tags/topics
    last_sourced_at TIMESTAMP WITH TIME ZONE,
    sourcing_interval VARCHAR(50) DEFAULT 'monthly', -- daily, weekly, monthly
    next_sourcing_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, github_url)
);

-- Contributors table (GitHub users)
CREATE TABLE contributors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id INTEGER UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    company VARCHAR(255),
    location VARCHAR(255),
    bio TEXT,
    blog VARCHAR(500),
    twitter_username VARCHAR(255),
    avatar_url VARCHAR(500),
    github_url VARCHAR(500),
    public_repos INTEGER DEFAULT 0,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Repository contributors relationship
CREATE TABLE repository_contributors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, contributor_id)
);

-- Contributor stats (activity metrics)
CREATE TABLE contributor_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    total_commits INTEGER DEFAULT 0,
    commits_last_3_months INTEGER DEFAULT 0,
    commits_last_6_months INTEGER DEFAULT 0,
    commits_last_year INTEGER DEFAULT 0,
    first_commit_date TIMESTAMP WITH TIME ZONE,
    last_commit_date TIMESTAMP WITH TIME ZONE,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    pull_requests INTEGER DEFAULT 0,
    issues_opened INTEGER DEFAULT 0,
    issues_closed INTEGER DEFAULT 0,
    code_reviews INTEGER DEFAULT 0,
    is_maintainer BOOLEAN DEFAULT false,
    is_core_team BOOLEAN DEFAULT false,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, contributor_id)
);

-- Social context (LinkedIn/web search enrichment)
CREATE TABLE social_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    linkedin_url VARCHAR(500),
    linkedin_profile_photo_url VARCHAR(500), -- LinkedIn profile photo
    linkedin_headline TEXT,
    current_company VARCHAR(255),
    current_position VARCHAR(255),
    position_level VARCHAR(100), -- Entry, Mid, Senior, Lead, Manager, Director, VP, C-Suite
    years_of_experience INTEGER,
    skills TEXT[],
    search_results JSONB, -- Raw search results
    raw_data JSONB, -- Full enriched data (network, career, contacts, company intel)
    classification VARCHAR(50), -- DECISION_MAKER, KEY_CONTRIBUTOR, HIGH_IMPACT
    classification_confidence DECIMAL(3,2), -- 0.00 to 1.00
    classification_reasoning TEXT,
    is_verified BOOLEAN DEFAULT false,
    last_enriched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contributor_id)
);

-- Sourcing jobs (background job tracking)
CREATE TABLE sourcing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- repository_sourcing, social_enrichment, similar_repos
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    total_steps INTEGER DEFAULT 0,
    current_step INTEGER DEFAULT 0,
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB, -- Additional job-specific data
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Job progress (detailed progress tracking)
CREATE TABLE job_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES sourcing_jobs(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    message TEXT,
    details JSONB,
    metadata JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Lead scores (computed scores for prioritization)
CREATE TABLE lead_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) DEFAULT 0.00, -- 0.00 to 100.00
    activity_score DECIMAL(5,2) DEFAULT 0.00,
    influence_score DECIMAL(5,2) DEFAULT 0.00,
    position_score DECIMAL(5,2) DEFAULT 0.00,
    engagement_score DECIMAL(5,2) DEFAULT 0.00,
    is_qualified_lead BOOLEAN DEFAULT false,
    priority VARCHAR(50), -- high, medium, low
    notes TEXT,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, contributor_id)
);

-- Application settings (API keys, configuration managed via UI)
CREATE TABLE app_settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description TEXT,
    is_secret BOOLEAN DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_is_active ON projects(is_active);

CREATE INDEX idx_repositories_project_id ON repositories(project_id);
CREATE INDEX idx_repositories_is_active ON repositories(is_active);
CREATE INDEX idx_repositories_next_sourcing ON repositories(next_sourcing_at) WHERE is_active = true;

CREATE INDEX idx_contributors_github_id ON contributors(github_id);
CREATE INDEX idx_contributors_username ON contributors(username);

CREATE INDEX idx_repo_contributors_repo ON repository_contributors(repository_id);
CREATE INDEX idx_repo_contributors_contributor ON repository_contributors(contributor_id);

CREATE INDEX idx_contributor_stats_repo ON contributor_stats(repository_id);
CREATE INDEX idx_contributor_stats_contributor ON contributor_stats(contributor_id);
CREATE INDEX idx_contributor_stats_activity ON contributor_stats(commits_last_3_months DESC);

CREATE INDEX idx_social_context_contributor ON social_context(contributor_id);
CREATE INDEX idx_social_context_classification ON social_context(classification);

CREATE INDEX idx_sourcing_jobs_project ON sourcing_jobs(project_id);
CREATE INDEX idx_sourcing_jobs_repository ON sourcing_jobs(repository_id);
CREATE INDEX idx_sourcing_jobs_status ON sourcing_jobs(status);
CREATE INDEX idx_sourcing_jobs_created_at ON sourcing_jobs(created_at DESC);

CREATE INDEX idx_job_progress_job_id ON job_progress(job_id);

CREATE INDEX idx_lead_scores_project ON lead_scores(project_id);
CREATE INDEX idx_lead_scores_contributor ON lead_scores(contributor_id);
CREATE INDEX idx_lead_scores_overall ON lead_scores(overall_score DESC);
CREATE INDEX idx_lead_scores_qualified ON lead_scores(is_qualified_lead) WHERE is_qualified_lead = true;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contributors_updated_at BEFORE UPDATE ON contributors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_context_updated_at BEFORE UPDATE ON social_context
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sourcing_jobs_updated_at BEFORE UPDATE ON sourcing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
-- Password hash generated using bcrypt
INSERT INTO users (username, email, password_hash, full_name, is_admin)
VALUES (
    'admin',
    'admin@plgleadsourcer.com',
    '$2b$12$dLt7uCAH40yUhPTLqIqxbe7Huzf1FiqV4SpLDBL67YJcbDALXDH4K',
    'System Administrator',
    true
)
ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Sample data for testing (optional)
-- Uncomment to add sample project

-- INSERT INTO projects (user_id, name, description)
-- SELECT id, 'Sample Project', 'A sample project for testing'
-- FROM users WHERE username = 'admin';
