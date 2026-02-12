# Interview Problem Pool: AI-First Engineering

## Purpose
Provide a shared set of problem scenarios that align to our AI-first hiring philosophy. Each scenario is designed to support the single-threaded interview loop, where candidates build on the same problem across rounds. Interviewers should select one scenario and stick to it throughout the loop.

## How To Use
- Pick one scenario per candidate.
- Run it end-to-end across rounds 1-6.
- Keep constraints consistent but add new requirements each round.
- Use the “round prompts” below as defaults and customize only if needed.

---

## Scenario A: Integrations Hub for Lead Sources

### Overview
Build a multi-tenant integrations hub that connects to lead data providers and normalizes lead data into the platform.

### Core Entities
- Provider: external data source (Clay, Apollo, Clearbit-like API).
- Connection: tenant-specific auth and configuration for a provider.
- Lead: normalized entity with provenance and enrichment fields.
- Job: background sync or on-demand import.

### Round Prompts

#### Round 1: Async Build
- Implement CSV upload and one external provider integration.
- Normalize lead data into a canonical schema.
- Add basic dedupe logic and an audit trail entry per import.

#### Round 2: Live AI Pairing
- Add a new provider with stricter rate limits and partial data returns.
- Add retries with exponential backoff and idempotency keys.
- Explain how you validate AI-generated code or schema mappings.

#### Round 3: Production Engineering
- Add per-tenant quotas and billing metering per enrichment call.
- Define SLOs, alerts, and a rollback strategy.
- Add observability for import latency and error rates.

#### Round 4: Evals and Data Quality
- Design an eval harness to measure enrichment accuracy and dedupe quality.
- Define gold data sources and an approach for noisy ground truth.
- Propose a monitoring plan for drift and provider quality regressions.

#### Round 5: AI-Mediated System Design
- Design the full architecture for multi-tenant scaling and data residency.
- Decide where to place normalization, enrichment, and dedupe in the pipeline.
- Clarify SLAs, compliance requirements, and cost constraints before designing.

#### Round 6: Communication and Execution
- Present a 5-minute executive summary and a 5-minute technical deep dive.
- Explain the largest risk and the mitigation plan.

---

## Scenario B: Clay Workflow Orchestration

### Overview
Build a workflow engine that uses Clay-style enrichment blocks to enrich and score leads in batches.

### Core Entities
- Workflow: a sequence of steps with inputs and outputs.
- Step: a single provider call or transformation.
- Run: execution instance of a workflow for a batch of leads.
- Result: output data and scoring metadata.

### Round Prompts

#### Round 1: Async Build
- Build a simple workflow runner with two steps and a batch input.
- Capture step outputs and persist results with provenance.

#### Round 2: Live AI Pairing
- Add branching based on output quality thresholds.
- Add a new step with caching and retry logic.

#### Round 3: Production Engineering
- Add concurrency controls and backpressure.
- Define failure handling and partial completion behavior.
- Add audit logs for workflow runs.

#### Round 4: Evals and Data Quality
- Design evals for scoring accuracy and step effectiveness.
- Define a dataset and baseline metrics for workflow quality.

#### Round 5: AI-Mediated System Design
- Design the system architecture for large batch workflows and tenant isolation.
- Identify bottlenecks and tradeoffs.

#### Round 6: Communication and Execution
- Summarize tradeoffs to an exec audience and propose a rollout plan.

---

## Scenario C: Billing and Metering for AI Enrichment

### Overview
Implement metering and billing for AI-based lead enrichment. Ensure accurate accounting, auditability, and fair use.

### Core Entities
- MeteredEvent: unit of usage (API call, token usage, enrichment run).
- Account: tenant billing entity.
- Invoice: aggregation of usage events.
- Quota: plan limits and overages.

### Round Prompts

#### Round 1: Async Build
- Implement event capture and aggregation per tenant.
- Generate a draft invoice summary view.

#### Round 2: Live AI Pairing
- Add real-time usage alerts and soft limits.
- Add reconciliation logic for duplicate events.

#### Round 3: Production Engineering
- Design durability guarantees and idempotency.
- Add auditability and immutable logs for billing events.

#### Round 4: Evals and Data Quality
- Define how to detect billing anomalies and data errors.
- Build an eval dataset of known-good billing events.

#### Round 5: AI-Mediated System Design
- Design end-to-end billing architecture, including payments, retries, and disputes.
- Clarify compliance constraints before designing.

#### Round 6: Communication and Execution
- Present a billing risk review and mitigation plan.

---

## Scenario D: Lead Scoring and Ranking Pipeline

### Overview
Create a lead scoring pipeline that uses external data and AI to rank leads by priority and fit.

### Core Entities
- Lead: entity to score.
- Score: multi-factor score with explainability.
- ModelVersion: scoring model and config.
- Evaluation: batch evaluation results.

### Round Prompts

#### Round 1: Async Build
- Implement a basic scoring pipeline with a small rules-based baseline.
- Store score explanations and provenance.

#### Round 2: Live AI Pairing
- Add AI-based scoring and fallback rules.
- Add a new data source with missing or noisy fields.

#### Round 3: Production Engineering
- Add versioning, rollback, and A/B scoring.
- Define monitoring for score drift and latency.

#### Round 4: Evals and Data Quality
- Create eval datasets and metrics for scoring quality.
- Define false positive and false negative risk thresholds.

#### Round 5: AI-Mediated System Design
- Design the scoring pipeline at scale with latency constraints.
- Clarify data governance and explainability requirements.

#### Round 6: Communication and Execution
- Present how scoring changes impact revenue and conversion.

---

## Scenario E: Integrations Reliability and Sync Engine

### Overview
Build a robust sync engine for pulling lead data from multiple providers on schedules and on-demand triggers.

### Core Entities
- SyncJob: scheduled or manual job definition.
- SyncRun: execution of a job.
- ProviderCursor: state for incremental sync.
- ErrorPolicy: per-provider retry and fallback.

### Round Prompts

#### Round 1: Async Build
- Implement a basic scheduled sync from one provider.
- Persist cursors and avoid duplicates.

#### Round 2: Live AI Pairing
- Add on-demand sync with concurrency limits.
- Add provider-specific retry policies.

#### Round 3: Production Engineering
- Add monitoring for stale syncs and job failures.
- Implement dead-letter handling and recovery flows.

#### Round 4: Evals and Data Quality
- Define completeness and freshness metrics.
- Build an evaluation plan for sync accuracy.

#### Round 5: AI-Mediated System Design
- Design multi-tenant scheduling, rate limiting, and isolation.
- Clarify SLAs and data residency constraints.

#### Round 6: Communication and Execution
- Present operational risks and scaling plan.

