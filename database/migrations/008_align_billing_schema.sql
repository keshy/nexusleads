-- Migration 008: Align billing/usage schema with current SQLAlchemy models
-- Safe to re-run.

-- org_billing: add missing columns expected by backend models
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS total_credits_purchased DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS total_credits_used DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS total_enrichments INTEGER DEFAULT 0;
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS is_byok BOOLEAN DEFAULT false;
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS is_enterprise BOOLEAN DEFAULT false;
ALTER TABLE org_billing ADD COLUMN IF NOT EXISTS stripe_payment_method_id VARCHAR(255);

-- Backfill from older lifetime_* columns when present
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='org_billing' AND column_name='lifetime_credits_purchased'
  ) THEN
    EXECUTE 'UPDATE org_billing
             SET total_credits_purchased = COALESCE(total_credits_purchased, lifetime_credits_purchased, 0),
                 total_credits_used = COALESCE(total_credits_used, lifetime_credits_used, 0)
             WHERE total_credits_purchased IS NULL OR total_credits_used IS NULL';
  END IF;
END $$;

-- credit_transactions: add optional columns used by current backend
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(255);
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES sourcing_jobs(id) ON DELETE SET NULL;
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS contributor_id UUID REFERENCES contributors(id) ON DELETE SET NULL;

-- usage_events: add fields used by billing usage summaries
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS cost DECIMAL(10,4) DEFAULT 0.0;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS is_byok BOOLEAN DEFAULT false;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS volume_tier VARCHAR(50);

-- Backfill cost from older credits column when present
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='usage_events' AND column_name='credits'
  ) THEN
    EXECUTE 'UPDATE usage_events
             SET cost = COALESCE(cost, credits)
             WHERE cost IS NULL';
  END IF;
END $$;

-- clay_push_log: add response status used by model
ALTER TABLE clay_push_log ADD COLUMN IF NOT EXISTS clay_response_status INTEGER;
