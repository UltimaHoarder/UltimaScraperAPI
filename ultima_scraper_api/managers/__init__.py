"""Managers for UltimaScraperAPI."""

from .redis import (
    AsyncRedisLogHandler,
    RedisLogHandler,
    RedisManager,
    WebSocketStorage,
    attach_redis,
    create_websocket_storage,
    detach_redis,
    get_redis,
    initialize_redis,
    publish_custom_event,
    setup_redis_logging,
    shutdown_redis,
    with_hooks,
    with_hooks_class,
)

__all__ = [
    # Redis connection management
    "RedisManager",
    "attach_redis",
    "detach_redis",
    "get_redis",
    "initialize_redis",
    "shutdown_redis",
    # Redis hooks/instrumentation
    "with_hooks",
    "with_hooks_class",
    "publish_custom_event",
    # Redis logging
    "RedisLogHandler",
    "AsyncRedisLogHandler",
    "setup_redis_logging",
    # WebSocket storage
    "WebSocketStorage",
    "create_websocket_storage",
]
