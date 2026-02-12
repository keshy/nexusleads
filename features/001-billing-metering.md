# 001 — Billing & Metering

## Overview

Stripe-based prepaid credit billing system. Organizations purchase credits that are consumed when contributors are enriched.

## Pricing

- **1 credit = 1 contributor enriched**
- Managed keys: $0.05/enrichment
- BYOK (Bring Your Own Keys): $0.02/enrichment
- Volume discounts:
  - 1K credits: 10% off
  - 5K credits: 20% off
  - 25K credits: 30% off

## Credit System

- Minimum top-up: $10
- Top-up increments: $10
- **$5.00 one-time free grant** for new organizations
- Auto-reload opt-in:
  - Customer controls threshold + reload amount
  - Requires saved payment method (Stripe)

## Master Toggle

- `BILLING_ENABLED` feature flag (stored in `feature_flags` table)
- `false` during pilot → silent metering only (usage tracked, no enforcement)
- `true` → full enforcement (credits required to run enrichment jobs)

## Job Behavior

- When credits are exhausted: job status = `out_of_credits` (resumable once credits added)
- Low balance warnings shown in UI when balance < threshold
- Billing is **per-organization**, not per-user

## Database Tables

- `org_billing` — one row per org: balance, lifetime stats, Stripe customer ID, auto-reload config
- `credit_transactions` — ledger: purchases, grants, deductions, refunds
- `usage_events` — per-enrichment metering: event type, credits consumed, job/contributor refs

## Implementation Phases

1. **Metering infra** — usage_events table, record events on enrichment, silent mode
2. **Stripe integration** — checkout sessions, webhooks, credit purchases, free grant
3. **Enforcement** — check balance before job, out_of_credits status, low balance warnings
4. **Polish** — billing dashboard tab, transaction history, auto-reload UI, volume tier display
