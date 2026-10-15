from __future__ import annotations

import asyncio
import platform
from typing import TYPE_CHECKING, TypeVar

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
                    OnlyFansAuthModel,
                )

                self.CreateAuth = OnlyFansAuthModel
            case "fansly":
                from ultima_scraper_api.apis.fansly.classes.extras import AuthDetails

                self.AuthDetails = AuthDetails
                from ultima_scraper_api.apis.fansly.classes.auth_model import (
                    FanslyAuthModel,
                )

                self.CreateAuth = FanslyAuthModel
            case "loyalfans":
                from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails

                self.AuthDetails = AuthDetails
                from ultima_scraper_api.apis.loyalfans.classes.auth_model import (
                    LoyalFansAuthModel,
                )

                self.CreateAuth = LoyalFansAuthModel
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
        self.system = platform.system()

    def add_auth(
        self,
        auth: ultima_scraper_api.auth_types,
    ) -> auth_types:
        # Guest /me responses commonly have ID 0. Register by the supplied
        # visitor identity so distinct owned clients survive until cleanup.
        auth_key = auth.id
        if getattr(auth, "guest", False):
            authenticator = getattr(auth, "authenticator", None)
            details = getattr(authenticator, "auth_details", None)
            auth_key = (
                getattr(authenticator, "guest_registration_id", None)
                or getattr(details, "id", None) or auth_key
            )
        self.api.auths[auth_key] = auth  # type: ignore
        return auth

    def has_active_auths(self):
        return bool([x for x in self.api.auths if x.is_authed()])  # type: ignore

    def get_site_settings(self):
        return self.config.site_apis.get_settings(self.api.site_name)

    def get_global_settings(self):
        return self.config.settings

    async def remove_auth(self, auth: auth_types) -> None:
        """Close and remove one auth through the shared site lifecycle."""
        try:
            await auth.get_requester().active_session.close()
        finally:
            for key, registered in list(self.api.auths.items()):
                if registered is auth:
                    self.api.auths.pop(key, None)

    async def close_pools(self) -> None:
        pending = getattr(self.api, "_mps_guest_auth_pending", {})
        tasks = [entry["task"] for entry in list(pending.values())]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.session_manager.stop_rate_limit_checker()
        await asyncio.gather(
            *(self.remove_auth(auth) for auth in list(self.api.auths.values())),  # type: ignore[attr-defined]
            return_exceptions=True,
        )
        for name in ("_mps_guest_auth_cache", "_mps_guest_auth_locks"):
            getattr(self.api, name, {}).clear()
