# Changelog

## [Unreleased] — 2026-03-10

### Added
- **Exclusion filters on Dashboard & Leads pages** — each filter (classification, industry, company, source, project) now supports include/exclude mode via a toggle button
- **Shared filter primitive** (`frontend/src/lib/leadFilters.ts`) — `SelectFilterState` type with `include`/`exclude` mode, plus helpers `isFilterActive`, `getFilterTone`
- **FacetFilter component** (`frontend/src/components/FacetFilter.tsx`) — reusable filter dropdown with built-in include/exclude toggle
- **Server-side exclusion support** — `GET /api/dashboard/top-leads` and `GET /api/members/` accept `exclude_classification`, `exclude_industry`, `exclude_company` query params so exclusions apply before the LIMIT, not after
- **StyledSelect enhancements** — supports `tone` prop for visual feedback (red tint in exclude mode)
- **Periodic sourcing scheduler** — job processor main loop now checks for sources whose `next_sourcing_at` is due and auto-creates scan jobs; idempotent (skips sources with pending/running jobs)
- **`next_sourcing_at` advancement** — after `repository_sourcing` or `source_ingestion` completes, `next_sourcing_at` is advanced by the source's interval (daily/weekly/monthly), ensuring the cycle continues across restarts and deployments

### Changed
- Dashboard and Leads filter bars refactored to use shared `FacetFilter` component
- `api.ts` updated with new query param support for exclusion filters

### Fixed
- **Periodic sourcing was non-functional** — `sourcing_interval` and `next_sourcing_at` columns existed but nothing read them; `schedule` library was in requirements.txt but never used

---

## [2026-03-04]

### Added
- **Lead owner assignment** — assign/unassign owners to leads, bulk assign from selection bar
- **CSV export** — export selected leads or per-project leads as CSV
- **Job metadata** — enrichment jobs now include target username (`@handle`) in job details
- **Migration 012** — `owner_id` column on `lead_scores` table for lead assignment
- **CLAUDE.md** — project conventions doc (dropdown theming, chat overflow, dark mode rules)
- **Configurable scan limits** — `CONTRIBUTOR_SCAN_LIMIT` and `STARGAZER_SCAN_LIMIT` in Settings

### Changed
- **Source card UX** — unified "Run" dropdown with Full Member Scan, Stargazer Analysis, Sample Members, Sample Stargazers options (opens downward)
- **Settings → Users tab** — visible to all authenticated users (read-only for non-admins); admin-only for add/delete
- **Backend `GET /api/users/`** — accessible to all authenticated users (was admin-only)
- **Themed dropdowns** — all native `<select>` replaced with `StyledSelect` across Sources, Jobs, Projects, Repositories, Layout org switcher, Leads bulk assign
- **Chat overflow fix** — `overflow-hidden` on bubbles, `word-break` on `.chat-markdown`
- **Dark mode fixes** — Settings users table, consistent styling throughout

### Fixed
- `sample_size` not respected in stargazer analysis — added `int()` cast and debug logging
- `repository_id` → `source_id` stale code in jobs container
- Dark mode on Settings users list (white background in table rows)

---

## [2026-02-26]

### Added
- **Community generalization** — Repository → CommunitySource, Contributor → Member, platform-agnostic architecture
- **Community source connectors** — GitHub, Discord, Reddit, X (Twitter), StockTwits
- **Dynamic classification** — user-defined labels and scoring weights per project
- **Feature docs** — 004 through 007 covering generalization, connectors, classification, migration playbook
- **Landing page** — updated to reflect multi-community platform scope
- **Organization management** — admin-only create org, org switcher in sidebar

---

## [2026-02-13]

### Added
- **AI Chat assistant** — Node.js host assistant with Codex SDK, generative UI (widgets, charts, tables), WebSocket streaming
- **Billing & credits UI** — credit balance, transaction history, usage events
- **Skills system** — `.agents/skills/plg-database/SKILL.md` for direct DB queries via psql
