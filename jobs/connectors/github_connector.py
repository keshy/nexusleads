"""GitHub connector — wraps the existing GitHubService behind the BaseConnector interface."""
import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .base import BaseConnector
from .registry import ConnectorRegistry
from services.github_service import GitHubService
from config import config

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """Connector for GitHub repositories."""

    source_type = "github_repo"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        super().__init__(db=db, user_id=user_id, source_config=source_config)
        self._gh = GitHubService(db=db, user_id=user_id)

    # ── Source metadata ──────────────────────────────────────────────

    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        repo_data = await asyncio.to_thread(
            self._gh.get_repository, source.owner, source.repo_name
        )
        return {
            "description": repo_data.get("description"),
            "stars": repo_data.get("stars", 0),
            "forks": repo_data.get("forks", 0),
            "open_issues": repo_data.get("open_issues", 0),
            "language": repo_data.get("language"),
            "topics": repo_data.get("topics", []),
        }

    # ── Members ──────────────────────────────────────────────────────

    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        raw = await asyncio.to_thread(
            self._gh.get_contributors, source.owner, source.repo_name, limit
        )
        return [self._normalize_member(m) for m in raw]

    # ── Activity / Stats ─────────────────────────────────────────────

    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        stats = await asyncio.to_thread(
            self._gh.get_contributor_stats, source.owner, source.repo_name, username
        )

        if config.FETCH_PR_ISSUE_COUNTS:
            prs, issues = await asyncio.to_thread(
                self._gh.get_pr_issue_counts, source.owner, source.repo_name, username
            )
            stats["pull_requests"] = prs
            stats["issues_opened"] = issues

        return stats

    async def fetch_member_activity_bulk(self, source: Any) -> Dict[str, Dict[str, Any]]:
        if not config.USE_BULK_CONTRIBUTOR_STATS:
            return {}
        return await asyncio.to_thread(
            self._gh.get_contributor_stats_bulk, source.owner, source.repo_name
        )

    # ── Discovery ────────────────────────────────────────────────────

    async def discover_sources(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        raw = await asyncio.to_thread(self._gh.search_repositories, query, limit)
        return [
            {
                "full_name": r.get("full_name", ""),
                "external_url": r.get("url", ""),
                "description": r.get("description", ""),
                "stars": r.get("stars", 0),
                "forks": r.get("forks", 0),
                "language": r.get("language"),
            }
            for r in raw
        ]

    # ── Secondary members (stargazers) ───────────────────────────────

    async def fetch_secondary_members(
        self, source: Any, member_type: str = "stargazer", limit: int = 200
    ) -> List[Dict[str, Any]]:
        if member_type != "stargazer":
            return []
        raw = await asyncio.to_thread(
            self._gh.get_stargazers, source.owner, source.repo_name, limit
        )
        return [self._normalize_member(m) for m in raw]

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize_member(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a GitHub user dict to the standard member format."""
        return {
            "platform_id": raw.get("github_id"),
            "username": raw.get("username"),
            "full_name": raw.get("full_name"),
            "email": raw.get("email"),
            "company": raw.get("company"),
            "location": raw.get("location"),
            "bio": raw.get("bio"),
            "blog": raw.get("blog"),
            "twitter_username": raw.get("twitter_username"),
            "avatar_url": raw.get("avatar_url"),
            "profile_url": raw.get("github_url"),
            "public_repos": raw.get("public_repos", 0),
            "followers": raw.get("followers", 0),
            "following": raw.get("following", 0),
            "contributions": raw.get("contributions"),
            # GitHub-specific extras preserved
            "github_id": raw.get("github_id"),
            "github_url": raw.get("github_url"),
        }


# Auto-register on import
ConnectorRegistry.register("github_repo", GitHubConnector)
