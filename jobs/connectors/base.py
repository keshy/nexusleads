"""Base connector interface for community sources."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


class BaseConnector(ABC):
    """Abstract base class for community source connectors.

    Each connector handles fetching data from a specific platform type
    (GitHub, Discord, Reddit, etc.). Connectors are stateless — they
    receive configuration and return normalized data dicts.
    """

    source_type: str = ""  # e.g. "github_repo", "discord_server"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        """Initialize connector with optional DB session for reading settings."""
        self.db = db
        self.user_id = user_id
        self.source_config = source_config or {}

    # ── Source metadata ──────────────────────────────────────────────

    @abstractmethod
    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        """Fetch and return updated metadata for a community source.

        Returns a dict of fields to update on the CommunitySource row,
        e.g. {"description": "...", "stars": 42, ...}.
        """

    # ── Members ──────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch members from the community source.

        Returns a list of normalized member dicts with at minimum:
        {
            "platform_id": <platform-specific unique id>,
            "username": "...",
            "full_name": "..." or None,
            "email": "..." or None,
            "company": "..." or None,
            "avatar_url": "..." or None,
            "profile_url": "..." or None,
            ...
        }
        """

    # ── Activity / Stats ─────────────────────────────────────────────

    @abstractmethod
    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        """Fetch activity stats for a single member in this source.

        Returns a dict of activity metrics, e.g.:
        {
            "total_commits": 42,
            "commits_last_3_months": 10,
            "pull_requests": 5,
            ...
        }
        """

    # ── Optional: Bulk stats ─────────────────────────────────────────

    async def fetch_member_activity_bulk(self, source: Any) -> Dict[str, Dict[str, Any]]:
        """Optionally fetch activity for all members at once.

        Returns {username_lower: activity_dict}.
        Default returns empty dict (connector does not support bulk).
        """
        return {}

    # ── Optional: Discovery ──────────────────────────────────────────

    async def discover_sources(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for sources of this type matching a query.

        Returns a list of dicts with at minimum:
        {
            "full_name": "...",
            "external_url": "...",
            "description": "...",
            ...
        }
        Default returns empty list.
        """
        return []

    # ── Optional: Secondary member types ─────────────────────────────

    async def fetch_secondary_members(
        self, source: Any, member_type: str = "stargazer", limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Fetch secondary member types (e.g. stargazers for GitHub).

        Default returns empty list.
        """
        return []
