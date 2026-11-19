from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.privacy import Media, SiteContent, parse_price, parse_time
from ultima_scraper_api.apis.privacy.urls import APIRoutes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.user_model import UserModel


class PostModel(SiteContent):
    """A timeline post (timelinequeries feed/profile/post); medias come inline."""

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        SiteContent.__init__(self, str(option["postId"]), user)
        self.__raw__ = option
        self.text: str = option.get("description") or ""
        self.created_at: datetime | None = parse_time(option.get("publishedDate"))
        self.expires_at: datetime | None = parse_time(option.get("endPublicationDate"))
        self.release_at: datetime | None = parse_time(option.get("releaseDate"))
        self.is_pinned: bool = bool(option.get("isPinned"))
        self.likes_count: int = int(option.get("likeCount") or 0)
        self.comments_count: int = int(option.get("commentCount") or 0)
        self.media_count: int = int(option.get("mediaCount") or 0)
        self.price, self.currency = parse_price(option.get("price"))
        self.is_unlocked: bool = bool(option.get("isUnlocked"))
        self.purchased: bool = bool(option.get("purchaseStatus"))
        self.repost_source_id: str | None = option.get("repostSourceId")
        self.media = [
            Media(
                media,
                # Post medias carry url; the signed-out preview calls it mediaUrl.
                url=media.get("url") or media.get("mediaUrl"),
                created_at=self.created_at,
            )
            for media in option.get("medias") or []
        ]
        self.comments: list[dict[str, Any]] = []

    def is_bought(self) -> bool:
        return self.purchased or self.is_unlocked

    async def get_comments(self) -> list[dict[str, Any]]:
        if not self.comments_count:
            return self.comments
        link = APIRoutes().post_comments(self.uid)
        result = await self.author.get_requester().json_request(link)
        self.comments = result if isinstance(result, list) else []
        return self.comments
