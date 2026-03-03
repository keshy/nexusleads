"""StockTwits connector — fetches stream participants for a ticker symbol."""
import asyncio
import logging
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from .base import BaseConnector
from .registry import ConnectorRegistry
from settings_service import get_setting, get_user_org_id

logger = logging.getLogger(__name__)

STOCKTWITS_API = "https://api.stocktwits.com/api/2"


class StockTwitsConnector(BaseConnector):
    """Connector for StockTwits ticker streams.

    Fetches recent message authors for a tracked ticker symbol.
    The StockTwits API is public but an access token enables higher rate limits.
    """

    source_type = "stock_forum"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        super().__init__(db=db, user_id=user_id, source_config=source_config)
        org_id = get_user_org_id(db, user_id) if db and user_id else None
        self.token = get_setting(db, "STOCKTWITS_TOKEN", org_id=org_id) if db else ""
        # StockTwits public API works without a token (lower rate limits)
        # so we don't raise on missing token

    def _ticker(self, source: Any) -> str:
        """Extract ticker symbol from source config or URL."""
        cfg = dict(source.source_config or {})
        if cfg.get("ticker_symbols"):
            symbols = cfg["ticker_symbols"]
            return symbols[0] if isinstance(symbols, list) else str(symbols)

        # Try from external_url: https://stocktwits.com/symbol/AAPL
        import re
        url = source.external_url or ""
        match = re.search(r"stocktwits\.com/symbol/([A-Za-z.]+)", url)
        if match:
            return match.group(1).upper()

        # Try from full_name
        name = source.full_name or ""
        if name.startswith("$"):
            return name[1:].upper()
        if name:
            return name.upper()

        raise ValueError("Cannot determine ticker symbol from source")

    def _params(self) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if self.token:
            params["access_token"] = self.token
        return params

    # ── Source metadata ──────────────────────────────────────────────

    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        ticker = self._ticker(source)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{STOCKTWITS_API}/streams/symbol/{ticker}.json",
                params=self._params(),
            )
            resp.raise_for_status()
            data = resp.json()
        symbol = data.get("symbol", {})
        return {
            "full_name": f"${ticker}",
            "description": symbol.get("title", ""),
            "stars": symbol.get("watchlist_count", 0),
        }

    # ── Members ──────────────────────────────────────────────────────

    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        ticker = self._ticker(source)
        seen: Dict[str, Dict[str, Any]] = {}
        max_id = None

        async with httpx.AsyncClient(timeout=15) as client:
            # Paginate through the stream to collect unique authors
            pages = 0
            while len(seen) < limit and pages < 10:
                params = self._params()
                if max_id:
                    params["max"] = str(max_id)

                resp = await client.get(
                    f"{STOCKTWITS_API}/streams/symbol/{ticker}.json",
                    params=params,
                )
                if resp.status_code == 429:
                    logger.warning("StockTwits rate limited, waiting 60s")
                    await asyncio.sleep(60)
                    continue
                resp.raise_for_status()

                data = resp.json()
                messages = data.get("messages", [])
                if not messages:
                    break

                for msg in messages:
                    user = msg.get("user", {})
                    uid = str(user.get("id", ""))
                    if uid and uid not in seen:
                        seen[uid] = self._normalize(user, msg)

                cursor = data.get("cursor", {})
                max_id = cursor.get("max")
                if not max_id:
                    # Fallback: use the last message id
                    max_id = messages[-1].get("id")
                pages += 1
                await asyncio.sleep(1)  # rate limit

        members = list(seen.values())[:limit]
        logger.info(f"StockTwits: fetched {len(members)} members for ${ticker}")
        return members

    # ── Activity ─────────────────────────────────────────────────────

    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        # StockTwits doesn't have per-user activity for a specific ticker
        return {
            "total_commits": 0,
            "commits_last_3_months": 0,
            "pull_requests": 0,
            "issues_opened": 0,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(user: Dict, message: Dict = None) -> Dict[str, Any]:
        """Normalize a StockTwits user to the standard member format."""
        username = user.get("username", "")
        followers = user.get("followers", 0)

        # Determine role based on follower count / classification
        role = "member"
        if user.get("official"):
            role = "analyst"
        elif followers and followers > 1000:
            role = "contributor"

        return {
            "platform_id": str(user.get("id", "")),
            "username": f"stocktwits:{username}",
            "full_name": user.get("name") or username,
            "email": None,
            "company": None,
            "location": None,
            "bio": (user.get("bio") or "")[:500],
            "avatar_url": user.get("avatar_url_ssl") or user.get("avatar_url"),
            "profile_url": f"https://stocktwits.com/{username}",
            "followers": followers,
            "role": role,
        }


# Auto-register on import
ConnectorRegistry.register("stock_forum", StockTwitsConnector)
