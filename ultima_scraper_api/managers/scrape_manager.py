from collections.abc import (
    AsyncIterable,
    AsyncGenerator,
    Awaitable,
    Callable,
    Iterable,
    Sized,
)
from contextlib import aclosing
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from ultima_scraper_api.apis.api_helper import handle_error_details
from ultima_scraper_api.helpers.concurrency import map_unordered
from ultima_scraper_api.managers.session_manager import consume_response_json

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

    async def iter_scrape(
        self,
        urls: Iterable[str] | AsyncIterable[str],
        on_progress: ScrapeProgressCallback | None = None,
        *,
        concurrency: int | None = None,
        total_pages: int | None = None,
    ) -> AsyncGenerator[Any, None]:
        """Stream flattened page results with bounded request admission.

        Unset admission concurrency follows the existing session request budget.
        A lazy URL source may supply its total for progress; zero denotes an
        unknown total. Callers stopping early must close this iterator.
        """
        limit = (
            self.auth_session.session_manager.max_threads
            if concurrency is None
            else concurrency
        )
        total = (
            total_pages
            if total_pages is not None
            else len(urls)
            if isinstance(urls, Sized)
            else 0
        )
        completed = 0
        items_count = 0

        async def scrape_page(url: str) -> Any:
            try:
                return await self.scrape(url)
            except Exception:
                # Preserve bulk_scrape's page-failure behavior. Cancellation
                # still propagates and drains all admitted requests.
                return None

        async with aclosing(map_unordered(scrape_page, urls, limit=limit)) as pages:
            async for page in pages:
                values = (
                    (page if isinstance(page, list) else [page])
                    if page and not isinstance(page, BaseException)
                    else []
                )
                completed += 1
                items_count += len(values)
                if on_progress:
                    await on_progress(completed, total, items_count)
                for value in values:
                    yield value

    async def bulk_scrape(
        self,
        urls: list[str],
        on_progress: ScrapeProgressCallback | None = None,
        *,
        concurrency: int | None = None,
    ) -> list[Any]:
        """Collect page results for callers that explicitly need a complete list.

        Runtime pipelines can consume iter_scrape instead to release each page
        incrementally. Both entry points bound admitted requests.
        """
        async with aclosing(
            self.iter_scrape(urls, on_progress, concurrency=concurrency)
        ) as values:
            return [value async for value in values]

    async def scrape(self, url: str):
        auth_session = self.auth_session
        async with auth_session.semaphore:
            result = await auth_session.request(url)
            assert result
            async with result as response:
                if result.status != 404:
                    json_res = await consume_response_json(response)
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
