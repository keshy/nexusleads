# Feature: Integrations Hub & Platform UX Evolution

**Status**: Draft  
**Priority**: High  
**Author**: NexusLeads Team  
**Date**: 2026-02-11  

---

## 1. Overview

Add a dedicated **Integrations** page to NexusLeads that transforms the product narrative from "GitHub lead visibility tool" to **"open-source-to-pipeline action platform."** The Integrations Hub is the connective tissue between NexusLeads' enrichment engine and the seller's existing workflow — CRMs, outreach tools, data platforms, and notification systems.

Clay is the first live integration. The page also showcases future connectors (Salesforce, HubSpot, Outreach, Slack, Webhooks) as "coming soon" or enterprise-gated tiles, signaling platform ambition and driving enterprise upsell.

This feature also includes updates to the **Landing page** and **Leads page** to reinforce the "Source → Enrich → Score → **Act**" narrative throughout the product.

---

## 2. The Problem We're Solving

### Current state
NexusLeads today tells the story: **"Find leads in open source."** The app flow is:

```
Dashboard → Projects → Repositories → Leads → (dead end)
```

Leads is a report. Users see scores, classifications, LinkedIn URLs — then what? They copy-paste into spreadsheets, manually enter into CRMs, or context-switch to Clay/Apollo/Outreach. The value chain breaks at the moment of action.

### Desired state
NexusLeads tells the story: **"Turn open source into pipeline."** The app flow becomes:

```
Dashboard → Projects → Repositories → Leads → ACT
                                                 ├── Push to Clay
                                                 ├── Sync to Salesforce (enterprise)
                                                 ├── Send to Outreach (enterprise)
                                                 ├── Notify via Slack (enterprise)
                                                 └── Trigger via Webhook (enterprise)
```

The Integrations Hub is where users **configure** these action channels. The Leads page is where they **trigger** them.

---

## 3. Goals

- Create a dedicated Integrations page at `/app/integrations`
- Visually communicate platform breadth (live + coming soon connectors)
- Separate "infrastructure config" (API keys in Settings) from "sales action config" (integrations)
- Drive enterprise upsell through visible but gated connectors
- Update Landing page to reflect the "Source → Act" narrative
- Add action buttons on Leads page that connect to configured integrations

---

## 4. Information Architecture

### 4.1 Navigation Restructure

**Current sidebar:**
```
Dashboard
Projects
Repositories
Leads
Jobs
Settings
```

**New sidebar:**
```
Dashboard
Projects
Repositories
Leads
Jobs
─────────────          ← visual separator (subtle border or spacing)
Integrations           ← NEW (Blocks icon from Lucide)
Settings
```

**Why this order**: The top group is the **data pipeline** (discover → enrich → score → view). The bottom group is **platform config** (connect → configure). Integrations sits above Settings because it's more action-oriented — you go there to *do* something, not just configure.

### 4.2 What Lives Where

| Page | Purpose | Contains |
|------|---------|----------|
| **Settings** | Infrastructure & identity | Profile, password, org management, API keys (GitHub, OpenAI, Serper), billing |
| **Integrations** | Sales action channels | Clay, Salesforce, HubSpot, Outreach, Slack, Webhooks — config + status + history |

**Rule of thumb**: If it powers the enrichment engine → Settings. If it connects to where sellers work → Integrations.

---

## 5. Integrations Page Design

### 5.1 Page Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Integrations                                                     │
│  Connect NexusLeads to your sales stack. Push enriched leads      │
│  directly into the tools your team already uses.                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  YOUR PIPELINE          Source → Enrich → Score → ACT      │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  │
│  │  NexusLeads finds the leads. These integrations close them. │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  DATA PLATFORMS                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │  ◉ Clay          │  │  ◎ Apollo.io     │                      │
│  │  ✅ Connected     │  │  Coming Soon     │                      │
│  │  Last push: 2h   │  │                  │                      │
│  │  [Configure]     │  │  [Notify Me]     │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                   │
│  CRM                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │  🔒 Salesforce   │  │  🔒 HubSpot     │                      │
│  │  Enterprise      │  │  Enterprise      │                      │
│  │  [Upgrade]       │  │  [Upgrade]       │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                   │
│  OUTREACH & NOTIFICATIONS                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  🔒 Outreach.io  │  │  🔒 Slack       │  │ 🔒 Webhooks   │  │
│  │  Enterprise      │  │  Enterprise      │  │ Enterprise     │  │
│  │  [Upgrade]       │  │  [Upgrade]       │  │ [Upgrade]      │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                   │
│  ═══════════════════════════════════════════════════════════════   │
│                                                                   │
│  CLAY INTEGRATION  (expanded detail panel when configured)        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Status: ✅ Connected                                       │  │
│  │  Webhook URL: https://hook.clay.com/... [Edit] [Test]       │  │
│  │  Table Name: NexusLeads Inbound                             │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────┐    │  │
│  │  │  RECENT ACTIVITY                                     │    │  │
│  │  │  Feb 11 — Pushed 23 leads (22 ✓, 1 ✗)  [View Job]  │    │  │
│  │  │  Feb 10 — Pushed 8 leads  (8 ✓, 0 ✗)   [View Job]  │    │  │
│  │  │  Feb 9  — Pushed 45 leads (43 ✓, 2 ✗)  [View Job]  │    │  │
│  │  └─────────────────────────────────────────────────────┘    │  │
│  │                                                              │  │
│  │  Total pushed: 312 leads  |  Success rate: 97.4%            │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Integration Tile States

Each integration tile has one of these states:

| State | Visual | Behavior |
|-------|--------|----------|
| **Available + Connected** | Green dot, "Connected", last activity | Click → expand config + activity panel |
| **Available + Not configured** | Gray dot, "Not configured" | Click → setup wizard / config form |
| **Enterprise-gated** | Lock icon, "Enterprise" badge | Click → upgrade prompt with feature description |
| **Coming Soon** | Dimmed, "Coming Soon" badge | Click → shows feature preview description (no backend capture) |

### 5.3 Integration Categories

| Category | Integrations | Status |
|----------|-------------|--------|
| **Data Platforms** | Clay, Apollo.io | Clay = live; Apollo = coming soon |
| **CRM** | Salesforce, HubSpot | Enterprise, coming soon |
| **Outreach & Notifications** | Outreach.io, Slack, Webhooks | Enterprise, coming soon |

### 5.4 Integration Detail Panel

When a user clicks on a connected/available integration tile, the detail panel expands below the tile grid. It contains:

1. **Connection status** — green/red indicator with last successful push timestamp
2. **Configuration** — webhook URL, table name, etc. (integration-specific)
3. **Test button** — sends a sample payload and shows success/failure
4. **Recent activity** — last 5 push jobs with lead count, success/fail, link to Jobs page
5. **Aggregate stats** — total leads pushed, success rate, first/last push date

---

## 6. Leads Page Enhancements

### 6.1 Action Buttons

The Leads page gets new action capabilities that connect to configured integrations:

**Per-lead actions** (in each lead row):
```
[LinkedIn ↗]  [GitHub ↗]  [Push to Clay ↗]
```

**Bulk actions per project group** (checkboxes within each expanded project):
```
┌─ Project: Acme Platform Leads ──────────────────────┐
│  ☑ Select All (23 leads)                             │
│  ☐ John Doe — Senior Engineer — Score: 82            │
│  ☐ Jane Smith — VP Engineering — Score: 91           │
│  ...                                                 │
│  [Push Selected to Clay]  [Export Selected CSV]      │
└──────────────────────────────────────────────────────┘
```

Checkboxes live within each project group, preserving the current grouped layout.

### 6.2 Auto-Export on Scan Completion

In **Project Settings / Configuration**, users can enable automatic push to integrations after a sourcing job completes:

```
┌─ Project Settings ──────────────────────────────────┐
│  Auto-Export After Scan                              │
│                                                      │
│  ☐ Push new leads to Clay automatically              │
│    Only push leads scoring above: [70] (optional)    │
│    Only push classifications: [DECISION_MAKER, ...]  │
│                                                      │
│  When enabled, every completed sourcing job will     │
│  automatically queue a clay_push job for new leads   │
│  matching the criteria above.                        │
└──────────────────────────────────────────────────────┘
```

This turns NexusLeads into a **set-and-forget pipeline**: configure a project, set auto-export rules, and qualified leads flow into Clay without manual intervention.

**Implementation**: After a sourcing/enrichment job completes successfully in `job_processor.py`, check if the project has auto-export enabled. If so, queue a `clay_push` job with the configured filters.

### 6.3 Push Status Indicators

Leads that have been pushed to an integration show a small indicator:

```
┌─────────────────────────────────────────────────┐
│  John Doe  •  Senior Engineer @ Acme            │
│  Score: 82  •  DECISION_MAKER  •  High Priority │
│  ☁ Pushed to Clay 2h ago                        │  ← subtle indicator
└─────────────────────────────────────────────────┘
```

### 6.4 Smart Defaults

- "Push to Clay" only appears if Clay is configured (check via API)
- If no integrations configured, show a subtle banner: "Connect an integration to push leads directly to your sales tools → [Set up Integrations]"
- Bulk push skips already-pushed leads by default (with override toggle)

---

## 7. Landing Page Updates

### 7.1 New Section: "Integrations" (between Features and Pricing)

Add a new landing page section that communicates the action story:

```
═══════ INTEGRATIONS ═══════

From Insight to Action

NexusLeads doesn't just find leads — it delivers them where your
sellers already work. One click to push enriched, scored, classified
leads into your sales stack.

┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│   Clay   │  │Salesforce│  │  HubSpot │  │ Outreach │
│  ✅ Live  │  │  Soon    │  │  Soon    │  │  Soon    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

Source → Enrich → Score → ACT
  ↑                         ↑
  GitHub data            Your CRM, Clay,
  + AI enrichment        outreach tools
```

### 7.2 Updated Hero Subtitle

Current: "Turn open source activity into qualified sales leads"

Consider updating to emphasize action:
**"Turn open source activity into qualified pipeline — automatically."**

### 7.3 Updated Features Grid

Add one more feature tile:
```
{ icon: Blocks, title: 'Sales Stack Integrations',
  desc: 'Push enriched leads to Clay, Salesforce, HubSpot, and more.
         One click from lead to pipeline.' }
```

---

## 8. Enterprise Upsell UX

### 8.1 Gated Integration Tile

When a user clicks a gated integration:

```
┌─────────────────────────────────────────────────────┐
│  🔒 Salesforce CRM Integration                      │
│                                                      │
│  Automatically sync qualified leads to Salesforce.   │
│  Create contacts, opportunities, and tasks from      │
│  NexusLeads scores and classifications.              │
│                                                      │
│  ✓ Auto-create contacts from qualified leads         │
│  ✓ Map NexusLeads scores to Salesforce fields        │
│  ✓ Bi-directional sync for lead status               │
│  ✓ Custom field mapping                              │
│                                                      │
│  Available on the Enterprise plan.                   │
│                                                      │
│  [Book a Call]           [Learn More]                │
└─────────────────────────────────────────────────────┘
```

### 8.2 Gating Behavior

Same pattern as billing feature flags:
- `BILLING_ENABLED = false` → all integrations available (pilot mode)
- `BILLING_ENABLED = true` → only Clay available on paid plans; CRM/outreach/webhooks require enterprise

---

## 9. Technical Design

### 9.1 New Route

```
/app/integrations → Integrations page
```

### 9.2 Integration Registry (Frontend)

A data-driven tile grid — each integration is defined as a config object:

```typescript
interface Integration {
  id: string
  name: string
  description: string
  category: 'data_platform' | 'crm' | 'outreach'
  icon: LucideIcon | string  // Lucide icon or custom SVG
  status: 'live' | 'coming_soon'
  tier: 'free' | 'paid' | 'enterprise'
  configFields: ConfigField[]  // what settings are needed
  features: string[]  // bullet points for gated modal
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'clay',
    name: 'Clay',
    description: 'Push enriched leads to Clay tables for 100+ provider enrichment and outreach automation.',
    category: 'data_platform',
    icon: Layers,  // or custom Clay logo SVG
    status: 'live',
    tier: 'paid',
    configFields: [
      { key: 'CLAY_WEBHOOK_URL', label: 'Webhook URL', type: 'url', required: true },
      { key: 'CLAY_TABLE_NAME', label: 'Table Name', type: 'text', required: false },
    ],
    features: [
      'One-click push from Leads page',
      'Bulk push with duplicate detection',
      'Full enrichment data + raw GitHub stats',
      'Tracked as a monitored job',
    ]
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    description: 'Sync qualified leads directly into Salesforce as contacts and opportunities.',
    category: 'crm',
    icon: Cloud,
    status: 'coming_soon',
    tier: 'enterprise',
    configFields: [],
    features: [
      'Auto-create contacts from qualified leads',
      'Map NexusLeads scores to Salesforce fields',
      'Bi-directional sync for lead status',
      'Custom field mapping',
    ]
  },
  // ... HubSpot, Outreach, Slack, Webhooks
]
```

### 9.3 Backend: Integration Status API

```
GET /api/integrations/status
```

Returns the status of all integrations for the current org:

```json
{
  "integrations": {
    "clay": {
      "configured": true,
      "last_push_at": "2026-02-11T00:48:22Z",
      "total_pushed": 312,
      "success_rate": 0.974
    },
    "salesforce": { "configured": false },
    "hubspot": { "configured": false }
  },
  "billing_enabled": false,
  "is_enterprise": false
}
```

This endpoint checks org_settings for each integration's required keys and aggregates stats from `clay_push_log` (and future tables).

### 9.4 Backend: Recent Push Activity

```
GET /api/integrations/clay/activity?limit=5
```

Returns recent push jobs for the Clay integration:

```json
{
  "activity": [
    {
      "job_id": "uuid",
      "pushed_at": "2026-02-11T00:48:22Z",
      "total_leads": 23,
      "success_count": 22,
      "failed_count": 1,
      "status": "completed"
    }
  ]
}
```

---

## 10. Implementation Plan

### Phase 1: Integrations Page Shell
1. Create `/app/integrations` route and page component
2. Add "Integrations" nav item to sidebar (with `Blocks` icon, separator above)
3. Build integration tile grid with categories (data-driven from registry)
4. Implement tile states: live, coming soon, enterprise-gated
5. Build gated integration modal (feature list + upgrade CTA)

### Phase 2: Clay Detail Panel
6. Build expandable detail panel for Clay integration
7. Move Clay config from Settings (Feature 002) into Integrations detail panel
8. Add test webhook button
9. Add recent activity feed (pulls from clay_push_log)
10. Add aggregate stats display

### Phase 3: Leads Page Actions
11. Add per-lead "Push to Clay" button (conditional on Clay configured)
12. Add checkbox selection to leads table
13. Add bulk action bar with "Push to Clay" and "Export CSV"
14. Add "Pushed to Clay" indicator on lead rows
15. Add "no integrations configured" banner with link to Integrations page

### Phase 4: Landing Page Updates
16. Add "Integrations" section between Features and Pricing
17. Add "Sales Stack Integrations" tile to Features grid
18. Update nav to include "Integrations" scroll target
19. Update hero subtitle to emphasize action

### Phase 5: Backend
20. Create `GET /api/integrations/status` endpoint
21. Create `GET /api/integrations/{id}/activity` endpoint
22. Wire up integration status checks (reads org_settings for required keys)

---

## 11. Testing Checklist

- [ ] Integrations page renders with correct tile grid
- [ ] Clay tile shows "Connected" when webhook URL is configured
- [ ] Clay tile shows "Not configured" when webhook URL is missing
- [ ] Enterprise-gated tiles show lock icon and upgrade modal
- [ ] Coming soon tiles show badge and "Notify Me" option
- [ ] Clay detail panel expands with config, test, and activity
- [ ] Test webhook button sends sample payload and reports result
- [ ] Recent activity shows last 5 push jobs with correct stats
- [ ] Leads page shows "Push to Clay" only when Clay is configured
- [ ] Bulk selection + push creates a clay_push job
- [ ] "Pushed to Clay" indicator appears on previously pushed leads
- [ ] "No integrations" banner shows when nothing is configured
- [ ] Landing page Integrations section renders correctly
- [ ] Sidebar shows Integrations with separator, correct icon
- [ ] `BILLING_ENABLED = false` → all integrations available
- [ ] `BILLING_ENABLED = true` → CRM/outreach gated to enterprise

---

## 12. Resolved Decisions

| Question | Decision |
|----------|----------|
| Separate Integrations page? | Yes — dedicated page at `/app/integrations` |
| Where does Clay config live? | Integrations page (not Settings) |
| Integration categories? | Data Platforms, CRM, Outreach & Notifications |
| Coming soon connectors? | Salesforce, HubSpot, Apollo, Outreach, Slack, Webhooks |
| Gating model? | Same as billing: pilot mode = all available; billing enabled = tier-gated |
| "Notify Me" for coming soon? | No — just show feature preview, no backend capture |
| Integration logos? | Lucide icons (ship fast, consistent with existing UI) |
| Leads page bulk select? | Checkboxes within each project group (preserve grouped layout) |
| Auto-export from project config? | Yes — optional auto-push to Clay after scan completes, with score/classification filters |
| Enterprise CTA? | "Book a Call" → Calendly link (calendly.com/keshi8) |
| Landing page hero subtitle? | TBD — decide during implementation |
