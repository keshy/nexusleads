"""Discord connector — fetches server members and message activity via Discord Bot API."""
import asyncio
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from .base import BaseConnector
from .registry import ConnectorRegistry
from settings_service import get_setting, get_user_org_id

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


class DiscordConnector(BaseConnector):
    """Connector for Discord servers.

    Requires a bot token with SERVER MEMBERS INTENT enabled.
    The guild_id is extracted from the source's external_url or source_config.
    """

    source_type = "discord_server"

    def __init__(self, db: Session = None, user_id=None, source_config: Dict[str, Any] = None):
        super().__init__(db=db, user_id=user_id, source_config=source_config)
        org_id = get_user_org_id(db, user_id) if db and user_id else None
        self.token = get_setting(db, "DISCORD_BOT_TOKEN", org_id=org_id) if db else ""
        if not self.token:
            raise ValueError("DISCORD_BOT_TOKEN is not configured")
        self._headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

    def _guild_id(self, source: Any) -> str:
        """Extract guild ID from source config or external_url."""
        cfg = dict(source.source_config or {})
        if cfg.get("guild_id"):
            return str(cfg["guild_id"])
        # Try to resolve from invite URL — requires an API call
        # For now expect guild_id in source_config
        raise ValueError(
            "guild_id not found in source_config. "
            "Please set it via the source configuration."
        )

    # ── Source metadata ──────────────────────────────────────────────

    async def fetch_source_metadata(self, source: Any) -> Dict[str, Any]:
        guild_id = self._guild_id(source)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{DISCORD_API}/guilds/{guild_id}?with_counts=true",
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "full_name": data.get("name", source.full_name),
            "description": data.get("description") or "",
            "stars": data.get("approximate_member_count", 0),  # reuse stars field for member count
        }

    # ── Members ──────────────────────────────────────────────────────

    async def fetch_members(self, source: Any, limit: int = 100) -> List[Dict[str, Any]]:
        guild_id = self._guild_id(source)
        members: List[Dict[str, Any]] = []
        after = "0"

        async with httpx.AsyncClient(timeout=30) as client:
            while len(members) < limit:
                batch_limit = min(1000, limit - len(members))
                resp = await client.get(
                    f"{DISCORD_API}/guilds/{guild_id}/members",
                    headers=self._headers,
                    params={"limit": batch_limit, "after": after},
                )
                if resp.status_code == 403:
                    raise ValueError(
                        "Bot lacks SERVER MEMBERS INTENT or access to this guild. "
                        "Enable it in the Discord Developer Portal."
                    )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break

                for m in batch:
                    user = m.get("user", {})
                    if user.get("bot"):
                        continue
                    members.append(self._normalize(user, m))

                after = batch[-1]["user"]["id"]
                if len(batch) < batch_limit:
                    break
                await asyncio.sleep(0.5)  # rate-limit courtesy

        logger.info(f"Discord: fetched {len(members)} members from guild {guild_id}")
        return members[:limit]

    # ── Activity ─────────────────────────────────────────────────────

    async def fetch_member_activity(
        self, source: Any, member_platform_id: Any, username: str
    ) -> Dict[str, Any]:
        # Discord doesn't have a per-user activity API for bots
        # Activity would need message scanning which is expensive
        # Return a stub — enrichment will fill in the rest
        return {
            "total_commits": 0,
            "commits_last_3_months": 0,
            "pull_requests": 0,
            "issues_opened": 0,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize(user: Dict, member: Dict) -> Dict[str, Any]:
        """Normalize a Discord guild member to the standard member format."""
        username = user.get("username", "")
        discriminator = user.get("discriminator", "0")
        display = f"{username}#{discriminator}" if discriminator != "0" else username
        nick = member.get("nick")
        avatar_hash = user.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_hash}.png"
            if avatar_hash
            else None
        )

        # Map top Discord role to our role taxonomy
        role = "member"
        if member.get("permissions"):
            perms = int(member["permissions"])
            if perms & 0x8:  # ADMINISTRATOR
                role = "moderator"

        return {
            "platform_id": user.get("id"),
            "username": f"discord:{username}",
            "full_name": nick or user.get("global_name") or username,
            "email": None,
            "company": None,
            "location": None,
            "bio": None,
            "avatar_url": avatar_url,
            "profile_url": None,
            "followers": 0,
            "role": role,
        }


# Auto-register on import
ConnectorRegistry.register("discord_server", DiscordConnector)
