# 007 — Information Architecture Migration

> Detailed migration plan for evolving the database, API, and UI from GitHub-only to the generalized community-to-revenue platform.

## Overview

This document is the execution playbook for features 004, 005, and 006. It inventories every file that must change, specifies the migration order, and defines the rollback strategy.

## Inventory of GitHub-Coupled Code

### Backend — Models (backend/models.py)

| Line(s) | Entity | GitHub Coupling | Action |
|---------|--------|-----------------|--------|
| 58-89 | `Repository` | `github_url`, `full_name` (owner/repo), `owner`, `repo_name`, `stars`, `forks`, `open_issues`, `language`, `topics` | **Replace** with `CommunitySource`. Move GitHub fields into `source_config` JSONB. |
| 92-118 | `Contributor` | `github_id`, `github_url`, `twitter_username`, `public_repos`, `followers`, `following` | **Rename** to `Member`. Move platform-specific IDs into `platform_identities` JSONB. Keep `full_name`, `email`, `company`, `location`, `bio`, `avatar_url` as top-level. |
| 121-136 | `RepositoryContributor` | Name, `repository_id` FK | **Rename** to `CommunityMember`. FK becomes `source_id`. Add `role`. |
| 139-169 | `ContributorStats` | `repository_id`, commit-centric columns | **Rename** to `MemberActivity`. Replace commit columns with `activity_type`, `count`, `period`, `details` JSONB. |
| 172-198 | `SocialContext` | `contributor_id` FK | FK rename to `member_id`. No other changes. |
| 201-224 | `SourcingJob` | `repository_id` FK | FK rename to `source_id`. |
| 321-333 | `ClayPushLog` | `contributor_id` FK | FK rename to `member_id`. |
| 359-372 | `CreditTransaction` | `contributor_id` FK | FK rename to `member_id`. |
| 375-387 | `UsageEvent` | `contributor_id` FK | FK rename to `member_id`. |
| 400-423 | `LeadScore` | `contributor_id` FK | FK rename to `member_id`. |

### Backend — Schemas (backend/schemas.py)

| Schema | Change |
|--------|--------|
| `RepositoryBase/Create/Update/Response` | → `CommunitySourceBase/Create/Update/Response`. Add `source_type`, `source_config`. Remove `github_url`. |
| `ContributorBase/Response` | → `MemberBase/Response`. Replace `github_id`, `github_url` with `platform_identities`. |
| `ContributorStatsResponse` | → `MemberActivityResponse`. Generic activity fields. |
| `ProjectStats` | `total_repositories` → `total_sources`, `total_contributors` → `total_members` |
| `DashboardStats` | Same renames. |
| `RepositoryLeadStats` | → `SourceLeadStats`. |
| `SimilarRepoSearch/Result` | → `SourceDiscoverySearch/Result`. |
| `SourcingJobCreate` | `repository_id` → `source_id`. `job_type` pattern updated. |
| `SourcingJobResponse` | `repository_id/name` → `source_id/name`. |
| `ProjectCreate/Update` | Add `classification_labels`, `scoring_weights`. |

### Backend — Routers (backend/routers/)

| File | Change |
|------|--------|
| `repositories.py` | **Rename** to `sources.py`. `parse_github_url` → connector-specific validation. Route prefix `/api/repositories` → `/api/sources`. Add backward-compat redirects. |
| `contributors.py` | **Rename** to `members.py`. Route prefix `/api/contributors` → `/api/members`. Update all model references. |
| `dashboard.py` | Update all `Repository` → `CommunitySource`, `Contributor` → `Member`, `ContributorStats` → `MemberActivity` references. |
| `projects.py` | Update `Repository` → `CommunitySource` references. Handle `classification_labels` and `scoring_weights` on create/update. |
| `jobs.py` | Update `repository_id` → `source_id`. |
| `integrations.py` | Update `contributor_id` → `member_id` in Clay push logic. |
| `__init__.py` | Update import paths. |

### Backend — Other

| File | Change |
|------|--------|
| `main.py` | Update router includes (repositories → sources, contributors → members). |
| `settings_service.py` | Add connector-specific setting definitions (DISCORD_BOT_TOKEN, REDDIT_CLIENT_ID, etc.). |

### Jobs Worker (jobs/)

| File | Change |
|------|--------|
| `job_processor.py` | Major refactor. `process_repository_sourcing` → `process_source_ingestion` with connector dispatch. `process_stargazer_analysis` → connector-specific variant. All `Contributor` → `Member`, `Repository` → `CommunitySource`, `ContributorStats` → `MemberActivity`. |
| `models.py` | Mirror backend model renames. |
| `services/github_service.py` | Refactor into `connectors/github.py` implementing `CommunityConnector`. |
| `services/enrichment_service.py` | `classify_contributor` → `classify_member`. Dynamic prompt from project's `sourcing_context` + `classification_labels`. |
| `services/scoring_service.py` | Read weights from project. Generalize activity/influence/engagement metrics to work with any `MemberActivity` data. |
| `services/linkedin_service.py` | `contributor` references → `member`. Minimal changes. |
| `billing_service.py` | `contributor_id` → `member_id`. |

### Frontend (frontend/src/)

| File | Change |
|------|--------|
| `lib/api.ts` | Rename methods: `getRepositories` → `getSources`, `createRepository` → `createSource`, `getContributors` → `getMembers`, etc. Add `source_type` to create/list. |
| `pages/Repositories.tsx` | **Rename** to `Sources.tsx`. Source-type picker, type icons, generic labels. |
| `pages/Projects.tsx` | "Add Repository" → "Add Community Source" with type picker. Classification labels + scoring weights in project create/edit. |
| `pages/Leads.tsx` | Replace GitHub-specific avatar/username with generic member card. Dynamic classification badges from project labels. |
| `pages/Dashboard.tsx` | "Repositories" → "Community Sources", "Contributors" → "Members". Dynamic classification charts. |
| `pages/ProjectDetail.tsx` | Update repo references → source references. |
| `pages/Jobs.tsx` | `repository_name` → `source_name`. |
| `pages/Settings.tsx` | Group API keys by connector type. |
| `pages/Integrations.tsx` | `contributor` → `member` in Clay push UI. |
| `components/Layout.tsx` | Nav: "Repositories" → "Sources". |
| `components/ChatSidecar.tsx` | No code changes needed (schema changes handled via SKILL.md). |
| `components/ScoreTooltip.tsx` | Show project's scoring weights, not hard-coded. |
| `App.tsx` | Route paths: `/repositories` → `/sources`. |

### Agent Skill (.agents/skills/plg-database/SKILL.md)

- Rename all table/column references in the schema section
- Update example queries
- Add `community_sources` table documentation
- Update response format examples to reference "members" not "contributors"

### Assistant Prompt (assistant/codex-bridge.js)

- Line 104-105: "repositories, leads/contributors" → "community sources, leads/members"
- Skill reference stays the same ($plg-database)

## Migration Phases

### Phase 0: Branch & Backward-Compat Layer (Day 1)

1. Create Alembic migration infrastructure if not present
2. Add database views aliasing old names to new names for transition

### Phase 1: Database Migration (Day 1-2)

```sql
-- 1. Rename tables
ALTER TABLE repositories RENAME TO community_sources;
ALTER TABLE contributors RENAME TO members;
ALTER TABLE repository_contributors RENAME TO community_members;
ALTER TABLE contributor_stats RENAME TO member_activity;

-- 2. Add new columns to community_sources
ALTER TABLE community_sources ADD COLUMN source_type VARCHAR(50) NOT NULL DEFAULT 'github_repo';
ALTER TABLE community_sources ADD COLUMN source_config JSONB;
ALTER TABLE community_sources ADD COLUMN external_url VARCHAR(500);

-- 3. Backfill community_sources
UPDATE community_sources SET
  source_config = jsonb_build_object(
    'owner', owner,
    'repo_name', repo_name,
    'stars', stars,
    'forks', forks,
    'open_issues', open_issues,
    'language', language,
    'topics', topics
  ),
  external_url = github_url;

-- 4. Add platform_identities to members
ALTER TABLE members ADD COLUMN platform_identities JSONB DEFAULT '{}';

-- 5. Backfill members
UPDATE members SET
  platform_identities = jsonb_build_object(
    'github', jsonb_build_object('id', github_id, 'url', github_url, 'username', username)
  );

-- 6. Add role to community_members
ALTER TABLE community_members ADD COLUMN role VARCHAR(50) DEFAULT 'contributor';

-- 7. Rename FK columns
ALTER TABLE community_members RENAME COLUMN repository_id TO source_id;
ALTER TABLE member_activity RENAME COLUMN repository_id TO source_id;
ALTER TABLE sourcing_jobs RENAME COLUMN repository_id TO source_id;

-- 8. Add activity generalization to member_activity
ALTER TABLE member_activity ADD COLUMN activity_type VARCHAR(50) DEFAULT 'commit';
ALTER TABLE member_activity ADD COLUMN details JSONB;
ALTER TABLE member_activity RENAME COLUMN contributor_id TO member_id;

-- 9. Rename contributor_id → member_id in other tables
ALTER TABLE social_context RENAME COLUMN contributor_id TO member_id;
ALTER TABLE lead_scores RENAME COLUMN contributor_id TO member_id;
ALTER TABLE clay_push_log RENAME COLUMN contributor_id TO member_id;
ALTER TABLE credit_transactions RENAME COLUMN contributor_id TO member_id;
ALTER TABLE usage_events RENAME COLUMN contributor_id TO member_id;

-- 10. Rename constraints
ALTER TABLE community_sources RENAME CONSTRAINT unique_project_repo TO unique_project_source;
ALTER TABLE community_members RENAME CONSTRAINT unique_repo_contributor TO unique_source_member;
ALTER TABLE member_activity RENAME CONSTRAINT unique_repo_contributor_stats TO unique_source_member_activity;
ALTER TABLE lead_scores RENAME CONSTRAINT unique_project_contributor_score TO unique_project_member_score;

-- 11. Add project-level classification and scoring
ALTER TABLE projects ADD COLUMN classification_labels JSONB;
ALTER TABLE projects ADD COLUMN scoring_weights JSONB;

-- 12. Create backward-compat views
CREATE VIEW repositories AS SELECT *, external_url AS github_url FROM community_sources;
CREATE VIEW contributors AS SELECT *, (platform_identities->'github'->>'id')::int AS github_id FROM members;
```

### Phase 2: Backend Models + Schemas (Day 2-3)

1. Update `models.py` — rename classes, add new columns
2. Update `schemas.py` — rename schemas, add new fields
3. Update all routers
4. Add backward-compat route aliases

### Phase 3: Connector Architecture (Day 3-4)

1. Create `jobs/connectors/` package with base class
2. Refactor `GitHubService` → `GitHubRepoConnector`
3. Update `job_processor.py` to use connector dispatch
4. Update `enrichment_service.py` for dynamic classification
5. Update `scoring_service.py` for configurable weights

### Phase 4: Frontend (Day 4-5)

1. Rename pages + routes
2. Update API client methods
3. Add source-type picker UI
4. Dynamic classification badges
5. Scoring weight sliders in project settings

### Phase 5: Agent + Skill (Day 5)

1. Update SKILL.md with new schema
2. Update codex-bridge.js prompt

### Phase 6: Testing + Polish (Day 5-6)

1. Verify all existing GitHub workflows still work
2. Test dynamic classification with custom labels
3. Test scoring weight customization
4. Verify chat agent queries
5. Run full sourcing pipeline end-to-end

## Rollback Strategy

- Alembic downgrade scripts for every migration step
- Backward-compat views allow old queries during transition
- Feature flag: `community_generalization_enabled` — when disabled, UI and API behave exactly as before
- Old route aliases remain active for 2 releases

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during table rename | High | Use ALTER TABLE RENAME, not DROP+CREATE. Test on staging DB first. |
| Breaking existing API clients | Medium | Backward-compat route aliases + deprecation warnings |
| LLM classification quality with dynamic labels | Medium | Keep rule-based fallback for default labels. Add confidence threshold — below 0.5, flag for human review. |
| Performance of JSONB queries | Low | Add GIN indexes on `platform_identities`, `source_config`. |
| Frontend regression | Medium | Thorough manual + automated testing. Feature flag for gradual rollout. |

## Files Changed (Complete List)

### Backend
- `backend/models.py`
- `backend/schemas.py`
- `backend/main.py`
- `backend/routers/__init__.py`
- `backend/routers/repositories.py` → `sources.py`
- `backend/routers/contributors.py` → `members.py`
- `backend/routers/dashboard.py`
- `backend/routers/projects.py`
- `backend/routers/jobs.py`
- `backend/routers/integrations.py`
- `backend/settings_service.py`

### Jobs
- `jobs/models.py`
- `jobs/job_processor.py`
- `jobs/services/github_service.py` → `jobs/connectors/github.py`
- `jobs/services/enrichment_service.py`
- `jobs/services/scoring_service.py`
- `jobs/services/linkedin_service.py`
- `jobs/billing_service.py`
- `jobs/connectors/__init__.py` (new)
- `jobs/connectors/base.py` (new)

### Frontend
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/Repositories.tsx` → `Sources.tsx`
- `frontend/src/pages/Projects.tsx`
- `frontend/src/pages/Leads.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/ProjectDetail.tsx`
- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Integrations.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/ScoreTooltip.tsx`

### Agent
- `.agents/skills/plg-database/SKILL.md`
- `assistant/codex-bridge.js`

### Docs
- `docs/chat-architecture.md`

**Total: ~35 files modified, ~3 new files created**

## Success Criteria

- All existing GitHub sourcing + enrichment + scoring + Clay export workflows work identically
- Database migration is reversible
- New community source types can be added without schema changes
- Dynamic classification produces comparable or better results than current fixed labels
- No API breaking changes for existing integrations (backward-compat aliases)
