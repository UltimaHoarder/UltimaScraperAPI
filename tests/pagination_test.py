from contextlib import aclosing
from types import SimpleNamespace

import pytest

import ultima_scraper_api.managers.redis as redis_module
from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate


def pages(*batches, cursors=None):
    """A fetcher over fixed pages; the cursor is the page index unless given."""
    calls = []

    async def fetch(cursor):
        calls.append(cursor)
        index = 0 if cursor is None else cursor
        items = batches[index] if index < len(batches) else []
        if cursors is not None:
            next_cursor = cursors[index] if index < len(cursors) else None
        else:
            next_cursor = index + 1 if index + 1 < len(batches) else None
        return items, next_cursor

    return fetch, calls


async def collect(generator):
    async with aclosing(generator) as items:
        return [item async for item in items]


@pytest.fixture
def events(monkeypatch):
    published = []

    async def publish(event):
        published.append(event)

    monkeypatch.setattr(redis_module, "publish_custom_event", publish)
    return published


@pytest.mark.asyncio
async def test_pages_until_the_cursor_runs_out(events):
    fetch, calls = pages([1, 2], [3, 4], [5])
    assert await collect(paginate(fetch)) == [1, 2, 3, 4, 5]
    assert calls == [None, 1, 2]


@pytest.mark.asyncio
async def test_max_items_trims_and_stops_fetching(events):
    fetch, calls = pages([1, 2], [3, 4], [5])
    assert await collect(paginate(fetch, max_items=3)) == [1, 2, 3]
    assert calls == [None, 1]
    assert await collect(paginate(fetch, max_items=0)) == []
    with pytest.raises(ValueError):
        await collect(paginate(fetch, max_items=-1))


@pytest.mark.asyncio
async def test_an_empty_page_ends_paging(events):
    fetch, calls = pages([1], [], [9])
    assert await collect(paginate(fetch)) == [1]
    assert calls == [None, 1]


@pytest.mark.asyncio
async def test_a_cursor_that_does_not_move_is_an_error(events):
    fetch, _ = pages([1], [2], cursors=[1, 1])
    with pytest.raises(RuntimeError, match="did not advance"):
        await collect(paginate(fetch))


@pytest.mark.asyncio
async def test_progress_reports_each_page(events):
    seen = []

    async def on_progress(done, total, items):
        seen.append((done, total, items))

    user = SimpleNamespace(id=5, username="someone")
    progress = ScrapeProgress(user, "Posts", job_id="j1", on_progress=on_progress)
    fetch, _ = pages([1, 2], [3])
    assert await collect(paginate(fetch, progress=progress)) == [1, 2, 3]
    assert seen == [(1, 2, 2), (2, 2, 3)]
    assert [(e["page"], e["has_more"]) for e in events] == [(1, True), (2, False)]
    assert {(e["job_id"], e["user_id"], e["content_type"]) for e in events} == {
        ("j1", 5, "Posts")
    }
