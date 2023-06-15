from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import ultima_scraper_api
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
