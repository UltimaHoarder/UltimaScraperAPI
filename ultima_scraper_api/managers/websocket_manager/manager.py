"""Centralized WebSocket manager for all sites."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Type

if TYPE_CHECKING:
    from ultima_scraper_api.config import UltimaScraperAPIConfig
    from ultima_scraper_api.managers.redis import RedisManager
    from ultima_scraper_api.managers.websocket_manager.connection import (
        WebSocketConnection,
    )
    from ultima_scraper_api.managers.websocket_manager.protocol import WebSocketProtocol

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Centralized WebSocket manager for all sites.

    Manages WebSocket connections across all supported sites (OnlyFans, Fansly, etc.).
    Creates and tracks individual WebSocketConnection instances with site-specific implementations.
    """

    def __init__(
        self,
        config: UltimaScraperAPIConfig | None = None,
        redis_manager: RedisManager | None = None,
    ) -> None:
        """Initialize centralized WebSocket manager.

        Args:
            redis_manager: Optional Redis manager for publishing messages
            config: Optional configuration object
        """
        self.redis_manager = redis_manager
        self.config = config
        self._connections: dict[str, WebSocketConnection] = {}
        if redis_manager:
            logger.info("WebSocket manager initialized with Redis")
        else:
            logger.warning(
                "⚠️ WebSocket manager initialized WITHOUT Redis - messages won't be stored"
            )

    def set_redis_manager(self, redis_manager: RedisManager) -> None:
        """Update the Redis manager for this WebSocket manager and all connections.

        This allows Redis to be set after initialization, which is useful when
        Redis needs to be initialized after the API is created.

        Args:
            redis_manager: Redis manager instance
        """
        logger.info(f"🔄 Updating WebSocket manager with Redis manager")
        self.redis_manager = redis_manager

        # Update all existing connections
        for conn_id, connection in self._connections.items():
            if not connection.redis_manager:
                connection.redis_manager = redis_manager
                # Reset storage initialization flag so it will initialize on next message
                connection._storage_initialized = False  # type: ignore[attr-defined]
                logger.info(f"Updated connection {conn_id} with Redis manager")

    def create_connection(
        self,
        auth: Any,
        websocket_impl_class: Type[WebSocketProtocol],
        connection_id: str,
        **kwargs: Any,
    ) -> WebSocketConnection:
        """Create and track a new WebSocket connection.

        Args:
            auth: Auth model from any site (OnlyFansAuthModel, FanslyAuthModel, etc.)
            websocket_impl_class: Site-specific WebSocket implementation class
            connection_id: Unique identifier for this connection
            **kwargs: Additional arguments passed to WebSocketConnection

        Returns:
            WebSocketConnection instance

        Example:
            >>> from apis.onlyfans.classes.websocket import OnlyFansWebSocket
            >>> connection = manager.create_connection(
            ...     auth=auth_model,
            ...     websocket_impl_class=OnlyFansWebSocket,
            ...     connection_id=f"onlyfans_{auth_model.id}"
            ... )
        """
        from ultima_scraper_api.managers.websocket_manager.connection import (
            WebSocketConnection,
        )

        # Instantiate site-specific WebSocket implementation
        websocket_impl = websocket_impl_class(auth)

        # Determine Redis channel if not provided
        if "redis_channel" not in kwargs and self.redis_manager:
            # Extract site name from auth model
            site_name = getattr(auth.api, "site_name", "unknown").lower()
            auth_id = getattr(auth, "id", "unknown")
            kwargs["redis_channel"] = f"{site_name}:ws:{auth_id}"

        # Create connection wrapper
        connection = WebSocketConnection(
            websocket_impl=websocket_impl,
            redis_manager=self.redis_manager,
            **kwargs,
        )

        # Track connection
        self._connections[connection_id] = connection
        logger.info(f"Created WebSocket connection: {connection_id}")

        return connection

    def get_connection(self, connection_id: str) -> WebSocketConnection | None:
        """Get a tracked connection by ID.

        Args:
            connection_id: Connection identifier

        Returns:
            WebSocketConnection if found, None otherwise
        """
        return self._connections.get(connection_id)

    def remove_connection(self, connection_id: str) -> None:
        """Remove a tracked connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self._connections:
            del self._connections[connection_id]
            logger.info(f"Removed WebSocket connection: {connection_id}")

    async def close_connection(self, connection_id: str) -> None:
        """Close and remove a connection.

        Args:
            connection_id: Connection identifier
        """
        connection = self.get_connection(connection_id)
        if connection:
            await connection.stop()
            self.remove_connection(connection_id)

    async def close_all_connections(self) -> None:
        """Close all tracked connections."""
        logger.info(f"Closing {len(self._connections)} WebSocket connections...")

        # Close all connections concurrently
        import asyncio

        tasks = [conn.stop() for conn in self._connections.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clear connections dict
        self._connections.clear()
        logger.info("All WebSocket connections closed")

    def get_all_connections(self) -> list[WebSocketConnection]:
        """Get all tracked connections.

        Returns:
            List of all WebSocketConnection instances
        """
        return list(self._connections.values())

    def get_connection_ids(self) -> list[str]:
        """Get all connection IDs.

        Returns:
            List of connection identifiers
        """
        return list(self._connections.keys())

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics for all connections.

        Returns:
            Dictionary with aggregate statistics
        """
        total_messages = 0
        total_published = 0
        total_redis_published = 0
        total_redis_failed = 0
        connected_count = 0

        for conn in self._connections.values():
            stats = conn.get_statistics()
            total_messages += stats["messages_received"]
            total_published += stats["messages_published"]
            total_redis_published += stats["redis_published"]
            total_redis_failed += stats["redis_failed"]
            if stats["is_connected"]:
                connected_count += 1

        return {
            "total_connections": len(self._connections),
            "connected_count": connected_count,
            "total_messages_received": total_messages,
            "total_messages_published": total_published,
            "total_redis_published": total_redis_published,
            "total_redis_failed": total_redis_failed,
            "connection_ids": self.get_connection_ids(),
        }
