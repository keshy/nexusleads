# 004 — Community Generalization

> Evolve NexusLeads from a GitHub-only lead sourcer into a **community-to-revenue** platform where GitHub is one of many community types.

## Problem Statement

Today every data model, API route, job worker, and UI component assumes "community" = "GitHub repository." The nouns are `Repository`, `Contributor`, `github_id`, `github_url`, `stars`, `forks`, etc. This makes it impossible to ingest signals from Discord, Reddit, X, Stock-community forums, or any future source without duplicating the entire stack.

## Vision

A **Project** contains one or more **Community Sources**. Each source has a **type** (GitHub, Discord, Reddit, X, Stock, …) and a **connector** that knows how to fetch members and activity. The rest of the platform — scoring, classification, enrichment, dashboard, chat — operates on the **abstract** `Member` + `MemberActivity` layer.

## Scope of Change — Current → Target

### Data Model (backend/models.py)

| Current | Target | Notes |
|---------|--------|-------|
| `Repository` | **`CommunitySource`** | Add `source_type` enum (github_repo, discord_server, reddit_sub, x_account, stock_forum). Keep GitHub-specific fields in a JSON `source_config` column. |
| `Contributor` | **`Member`** | Replace `github_id`, `github_url`, `twitter_username` with a generic `platform_identities` JSONB (`{github: {id, url}, discord: {id, username}, …}`). Keep `full_name`, `email`, `company`, `location`, `bio`, `avatar_url` as top-level. |
| `RepositoryContributor` | **`CommunityMember`** | Junction of `CommunitySource ↔ Member`. Add `role` (owner, moderator, contributor, member, lurker). |
| `ContributorStats` | **`MemberActivity`** | Replace commit-centric columns with generic + platform-specific: `activity_type` enum, `activity_count`, `activity_period`, plus JSONB `details` for platform-specific metrics. |
| `LeadScore.contributor_id` | `LeadScore.member_id` | FK rename. |
| `SocialContext.contributor_id` | `SocialContext.member_id` | FK rename. |
| `ClayPushLog.contributor_id` | `ClayPushLog.member_id` | FK rename. |
| `CreditTransaction.contributor_id` | `CreditTransaction.member_id` | FK rename. |
| `UsageEvent.contributor_id` | `UsageEvent.member_id` | FK rename. |

### New Enum: `SourceType`

```
github_repo, github_org, discord_server, reddit_subreddit,
x_account, x_hashtag, stock_forum, custom
```

### New Table: `community_sources`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| project_id | UUID | FK → projects |
| source_type | VARCHAR(50) | SourceType enum |
| name | VARCHAR(255) | Human label (e.g. "kubernetes/kubernetes") |
| external_url | VARCHAR(500) | Original URL |
| source_config | JSONB | Type-specific config (token scopes, channels, subreddits) |
| last_sourced_at | TIMESTAMPTZ | |
| sourcing_interval | VARCHAR(50) | |
| next_sourcing_at | TIMESTAMPTZ | |
| is_active | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

### Schemas (backend/schemas.py)

- `RepositoryCreate` → `CommunitySourceCreate` with `source_type` + `external_url` + optional `source_config`
- `RepositoryResponse` → `CommunitySourceResponse`
- `ContributorResponse` → `MemberResponse` (platform_identities replaces github_id/github_url)
- `ContributorStatsResponse` → `MemberActivityResponse`
- `DashboardStats.total_repositories` → `total_community_sources`
- `DashboardStats.total_contributors` → `total_members`

### API Routes (backend/routers/)

| Current Route | Target Route | Change |
|---------------|-------------|--------|
| `/api/repositories` | `/api/sources` | CRUD for CommunitySource |
| `/api/repositories/{id}/source-now` | `/api/sources/{id}/source-now` | Trigger sourcing |
| `/api/repositories/{id}/analyze-stargazers` | `/api/sources/{id}/analyze-followers` | Generalized follower/member analysis |
| `/api/repositories/similar` | `/api/sources/discover` | Cross-type discovery |
| `/api/contributors` | `/api/members` | Renamed |
| `/api/leads/by-project` | `/api/leads/by-project` | No URL change, internals updated |

### Job Worker (jobs/)

| Current | Target |
|---------|--------|
| `GitHubService` | One of many connectors behind a `ConnectorInterface` |
| `job_processor.process_repository_sourcing` | `process_source_ingestion` dispatches to the right connector |
| Hard-coded contributor fields | Connector returns normalized `MemberData` + `ActivityData` dicts |

### Frontend (frontend/src/)

| Area | Change |
|------|--------|
| `Repositories.tsx` | → `Sources.tsx` — show source type icon + badge |
| `Projects.tsx` | "Add Repository" → "Add Community Source" with source-type picker |
| `Leads.tsx` | Replace GitHub avatar/username with generic member card |
| `Dashboard.tsx` | "Repositories" KPI → "Community Sources", "Contributors" → "Members" |
| `api.ts` | Rename methods: `getRepositories` → `getSources`, `getContributors` → `getMembers`, etc. |
| `ChatSidecar.tsx` | Agent skill schema updated (handled in SKILL.md update) |

### Agent Skill (.agents/skills/)

- Rename tables in SKILL.md schema section
- Update example queries to use `community_sources`, `members`, `member_activity`

## Migration Strategy

1. **Alembic migration** that renames tables + columns and adds new columns. Keep old column names as aliases/views for a transition period.
2. **Backward-compat API aliases**: old `/api/repositories` routes redirect to `/api/sources` for one release.
3. **Data backfill**: existing `Repository` rows become `CommunitySource` with `source_type = 'github_repo'` and `source_config` populated from the GitHub-specific columns. Existing `Contributor` rows get `platform_identities = {github: {id: github_id, url: github_url}}`.

## Out of Scope (handled in other feature docs)

- Connector implementations for non-GitHub sources → 005
- Dynamic/user-defined classification → 006
- Detailed migration plan + rollback → 007

## Success Criteria

- All existing functionality works identically after migration (GitHub is just one source type)
- Adding a new source type requires only a new connector class, no schema changes
- Frontend renders any source type with appropriate icons and labels
- Chat agent queries work against the new schema
