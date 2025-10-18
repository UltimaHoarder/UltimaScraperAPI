"""WebSocket message storage in Redis with deduplication.

This module provides Redis-based storage for WebSocket messages with
built-in deduplication to handle multiple API instances.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ultima_scraper_api.managers.redis.connection import RedisManager

logger = logging.getLogger(__name__)


class WebSocketStorage:
    """
    Stores WebSocket messages in Redis with automatic deduplication.

    Features:
    - Deduplication using message content hashing
    - TTL-based expiration for dedup tracking
    - Configurable storage keys and channels
    - Support for multiple API instances
    - Message retrieval and filtering
    """

    def __init__(
        self,
        redis_manager: RedisManager,
        namespace: str = "websocket",
        dedup_ttl: int = 3600,  # 1 hour dedup window
        storage_ttl: Optional[int] = 86400,  # 24 hours message retention
    ) -> None:
        """
        Initialize WebSocket storage.

        Args:
            redis_manager: RedisManager instance
            namespace: Namespace suffix for Redis keys (will be prefixed with RedisManager.KEY_PREFIX)
            dedup_ttl: TTL in seconds for deduplication tracking
            storage_ttl: TTL in seconds for stored messages (None = no expiration)
        """
        self.redis = redis_manager
        self.namespace = namespace
        self.dedup_ttl = dedup_ttl
        self.storage_ttl = storage_ttl

        # Redis key patterns - all prefixed with RedisManager.KEY_PREFIX
        base_prefix = f"{redis_manager.KEY_PREFIX}:{namespace}"
        self._dedup_key_prefix = f"{base_prefix}:dedup"
        self._message_key_prefix = f"{base_prefix}:messages"
        self._index_key = f"{base_prefix}:index"
        self._channel = f"{base_prefix}:stream"

    def _generate_message_id(self, message: dict[str, Any]) -> str:
        """
        Generate a unique ID for a message based on its content.

        Args:
            message: Message dictionary

        Returns:
            Unique message ID (hash)
        """
        # Extract relevant fields for deduplication
        # Exclude timestamp as the same message can arrive at different times
        dedup_fields = {
            k: v
            for k, v in message.items()
            if k not in ("timestamp", "datetime", "received_at")
        }

        # Create deterministic hash
        content = json.dumps(dedup_fields, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def store_message(
        self,
        message: dict[str, Any],
        source_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Store a WebSocket message with deduplication.

        Args:
            message: Message dictionary to store
            source_id: Optional identifier for the API instance

        Returns:
            Tuple of (was_stored, message_id)
            - was_stored: True if message was new, False if duplicate
            - message_id: Unique ID of the message
        """
        if not self.redis.is_connected:
            logger.warning("Redis not connected, cannot store WebSocket message")
            return False, ""

        try:
            # Generate message ID
            message_id = self._generate_message_id(message)
            dedup_key = f"{self._dedup_key_prefix}:{message_id}"

            # Check if this message was already processed
            exists = await self.redis.exists(dedup_key)
            if exists:
                logger.debug(f"Duplicate message detected: {message_id}")
                return False, message_id

            # Mark as processed (with TTL)
            await self.redis.set(dedup_key, "1", ex=self.dedup_ttl)

            # Enrich message with metadata
            enriched_message: dict[str, Any] = {
                **message,
                "id": message_id,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "source_id": source_id,
            }

            # Store the full message
            message_key = f"{self._message_key_prefix}:{message_id}"
            await self.redis.set(
                message_key,
                json.dumps(enriched_message),
                ex=self.storage_ttl,
            )

            # Add to index (sorted set by timestamp)
            timestamp = message.get("timestamp", datetime.now(timezone.utc).timestamp())
            if self.redis.client:
                await self.redis.client.zadd(self._index_key, {message_id: timestamp})
                if self.storage_ttl:
                    await self.redis.expire(self._index_key, self.storage_ttl)

            # Publish to stream for real-time subscribers
            await self.redis.publish_json(self._channel, enriched_message)

            logger.debug(f"Stored WebSocket message: {message_id}")
            return True, message_id

        except Exception as e:
            logger.error(f"Failed to store WebSocket message: {e}", exc_info=True)
            return False, ""

    async def get_message(self, message_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a specific message by ID.

        Args:
            message_id: Unique message ID

        Returns:
            Message dictionary or None if not found
        """
        if not self.redis.is_connected:
            return None

        try:
            message_key = f"{self._message_key_prefix}:{message_id}"
            data = await self.redis.get(message_key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            return None

    async def get_recent_messages(
        self,
        count: int = 100,
        min_timestamp: Optional[float] = None,
        max_timestamp: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent messages from the index.

        Args:
            count: Maximum number of messages to retrieve
            min_timestamp: Optional minimum timestamp filter
            max_timestamp: Optional maximum timestamp filter

        Returns:
            List of message dictionaries, newest first
        """
        if not self.redis.is_connected or not self.redis.client:
            return []

        try:
            # Get message IDs from sorted set (newest first)
            min_score = min_timestamp if min_timestamp else "-inf"
            max_score = max_timestamp if max_timestamp else "+inf"

            message_ids = await self.redis.client.zrevrangebyscore(
                self._index_key,
                max_score,
                min_score,
                start=0,
                num=count,
            )

            # Retrieve full messages
            messages: list[dict[str, Any]] = []
            for msg_id in message_ids:
                message = await self.get_message(msg_id)
                if message:
                    messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Failed to retrieve recent messages: {e}")
            return []

    async def get_message_count(
        self,
        min_timestamp: Optional[float] = None,
        max_timestamp: Optional[float] = None,
    ) -> int:
        """
        Get count of stored messages.

        Args:
            min_timestamp: Optional minimum timestamp filter
            max_timestamp: Optional maximum timestamp filter

        Returns:
            Number of messages
        """
        if not self.redis.is_connected or not self.redis.client:
            return 0

        try:
            min_score = min_timestamp if min_timestamp else "-inf"
            max_score = max_timestamp if max_timestamp else "+inf"

            count = await self.redis.client.zcount(
                self._index_key,
                min_score,
                max_score,
            )
            return count

        except Exception as e:
            logger.error(f"Failed to count messages: {e}")
            return 0

    async def clear_old_messages(self, before_timestamp: float) -> int:
        """
        Remove messages older than specified timestamp.

        Args:
            before_timestamp: Unix timestamp cutoff

        Returns:
            Number of messages removed
        """
        if not self.redis.is_connected or not self.redis.client:
            return 0

        try:
            # Get old message IDs
            message_ids = await self.redis.client.zrangebyscore(
                self._index_key,
                "-inf",
                before_timestamp,
            )

            if not message_ids:
                return 0

            # Delete message data
            for msg_id in message_ids:
                message_key = f"{self._message_key_prefix}:{msg_id}"
                await self.redis.delete(message_key)

            # Remove from index
            removed = await self.redis.client.zremrangebyscore(
                self._index_key,
                "-inf",
                before_timestamp,
            )

            logger.info(f"Cleared {removed} old WebSocket messages")
            return removed

        except Exception as e:
            logger.error(f"Failed to clear old messages: {e}")
            return 0

    async def subscribe_to_stream(self) -> Optional[Any]:
        """
        Subscribe to the WebSocket message stream.

        Returns:
            PubSub object for listening to new messages
        """
        if not self.redis.is_connected:
            return None

        return await self.redis.subscribe(self._channel)

    def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        return {
            "namespace": self.namespace,
            "dedup_ttl": self.dedup_ttl,
            "storage_ttl": self.storage_ttl,
            "dedup_key_prefix": self._dedup_key_prefix,
            "message_key_prefix": self._message_key_prefix,
            "index_key": self._index_key,
            "channel": self._channel,
        }


async def create_websocket_storage(
    redis_manager: RedisManager,
    namespace: str = "ws",
    **kwargs: Any,
) -> WebSocketStorage:
    """
    Factory function to create WebSocketStorage instance.

    Args:
        redis_manager: RedisManager instance
        namespace: Namespace prefix for Redis keys
        **kwargs: Additional arguments for WebSocketStorage

    Returns:
        Configured WebSocketStorage instance
    """
    return WebSocketStorage(redis_manager, namespace=namespace, **kwargs)
