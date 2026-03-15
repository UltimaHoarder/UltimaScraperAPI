from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types
    user_types = ultima_scraper_api.user_types


class SubscriptionModel(BaseSubscriptionModel):
    def __init__(
        self, data: dict[str, Any], user: "user_types", subscriber: "auth_types"
    ) -> None:
        self.active = data["subscribedBy"]
        self.subscribed_by_data: dict[str, Any] = data["subscribedByData"]
        self.subscribed_by_expire: bool = data["subscribedByExpire"]
        self.subscribed_by_expire_date: datetime = datetime.fromisoformat(
            data["subscribedByExpireDate"]
        )
        self.subscribed_by_autoprolong: bool = data["subscribedByAutoprolong"]
        self.subscribed_is_expired_now: bool = data["subscribedIsExpiredNow"]
        self.current_subscribe_price: int = data["currentSubscribePrice"]
        self.subscribed_on: bool = data["subscribedOn"]
        self.subscribed_on_data: dict[str, Any] = data["subscribedOnData"]
        self.subscribed_on_expired_now: bool = data["subscribedOnExpiredNow"]
        self.subscribed_on_duration: str = data["subscribedOnDuration"]
        self.subscribe_price: int = data["subscribePrice"]
        self.user = user
        self.subscriber = subscriber
        self.__raw__ = data

    def is_active(self):
        time_now = datetime.now().astimezone()
        if self.subscribed_by_expire_date >= time_now:
            return True
        else:
            return False

    def get_authed(self):
        return self.subscriber

    def get_price(self):
        return self.subscribe_price

    def resolve_expires_at(self):
        return self.subscribed_by_expire_date
