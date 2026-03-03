"""Reddit connector — fetches subreddit participants via Reddit OAuth2 API."""
import asyncio
import logging
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from .base import BaseConnector
from .registry import ConnectorRegistry
from settings_service import get_setting, get_user_org_id

logger = logging.getLogger(__name__)

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API = "https://oauth.reddit.com"
USER_AGENT = "NexusLeads/1.0 (community lead sourcing)"


class RedditConnector(BaseConnector):
    """Connector for Reddit subreddits.

    Uses OAuth2 application-only (script) auth.
    Fetches recent post/comment authors in a subreddit.
    """

    source_type = "reddit_subreddit"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        super().__init__(db=db, user_id=user_id, source_config=source_config)
        org_id = get_user_org_id(db, user_id) if db and user_id else None
        self.client_id = get_setting(db, "REDDIT_CLIENT_ID", org_id=org_id) if db else ""
        self.client_secret = get_setting(db, "REDDIT_CLIENT_SECRET", org_id=org_id) if db else ""
        if not self.client_id or not self.client_secret:
            raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are not configured")
        self._access_token: str = ""

    async def _authenticate(self):
        """Get an OAuth2 bearer token using client credentials."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                REDDIT_AUTH_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": USER_AGENT,
        }

    def _subreddit_name(self, source: Any) -> str:
        """Extract subreddit name from source."""
        name = source.full_name or ""
        if name.startswith("r/"):
            return name[2:]
        # Try from external_url
        url = source.external_url or ""
        import re
        match = re.search(r"reddit\.com/r/([^/]+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot determine subreddit name from source: {source.full_name}")

    # ── Source metadata ──────────────────────────────────────────────

    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        await self._authenticate()
        sub = self._subreddit_name(source)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{REDDIT_API}/r/{sub}/about",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        return {
            "full_name": f"r/{sub}",
            "description": (data.get("public_description") or data.get("title") or "")[:500],
            "stars": data.get("subscribers", 0),
        }

    # ── Members ──────────────────────────────────────────────────────

    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        await self._authenticate()
        sub = self._subreddit_name(source)
        seen_authors: Dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=15) as client:
            # Fetch from hot + new posts to get active participants
            for listing in ("hot", "new"):
                after = None
                fetched = 0
                while fetched < limit * 2 and len(seen_authors) < limit:
                    params: Dict[str, Any] = {"limit": 100}
                    if after:
                        params["after"] = after
                    resp = await client.get(
                        f"{REDDIT_API}/r/{sub}/{listing}",
                        headers=self._headers(),
                        params=params,
                    )
                    if resp.status_code == 429:
                        await asyncio.sleep(2)
                        continue
                    resp.raise_for_status()
                    listing_data = resp.json().get("data", {})
                    posts = listing_data.get("children", [])
                    if not posts:
                        break

                    for post in posts:
                        pd = post.get("data", {})
                        author = pd.get("author")
                        if not author or author in ("[deleted]", "AutoModerator"):
                            continue
                        if author not in seen_authors:
                            seen_authors[author] = {
                                "username": author,
                                "post_karma": pd.get("score", 0),
                                "is_op": True,
                            }
                        # Also grab commenters from the post
                        # (only top-level for efficiency)

                    after = listing_data.get("after")
                    fetched += len(posts)
                    if not after:
                        break
                    await asyncio.sleep(0.6)  # ~60 req/min

            # Now fetch comment authors from recent comments
            resp = await client.get(
                f"{REDDIT_API}/r/{sub}/comments",
                headers=self._headers(),
                params={"limit": 100},
            )
            if resp.status_code == 200:
                for comment in resp.json().get("data", {}).get("children", []):
                    cd = comment.get("data", {})
                    author = cd.get("author")
                    if not author or author in ("[deleted]", "AutoModerator"):
                        continue
                    if author not in seen_authors:
                        seen_authors[author] = {
                            "username": author,
                            "post_karma": cd.get("score", 0),
                            "is_op": False,
                        }

        # Enrich with user profiles (batch, respecting rate limits)
        members = []
        authors_list = list(seen_authors.values())[:limit]
        async with httpx.AsyncClient(timeout=15) as client:
            for author_info in authors_list:
                uname = author_info["username"]
                try:
                    resp = await client.get(
                        f"{REDDIT_API}/user/{uname}/about",
                        headers=self._headers(),
                    )
                    if resp.status_code == 200:
                        ud = resp.json().get("data", {})
                        members.append(self._normalize(ud))
                    else:
                        members.append(self._normalize_minimal(uname))
                except Exception:
                    members.append(self._normalize_minimal(uname))
                await asyncio.sleep(0.6)

        logger.info(f"Reddit: fetched {len(members)} members from r/{sub}")
        return members

    # ── Activity ─────────────────────────────────────────────────────

    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        # Reddit doesn't expose per-subreddit activity easily
        # Return stub — enrichment handles the rest
        return {
            "total_commits": 0,
            "commits_last_3_months": 0,
            "pull_requests": 0,
            "issues_opened": 0,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(user_data: Dict) -> Dict[str, Any]:
        """Normalize a Reddit user about response."""
        name = user_data.get("name", "")
        return {
            "platform_id": user_data.get("id"),
            "username": f"reddit:{name}",
            "full_name": user_data.get("subreddit", {}).get("title") or name,
            "email": None,
            "company": None,
            "location": None,
            "bio": (user_data.get("subreddit", {}).get("public_description") or "")[:500],
            "avatar_url": user_data.get("icon_img", "").split("?")[0] or None,
            "profile_url": f"https://reddit.com/user/{name}",
            "followers": user_data.get("subreddit", {}).get("subscribers", 0),
            "role": "member",
        }

    @staticmethod
    def _normalize_minimal(username: str) -> Dict[str, Any]:
        """Minimal member dict when profile fetch fails."""
        return {
            "platform_id": username,
            "username": f"reddit:{username}",
            "full_name": username,
            "email": None,
            "company": None,
            "location": None,
            "bio": None,
            "avatar_url": None,
            "profile_url": f"https://reddit.com/user/{username}",
            "followers": 0,
            "role": "member",
        }


# Auto-register on import
ConnectorRegistry.register("reddit_subreddit", RedditConnector)
