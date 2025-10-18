from typing import Any


class SubscriptionCategoryCount:
    """Represents subscription counts broken down by category."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.active: int = data.get("active", 0)
        self.muted: int = data.get("muted", 0)
        self.restricted: int = data.get("restricted", 0)
        self.expired: int = data.get("expired", 0)
        self.blocked: int = data.get("blocked", 0)
        self.attention: int = data.get("attention", 0)
        self.all: int = data.get("all", 0)
        self.__raw__ = data


class SubscriberCategoryCount:
    """Represents subscriber counts broken down by category."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.active: int = data.get("active", 0)
        self.muted: int = data.get("muted", 0)
        self.restricted: int = data.get("restricted", 0)
        self.expired: int = data.get("expired", 0)
        self.blocked: int = data.get("blocked", 0)
        self.all: int = data.get("all", 0)
        self.active_online: int = data.get("activeOnline", 0)
        self.__raw__ = data


class SubscriptionCountModel:
    """Model for subscription count API response from OnlyFans."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.subscriptions: SubscriptionCategoryCount = SubscriptionCategoryCount(
            data.get("subscriptions", {})
        )
        self.subscribers: SubscriberCategoryCount = SubscriberCategoryCount(
            data.get("subscribers", {})
        )
        self.bookmarks: int = data.get("bookmarks", 0)
        self.__raw__ = data

    def __repr__(self) -> str:
        return (
            f"SubscriptionCountModel("
            f"subscriptions.all={self.subscriptions.all}, "
            f"subscribers.all={self.subscribers.all}, "
            f"bookmarks={self.bookmarks})"
        )
