-- Migration 006: Add clay_push_log table

CREATE TABLE IF NOT EXISTS clay_push_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    repository_id UUID REFERENCES repositories(id) ON DELETE SET NULL,
    job_id UUID REFERENCES sourcing_jobs(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, success, failed
    error_message TEXT,
    pushed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, contributor_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_clay_push_log_org ON clay_push_log(org_id);
CREATE INDEX IF NOT EXISTS idx_clay_push_log_contributor ON clay_push_log(contributor_id);
CREATE INDEX IF NOT EXISTS idx_clay_push_log_pushed ON clay_push_log(pushed_at DESC);
