from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import ultima_scraper_api


class CacheStats:
    def __init__(self) -> None:
        self.processed_at: datetime | None = None
        self.delay_in_seconds = 3600 * 1  # hour in seconds * hour
        self.released_at: datetime | None = None

    def activate(self):
        self.processed_at = datetime.utcnow()
        self.released_at = self.processed_at + timedelta(seconds=self.delay_in_seconds)

    def is_released(self):
        status = True
        if self.released_at:
            if datetime.utcnow() < self.released_at:
                status = False
            else:
                self.processed_at = self.released_at = None
        return status


class Cache:
    def __init__(self) -> None:
        self.paid_content = CacheStats()


class StreamlinedAuth:
    def __init__(self, authenticator: "ultima_scraper_api.authenticator_types") -> None:
        self.authenticator = authenticator
        self.cache = Cache()
        self.issues: dict[str, Any] | None = None

    def is_authed(self):
        return self.authenticator.is_authed()

    def get_auth_details(self):
        return self.authenticator.auth_details

    def get_api(self):
        return self.authenticator.api
