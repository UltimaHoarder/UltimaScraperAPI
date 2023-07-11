from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


class StreamlinedAPI:
    def __init__(
        self,
        api: api_types,
        config: UltimaScraperAPIConfig,
    ) -> None:
        from ultima_scraper_api.managers.job_manager.job_manager import JobManager

        self.api = api
        self.config = config
        self.lists = None
        self.pool = api_helper.CustomPool()

        self.job_manager = JobManager()
        self.packages = Packages(self.api.site_name)

    def add_auth(
        self,
        authenticator: ultima_scraper_api.authenticator_types,
        only_active: bool = False,
    ) -> auth_types:
        """Creates and appends an auth object to auths property

        Args:
            auth_json (dict[str, str], optional): []. Defaults to {}.
            only_active (bool, optional): [description]. Defaults to False.

        Returns:
            create_auth: [Auth object]
        """
        packages = self.packages
        auth = packages.CreateAuth(authenticator)  # type: ignore
        if only_active and not auth.authenticator.auth_details.active:
            return auth
        auth.extras["settings"] = self.config
        self.api.auths.append(auth)  # type: ignore
        return auth

    def has_active_auths(self):
        return bool([x for x in self.api.auths if x.is_authed()])

    def get_auths_via_subscription_identifier(self, identifier: str):
        for auth in self.api.auths:
            if auth.username == identifier:
                pass

    def get_site_settings(self):
        return self.config.site_apis.get_settings(self.api.site_name)

    def get_global_settings(self):
        return self.config.settings

    async def close_pools(self):
        for auth in self.api.auths:
            await auth.session_manager.active_session.close()

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
