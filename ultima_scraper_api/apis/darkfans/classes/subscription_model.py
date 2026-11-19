from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import parse_time, price_of
from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel

if TYPE_CHECKING:
    import ultima_scraper_api
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel

    auth_types = ultima_scraper_api.auth_types


class SubscriptionModel(BaseSubscriptionModel):
    """A paid subscription (GET /user/{me}/subscriptions) or a free follow.

    ``kind`` says which: "subscribed" rows have ``status`` (valid/expired) and
    ``expiresAt``; "following" (a followee) stays active while followed.
    """

    def __init__(
        self,
        data: dict[str, Any],
        user: UserModel,
        subscriber: auth_types,
        kind: str = "subscribed",
    ) -> None:
        BaseSubscriptionModel.__init__(self, data, user, subscriber)
        self.user: UserModel = user
        self.kind = kind
        self.status: str = data.get("status") or ""
        self.expired_at: datetime | None = parse_time(data.get("expiresAt"))
        self.subscribed_at: datetime | None = parse_time(data.get("subscribedSince"))
        self.subscribed_price = price_of(data.get("subscribedPrice"))
        self.subscribed_by_expire_date = self.expired_at

    def is_active(self) -> bool:
        if self.kind != "subscribed":
            return True
        if self.status:
            return self.status == "valid"
        return bool(self.expired_at and self.expired_at > datetime.now(timezone.utc))

    def get_price(self) -> float:
        return self.subscribed_price if self.kind == "subscribed" else 0.0

    def resolve_expires_at(self):
        return self.subscribed_by_expire_date
