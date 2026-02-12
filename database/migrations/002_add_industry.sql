-- Migration: Add industry column to social_context
-- Usage: docker exec plg-postgres psql -U plg_user -d plg_lead_sourcer -f /docker-entrypoint-initdb.d/migrations/002_add_industry.sql

ALTER TABLE social_context ADD COLUMN IF NOT EXISTS industry VARCHAR(255);
