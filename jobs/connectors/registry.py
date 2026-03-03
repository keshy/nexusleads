"""Connector registry — maps source_type strings to connector classes."""
from typing import Dict, Type, Optional
from sqlalchemy.orm import Session

from .base import BaseConnector

_REGISTRY: Dict[str, Type[BaseConnector]] = {}


class ConnectorRegistry:
    """Central registry for community source connectors."""

    @staticmethod
    def register(source_type: str, connector_cls: Type[BaseConnector]):
        """Register a connector class for a source type."""
        _REGISTRY[source_type] = connector_cls

    @staticmethod
    def get(source_type: str) -> Optional[Type[BaseConnector]]:
        """Get the connector class for a source type."""
        return _REGISTRY.get(source_type)

    @staticmethod
    def list_types():
        """List all registered source types."""
        return list(_REGISTRY.keys())


def get_connector(
    source_type: str,
    db: Session = None,
    user_id=None,
    source_config: dict = None,
) -> BaseConnector:
    """Instantiate the appropriate connector for a source type.

    Raises ValueError if no connector is registered for the type.
    """
    cls = _REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"No connector registered for source type: {source_type}")
    return cls(db=db, user_id=user_id, source_config=source_config)
