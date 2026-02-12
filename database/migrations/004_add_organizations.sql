-- Migration 004: Add organizations, org_members, org_settings tables
-- and add org_id to projects

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, user_id)
);

CREATE TABLE IF NOT EXISTS org_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, key)
);

-- Add org_id to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

-- Add auto-export Clay columns to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS auto_export_clay_enabled BOOLEAN DEFAULT false;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS auto_export_clay_min_score DECIMAL(5,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS auto_export_clay_classifications TEXT[];

-- Indexes
CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_settings_org ON org_settings(org_id);
CREATE INDEX IF NOT EXISTS idx_projects_org_id ON projects(org_id);

-- Seed: create a default org for the admin user and migrate existing projects
DO $$
DECLARE
    admin_id UUID;
    default_org_id UUID;
BEGIN
    SELECT id INTO admin_id FROM users WHERE username = 'admin' LIMIT 1;
    IF admin_id IS NOT NULL THEN
        INSERT INTO organizations (name, slug) VALUES ('Default', 'default')
        ON CONFLICT (slug) DO NOTHING
        RETURNING id INTO default_org_id;

        IF default_org_id IS NULL THEN
            SELECT id INTO default_org_id FROM organizations WHERE slug = 'default';
        END IF;

        INSERT INTO org_members (org_id, user_id, role)
        VALUES (default_org_id, admin_id, 'owner')
        ON CONFLICT (org_id, user_id) DO NOTHING;

        -- Migrate existing projects to the default org
        UPDATE projects SET org_id = default_org_id WHERE org_id IS NULL;

        -- Migrate app_settings to org_settings
        INSERT INTO org_settings (org_id, key, value)
        SELECT default_org_id, key, value FROM app_settings
        ON CONFLICT (org_id, key) DO NOTHING;
    END IF;
END $$;
