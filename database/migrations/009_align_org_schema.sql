-- Migration 009: Align organization-related tables with SQLAlchemy models
-- Safe to re-run.

-- organizations: add audit columns expected by backend models
ALTER TABLE IF EXISTS organizations
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE IF EXISTS organizations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- org_settings: add columns expected by backend models
ALTER TABLE IF EXISTS org_settings
    ADD COLUMN IF NOT EXISTS is_secret BOOLEAN DEFAULT false;

ALTER TABLE IF EXISTS org_settings
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Ensure settings values are never null for ORM assumptions.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'org_settings'
  ) THEN
    UPDATE org_settings
    SET value = ''
    WHERE value IS NULL;
  END IF;
END $$;
