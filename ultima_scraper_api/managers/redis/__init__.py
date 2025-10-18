"""Redis management package for UltimaScraperAPI.

This package contains all Redis-related functionality:
- Connection management and operations
- Function instrumentation hooks
- Logging handlers for broadcasting logs
- WebSocket message storage with deduplication
"""

from .connection import (
    RedisManager,
    get_redis,
    initialize_redis,
    shutdown_redis,
)
from .hooks import (
    publish_custom_event,
    with_hooks,
    with_hooks_class,
)
from .log_handler import (
    AsyncRedisLogHandler,
    RedisLogHandler,
    setup_redis_logging,
)
from .websocket_storage import (
    WebSocketStorage,
    create_websocket_storage,
)

__all__ = [
    # Connection management
    "RedisManager",
    "get_redis",
    "initialize_redis",
    "shutdown_redis",
    # Hooks/instrumentation
    "with_hooks",
    "with_hooks_class",
    "publish_custom_event",
    # Logging
    "RedisLogHandler",
    "AsyncRedisLogHandler",
    "setup_redis_logging",
    # WebSocket storage
    "WebSocketStorage",
    "create_websocket_storage",
]
