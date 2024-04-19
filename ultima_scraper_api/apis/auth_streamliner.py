from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

from ultima_scraper_api.managers.session_manager import AuthedSession


class CacheStats:
    def __init__(self) -> None:
        self.processed_at: datetime | None = None
        self.delay_in_seconds = 3600 * 1  # hour in seconds * hour
        self.released_at: datetime | None = None

    def activate(self):
        self.processed_at = datetime.now()
        self.released_at = self.processed_at + timedelta(seconds=self.delay_in_seconds)

    def deactivate(self):
        self.processed_at = self.released_at = None

    def is_released(self):
        status = True
        if self.released_at:
            if datetime.now() < self.released_at:
                status = False
            else:
                self.processed_at = self.released_at = None
        return status


class Cache:
    def __init__(self) -> None:
        self.chats = CacheStats()
        self.paid_content = CacheStats()
        self.mass_message_stats = CacheStats()
        self.mass_messages = CacheStats()
        self.subscriptions = CacheStats()


T = TypeVar("T")
TAPI = TypeVar("TAPI")
TAuthDetails = TypeVar("TAuthDetails")


class StreamlinedAuth(Generic[T, TAPI, TAuthDetails]):
    def __init__(self, authenticator: T) -> None:
        self.authenticator = authenticator
        self.auth_session: AuthedSession = authenticator.auth_session  # type:ignore
        self.cache = Cache()
        self.issues: dict[str, Any] | None = None

    def is_authed(self) -> bool:
        return self.authenticator.is_authed()  # type:ignore

    def get_auth_details(self) -> TAuthDetails:
        return self.authenticator.auth_details  # type:ignore

    def get_api(self) -> TAPI:
        return self.authenticator.api  # type:ignore

    def get_requester(self):
        return self.auth_session

    def webhook(self):
        # Unfinished
        site_config = self.authenticator.api.get_site_settings()  # type:ignore
        webhook_auth = site_config.webhooks.auth  # type:ignore
        if webhook_auth.active:  # type:ignore
            pass
