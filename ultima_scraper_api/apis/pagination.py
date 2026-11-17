"""Shared paging for the sites' streaming ``iter_*`` methods.

A site supplies one function that fetches a page for a cursor (an offset, a
page number, an id or a timestamp: whatever the site pages by) and returns the
page's items and the next cursor, or ``None`` when there are no more pages.
``paginate()`` does the rest the way OnlyFans' ``iter_messages`` does: it stops
at ``max_items``, refuses a cursor that does not move, and reports progress
after every page.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Hashable, Sequence
from typing import Any, TypeVar

from ultima_scraper_api.managers.scrape_manager import ScrapeProgressCallback

C = TypeVar("C", bound=Hashable)
T = TypeVar("T")


class ScrapeProgress:
    """Publishes the backend's ``scrape_progress`` event for one user and content type.

    Total pages are rarely known in advance, so the estimate is the pages done
    plus one while more remain (as OnlyFans' message paging reports it).
    """

    def __init__(
        self,
        user: Any,
        content_type: str,
        *,
        job_id: str | None = None,
        total_items: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
    ) -> None:
        self.user = user
        self.content_type = content_type
        self.job_id = job_id or "api"
        self.total_items = total_items
        self.on_progress = on_progress

    async def page(self, pages_completed: int, items_so_far: int, has_more: bool) -> None:
        from ultima_scraper_api.managers.redis import publish_custom_event

        total_pages = pages_completed + int(has_more)
        await publish_custom_event(
            {
                "event": "scrape_progress",
                "job_id": self.job_id,
                "username": getattr(self.user, "username", None),
                "user_id": getattr(self.user, "id", None),
                "content_type": self.content_type,
                "status": "progress",
                "items_scraped": items_so_far,
                "items_saved": 0,
                "total_items": self.total_items,
                "page": pages_completed,
                "total_pages": total_pages,
                "has_more": has_more,
            }
        )
        if self.on_progress:
            await self.on_progress(pages_completed, total_pages, items_so_far)


async def paginate(
    fetch_page: Callable[[C | None], Awaitable[tuple[Sequence[T], C | None]]],
    *,
    first_cursor: C | None = None,
    max_items: int | None = None,
    progress: ScrapeProgress | None = None,
) -> AsyncGenerator[T, None]:
    """Yield items page by page, holding only the current page.

    Callers that stop early must close the generator (``contextlib.aclosing``).
    """
    if max_items is not None and max_items < 0:
        raise ValueError("max_items must be nonnegative or None")
    if max_items == 0:
        return
    cursor = first_cursor
    seen: set[C | None] = {cursor}
    pages = count = 0
    while True:
        items, next_cursor = await fetch_page(cursor)
        if not items:
            if progress and pages:
                await progress.page(pages, count, False)
            return
        remaining = None if max_items is None else max_items - count
        selected = items if remaining is None else items[:remaining]
        pages += 1
        count += len(selected)
        has_more = next_cursor is not None and (max_items is None or count < max_items)
        if progress:
            await progress.page(pages, count, has_more)
        for item in selected:
            yield item
        if not has_more:
            return
        if next_cursor in seen:
            raise RuntimeError(f"Pagination did not advance past cursor {next_cursor!r}")
        seen.add(next_cursor)
        cursor = next_cursor
