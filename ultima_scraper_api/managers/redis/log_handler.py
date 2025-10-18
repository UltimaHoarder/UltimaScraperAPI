"""Redis-based logging handler for broadcasting logs to TUI clients.

This module provides a logging handler that publishes log records to Redis,
allowing the TUI to display logs from multiple processes in real-time.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from ultima_scraper_api.managers.redis.connection import RedisManager, get_redis


class RedisLogHandler(logging.Handler):
    """Logging handler that publishes log records to Redis.

    This handler allows any process to broadcast its logs to Redis,
    where they can be picked up by TUI clients for display.

    Usage:
        import logging
        from ultima_scraper_api.managers.redis import RedisLogHandler

        logger = logging.getLogger(__name__)
        redis_handler = RedisLogHandler()
        logger.addHandler(redis_handler)

        logger.info("This will appear in the TUI Logs tab!")
    """

    def __init__(
        self,
        channel: str | None = None,
        level: int = logging.INFO,
        process_name: Optional[str] = None,
    ):
        """Initialize the Redis log handler.

        Args:
            channel: Redis channel to publish to (default: RedisManager.LOGS_CHANNEL)
            level: Minimum log level to publish (default: INFO)
            process_name: Optional name to identify this process in logs
        """
        super().__init__(level)
        self.channel = channel or RedisManager.LOGS_CHANNEL
        self.process_name = process_name or "unknown"
        self._redis = None
        self._connection_warned = False

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by publishing to Redis.

        Args:
            record: The log record to emit
        """
        try:
            # Get Redis connection (lazy initialization)
            if self._redis is None:
                self._redis = get_redis()

            # Check if Redis is available
            if not self._redis or not self._redis.is_connected:
                if not self._connection_warned:
                    # Only warn once to avoid spam
                    print(
                        f"RedisLogHandler: Redis not connected, logs will not be broadcast"
                    )
                    self._connection_warned = True
                return

            # Reset warning flag if we reconnect
            self._connection_warned = False

            # Format the log record
            message = self.format(record)

            # Build event payload
            event: dict[str, Any] = {
                "event": "log_message",
                "event_type": "log",
                "level": record.levelname,
                "level_no": record.levelno,
                "logger": record.name,
                "process": self.process_name,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add exception info if present
            if record.exc_info:
                event["exception"] = "".join(
                    traceback.format_exception(*record.exc_info)
                )

            # Publish to Redis (synchronous - handler expects sync method)
            try:
                # Try to get running loop
                _loop = asyncio.get_running_loop()
                # Schedule the publish as a task
                asyncio.create_task(self._async_publish(event))
            except RuntimeError:
                # No running loop - try to publish synchronously
                # Note: This may not work well with async Redis client
                # Better to ensure handler is used in async context
                pass

        except Exception as _exc:
            # Don't let logging errors crash the application
            self.handleError(record)

    async def _async_publish(self, event: dict[str, Any]) -> None:
        """Async helper to publish event to Redis.

        Args:
            event: Event payload to publish
        """
        try:
            if self._redis and self._redis.is_connected:
                await self._redis.publish_log(event)
        except Exception:
            # Silently ignore publish errors
            pass


class AsyncRedisLogHandler(logging.Handler):
    """Async-friendly logging handler for Redis.

    This is a convenience wrapper that works better in async contexts.
    Use this when your process is async-based.

    Usage:
        import logging
        from ultima_scraper_api.managers.redis import AsyncRedisLogHandler

        logger = logging.getLogger(__name__)
        handler = AsyncRedisLogHandler(process_name="worker-1")
        logger.addHandler(handler)

        # Initialize the handler's async connection
        await handler.initialize()

        logger.info("This will appear in the TUI!")
    """

    def __init__(
        self,
        channel: str | None = None,
        level: int = logging.INFO,
        process_name: Optional[str] = None,
    ):
        """Initialize the async Redis log handler.

        Args:
            channel: Redis channel to publish to (default: RedisManager.LOGS_CHANNEL)
            level: Minimum log level to publish
            process_name: Optional name to identify this process
        """
        super().__init__(level)
        self.channel = channel or RedisManager.LOGS_CHANNEL
        self.process_name = process_name or "unknown"
        self._redis = None
        self._queue: list[dict[str, Any]] = []
        self._connection_warned = False

    async def initialize(self) -> None:
        """Initialize the Redis connection.

        Call this once when setting up the handler in an async context.
        """
        self._redis = get_redis()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record.

        Queues the record for async publishing.

        Args:
            record: The log record to emit
        """
        try:
            # Format the log record
            message = self.format(record)

            # Build event payload
            event: dict[str, Any] = {
                "event": "log_message",
                "event_type": "log",
                "level": record.levelname,
                "level_no": record.levelno,
                "logger": record.name,
                "process": self.process_name,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add exception info if present
            if record.exc_info:
                event["exception"] = "".join(
                    traceback.format_exception(*record.exc_info)
                )

            # Try to publish immediately if we have an event loop
            try:
                _loop = asyncio.get_running_loop()
                asyncio.create_task(self._publish(event))
            except RuntimeError:
                # No running loop - queue for later
                self._queue.append(event)

        except Exception:
            self.handleError(record)

    async def _publish(self, event: dict[str, Any]) -> None:
        """Publish event to Redis.

        Args:
            event: Event payload to publish
        """
        try:
            if self._redis is None:
                self._redis = get_redis()

            if not self._redis or not self._redis.is_connected:
                if not self._connection_warned:
                    self._connection_warned = True
                return

            self._connection_warned = False

            await self._redis.publish_log(event)
        except Exception:
            pass  # Silently ignore

    async def flush_queue(self) -> None:
        """Flush any queued log messages.

        Call this after initializing to publish any logs that were
        emitted before the Redis connection was ready.
        """
        if not self._queue:
            return

        for event in self._queue:
            await self._publish(event)

        self._queue.clear()


def setup_redis_logging(
    logger_name: Optional[str] = None,
    level: int = logging.INFO,
    process_name: Optional[str] = None,
    channel: str | None = None,
) -> logging.Logger:
    """Convenience function to set up Redis logging for a logger.

    Args:
        logger_name: Name of logger to configure (None for root logger)
        level: Logging level
        process_name: Name to identify this process in logs
        channel: Redis channel to publish to (default: RedisManager.LOGS_CHANNEL)

    Returns:
        Configured logger instance

    Example:
        from ultima_scraper_api.managers.redis import setup_redis_logging

        logger = setup_redis_logging(__name__, process_name="backend-worker")
        logger.info("Hello from the worker!")
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Add Redis handler
    redis_handler = RedisLogHandler(
        channel=channel,
        level=level,
        process_name=process_name,
    )

    # Add simple formatter
    formatter = logging.Formatter(
        "%(message)s"  # Keep it simple, metadata is in the event
    )
    redis_handler.setFormatter(formatter)

    logger.addHandler(redis_handler)

    return logger
