import asyncio
from itertools import chain
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.api_helper import handle_error_details

if TYPE_CHECKING:
    from ultima_scraper_api.managers.session_manager import AuthedSession


class ContentManager:
    def __init__(self, auth_session: "AuthedSession") -> None:
        self.auth_session = auth_session
        self.categorized = auth_session.auth.api.CategorizedContent()

    def get_contents(self, content_type: str):
        return getattr(self.categorized, content_type)

    def set_content(self, content_type: str, scraped: list[Any]):
        for content in scraped:
            content_item = getattr(self.categorized, content_type)
            content_item[content.content_id] = content

    def find_content(self, content_id: int, content_type: str):
        found_content = None
        try:
            found_content = getattr(self.categorized, content_type)[content_id]
        except KeyError:
            pass
        return found_content


class ScrapeManager:
    def __init__(self, auth_session: "AuthedSession") -> None:
        self.auth_session = auth_session
        self.handle_errors = True
        self.scraped = auth_session.auth.api.ContentTypes()

    async def bulk_scrape(self, urls: list[str]):
        result = await asyncio.gather(
            *[self.scrape(x) for x in urls], return_exceptions=True
        )
        final_result = list(chain(*result))
        return final_result

    async def scrape(self, url: str):
        auth_session = self.auth_session
        async with auth_session.semaphore:
            result = await auth_session.request(url)
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
            if isinstance(auth, onlyfans_classes.auth_model.AuthModel):
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
