from __future__ import annotations

from typing import TYPE_CHECKING, Any

import ultima_scraper_api
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.classes.make_settings import Config

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
                    create_auth,
                )

                self.CreateAuth = create_auth
            case "fansly":
                from ultima_scraper_api.apis.fansly.classes.extras import AuthDetails

                self.AuthDetails = AuthDetails
                from ultima_scraper_api.apis.fansly.classes.auth_model import (
                    create_auth,
                )

                self.CreateAuth = create_auth
            case _:
                raise ValueError("Site Doesn't Exist")


class StreamlinedAPI:
    def __init__(
        self,
        api: api_types,
        config: Config,
    ) -> None:
        from ultima_scraper_api.managers.job_manager.job_manager import JobManager

        self.api = api
        self.max_threads = config.settings.max_threads
        self.config = config
        self.lists = None
        self.pool = api_helper.CustomPool()

        self.job_manager = JobManager()
        self.packages = Packages(self.api.site_name)

    async def login(self, auth_json: dict[str, Any] = {}, guest: bool = False):
        auth = self.add_auth(auth_json)
        authed = await auth.login(guest=guest)
        return authed

    def add_auth(
        self, auth_json: dict[str, Any] = {}, only_active: bool = False
    ) -> auth_types:
        """Creates and appends an auth object to auths property

        Args:
            auth_json (dict[str, str], optional): []. Defaults to {}.
            only_active (bool, optional): [description]. Defaults to False.

        Returns:
            create_auth: [Auth object]
        """
        packages = self.packages
        temp_auth_details = packages.AuthDetails(**auth_json).upgrade_legacy(auth_json)
        auth = packages.CreateAuth(
            self.api, max_threads=self.max_threads, auth_details=temp_auth_details  # type: ignore
        )
        if only_active and not auth.auth_details.active:
            return auth
        auth.auth_details = temp_auth_details  # type: ignore
        auth.extras["settings"] = self.config
        self.api.auths.append(auth)  # type: ignore
        return auth

    def has_active_auths(self):
        return bool([x for x in self.api.auths if x.active])

    def get_auths_via_subscription_identifier(self, identifier: str):
        for auth in self.api.auths:
            if auth.username == identifier:
                pass

    def get_site_settings(self):
        return self.config.supported.get_settings(self.api.site_name)

    def get_global_settings(self):
        return self.config.settings

    async def close_pools(self):
        for auth in self.api.auths:
            await auth.session_manager.active_session.close()
