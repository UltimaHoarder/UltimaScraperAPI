from __future__ import annotations

from multiprocessing.pool import Pool

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.dashboard_controller_api import DashboardControllerAPI
from ultima_scraper_api.apis.fansly import classes as fansly_classes
from ultima_scraper_api.apis.onlyfans import classes as onlyfans_classes
from ultima_scraper_api.classes.make_settings import Config

auth_types = (
    onlyfans_classes.auth_model.create_auth | fansly_classes.auth_model.create_auth
)
user_types = (
    onlyfans_classes.user_model.create_user | fansly_classes.user_model.create_user
)
error_types = onlyfans_classes.extras.ErrorDetails | fansly_classes.extras.ErrorDetails

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.fansly import start as FanslyAPI
    from ultima_scraper_api.apis.onlyfans.onlyfans import start as OnlyFansAPI

    api_types = OnlyFansAPI | FanslyAPI


class StreamlinedAPI:
    def __init__(
        self,
        api: api_types,
        config: Config,
        dashboard_controller_api: Optional[DashboardControllerAPI] = None,
    ) -> None:
        from ultima_scraper_api.managers.job_manager.job_manager import JobManager
        from ultima_scraper_api.managers.storage_managers.filesystem_manager import (
            FilesystemManager,
        )

        self.api = api
        self.dashboard_controller_api = dashboard_controller_api
        self.max_threads = config.settings.max_threads
        self.config = config
        self.lists = None
        self.pool: Pool = api_helper.multiprocessing()

        self.job_manager = JobManager()
        self.filesystem_manager = FilesystemManager()

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

    def close_pools(self):
        self.pool.close()
        for auth in self.api.auths:
            if auth.session_manager:
                auth.session_manager.pool.close()
