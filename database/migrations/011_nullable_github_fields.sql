-- 011_nullable_github_fields.sql
-- Make GitHub-specific columns nullable so non-GitHub source types can be stored.
-- Safe to re-run.

ALTER TABLE community_sources ALTER COLUMN github_url DROP NOT NULL;
ALTER TABLE community_sources ALTER COLUMN owner DROP NOT NULL;
ALTER TABLE community_sources ALTER COLUMN repo_name DROP NOT NULL;

-- Replace the old unique constraint (project_id, github_url) with (project_id, external_url)
-- so duplicate detection works for all source types.
ALTER TABLE community_sources DROP CONSTRAINT IF EXISTS repositories_project_id_github_url_key;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'community_sources_project_external_url_key'
  ) THEN
    ALTER TABLE community_sources
      ADD CONSTRAINT community_sources_project_external_url_key UNIQUE (project_id, external_url);
  END IF;
END $$;
