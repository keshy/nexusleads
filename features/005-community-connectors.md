# 005 — Community Types & Connectors

> Define the connector architecture and initial set of community source types.

## Overview

Each community type is served by a **Connector** — a class that implements a standard interface for discovering members, fetching activity, and normalizing data into the platform's abstract `Member` + `MemberActivity` models. This doc specifies the interface, the initial connectors, and how users add sources through the UI.

## Connector Interface

```python
class CommunityConnector(ABC):
    """Base class all connectors implement."""

    source_type: str  # e.g. "github_repo"

    @abstractmethod
    async def validate_source(self, external_url: str, source_config: dict) -> dict:
        """Validate that the source exists and credentials work.
        Returns normalized metadata (name, description, member_count, etc.)."""

    @abstractmethod
    async def fetch_members(self, source: CommunitySource, limit: int = 200) -> list[MemberData]:
        """Fetch members/participants from the community source.
        Returns list of normalized MemberData dicts."""

    @abstractmethod
    async def fetch_activity(self, source: CommunitySource, member: Member) -> list[ActivityData]:
        """Fetch activity metrics for a specific member in this source.
        Returns list of normalized ActivityData dicts."""

    @abstractmethod
    async def fetch_metadata(self, source: CommunitySource) -> dict:
        """Refresh source-level metadata (member count, activity summary)."""

    def get_required_settings(self) -> list[str]:
        """Return setting keys needed (e.g. GITHUB_TOKEN, DISCORD_BOT_TOKEN)."""
        return []
```

### Normalized Data Types

```python
@dataclass
class MemberData:
    """Platform-agnostic member representation returned by connectors."""
    platform_id: str          # Unique ID on the platform
    platform_username: str    # Display handle
    full_name: str | None
    email: str | None
    company: str | None
    location: str | None
    bio: str | None
    avatar_url: str | None
    profile_url: str | None
    follower_count: int = 0
    role: str = "member"      # owner, moderator, contributor, member, lurker
    raw_data: dict = field(default_factory=dict)  # Platform-specific extras

@dataclass
class ActivityData:
    """Platform-agnostic activity record."""
    activity_type: str        # e.g. "commit", "message", "post", "comment", "trade"
    count: int
    period: str               # "last_3_months", "last_6_months", "last_year", "all_time"
    details: dict = field(default_factory=dict)  # Platform-specific extras
    recorded_at: datetime | None = None
```

## Connector Registry

```python
CONNECTOR_REGISTRY: dict[str, type[CommunityConnector]] = {
    "github_repo": GitHubRepoConnector,
    "github_org": GitHubOrgConnector,
    "discord_server": DiscordConnector,
    "reddit_subreddit": RedditConnector,
    "x_account": XConnector,
    "stock_forum": StockForumConnector,
}
```

The job processor looks up the connector by `source.source_type` and delegates.

## Initial Connectors

### 1. GitHub Repository (`github_repo`) — **Existing, Refactored**

Wraps the current `GitHubService`. Becomes the reference implementation.

| Field | Mapping |
|-------|---------|
| `source_config` | `{owner, repo_name, include_stargazers: bool}` |
| `MemberData.platform_id` | `github_id` |
| `MemberData.role` | `contributor` (or `maintainer` if flagged) |
| `ActivityData.activity_type` | `commit`, `pull_request`, `issue`, `review`, `star` |
| Required settings | `GITHUB_TOKEN` |

### 2. GitHub Organization (`github_org`)

Fetches all public members of a GitHub org.

| Field | Mapping |
|-------|---------|
| `source_config` | `{org_name}` |
| Members | Public org members via `/orgs/{org}/members` |
| Activity | Per-member public events via `/users/{login}/events/public` |
| Required settings | `GITHUB_TOKEN` |

### 3. Discord Server (`discord_server`)

| Field | Mapping |
|-------|---------|
| `source_config` | `{guild_id, tracked_channels: [channel_ids], min_messages: int}` |
| `MemberData.platform_id` | Discord user ID |
| `MemberData.role` | Mapped from Discord roles (owner, admin → moderator, etc.) |
| `ActivityData.activity_type` | `message`, `reaction`, `thread_start`, `voice_minutes` |
| Required settings | `DISCORD_BOT_TOKEN` |

**Notes:**
- Bot must be added to the server with `SERVER MEMBERS INTENT` and `MESSAGE CONTENT INTENT`
- `source_config.tracked_channels` lets users focus on specific channels (e.g. #support, #feature-requests)
- Activity aggregated over configurable windows

### 4. Reddit Subreddit (`reddit_subreddit`)

| Field | Mapping |
|-------|---------|
| `source_config` | `{subreddit_name, post_types: [submission, comment], min_karma: int}` |
| `MemberData.platform_id` | Reddit username |
| `MemberData.role` | `moderator` if in mod list, else `member` |
| `ActivityData.activity_type` | `post`, `comment`, `award_given`, `award_received` |
| Required settings | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` |

**Notes:**
- Uses PRAW or async Reddit API
- Karma, account age, and flair as enrichment signals
- Rate limits: 60 req/min with OAuth

### 5. X / Twitter (`x_account`)

| Field | Mapping |
|-------|---------|
| `source_config` | `{account_handle, track_mode: "followers" | "engagers" | "list", list_id?: str}` |
| `MemberData.platform_id` | X user ID |
| `MemberData.role` | `follower` or `engager` |
| `ActivityData.activity_type` | `tweet`, `reply`, `retweet`, `like`, `mention` |
| Required settings | `X_BEARER_TOKEN` |

**Notes:**
- `engagers` mode: scrape replies/retweets/quotes to find active community members
- `followers` mode: paginate followers list, filter by bio/follower count
- X API v2 rate limits are tight — connector must handle 429s gracefully

### 6. Stock / Finance Forum (`stock_forum`)

| Field | Mapping |
|-------|---------|
| `source_config` | `{platform: "stocktwits" | "seeking_alpha" | "reddit_wsb", ticker_symbols: [str]}` |
| `MemberData.platform_id` | Forum user ID |
| `MemberData.role` | `analyst`, `contributor`, `member` |
| `ActivityData.activity_type` | `post`, `sentiment_signal`, `trade_idea`, `comment` |
| Required settings | Depends on platform |

**Notes:**
- StockTwits has a public API; Seeking Alpha may require scraping
- Could start with reddit/r/wallstreetbets and r/stocks as sub-types of the Reddit connector with finance-specific activity parsing

## UI: Adding a Community Source

### Source Type Picker (in Projects.tsx → Sources.tsx)

```
┌────────────────────────────────────┐
│  Add Community Source               │
│                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │GitHub│ │Discord│ │Reddit│       │
│  └──────┘ └──────┘ └──────┘       │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │  X   │ │Stock │ │Custom│       │
│  └──────┘ └──────┘ └──────┘       │
│                                     │
│  URL: [_________________________]   │
│  Sourcing interval: [monthly ▾]     │
│  (type-specific config fields)      │
│                                     │
│  [Cancel]  [Add Source]             │
└────────────────────────────────────┘
```

Each source type renders its own config fields (e.g. Discord shows channel picker, Reddit shows subreddit + post type toggles).

## Settings Page Changes

The Settings page currently shows `GITHUB_TOKEN` and other API keys. With community generalization:

- Group settings by connector type
- Show which connectors are "enabled" (have required keys set)
- Connector-specific help text and setup guides

## Job Processing Changes

```python
async def process_source_ingestion(self, db, job):
    source = db.query(CommunitySource).get(job.source_id)
    connector = CONNECTOR_REGISTRY[source.source_type](db=db, user_id=job.created_by)

    # Step 1: Refresh metadata
    metadata = await connector.fetch_metadata(source)
    source.update_from_metadata(metadata)

    # Step 2: Fetch members
    members_data = await connector.fetch_members(source, limit=200)

    # Step 3: Upsert members + activity
    for md in members_data:
        member = upsert_member(db, md, source)
        activities = await connector.fetch_activity(source, member)
        upsert_activities(db, member, source, activities)
        upsert_lead_score(db, source.project_id, member, activities)

    # Step 4: Queue enrichment
    queue_enrichment_jobs(db, source)
```

## Phasing

| Phase | Connectors | Target |
|-------|-----------|--------|
| **Phase 1** | GitHub Repo (refactor existing) | Prove the abstraction works |
| **Phase 2** | Discord, Reddit | Most common developer communities |
| **Phase 3** | X, GitHub Org | Social/brand signals |
| **Phase 4** | Stock Forum, Custom | Niche verticals |

## Required API Keys Per Connector

| Connector | Settings Key(s) | Free Tier? |
|-----------|----------------|------------|
| GitHub | `GITHUB_TOKEN` | Yes (60 req/hr unauth, 5000/hr with token) |
| Discord | `DISCORD_BOT_TOKEN` | Yes (bot accounts are free) |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Yes (script apps) |
| X | `X_BEARER_TOKEN` | Free tier: 500K tweets/month read |
| StockTwits | `STOCKTWITS_TOKEN` | Yes |

## Success Criteria

- Connector interface is clean enough that a new connector can be added in < 200 lines
- GitHub connector passes all existing tests after refactor
- At least Discord + Reddit connectors are functional in Phase 2
- UI dynamically renders source-type-specific config and icons
