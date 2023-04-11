import asyncio
from itertools import chain
from typing import Any

from ultima_scraper_api.apis.api_helper import handle_error_details
from ultima_scraper_api.managers.session_manager import SessionManager


class ScrapeManager:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.handle_errors = True
        self.scraped = session_manager.auth.api.ContentTypes()

    async def bulk_scrape(self, urls: list[str]):
        result = await asyncio.gather(
            *[self.scrape(x) for x in urls], return_exceptions=True
        )
        final_result = list(chain(*result))
        return final_result

    async def scrape(self, url: str):
        session_manager = self.session_manager
        async with session_manager.semaphore:
            result = await session_manager.request(url)
            async with result as response:
                json_res = await response.json()
                final_result = await self.handle_error(url, json_res)
                return final_result

    async def handle_error(self, url: str, json_res: dict[str, Any]):
        import ultima_scraper_api.apis.fansly.classes as fansly_classes
        import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

        session_manager = self.session_manager
        auth = session_manager.auth
        if "error" in json_res:
            extras: dict[str, Any] = {}
            extras["auth"] = session_manager.auth
            extras["link"] = url
            if isinstance(auth, onlyfans_classes.auth_model.create_auth):
                handle_error_ = onlyfans_classes.extras.ErrorDetails
            else:
                handle_error_ = fansly_classes.extras.ErrorDetails

            result = await handle_error_(json_res).format(extras)
            if self.handle_errors:
                return await handle_error_details(result)
        return json_res

    async def handle_refresh(self, item: Any):
        abc = getattr(self.session_manager.auth, f"get_{item.responseType}")
        return abc

    def set_scraped(self, name: str, scraped: list[Any]):
        setattr(self.scraped, name, scraped)