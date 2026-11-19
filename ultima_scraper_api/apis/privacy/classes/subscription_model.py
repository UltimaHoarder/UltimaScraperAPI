from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.privacy import parse_time
from ultima_scraper_api.apis.privacy.classes.user_model import UserModel
from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types


class SubscriptionModel(BaseSubscriptionModel):
    """An entry of /subscriptionmanager/subscriptions/active."""

    def __init__(
        self, data: dict[str, Any], user: UserModel, subscriber: "auth_types"
    ) -> None:
        BaseSubscriptionModel.__init__(self, data, user, subscriber)
        self.status: str = data.get("status") or ""
        self.is_free: bool = bool(data.get("isFree"))
        self.is_recurring: bool = bool(data.get("isRecurring"))
        self.ended_at: datetime | None = parse_time(data.get("endedAt"))
        self.next_renewal_at: datetime | None = parse_time(data.get("nextRenewalAt"))
        self.subscribed_by_expire_date = self.ended_at or self.next_renewal_at

    def is_active(self) -> bool:
        return self.status == "active"

    def get_price(self) -> float:
        return 0.0 if self.is_free else float(self.__raw__.get("price") or 0)

    def resolve_expires_at(self):
        return self.subscribed_by_expire_date
