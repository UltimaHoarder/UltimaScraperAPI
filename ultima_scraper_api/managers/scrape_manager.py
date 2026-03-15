import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from ultima_scraper_api.apis.api_helper import handle_error_details

if TYPE_CHECKING:
    from ultima_scraper_api.managers.session_manager import AuthedSession


TAPI = TypeVar("TAPI")
TCC = TypeVar("TCC")

# Progress callback type: (completed_pages, total_pages, items_so_far) -> Awaitable[None]
type ScrapeProgressCallback = Callable[[int, int, int], Awaitable[None]]


class ScrapeManager(Generic[TAPI, TCC]):
    def __init__(self, authed: TAPI) -> None:
        self.auth_session: AuthedSession = authed.auth_session  # type: ignore
        self.scraped: TCC = authed.api.CategorizedContent()  # type: ignore
        self.handle_errors = True

    async def bulk_scrape(
        self,
        urls: list[str],
        on_progress: ScrapeProgressCallback | None = None,
    ) -> list[Any]:
        """Scrape multiple URLs in parallel with optional progress callback.

        Args:
            urls: List of URLs to scrape.
            on_progress: Optional async callback called after each page completes.
                         Signature: (completed_pages, total_pages, items_so_far) -> Awaitable[None]

        Returns:
            Flattened list of all scraped items.
        """
        total = len(urls)
        if total == 0:
            return []

        # Create tasks for all URLs
        tasks = [asyncio.create_task(self.scrape(url)) for url in urls]

        results: list[Any] = []
        completed = 0
        items_count = 0

        # Process as each task completes (maintains parallelism)
        for coro in asyncio.as_completed(tasks):
            try:
                page_result = await coro
                if page_result and not isinstance(page_result, BaseException):
                    if isinstance(page_result, list):
                        results.extend(page_result)
                        items_count += len(page_result)
                    else:
                        results.append(page_result)
                        items_count += 1
            except Exception:
                # Silently skip failed requests (matches original behavior)
                pass

            completed += 1

            # Call progress callback if provided (caller handles event publishing)
            if on_progress:
                await on_progress(completed, total, items_count)

        return results

    async def scrape(self, url: str):
        auth_session = self.auth_session
        async with auth_session.semaphore:
            result = await auth_session.request(url)
            assert result
            async with result as response:
                if result.status != 404:
                    json_res = await response.json()
                    final_result = await self.handle_error(url, json_res)
                else:
                    final_result = []
                return final_result

    async def handle_error(self, url: str, json_res: dict[str, Any]):
        import ultima_scraper_api.apis.fansly.classes as fansly_classes
        import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

        auth_session = self.auth_session
        auth = auth_session.auth
        if "error" in json_res:
            extras: dict[str, Any] = {}
            extras["auth"] = auth_session.auth
            extras["link"] = url
            if isinstance(auth, onlyfans_classes.auth_model.OnlyFansAuthModel):
                handle_error_ = onlyfans_classes.extras.ErrorDetails
            else:
                handle_error_ = fansly_classes.extras.ErrorDetails

            result = await handle_error_(json_res).format(extras)
            if self.handle_errors:
                return await handle_error_details(result)
        return json_res

    async def handle_refresh(self, item: Any):
        abc = getattr(self.auth_session.auth, f"get_{item.responseType}")
        return abc

    def set_scraped(self, name: str, scraped: list[Any]):
        setattr(self.scraped, name, scraped)
