-- Add source column to contributor_stats to track how a contributor was discovered
ALTER TABLE contributor_stats ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'commit';

-- Add index for filtering by source
CREATE INDEX IF NOT EXISTS idx_contributor_stats_source ON contributor_stats(source);
