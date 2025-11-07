"""Redis manager for UltimaScraperAPI.

This module provides centralized Redis connection management and operations
for the entire application.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.asyncio.client import PubSub

if TYPE_CHECKING:
    from ultima_scraper_api.config import Redis as RedisConfig


logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connection and operations for USAPI.

    This class provides a centralized interface for all Redis operations,
    including connection management, pub/sub, and key-value operations.
    """

    # Single source of truth for Redis key prefix
    KEY_PREFIX = "ultimascraper"

    # Default Redis channels
    LOGS_CHANNEL = f"{KEY_PREFIX}:logs"
    HOOKS_CHANNEL = f"{KEY_PREFIX}:hooks"

    def __init__(
        self,
        config: RedisConfig,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        socket_keepalive: bool = True,
        socket_keepalive_options: Optional[dict[int, int]] = None,
        retry_on_timeout: bool = True,
        **pool_kwargs: Any,
    ) -> None:
        """Initialize Redis manager with connection pooling.

        Args:
            config: Redis configuration object
            max_connections: Maximum connections in pool (default: 50)
            socket_timeout: Socket timeout in seconds (default: 5.0)
            socket_connect_timeout: Connection timeout in seconds (default: 5.0)
            socket_keepalive: Enable TCP keepalive (default: True)
            socket_keepalive_options: TCP keepalive options
            retry_on_timeout: Whether to retry on timeout (default: True)
            **pool_kwargs: Additional ConnectionPool arguments
        """
        self.config = config
        self.client: Optional[Any] = None
        self._pubsub: Optional[PubSub] = None
        self._connected = False
        self._pool: Optional[ConnectionPool] = None

        # Store pool configuration
        self.pool_config: dict[str, Any] = {
            "host": config.host,
            "port": config.port,
            "db": config.db,
            "password": config.password,
            "max_connections": max_connections,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "socket_keepalive": socket_keepalive,
            "socket_keepalive_options": socket_keepalive_options,
            "retry_on_timeout": retry_on_timeout,
            "decode_responses": True,
            **pool_kwargs,
        }

    async def connect(self) -> bool:
        """Connect to Redis server with connection pooling.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        if not self.config.enabled:
            logger.info("Redis is disabled in configuration")
            return False

        try:
            # Create connection pool
            self._pool = ConnectionPool(**self.pool_config)

            # Create Redis client with pool
            self.client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info(
                "Connected to Redis at %s:%s (db=%s, pool: max_connections=%s, timeout=%ss)",
                self.config.host,
                self.config.port,
                self.config.db,
                self.pool_config["max_connections"],
                self.pool_config["socket_timeout"],
            )
            return True
        except Exception as exc:
            logger.warning("Failed to connect to Redis: %s", exc)
            self.client = None
            self._connected = False
            if self._pool:
                await self._pool.aclose()
                self._pool = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server and close connection pool."""
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()  # type: ignore
                await self._pubsub.close()
            except Exception as exc:
                logger.debug("Error closing pubsub: %s", exc)
            self._pubsub = None

        if self.client:
            try:
                await self.client.aclose()
            except Exception as exc:
                logger.debug("Error closing Redis client: %s", exc)
            self.client = None

        if self._pool:
            try:
                await self._pool.aclose()
            except Exception as exc:
                logger.debug("Error closing connection pool: %s", exc)
            self._pool = None

        self._connected = False
        logger.info("Disconnected from Redis")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self.client is not None

    # Pub/Sub Operations

    async def publish(self, channel: str, message: str) -> bool:
        """Publish message to Redis channel.

        Args:
            channel: Channel name
            message: Message to publish

        Returns:
            bool: True if published successfully
        """
        if not self.is_connected or not self.client:
            return False

        try:
            await self.client.publish(channel, message)
            return True
        except Exception as exc:
            logger.debug("Failed to publish to Redis: %s", exc)
            return False

    async def publish_json(self, channel: str, data: dict[str, Any]) -> bool:
        """Publish JSON data to Redis channel.

        Args:
            channel: Channel name
            data: Dictionary to publish as JSON

        Returns:
            bool: True if published successfully
        """
        try:
            message = json.dumps(data)
            return await self.publish(channel, message)
        except Exception as exc:
            logger.debug("Failed to serialize/publish JSON to Redis: %s", exc)
            return False

    async def subscribe(self, *channels: str) -> Optional[PubSub]:
        """Subscribe to Redis channels.

        Args:
            *channels: Channel names to subscribe to

        Returns:
            PubSub object if successful, None otherwise
        """
        if not self.is_connected or not self.client:
            return None

        try:
            self._pubsub = self.client.pubsub()
            await self._pubsub.subscribe(*channels)  # type: ignore
            return self._pubsub
        except Exception as exc:
            logger.debug("Failed to subscribe to Redis channels: %s", exc)
            return None

    # Key-Value Operations

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis.

        Args:
            key: Key name
            value: Value to store
            ex: Expiration time in seconds (optional)

        Returns:
            bool: True if set successfully
        """
        if not self.is_connected or not self.client:
            return False

        try:
            await self.client.set(key, value, ex=ex)
            return True
        except Exception as exc:
            logger.debug("Failed to set Redis key: %s", exc)
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis.

        Args:
            key: Key name

        Returns:
            Value if found, None otherwise
        """
        if not self.is_connected or not self.client:
            return None

        try:
            return await self.client.get(key)
        except Exception as exc:
            logger.debug("Failed to get Redis key: %s", exc)
            return None

    async def delete(self, key: str) -> bool:
        """Delete key from Redis.

        Args:
            key: Key name

        Returns:
            bool: True if deleted successfully
        """
        if not self.is_connected or not self.client:
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as exc:
            logger.debug("Failed to delete Redis key: %s", exc)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis.

        Args:
            key: Key name

        Returns:
            bool: True if key exists
        """
        if not self.is_connected or not self.client:
            return False

        try:
            return bool(await self.client.exists(key))
        except Exception as exc:
            logger.debug("Failed to check Redis key existence: %s", exc)
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: Key name
            seconds: Expiration time in seconds

        Returns:
            bool: True if expiration set successfully
        """
        if not self.is_connected or not self.client:
            return False

        try:
            await self.client.expire(key, seconds)
            return True
        except Exception as exc:
            logger.debug("Failed to set Redis key expiration: %s", exc)
            return False

    # High-level convenience methods

    async def publish_log(self, log_data: dict[str, Any]) -> bool:
        """Publish log message to logs channel.

        Args:
            log_data: Log data to publish

        Returns:
            bool: True if published successfully
        """
        return await self.publish_json(self.LOGS_CHANNEL, log_data)

    async def publish_hook(self, hook_data: dict[str, Any]) -> bool:
        """Publish hook event to hooks channel.

        Args:
            hook_data: Hook event data to publish

        Returns:
            bool: True if published successfully
        """
        return await self.publish_json(self.HOOKS_CHANNEL, hook_data)


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def initialize_redis(config: RedisConfig) -> RedisManager:
    """Initialize global Redis manager.

    Args:
        config: Redis configuration

    Returns:
        RedisManager instance
    """
    global _redis_manager
    if _redis_manager:
        return _redis_manager
    _redis_manager = RedisManager(config)
    return _redis_manager


def get_redis() -> Optional[RedisManager]:
    """Get global Redis manager instance.

    Returns:
        RedisManager if initialized, None otherwise
    """
    return _redis_manager


async def shutdown_redis() -> None:
    """Shutdown global Redis manager."""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.disconnect()
        _redis_manager = None
