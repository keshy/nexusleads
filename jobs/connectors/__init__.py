"""Community source connectors."""
from .base import BaseConnector
from .registry import ConnectorRegistry, get_connector

# Import all connectors so they auto-register
from . import github_connector      # noqa: F401
from . import discord_connector     # noqa: F401
from . import reddit_connector      # noqa: F401
from . import x_connector           # noqa: F401
from . import stocktwits_connector  # noqa: F401

__all__ = ["BaseConnector", "ConnectorRegistry", "get_connector"]
