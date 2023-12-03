from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

import ultima_scraper_api
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.config import UltimaScraperAPIConfig

if TYPE_CHECKING:
    api_types = ultima_scraper_api.api_types
    auth_types = ultima_scraper_api.auth_types


class Packages:
    def __init__(self, site_name: str) -> None:
        match site_name.lower():
            case "onlyfans":
                from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails

                self.AuthDetails = AuthDetails
                from ultima_scraper_api.apis.onlyfans.classes.auth_model import (
                    AuthModel,
                )

                self.CreateAuth = AuthModel
            case "fansly":
                from ultima_scraper_api.apis.fansly.classes.extras import AuthDetails

                self.AuthDetails = AuthDetails
                from ultima_scraper_api.apis.fansly.classes.auth_model import AuthModel

                self.CreateAuth = AuthModel
            case _:
                raise ValueError("Site Doesn't Exist")


T = TypeVar("T")


class StreamlinedAPI:
    def __init__(
        self,
        api: api_types,
        config: UltimaScraperAPIConfig,
    ) -> None:
        from ultima_scraper_api.managers.job_manager.job_manager import JobManager
        from ultima_scraper_api.managers.session_manager import SessionManager

        self.api = api
        self.config = config
        self.lists = None
        self.pool = api_helper.CustomPool()

        self.job_manager = JobManager()
        self.session_manager = SessionManager(
            self.api, proxies=self.config.settings.network.proxies
        )
        self.packages = Packages(self.api.site_name)

    def add_auth(
        self,
        auth: ultima_scraper_api.auth_types,
    ) -> auth_types:
        self.api.auths[auth.id] = auth  # type: ignore
        return auth

    def has_active_auths(self):
        return bool([x for x in self.api.auths if x.is_authed()])  # type: ignore

    def get_site_settings(self):
        return self.config.site_apis.get_settings(self.api.site_name)

    def get_global_settings(self):
        return self.config.settings

    async def close_pools(self):
        for auth in self.api.auths:
            await auth.auth_session.active_session.close()  # type: ignore

    class CategorizedContent:
        def __init__(self) -> None:
            self.Stories: dict[int, Any] = {}
            self.Posts: dict[int, Any] = {}
            self.Chats: dict[int, Any] = {}
            self.Messages: dict[int, Any] = {}
            self.Highlights: dict[int, Any] = {}
            self.MassMessages: dict[int, Any] = {}

        def find_content(self, content_id: int, content_type: str):
            return getattr(self, content_type)[content_id]
