from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.loyalfans import parse_time
from ultima_scraper_api.models.subscription_model import BaseSubscriptionModel

if TYPE_CHECKING:
    import ultima_scraper_api
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel

    auth_types = ultima_scraper_api.auth_types


class SubscriptionModel(BaseSubscriptionModel):
    """A member of the "subscribed" or "following" system list.

    ``kind`` says which: "subscribed" is a paid subscription (its
    ``subscription_status`` has the dates), "following" a free follow, which
    stays active while followed.
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
        status: dict[str, Any] = data.get("subscription_status") or {}
        self.status = status
        self.subscribed_at: datetime | None = parse_time(status.get("subscribed_at"))
        self.expired_at: datetime | None = parse_time(status.get("expired_at"))
        self.canceled_at: datetime | None = parse_time(status.get("canceled_at"))
        self.subscribed_by_expire_date = self.expired_at

    def is_active(self) -> bool:
        if self.kind != "subscribed":
            return True
        if self.expired_at is not None:
            return self.expired_at > datetime.now(timezone.utc)
        return bool(self.status.get("is_subscribed_to"))

    def get_price(self) -> float:
        return float(self.user.subscription_price or 0) if self.kind == "subscribed" else 0.0

    def resolve_expires_at(self):
        return self.subscribed_by_expire_date
