"""WebSocket connection wrapper for individual connections."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ultima_scraper_api.managers.redis import RedisManager, WebSocketStorage
    from ultima_scraper_api.managers.websocket_manager.protocol import WebSocketProtocol

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Individual WebSocket connection with site-specific implementation.

    Wraps a site-specific WebSocket implementation and provides:
    - Message history recording
    - Pub/Sub distribution to subscribers
    - Redis publishing
    - Connection statistics
    - Event callbacks
    - Automatic reconnection
    """

    def __init__(
        self,
        websocket_impl: WebSocketProtocol,
        redis_manager: RedisManager | None = None,
        redis_channel: str | None = None,
        max_reconnect_attempts: int = 5,
        initial_reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
        record_all_messages: bool = True,
    ) -> None:
        """Initialize WebSocket connection.

        Args:
            websocket_impl: Site-specific WebSocket implementation
            redis_manager: Optional Redis manager for publishing messages
            redis_channel: Optional Redis channel for publishing
            max_reconnect_attempts: Maximum reconnection attempts before giving up
            initial_reconnect_delay: Initial delay before reconnecting (seconds)
            max_reconnect_delay: Maximum reconnection delay (seconds)
            record_all_messages: Whether to record all messages in history
        """
        self.websocket_impl = websocket_impl
        self.redis_manager = redis_manager
        self.redis_channel = redis_channel

        # Message history - NO LIMIT! Record everything
        self._message_history: list[dict[str, Any]] = []
        self._event_history: list[dict[str, Any]] = []
        self.record_all_messages = record_all_messages

        # For backwards compatibility, maintain recent buffer
        self._recent: deque[Any] = deque(maxlen=100)

        # Subscribers
        self._subscribers: set[asyncio.Queue[Any]] = set()

        # Redis tracking
        self._redis_published_count = 0
        self._redis_failed_count = 0
        self._websocket_storage: WebSocketStorage | None = None
        self._storage_initialized = False

        # Event callbacks
        self._callbacks: dict[str, list[Callable[..., Any]]] = {
            "message": [],
            "connected": [],
            "closed": [],
            "reconnecting": [],
            "error": [],
            "stopped": [],
        }

        # Reconnection settings
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_reconnect_delay = initial_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self._reconnect_attempts = 0
        self._should_stop = False

        # Statistics
        self._connection_count = 0
        self._messages_received = 0
        self._messages_published = 0
        self._last_message_time: float | None = None

        # Task management
        self._listen_task: asyncio.Task[None] | None = None
        self._ws_lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the WebSocket connection and listening loop.

        Safe to call multiple times; subsequent calls are no-ops if already running.
        """
        async with self._ws_lock:
            if self._listen_task and not self._listen_task.done():
                logger.debug("WebSocket connection already running")
                return

            self._should_stop = False
            self._listen_task = asyncio.create_task(self._listen_loop())
            logger.debug("WebSocket connection started")
            await asyncio.sleep(0)  # Yield to start the task

    async def stop(self) -> None:
        """Gracefully stop the WebSocket connection."""
        async with self._ws_lock:
            if not self._listen_task or self._listen_task.done():
                logger.debug("WebSocket connection not running")
                return

            self._should_stop = True

            # Disconnect the websocket implementation
            try:
                await self.websocket_impl.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting websocket: {e}")

            # Cancel and await the listen task
            if self._listen_task:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass

            await self._publish_event({"type": "stopped"})
            logger.info("WebSocket connection stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop with automatic reconnection."""
        import time

        while not self._should_stop:
            try:
                await self._connect_and_listen()
                # If we exit cleanly, reset reconnect attempts
                self._reconnect_attempts = 0
            except Exception as e:
                if self._should_stop:
                    logger.info("WebSocket connection stopped")
                    break

                self._reconnect_attempts += 1

                if self._reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error(
                        f"Max reconnection attempts ({self.max_reconnect_attempts}) "
                        f"reached. Stopping WebSocket connection."
                    )
                    await self._publish_event(
                        {
                            "type": "error",
                            "error": "max_reconnect_attempts_reached",
                            "message": str(e),
                        }
                    )
                    break

                # Exponential backoff
                delay = min(
                    self.initial_reconnect_delay
                    * (2 ** (self._reconnect_attempts - 1)),
                    self.max_reconnect_delay,
                )
                logger.warning(
                    f"WebSocket connection failed (attempt {self._reconnect_attempts}/"
                    f"{self.max_reconnect_attempts}). Reconnecting in {delay:.1f}s... "
                    f"Error: {e}"
                )
                await self._publish_event(
                    {
                        "type": "reconnecting",
                        "attempt": self._reconnect_attempts,
                        "delay": delay,
                        "error": str(e),
                    }
                )
                await asyncio.sleep(delay)

    async def _connect_and_listen(self) -> None:
        """Establish connection and listen for messages."""
        import time

        # Connect using site-specific implementation
        await self.websocket_impl.connect()

        self._connection_count += 1
        logger.debug(f"WebSocket connected (connection #{self._connection_count})")
        await self._publish_event(
            {
                "type": "connected",
                "connection_count": self._connection_count,
            }
        )

        try:
            while not self._should_stop and self.websocket_impl.is_connected:
                # Receive message using site-specific implementation
                msg = await self.websocket_impl.receive()

                self._messages_received += 1
                self._last_message_time = time.time()

                # Store in history
                if self.record_all_messages:
                    self._message_history.append(msg)

                self._recent.append(msg)

                # Publish to subscribers
                await self._publish_to_subscribers(msg)

                # Publish to Redis if available
                await self._publish_to_redis(msg)

                # Trigger callbacks
                await self._trigger_callbacks("message", msg)

                # Periodic logging
                if self._messages_received % 100 == 0:
                    logger.debug(
                        f"WebSocket stats: {self._messages_received} received, "
                        f"{self._messages_published} published"
                    )

        except Exception as e:
            logger.warning(f"WebSocket connection error: {e}")
            await self._publish_event(
                {
                    "type": "closed",
                    "error": str(e),
                }
            )
            raise  # Re-raise to trigger reconnection

    async def _publish_to_subscribers(self, message: dict[str, Any]) -> None:
        """Publish message to all subscribers."""
        self._messages_published += 1
        dead_queues: set[asyncio.Queue[Any]] = set()

        for queue in self._subscribers:
            try:
                queue.put_nowait({"type": "message", "data": message})
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping message")
            except Exception as e:
                logger.debug(f"Error publishing to subscriber: {e}")
                dead_queues.add(queue)

        # Remove dead subscribers
        self._subscribers -= dead_queues

    async def _publish_to_redis(self, message: dict[str, Any]) -> None:
        """Publish message to Redis and store in WebSocketStorage."""
        if not self.redis_manager:
            logger.warning(
                f"WebSocketConnection: No redis_manager, cannot store messages"
            )
            return

        if not self.redis_manager.is_connected:
            logger.warning(
                f"WebSocketConnection: Redis not connected, cannot store messages"
            )
            return

        try:
            # Initialize WebSocketStorage on first use
            if not self._storage_initialized:
                from ultima_scraper_api.managers.redis import create_websocket_storage
                from ultima_scraper_api.managers.redis.connection import RedisManager

                try:
                    self._websocket_storage = await create_websocket_storage(
                        redis_manager=self.redis_manager,
                        namespace="websocket",  # Will be prefixed with RedisManager.KEY_PREFIX
                    )
                    self._storage_initialized = True
                    logger.debug("✅ WebSocketStorage initialized for connection")
                except Exception as e:
                    logger.warning(
                        f"Failed to create WebSocketStorage: {e}", exc_info=True
                    )
                    self._storage_initialized = True  # Don't retry every time
                    return

            # Store message in WebSocketStorage
            if self._websocket_storage:
                was_stored, _ = await self._websocket_storage.store_message(
                    message,
                    source_id=self.redis_channel,
                )
                if was_stored:
                    self._redis_published_count += 1
            else:
                # Fallback to simple pub/sub if storage failed
                if self.redis_channel:
                    success = await self.redis_manager.publish_json(
                        self.redis_channel,
                        {
                            "event": "websocket_message",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": message,
                        },
                    )
                    if success:
                        self._redis_published_count += 1
                    else:
                        self._redis_failed_count += 1

        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}", exc_info=True)
            self._redis_failed_count += 1

    async def _publish_event(self, event: dict[str, Any]) -> None:
        """Publish event to subscribers and store in history."""
        if self.record_all_messages:
            self._event_history.append(event)

        dead_queues: set[asyncio.Queue[Any]] = set()
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
            except Exception:
                dead_queues.add(queue)

        self._subscribers -= dead_queues

        # Trigger callbacks
        event_type = event.get("type")
        if event_type:
            await self._trigger_callbacks(event_type, event)

    async def _trigger_callbacks(self, event_type: str, data: Any) -> None:
        """Trigger registered callbacks for an event type."""
        callbacks = self._callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {e}")

    def subscribe(self) -> asyncio.Queue[Any]:
        """Subscribe to WebSocket messages.

        Returns:
            Queue that will receive messages and events
        """
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Any]) -> None:
        """Unsubscribe from WebSocket messages.

        Args:
            queue: Queue to remove from subscribers
        """
        self._subscribers.discard(queue)

    def on(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Register callback for an event type.

        Args:
            event_type: Type of event (message, connected, closed, etc.)
            callback: Callback function (can be async)
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def send(self, data: dict[str, Any]) -> None:
        """Send data through the WebSocket.

        Args:
            data: Data to send
        """
        await self.websocket_impl.send(data)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.websocket_impl.is_connected

    @property
    def message_history(self) -> list[dict[str, Any]]:
        """Get complete message history.

        Returns:
            List of all received messages
        """
        return self._message_history.copy()

    @property
    def event_history(self) -> list[dict[str, Any]]:
        """Get complete event history.

        Returns:
            List of all events
        """
        return self._event_history.copy()

    @property
    def recent_messages(self) -> list[Any]:
        """Get recent messages (last 100).

        Returns:
            List of recent messages
        """
        return list(self._recent)

    def get_statistics(self) -> dict[str, Any]:
        """Get connection statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "connection_count": self._connection_count,
            "messages_received": self._messages_received,
            "messages_published": self._messages_published,
            "subscriber_count": len(self._subscribers),
            "redis_published": self._redis_published_count,
            "redis_failed": self._redis_failed_count,
            "last_message_time": self._last_message_time,
            "is_connected": self.is_connected,
            "reconnect_attempts": self._reconnect_attempts,
        }
