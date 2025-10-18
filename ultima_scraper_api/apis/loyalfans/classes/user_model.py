from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.managers.scrape_manager import ScrapeManager

if TYPE_CHECKING:
    from ultima_scraper_api import LoyalFansAPI
    from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel


class UserModel(StreamlinedUser["LoyalFansAuthModel", "LoyalFansAPI"]):
    def __init__(self, option: dict[str, Any], authed: "LoyalFansAuthModel") -> None:
        self.id: int = int(option.get("id", 0))
        self.username: str = option.get("username", f"u{self.id}")
        self.name: str = option.get("name", self.username)
        self.avatar: str | None = option.get("avatar")
        self.header: str | None = option.get("header")
        self.about: str = option.get("about", "")
        self.location: str | None = option.get("location")
        self.website: str | None = option.get("website")
        self.is_verified: bool = option.get("isVerified", False)
        self.subscriber_count: int = option.get("subscriberCount", 0)
        self.post_count: int = option.get("postCount", 0)
        self.media_count: int = option.get("mediaCount", 0)
        self.subscription_price: float = option.get("subscriptionPrice", 0.0)
        self.is_subscribed: bool = option.get("isSubscribed", False)
        self.is_blocked: bool = option.get("isBlocked", False)
        self.can_message: bool = option.get("canMessage", False)
        self.join_date: str | None = option.get("joinDate")
        self.last_seen: str | None = option.get("lastSeen")
        self.is_online: bool = option.get("isOnline", False)

        # Custom fields for internal use
        found_user = authed.find_user(self.id)
        if not found_user:
            authed.add_user(self)
        self.username = self.get_username()
        self.download_info: dict[str, Any] = {}
        self.duplicate_media = []
        self.scrape_manager = ScrapeManager[
            "LoyalFansAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def get_username(self) -> str:
        """Returns username, if not available returns user ID prefixed with 'u'"""
        if not self.username:
            self.username = f"u{self.id}"
        return self.username

    def get_link(self, use_username: bool = False) -> str:
        """Returns the user's profile link"""
        if use_username:
            return f"https://www.loyalfans.com/{self.username}"
        return f"https://www.loyalfans.com/user/{self.id}"

    async def get_avatar(self) -> str | None:
        """Returns the user's avatar URL"""
        return self.avatar

    async def get_header(self) -> str | None:
        """Returns the user's header/banner URL"""
        return self.header

    def is_performer(self) -> bool:
        """Returns True if the user is a content creator"""
        # In LoyalFans, anyone with subscription price > 0 is considered a performer
        return self.subscription_price > 0

    async def match_identifiers(self, identifiers: list[int | str]) -> bool:
        """Checks if user matches any of the provided identifiers"""
        return self.id in identifiers or self.username in identifiers

    async def get_posts(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Gets user's posts with pagination"""
        if not self.is_subscribed:
            return []

        link = f"https://www.loyalfans.com/api/v2/user/{self.id}/posts"
        params = {"limit": limit, "offset": offset}
        results = await self.get_requester().json_request(link, params=params)
        return results.get("posts", [])

    async def get_messages(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Gets private messages between authenticated user and this user"""
        if not self.can_message:
            return []

        link = f"https://www.loyalfans.com/api/v2/messages/{self.id}"
        params = {"limit": limit, "offset": offset}
        results = await self.get_requester().json_request(link, params=params)
        return results.get("messages", [])
