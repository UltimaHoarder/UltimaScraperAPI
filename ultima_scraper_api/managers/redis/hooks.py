"""Hooks system for monitoring and logging API operations via Redis."""

from __future__ import annotations

import functools
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

from ultima_scraper_api.managers.redis.connection import RedisManager, get_redis

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def _serialize_value(value: Any) -> Any:
    """Serialize value for JSON encoding.

    Args:
        value: Value to serialize

    Returns:
        JSON-serializable value
    """
    # Handle common non-serializable types
    if hasattr(value, "__dict__"):
        # Object with __dict__ - try to get class name and relevant attributes
        class_name = value.__class__.__name__
        # Return simplified representation
        return f"<{class_name}>"
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]  # type: ignore[misc]
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}  # type: ignore[misc]
    else:
        # Primitive types or already serializable
        return value


def _get_hook_metadata(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    event_type: str,
    result: Any = None,
    error: Optional[Exception] = None,
) -> dict[str, Any]:
    """Generate metadata for hook event.

    Args:
        func: Function being called
        args: Positional arguments
        kwargs: Keyword arguments
        event_type: Type of event (started/finished/error)
        result: Function result (for finished events)
        error: Exception (for error events)

    Returns:
        Dictionary with hook metadata
    """
    # Get function signature
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())

    # Build arguments dict (skip 'self' for methods)
    func_args: dict[str, Any] = {}
    start_idx = 1 if param_names and param_names[0] == "self" else 0

    for idx, arg in enumerate(args[start_idx:], start=start_idx):
        if idx < len(param_names):
            func_args[param_names[idx]] = _serialize_value(arg)

    for key, value in kwargs.items():
        func_args[key] = _serialize_value(value)

    # Build metadata
    metadata: dict[str, Any] = {
        "event_type": event_type,
        "function": func.__name__,
        "module": func.__module__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "arguments": func_args,
    }

    # Add result or error info
    if event_type == "finished" and result is not None:
        metadata["result_type"] = type(result).__name__
        # For collections, add count
        if isinstance(result, (list, tuple)):
            metadata["result_count"] = len(result)  # type: ignore[arg-type]
        elif hasattr(result, "__len__"):
            try:
                metadata["result_count"] = len(result)
            except:
                pass

    if event_type == "error" and error is not None:
        metadata["error_type"] = type(error).__name__
        metadata["error_message"] = str(error)

    return metadata


async def _publish_hook_event(metadata: dict[str, Any]) -> None:
    """Publish hook event to Redis.

    Args:
        metadata: Event metadata to publish
    """
    redis_conn = get_redis()
    if not redis_conn or not redis_conn.is_connected:
        logger.warning(
            f"Cannot publish hook event - Redis not connected (redis_conn={redis_conn}, "
            f"is_connected={redis_conn.is_connected if redis_conn else 'N/A'})"
        )
        return

    try:
        await redis_conn.publish_hook(metadata)

        # Log based on what fields are available
        if "module" in metadata and "function" in metadata and "event_type" in metadata:
            # Standard hook event from @with_hooks decorator
            logger.info(
                "✓ Published hook event: %s.%s [%s]",
                metadata["module"],
                metadata["function"],
                metadata["event_type"],
            )
        elif "event" in metadata:
            # Custom event (like scrape_progress, scrape_finished)
            logger.info(
                "✓ Published custom event: %s",
                metadata["event"],
            )
        else:
            # Generic event
            logger.info("✓ Published event to %s", RedisManager.HOOKS_CHANNEL)
    except Exception as exc:
        logger.error("Failed to publish hook event: %s", exc, exc_info=True)


def with_hooks(func: F) -> F:
    """Decorator to add hooks around function execution.

    Publishes events to Redis channel defined in RedisManager.HOOKS_CHANNEL with metadata:
    - event_type: 'started', 'finished', or 'error'
    - function: Function name
    - module: Module name
    - timestamp: ISO timestamp
    - arguments: Function arguments (serialized)
    - result_type/result_count: For successful completion
    - error_type/error_message: For errors

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    # Handle both sync and async functions
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(f"🎣 Hook wrapper called for {func.__module__}.{func.__name__}")
            # Publish started event
            started_metadata = _get_hook_metadata(func, args, kwargs, "started")
            await _publish_hook_event(started_metadata)

            try:
                result = await func(*args, **kwargs)

                # Publish finished event
                finished_metadata = _get_hook_metadata(
                    func, args, kwargs, "finished", result=result
                )
                await _publish_hook_event(finished_metadata)

                return result
            except Exception as exc:
                # Publish error event
                error_metadata = _get_hook_metadata(
                    func, args, kwargs, "error", error=exc
                )
                await _publish_hook_event(error_metadata)
                raise

        return async_wrapper  # type: ignore

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For sync functions, we can't await publish
            # So we just log locally (Redis requires async)
            logger.debug("Hook: %s.%s started", func.__module__, func.__name__)

            try:
                result = func(*args, **kwargs)
                logger.debug("Hook: %s.%s finished", func.__module__, func.__name__)
                return result
            except Exception as exc:
                logger.debug(
                    "Hook: %s.%s error: %s", func.__module__, func.__name__, exc
                )
                raise

        return sync_wrapper  # type: ignore


async def publish_custom_event(event_data: dict[str, Any]) -> None:
    """Publish a custom event to the ultima:hooks channel.

    This allows manual publishing of custom events (like scrape_progress, scrape_finished)
    that don't fit the standard function hook pattern.

    Args:
        event_data: Dictionary containing event data. Should include at minimum:
            - event: Event name (e.g., "scrape_progress", "scrape_finished")
            - timestamp: ISO timestamp (will be added if not present)

    Example:
        await publish_custom_event({
            "event": "scrape_progress",
            "username": "user123",
            "user_id": 123,
            "content_type": "posts",
            "scraped": 25,
            "saved": 25,
            "total": 100,
            "media_saved": 10,
            "media_failed": 0
        })
    """
    # Add timestamp if not present
    if "timestamp" not in event_data:
        event_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    await _publish_hook_event(event_data)


def with_hooks_class(cls: type) -> type:
    """Class decorator to add hooks to all async methods.

    Args:
        cls: Class to decorate

    Returns:
        Decorated class
    """
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_") and inspect.iscoroutinefunction(method):
            setattr(cls, name, with_hooks(method))
    return cls
