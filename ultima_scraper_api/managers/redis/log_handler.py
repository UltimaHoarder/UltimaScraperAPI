"""Bounded, best-effort Redis broadcast of independently persisted log records."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import traceback
from collections import deque
from datetime import datetime, timezone
from typing import Any

from ultima_scraper_api.managers.redis.connection import RedisManager, get_redis


def _positive_budget(name: str, value: int | None, default: int | None) -> int | None:
    raw = value if value is not None else os.getenv(name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    if isinstance(raw, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0 or (not isinstance(raw, (int, str))):
        raise ValueError(f"{name} must be a positive integer")
    return parsed


class RedisLogHandler(logging.Handler):
    """Broadcast through one consumer and a bounded queue, including in-flight work.

    File logging remains independent. When broadcast admission is exhausted the
    new event is dropped and counted; logging never blocks application work on
    Redis. Thread-originated records use one coalesced event-loop wakeup.
    """

    def __init__(
        self,
        channel: str | None = None,
        level: int = logging.INFO,
        process_name: str | None = None,
        *,
        max_entries: int | None = None,
        max_bytes: int | None = None,
    ):
        entries = _positive_budget(
            "ULTIMA_LOG_QUEUE_MAX_ENTRIES", max_entries, RedisManager.LOGS_HISTORY_MAX
        )
        byte_budget = _positive_budget("ULTIMA_LOG_QUEUE_MAX_BYTES", max_bytes, None)
        assert entries is not None
        super().__init__(level)
        self.channel = channel or RedisManager.LOGS_CHANNEL
        self.process_name = process_name or "unknown"
        self.max_entries = entries
        self.max_bytes = byte_budget
        self._redis: RedisManager | None = None
        self._queue: deque[str] = deque()
        self._state_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._wakeup_pending = False
        self._closing = False
        self._pending_entries = 0
        self._pending_bytes = 0
        self._accepted = self._published = self._dropped = self._failed = 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            try:
                current_loop = asyncio.get_running_loop()
                if self._task is not None and asyncio.current_task() is self._task:
                    # A transport diagnostic must not recursively broadcast itself.
                    return
            except RuntimeError:
                current_loop = None
            with self._state_lock:
                if self._closing or self._pending_entries >= self.max_entries:
                    self._dropped += 1
                    return
            event: dict[str, Any] = {
                "event": "log_message",
                "event_type": "log",
                "level": record.levelname,
                "level_no": record.levelno,
                "logger": record.name,
                "process": self.process_name,
                "message": self.format(record),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if record.exc_info:
                event["exception"] = "".join(
                    traceback.format_exception(*record.exc_info)
                )
            # ASCII encoding makes len(payload) an exact serialized byte count;
            # Redis receives this same payload for publication and history.
            payload = json.dumps(event, ensure_ascii=True, separators=(",", ":"))
            with self._state_lock:
                if (
                    self._closing
                    or self._pending_entries >= self.max_entries
                    or (
                        self.max_bytes is not None
                        and self._pending_bytes + len(payload) > self.max_bytes
                    )
                ):
                    self._dropped += 1
                    return
                self._queue.append(payload)
                self._pending_entries += 1
                self._pending_bytes += len(payload)
                self._accepted += 1
            self._wake(current_loop)
        except Exception:
            self.handleError(record)

    def _wake(self, current_loop: asyncio.AbstractEventLoop | None = None) -> None:
        with self._state_lock:
            if self._loop is None or self._loop.is_closed():
                self._loop = current_loop
            loop = self._loop
            if (
                loop is None
                or not loop.is_running()
                or not self._queue
                or self._wakeup_pending
                or (self._task is not None and not self._task.done())
            ):
                return
            self._wakeup_pending = True
        try:
            if loop is current_loop:
                loop.call_soon(self._start_drain)
            else:
                loop.call_soon_threadsafe(self._start_drain)
        except RuntimeError:
            with self._state_lock:
                self._wakeup_pending = False

    def _start_drain(self) -> None:
        with self._state_lock:
            self._wakeup_pending = False
            if self._queue and (self._task is None or self._task.done()):
                self._task = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        cancelled = False
        try:
            while True:
                with self._state_lock:
                    if not self._queue:
                        return
                    payload = self._queue.popleft()
                published = False
                try:
                    if self._redis is None:
                        self._redis = get_redis()
                    if self._redis and self._redis.is_connected:
                        published = await self._redis.publish_log_payload(
                            payload, channel=self.channel
                        )
                except Exception:
                    pass
                finally:
                    with self._state_lock:
                        self._pending_entries -= 1
                        self._pending_bytes -= len(payload)
                        if published:
                            self._published += 1
                        else:
                            self._failed += 1
                            # A failed broadcast is best effort. Do not replay a
                            # queued outage burst one network timeout at a time.
                            self._discard_queued()
                # A disconnected or immediate-return transport still yields;
                # draining a burst must not monopolize the application loop.
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            cancelled = True
            with self._state_lock:
                self._discard_queued()
            raise
        finally:
            with self._state_lock:
                self._task = None
            if not cancelled:
                self._wake(asyncio.get_running_loop())

    async def initialize(self) -> None:
        self._redis = get_redis()
        self._wake(asyncio.get_running_loop())

    async def flush_queue(self) -> None:
        self._wake(asyncio.get_running_loop())
        while True:
            with self._state_lock:
                task, pending = self._task, self._pending_entries
            if not pending:
                return
            if task is not None:
                await asyncio.shield(task)
            else:
                await asyncio.sleep(0)

    def stats(self) -> dict[str, int | None]:
        with self._state_lock:
            return {
                "max_entries": self.max_entries,
                "max_bytes": self.max_bytes,
                "pending_entries": self._pending_entries,
                "pending_bytes": self._pending_bytes,
                "accepted": self._accepted,
                "published": self._published,
                "dropped": self._dropped,
                "failed": self._failed,
            }

    async def aclose(self) -> None:
        with self._state_lock:
            self._closing = True
        try:
            await self.flush_queue()
        finally:
            self.close()

    def _discard_queued(self) -> None:
        """Drop queued broadcasts while holding _state_lock."""
        self._dropped += len(self._queue)
        self._pending_entries -= len(self._queue)
        self._pending_bytes -= sum(map(len, self._queue))
        self._queue.clear()

    def close(self) -> None:
        with self._state_lock:
            self._closing = True
            self._discard_queued()
            task, loop = self._task, self._loop
        if task is not None and loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass  # The owning loop may have closed during logging shutdown.
        super().close()


class AsyncRedisLogHandler(RedisLogHandler):
    """Compatibility name for the same bounded async broadcast implementation."""


def setup_redis_logging(
    logger_name: str | None = None,
    level: int = logging.INFO,
    process_name: str | None = None,
    channel: str | None = None,
    *,
    max_entries: int | None = None,
    max_bytes: int | None = None,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    handler = RedisLogHandler(
        channel, level, process_name, max_entries=max_entries, max_bytes=max_bytes
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger
