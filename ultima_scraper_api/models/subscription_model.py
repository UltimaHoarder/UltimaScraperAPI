from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types
    user_types = ultima_scraper_api.user_types


class BaseSubscriptionModel:
    def __init__(
        self, data: dict[str, Any], user: "user_types", subscriber: "auth_types"
    ) -> None:
        self.id = user.id
        self.username = user.username
        self.name = user.name
        self.user = user
        self.subscriber = subscriber
        self.__raw__ = data

    def get_api(self):
        return self.subscriber.get_api()

    def get_authed(self):
        return self.user.get_authed()
