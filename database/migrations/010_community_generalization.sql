-- Migration 010: Community Generalization
-- Evolve from GitHub-only to multi-community platform.
-- Safe to re-run (uses IF NOT EXISTS / IF EXISTS guards).

-- ============================================================
-- 1. Rename tables
-- ============================================================
ALTER TABLE IF EXISTS repositories RENAME TO community_sources;
ALTER TABLE IF EXISTS contributors RENAME TO members;
ALTER TABLE IF EXISTS repository_contributors RENAME TO community_members;
ALTER TABLE IF EXISTS contributor_stats RENAME TO member_activity;

-- ============================================================
-- 2. Add new columns to community_sources (was repositories)
-- ============================================================
ALTER TABLE community_sources
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) NOT NULL DEFAULT 'github_repo';

ALTER TABLE community_sources
    ADD COLUMN IF NOT EXISTS source_config JSONB;

ALTER TABLE community_sources
    ADD COLUMN IF NOT EXISTS external_url VARCHAR(500);

-- Backfill: copy github_url into external_url, pack GitHub-specific fields into source_config
UPDATE community_sources SET
    external_url = github_url,
    source_config = jsonb_build_object(
        'owner', owner,
        'repo_name', repo_name,
        'stars', stars,
        'forks', forks,
        'open_issues', open_issues,
        'language', language,
        'topics', topics
    )
WHERE external_url IS NULL;

-- ============================================================
-- 3. Add platform_identities to members (was contributors)
-- ============================================================
ALTER TABLE members
    ADD COLUMN IF NOT EXISTS platform_identities JSONB DEFAULT '{}';

-- Backfill: pack GitHub-specific IDs into platform_identities
UPDATE members SET
    platform_identities = jsonb_build_object(
        'github', jsonb_build_object(
            'id', github_id,
            'url', github_url,
            'username', username
        )
    )
WHERE platform_identities = '{}' OR platform_identities IS NULL;

-- ============================================================
-- 4. Add role to community_members (was repository_contributors)
-- ============================================================
ALTER TABLE community_members
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'contributor';

-- ============================================================
-- 5. Rename FK columns
-- ============================================================
-- community_members: repository_id -> source_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'community_members' AND column_name = 'repository_id') THEN
        ALTER TABLE community_members RENAME COLUMN repository_id TO source_id;
    END IF;
END $$;

-- community_members: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'community_members' AND column_name = 'contributor_id') THEN
        ALTER TABLE community_members RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- member_activity: repository_id -> source_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'member_activity' AND column_name = 'repository_id') THEN
        ALTER TABLE member_activity RENAME COLUMN repository_id TO source_id;
    END IF;
END $$;

-- member_activity: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'member_activity' AND column_name = 'contributor_id') THEN
        ALTER TABLE member_activity RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- Add activity_type and details to member_activity
ALTER TABLE member_activity
    ADD COLUMN IF NOT EXISTS activity_type VARCHAR(50) DEFAULT 'commit';

ALTER TABLE member_activity
    ADD COLUMN IF NOT EXISTS details JSONB;

-- sourcing_jobs: repository_id -> source_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sourcing_jobs' AND column_name = 'repository_id') THEN
        ALTER TABLE sourcing_jobs RENAME COLUMN repository_id TO source_id;
    END IF;
END $$;

-- social_context: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'social_context' AND column_name = 'contributor_id') THEN
        ALTER TABLE social_context RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- lead_scores: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'lead_scores' AND column_name = 'contributor_id') THEN
        ALTER TABLE lead_scores RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- clay_push_log: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'clay_push_log' AND column_name = 'contributor_id') THEN
        ALTER TABLE clay_push_log RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- credit_transactions: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'credit_transactions' AND column_name = 'contributor_id') THEN
        ALTER TABLE credit_transactions RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- usage_events: contributor_id -> member_id
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'usage_events' AND column_name = 'contributor_id') THEN
        ALTER TABLE usage_events RENAME COLUMN contributor_id TO member_id;
    END IF;
END $$;

-- ============================================================
-- 6. Add classification_labels and scoring_weights to projects
-- ============================================================
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS classification_labels JSONB;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS scoring_weights JSONB;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS scoring_preset VARCHAR(50);

-- ============================================================
-- 7. Rename constraints (safe — skip if already renamed)
-- ============================================================
DO $$ BEGIN
    ALTER TABLE community_sources RENAME CONSTRAINT unique_project_repo TO unique_project_source;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE community_members RENAME CONSTRAINT unique_repo_contributor TO unique_source_member;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE member_activity RENAME CONSTRAINT unique_repo_contributor_stats TO unique_source_member_activity;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE lead_scores RENAME CONSTRAINT unique_project_contributor_score TO unique_project_member_score;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

-- ============================================================
-- 8. Rename triggers
-- ============================================================
DROP TRIGGER IF EXISTS update_repositories_updated_at ON community_sources;
CREATE TRIGGER update_community_sources_updated_at BEFORE UPDATE ON community_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_contributors_updated_at ON members;
CREATE TRIGGER update_members_updated_at BEFORE UPDATE ON members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 9. Rename indexes
-- ============================================================
ALTER INDEX IF EXISTS idx_repositories_project_id RENAME TO idx_community_sources_project_id;
ALTER INDEX IF EXISTS idx_repositories_is_active RENAME TO idx_community_sources_is_active;
ALTER INDEX IF EXISTS idx_repositories_next_sourcing RENAME TO idx_community_sources_next_sourcing;

ALTER INDEX IF EXISTS idx_contributors_github_id RENAME TO idx_members_github_id;
ALTER INDEX IF EXISTS idx_contributors_username RENAME TO idx_members_username;

ALTER INDEX IF EXISTS idx_repo_contributors_repo RENAME TO idx_community_members_source;
ALTER INDEX IF EXISTS idx_repo_contributors_contributor RENAME TO idx_community_members_member;

ALTER INDEX IF EXISTS idx_contributor_stats_repo RENAME TO idx_member_activity_source;
ALTER INDEX IF EXISTS idx_contributor_stats_contributor RENAME TO idx_member_activity_member;
ALTER INDEX IF EXISTS idx_contributor_stats_activity RENAME TO idx_member_activity_recent;

ALTER INDEX IF EXISTS idx_social_context_contributor RENAME TO idx_social_context_member;

ALTER INDEX IF EXISTS idx_sourcing_jobs_repository RENAME TO idx_sourcing_jobs_source;

ALTER INDEX IF EXISTS idx_lead_scores_contributor RENAME TO idx_lead_scores_member;

-- New indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_members_platform_identities ON members USING gin (platform_identities);
CREATE INDEX IF NOT EXISTS idx_community_sources_source_type ON community_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_community_sources_source_config ON community_sources USING gin (source_config);
