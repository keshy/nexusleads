-- Add owner_id to lead_scores for lead assignment
ALTER TABLE lead_scores ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL;
