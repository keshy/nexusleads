-- Migration 005: Add billing tables (org_billing, credit_transactions, usage_events)

CREATE TABLE IF NOT EXISTS org_billing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    credit_balance DECIMAL(12,2) DEFAULT 0.00,
    lifetime_credits_purchased DECIMAL(12,2) DEFAULT 0.00,
    lifetime_credits_used DECIMAL(12,2) DEFAULT 0.00,
    free_grant_applied BOOLEAN DEFAULT false,
    stripe_customer_id VARCHAR(255),
    auto_reload_enabled BOOLEAN DEFAULT false,
    auto_reload_threshold DECIMAL(12,2),
    auto_reload_amount DECIMAL(12,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- purchase, usage, grant, refund
    amount DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2),
    description TEXT,
    reference_id VARCHAR(255), -- stripe payment intent, job id, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- enrichment, clay_push, etc.
    credits DECIMAL(12,4) DEFAULT 0,
    job_id UUID REFERENCES sourcing_jobs(id) ON DELETE SET NULL,
    contributor_id UUID REFERENCES contributors(id) ON DELETE SET NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_org_billing_org ON org_billing(org_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_org ON credit_transactions(org_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_org ON usage_events(org_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events(created_at DESC);
