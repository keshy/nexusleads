# Feature: Clay.com Enterprise Integration

**Status**: Draft  
**Priority**: High  
**Author**: NexusLeads Team  
**Date**: 2026-02-11  

---

## 1. Overview

Integrate NexusLeads with [Clay.com](https://www.clay.com/) to enable one-click push of enriched leads into Clay tables. Clay is the dominant GTM data platform where sellers already live — this integration meets them where they are. The push to Clay is implemented as a tracked job (like existing sourcing/enrichment jobs) for full observability.

**Gating**: Available to all users during the free trial / pilot phase (when `BILLING_ENABLED = false`). Once billing is enabled, Clay integration is gated to **Enterprise** plan only. Users provide their own Clay credentials (BYOK model).

---

## 2. Goals

- One-click "Push to Clay" from the Leads page
- Push enriched lead data into a Clay table via Clay's webhook API
- Track the push as a monitored job with progress, success/failure per lead
- Store Clay credentials per-organization using existing settings infrastructure
- Gate behind Enterprise plan when billing is enabled

---

## 3. Clay Integration Architecture

### 3.1 How Clay Webhooks Work

Every Clay table has a unique **webhook URL**. When you POST data to it, Clay creates a new row in the table and can immediately trigger enrichment workflows on that data.

```
NexusLeads                          Clay
    |                                 |
    |-- POST lead data to webhook --->|
    |                                 |-- Creates row in Clay table
    |                                 |-- Triggers Clay enrichments
    |                                 |   (100+ data providers)
    |                                 |-- Seller works in Clay
```

### 3.2 What We Push

For each lead, we push a structured payload containing all NexusLeads enrichment data:

```json
{
  "_meta": {
    "source": "nexusleads",
    "nexusleads_project": "Acme Platform Leads",
    "nexusleads_project_id": "uuid",
    "nexusleads_repository": "acme/platform",
    "nexusleads_repository_id": "uuid",
    "nexusleads_contributor_id": "uuid",
    "pushed_at": "2026-02-11T00:00:00Z"
  },
  "github_username": "johndoe",
  "full_name": "John Doe",
  "email": "john@example.com",
  "github_url": "https://github.com/johndoe",
  "avatar_url": "https://avatars.githubusercontent.com/...",
  "company": "Acme Corp",
  "location": "San Francisco, CA",
  "bio": "Senior Engineer at Acme",
  "public_repos": 45,
  "followers": 230,
  "following": 120,
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "linkedin_headline": "Senior Software Engineer at Acme Corp",
  "current_company": "Acme Corp",
  "current_position": "Senior Software Engineer",
  "position_level": "Senior",
  "industry": "Technology",
  "years_of_experience": 8,
  "skills": ["Python", "Kubernetes", "Go"],
  "classification": "DECISION_MAKER",
  "classification_confidence": 0.87,
  "classification_reasoning": "Senior engineer with 8 years experience...",
  "overall_score": 82.5,
  "activity_score": 75.0,
  "influence_score": 88.0,
  "position_score": 90.0,
  "engagement_score": 70.0,
  "priority": "high",
  "is_qualified_lead": true,
  "raw_github_stats": {
    "total_commits": 342,
    "commits_last_3_months": 45,
    "commits_last_6_months": 98,
    "commits_last_year": 210,
    "pull_requests": 67,
    "issues_opened": 23,
    "issues_closed": 18,
    "code_reviews": 89,
    "is_maintainer": true,
    "is_core_team": false,
    "first_commit_date": "2024-03-15",
    "last_commit_date": "2026-02-10"
  }
}
```

### 3.3 Why This Is Valuable for Sellers

Once leads land in Clay, sellers can:
- Run Clay's 100+ enrichment providers (verified emails, phone numbers, company revenue, tech stack, funding data)
- Use AI to draft personalized outreach messages
- Sync directly to CRM (Salesforce, HubSpot)
- Build automated outreach sequences
- Score and prioritize using Clay's own scoring on top of NexusLeads scores

NexusLeads provides the **unique GitHub-sourced signal** that Clay doesn't have natively. Clay provides the **sales execution layer** that NexusLeads doesn't need to build.

---

## 4. User Experience

### 4.1 Integrations Page: Clay Configuration

In the **Integrations** page (see [Feature 003: Integrations Hub](./003-integrations-hub.md)), Clay configuration lives in the expandable detail panel:

| Setting | Description |
|---------|-------------|
| `CLAY_WEBHOOK_URL` | The webhook URL for the target Clay table |
| `CLAY_TABLE_NAME` | Display name for reference (optional, informational) |

These are stored as org-level settings using the existing `org_settings` infrastructure.

**Setup flow**:
1. User creates a table in Clay
2. User copies the table's webhook URL from Clay
3. User navigates to Integrations → Clay → Configure
4. User pastes webhook URL, NexusLeads validates the format
5. User clicks "Test" to verify connectivity with a sample payload

### 4.2 Leads Page: Push to Clay

**Single lead push**:
- Each lead row has a "Push to Clay" action button (icon: external link or Clay logo)
- Clicking it immediately queues a clay_push job for that single lead
- Toast notification: "Pushing 1 lead to Clay..."

**Bulk push**:
- Checkbox selection on the Leads table
- "Push to Clay" button in the bulk actions bar
- Confirmation modal: "Push X leads to Clay table [table_name]?"
- Queues a single clay_push job for all selected leads

**Filter-based push**:
- "Push All Filtered Leads to Clay" option
- Uses current filter/search criteria
- Shows count and confirmation

### 4.3 Push Status

- Job appears in the Jobs page like any other job
- Job type: `clay_push`
- Progress shows: "Pushed X of Y leads to Clay"
- Per-lead status tracked (success/failed per row)
- Failed leads can be retried

### 4.4 Auto-Export on Scan Completion

Projects can be configured to automatically push new leads to Clay after a sourcing/enrichment job completes. See [Feature 003: Integrations Hub](./003-integrations-hub.md) §6.2 for full UX.

**How it works**:
1. User enables "Auto-Export to Clay" in project settings
2. Optionally sets filters: minimum score threshold, classification types
3. When a sourcing/enrichment job completes for that project, the job processor checks for auto-export config
4. If enabled, a `clay_push` job is automatically queued with `push_mode: "auto"` and the configured filters
5. Only **new** leads (not previously pushed) are included

**Project settings stored in DB** (new columns on `projects` table or a `project_settings` JSON column):

| Setting | Type | Default |
|---------|------|---------|
| `auto_export_clay_enabled` | boolean | false |
| `auto_export_clay_min_score` | integer | null (no filter) |
| `auto_export_clay_classifications` | text[] | null (no filter) |

### 4.5 Duplicate Prevention

- Track which leads have been pushed to Clay (timestamp + job_id)
- Show "Already in Clay" indicator on leads that were previously pushed
- Option to "Push Again" (re-push with updated data)
- Bulk push skips already-pushed leads by default (with override option)

---

## 5. Backend Design

### 5.1 New Job Type: `clay_push`

```python
# Job metadata structure
{
    "job_type": "clay_push",
    "metadata": {
        "lead_ids": ["uuid1", "uuid2", ...],       # specific leads
        "project_id": "uuid",                        # for filter-based push
        "filters": { ... },                          # optional filter criteria
        "clay_webhook_url": "https://...",           # snapshot at job creation time
        "push_mode": "selected" | "filtered" | "all" | "auto",
        "auto_export_filters": {              # only for auto mode
            "min_score": 70,
            "classifications": ["DECISION_MAKER", "CHAMPION"]
        }
    }
}
```

### 5.2 Job Processing Flow

```
clay_push job starts
  → Step 1: "Preparing leads" (resolve lead list from IDs or filters)
  → Step 2: "Pushing to Clay" (iterate leads, POST each to webhook)
      For each lead:
        1. Build payload (gather contributor + social_context + lead_score data)
        2. POST to Clay webhook URL
        3. Record success/failure
        4. Update progress (X of Y)
        5. Rate limit: respect Clay's rate limits (configurable delay between pushes)
  → Step 3: "Completing" (summary: X pushed, Y failed, Z skipped)
```

### 5.3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/clay/push` | POST | Queue a clay_push job for selected leads |
| `POST /api/clay/push-filtered` | POST | Queue a clay_push job for filtered leads |
| `POST /api/clay/test` | POST | Test Clay webhook with a sample payload |
| `GET /api/clay/status` | GET | Check Clay integration status (configured, last push, etc.) |

### 5.4 Request/Response Examples

**Push selected leads:**
```json
POST /api/clay/push
{
    "lead_ids": ["uuid1", "uuid2", "uuid3"],
    "project_id": "project-uuid"
}

Response:
{
    "job_id": "job-uuid",
    "lead_count": 3,
    "message": "Clay push job queued"
}
```

**Test webhook:**
```json
POST /api/clay/test

Response:
{
    "success": true,
    "message": "Test payload sent to Clay successfully",
    "clay_response_status": 200
}
```

---

## 6. Database Schema

### 6.1 New Table

```sql
-- Track which leads have been pushed to Clay
CREATE TABLE clay_push_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES sourcing_jobs(id) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'skipped'
    error_message TEXT,
    clay_response_status INTEGER,
    pushed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for duplicate detection
CREATE INDEX idx_clay_push_log_contributor ON clay_push_log(org_id, contributor_id);
CREATE INDEX idx_clay_push_log_job ON clay_push_log(job_id);
```

### 6.2 Settings Keys

Stored in `org_settings` (existing infrastructure):

| Key | Description | Required |
|-----|-------------|----------|
| `CLAY_WEBHOOK_URL` | Clay table webhook URL | Yes (for Clay features) |
| `CLAY_TABLE_NAME` | Display name for the Clay table | No |
| `CLAY_RATE_LIMIT_MS` | Delay between pushes in ms (default: 200) | No |

---

## 7. Feature Gating

### 7.1 Gating Logic

```python
def can_use_clay(org_id, billing_enabled):
    if not billing_enabled:
        # Pilot mode: everyone gets access
        return True
    
    # Billing enabled: enterprise only
    org_billing = get_org_billing(org_id)
    return org_billing.is_enterprise
```

### 7.2 UI Gating

When Clay is not available (billing enabled + not enterprise):
- "Push to Clay" buttons show a lock icon
- Clicking shows: "Clay integration is available on the Enterprise plan. Contact us to upgrade."
- Settings → Integrations → Clay section shows Enterprise badge

When Clay is available but not configured:
- "Push to Clay" buttons show with a setup prompt
- Clicking shows: "Configure your Clay webhook URL in Settings → Integrations"

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| Clay webhook URL not configured | Block push, show setup prompt |
| Clay webhook returns 4xx | Mark lead as failed, log error, continue with next |
| Clay webhook returns 5xx | Retry up to 3 times with exponential backoff, then mark failed |
| Clay webhook timeout (>30s) | Mark as failed, continue |
| Network error | Retry up to 3 times, then mark failed |
| Rate limited by Clay | Back off, increase delay, retry |
| All leads fail | Mark job as failed with summary |
| Partial failure | Mark job as completed with warnings, show success/fail counts |

---

## 9. Implementation Plan

### Phase 1: Backend Infrastructure
1. Add `clay_push` job type to job processor
2. Create `clay_push_log` table
3. Add Clay settings to `MANAGED_SETTINGS` (with hints, help URL)
4. Implement Clay webhook push service (`jobs/services/clay_service.py`)
5. Add `/api/clay/*` endpoints

### Phase 2: Frontend — Integrations Page
6. Clay config in Integrations page detail panel (see Feature 003)
7. Clay webhook URL configuration with test button
8. Validation and connection test UI

### Phase 3: Frontend — Leads Page
9. Add "Push to Clay" button per lead row
10. Add bulk selection + "Push to Clay" bulk action
11. "Already in Clay" indicator on previously pushed leads
12. Push confirmation modal with lead count

### Phase 4: Job Tracking
13. Clay push job appears in Jobs page with proper progress
14. Per-lead push status in job detail view
15. Retry failed leads action

### Phase 5: Auto-Export
16. Add auto-export settings to project configuration UI
17. Add post-job hook in job_processor to check auto-export config and queue clay_push
18. Filter logic: min score, classification types, exclude already-pushed

### Phase 6: Gating
19. Enterprise gating logic (respects `BILLING_ENABLED` flag)
20. Gated UI states (lock icons, upgrade prompts)

---

## 10. Testing Checklist

- [ ] Clay webhook URL can be saved in org settings
- [ ] Test webhook sends sample payload and reports success/failure
- [ ] Single lead push creates a clay_push job
- [ ] Bulk lead push creates a clay_push job with all selected leads
- [ ] Job progress updates correctly (X of Y pushed)
- [ ] Failed pushes are logged with error details
- [ ] Retries work for 5xx errors
- [ ] Rate limiting is respected
- [ ] Duplicate detection works (already-pushed leads shown)
- [ ] Re-push option works for previously pushed leads
- [ ] `BILLING_ENABLED = false` → Clay available to all
- [ ] `BILLING_ENABLED = true` + not enterprise → Clay gated with upgrade prompt
- [ ] `BILLING_ENABLED = true` + enterprise → Clay available
- [ ] Clay not configured → setup prompt instead of push
- [ ] Job appears in Jobs page with correct type and progress
- [ ] Partial failures handled gracefully (job completes with warnings)
- [ ] Auto-export triggers clay_push after sourcing job completes
- [ ] Auto-export respects score and classification filters
- [ ] Auto-export skips already-pushed leads
- [ ] Auto-export does not trigger if Clay is not configured

---

## 11. Future Enhancements (v2)

1. **Pull from Clay**: Receive enrichment data back from Clay via webhook (verified emails, phone numbers) to enhance NexusLeads profiles
2. **Bidirectional sync**: Automatic sync — new leads auto-push to Clay, Clay enrichments auto-pull back
3. **Multiple Clay tables**: Support pushing different lead segments to different Clay tables
4. **Clay table templates**: Pre-built Clay table schemas optimized for NexusLeads data
5. **Field mapping UI**: Let users customize which NexusLeads fields map to which Clay columns
6. **Scheduled push**: Auto-push new qualified leads to Clay on a schedule

---

## 12. Resolved Decisions

| Question | Decision |
|----------|----------|
| Multiple Clay webhook URLs? | No — one per org for now. `_meta` block includes project/repo IDs so users can disambiguate on Clay side |
| Include raw GitHub stats? | Yes — full raw stats included in `raw_github_stats` nested object |
| Clay branding in UI? | TBD — can decide during implementation |
| Track Clay credit consumption? | No — out of scope, Clay handles their own billing |
