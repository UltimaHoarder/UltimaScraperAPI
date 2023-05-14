from datetime import datetime
from typing import TYPE_CHECKING, Any
from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel
from ultima_scraper_api.apis.fansly.classes.user_model import create_user

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types
    user_types = ultima_scraper_api.user_types


class SubscriptionModel(BaseSubscriptionModel):
    def __init__(
        self, data: dict[str, Any], user: "create_user", subscriber: "auth_types"
    ) -> None:
        self.ends_at: datetime = datetime.fromtimestamp(data["endsAt"] / 1000)
        self.price: int = data["price"]
        self.user = user
        self.subscriber = subscriber
        self.__raw__ = data

    def get_authed(self):
        return self.subscriber.get_authed()

    def get_price(self):
        return self.price
