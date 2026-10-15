"""Bounded asynchronous iteration for API request and hydration work."""

from __future__ import annotations

import asyncio
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    Awaitable,
    Callable,
    Generator,
    Iterable,
)


async def map_unordered[T, R](
    function: Callable[[T], Awaitable[R]],
    items: Iterable[T] | AsyncIterable[T],
    *,
    limit: int,
) -> AsyncGenerator[R, None]:
    """Yield completed results with at most ``limit`` admitted operations.

    Input retrieval can await independently of running work. Results apply
    backpressure: a slow consumer stops further admission. Callers that may
    stop iteration early should own this iterator with ``contextlib.aclosing``.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    async def iterate_sync(values: Iterable[T]) -> AsyncGenerator[T, None]:
        source = iter(values)
        try:
            for value in source:
                yield value
        finally:
            if isinstance(source, Generator):
                source.close()

    source = aiter(items) if isinstance(items, AsyncIterable) else iterate_sync(items)
    pending: set[asyncio.Task[R]] = set()
    next_item: asyncio.Task[T] | None = None
    exhausted = False

    async def apply(item: T) -> R:
        return await function(item)

    try:
        while pending or not exhausted:
            if next_item is None and not exhausted and len(pending) < limit:
                next_item = asyncio.create_task(anext(source))
            waiting: set[asyncio.Task[R] | asyncio.Task[T]] = set(pending)
            if next_item is not None:
                waiting.add(next_item)
            done, _ = await asyncio.wait(waiting, return_when=asyncio.FIRST_COMPLETED)
            for task in pending.intersection(done):
                pending.remove(task)
                yield task.result()
            if next_item in done:
                assert next_item is not None
                try:
                    item = next_item.result()
                except StopAsyncIteration:
                    exhausted = True
                else:
                    pending.add(asyncio.create_task(apply(item)))
                next_item = None
    finally:
        remaining: set[asyncio.Task[R] | asyncio.Task[T]] = set(pending)
        if next_item is not None:
            remaining.add(next_item)
        for task in remaining:
            task.cancel()
        if remaining:
            await asyncio.gather(*remaining, return_exceptions=True)
        if isinstance(source, AsyncGenerator):
            await source.aclose()
