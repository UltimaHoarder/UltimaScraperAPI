from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import from_timestamp
from ultima_scraper_api.apis.fansly.classes.user_model import UserModel
from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel

if TYPE_CHECKING:
    import ultima_scraper_api

    auth_types = ultima_scraper_api.auth_types


class SubscriptionModel(BaseSubscriptionModel):
    """An entry of GET /subscriptions (one per tier subscribed to)."""

    def __init__(
        self, data: dict[str, Any], user: "UserModel", subscriber: "auth_types"
    ) -> None:
        # Base sets id/username/name from the user, as the OnlyFans model does.
        BaseSubscriptionModel.__init__(self, data, user, subscriber)
        self.subscription_id: int = int(data["id"])
        # Prices are in thousandths of a dollar (5000 == $5).
        self.price: int = data["price"]
        self.renew_price: int | None = data.get("renewPrice")
        self.tier_id: int = int(data["subscriptionTierId"])
        self.tier_name: str = data.get("subscriptionTierName") or ""
        self.status: int = data.get("status", 0)
        self.auto_renew: bool = bool(data.get("autoRenew"))
        self.created_at: datetime = from_timestamp(data["createdAt"])  # type: ignore[assignment]
        self.ends_at: datetime = from_timestamp(data["endsAt"])  # type: ignore[assignment]
        self.subscribed_by_expire_date = self.ends_at

    def is_active(self):
        return self.ends_at > datetime.now()

    def get_price(self):
        return self.price

    def resolve_expires_at(self):
        return self.ends_at
