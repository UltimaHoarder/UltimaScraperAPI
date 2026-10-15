"""The API must work with only its own declared dependencies installed."""

import subprocess
import sys
from pathlib import Path


def test_api_import_and_runtime_paths_without_scraper_core():
    script = """
import asyncio
import importlib.abc
import os
import sys
from types import SimpleNamespace

class BlockCore(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "ultima_scraper_core" or fullname.startswith("ultima_scraper_core."):
            raise AssertionError("API tried to import Scraper Core: " + fullname)

sys.meta_path.insert(0, BlockCore())

from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel
from ultima_scraper_api.apis.onlyfans.classes.only_drm import MediaFormatter
from ultima_scraper_api.helpers.processes import run_process, run_process_sync
from ultima_scraper_api.managers.redis.log_handler import RedisLogHandler
from ultima_scraper_api.managers.scrape_manager import ScrapeManager
from ultima_scraper_api.managers.session_manager import SessionManager

os.environ["ULTIMA_MEDIA_PROCESS_CONCURRENCY"] = "2"
os.environ["ULTIMA_LOG_QUEUE_MAX_ENTRIES"] = "3"
os.environ["ULTIMA_SUBSCRIPTION_HYDRATION_CONCURRENCY"] = "0"
assert MediaFormatter().max_workers == 2
handler = RedisLogHandler()
assert handler.max_entries == 3
handler.close()
assert run_process_sync([sys.executable, "-c", "print('sync')"]).stdout == b"sync\\n"

async def check():
    manager = SessionManager(api=None)
    assert manager.max_threads > 0
    auth = SimpleNamespace(
        auth_session=SimpleNamespace(session_manager=manager),
        api=SimpleNamespace(CategorizedContent=lambda: None),
    )
    scraper = ScrapeManager(auth)
    async def scrape(url):
        return [url]
    scraper.scrape = scrape
    assert sorted(await scraper.bulk_scrape(["a", "b", "c"], concurrency=2)) == ["a", "b", "c"]
    # Exercise the deferred subscription imports and environment validation.
    stream = OnlyFansAuthModel.iter_subscriptions(SimpleNamespace())
    try:
        await anext(stream)
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("invalid hydration budget was accepted")
    result = await run_process([sys.executable, "-c", "print('async')"])
    assert result.stdout == b"async\\n"
    await manager.stop_rate_limit_checker()

asyncio.run(check())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
