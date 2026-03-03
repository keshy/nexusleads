"""X / Twitter connector — fetches followers and engagers via X API v2."""
import asyncio
import logging
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from .base import BaseConnector
from .registry import ConnectorRegistry
from settings_service import get_setting, get_user_org_id

logger = logging.getLogger(__name__)

X_API = "https://api.twitter.com/2"


class XConnector(BaseConnector):
    """Connector for X (Twitter) accounts.

    Uses the X API v2 with a Bearer Token.
    Fetches followers of a tracked account and optionally engagers
    (users who replied to / retweeted / quoted the account's tweets).
    """

    source_type = "x_account"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        super().__init__(db=db, user_id=user_id, source_config=source_config)
        org_id = get_user_org_id(db, user_id) if db and user_id else None
        self.token = get_setting(db, "X_BEARER_TOKEN", org_id=org_id) if db else ""
        if not self.token:
            raise ValueError("X_BEARER_TOKEN is not configured")
        self._headers = {
            "Authorization": f"Bearer {self.token}",
        }

    def _account_handle(self, source: Any) -> str:
        """Extract the X handle from the source."""
        name = source.full_name or ""
        if name.startswith("@"):
            return name[1:]
        # Try from external_url
        import re
        url = source.external_url or ""
        match = re.search(r"(?:twitter|x)\.com/([^/?\s]+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot determine X handle from source: {source.full_name}")

    async def _get_user_id(self, client: httpx.AsyncClient, handle: str) -> str:
        """Resolve a handle to a numeric user ID."""
        resp = await client.get(
            f"{X_API}/users/by/username/{handle}",
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json().get("data")
        if not data:
            raise ValueError(f"X user @{handle} not found")
        return data["id"]

    # ── Source metadata ──────────────────────────────────────────────

    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        handle = self._account_handle(source)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{X_API}/users/by/username/{handle}",
                headers=self._headers,
                params={"user.fields": "public_metrics,description"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        metrics = data.get("public_metrics", {})
        return {
            "full_name": f"@{handle}",
            "description": data.get("description", "")[:500],
            "stars": metrics.get("followers_count", 0),
        }

    # ── Members ──────────────────────────────────────────────────────

    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        handle = self._account_handle(source)
        members: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30) as client:
            user_id = await self._get_user_id(client, handle)

            # Fetch followers
            pagination_token = None
            while len(members) < limit:
                params: Dict[str, Any] = {
                    "max_results": min(1000, limit - len(members)),
                    "user.fields": "name,username,description,profile_image_url,public_metrics,location",
                }
                if pagination_token:
                    params["pagination_token"] = pagination_token

                resp = await client.get(
                    f"{X_API}/users/{user_id}/followers",
                    headers=self._headers,
                    params=params,
                )

                if resp.status_code == 429:
                    # Rate limited — wait and retry
                    retry_after = int(resp.headers.get("retry-after", "60"))
                    logger.warning(f"X API rate limited, waiting {retry_after}s")
                    await asyncio.sleep(min(retry_after, 120))
                    continue

                resp.raise_for_status()
                body = resp.json()
                users = body.get("data", [])
                if not users:
                    break

                for u in users:
                    members.append(self._normalize(u, role="follower"))

                pagination_token = body.get("meta", {}).get("next_token")
                if not pagination_token:
                    break
                await asyncio.sleep(1)  # courtesy delay

            # Also try to fetch recent engagers (people who replied)
            try:
                resp = await client.get(
                    f"{X_API}/users/{user_id}/mentions",
                    headers=self._headers,
                    params={
                        "max_results": 100,
                        "expansions": "author_id",
                        "user.fields": "name,username,description,profile_image_url,public_metrics,location",
                    },
                )
                if resp.status_code == 200:
                    includes = resp.json().get("includes", {})
                    for u in includes.get("users", []):
                        # Avoid duplicates
                        if not any(m["platform_id"] == u["id"] for m in members):
                            members.append(self._normalize(u, role="engager"))
            except Exception as e:
                logger.warning(f"Failed to fetch X engagers: {e}")

        logger.info(f"X: fetched {len(members)} members for @{handle}")
        return members[:limit]

    # ── Activity ─────────────────────────────────────────────────────

    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        # X API doesn't provide per-relationship activity easily
        # Public metrics are captured in the member fetch
        return {
            "total_commits": 0,
            "commits_last_3_months": 0,
            "pull_requests": 0,
            "issues_opened": 0,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(user: Dict, role: str = "follower") -> Dict[str, Any]:
        """Normalize an X API v2 user object."""
        metrics = user.get("public_metrics", {})
        return {
            "platform_id": user.get("id"),
            "username": f"x:{user.get('username', '')}",
            "full_name": user.get("name"),
            "email": None,
            "company": None,
            "location": user.get("location"),
            "bio": (user.get("description") or "")[:500],
            "avatar_url": user.get("profile_image_url"),
            "profile_url": f"https://x.com/{user.get('username', '')}",
            "followers": metrics.get("followers_count", 0),
            "role": role,
        }


# Auto-register on import
ConnectorRegistry.register("x_account", XConnector)
