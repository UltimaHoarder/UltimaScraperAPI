from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class StoryModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, option, user)
        self.user_id: int = option.get("userId", user.id)
        self.expiredAt: str | None = option.get("expiredAt")
        self.is_ready: bool | None = option.get("isReady")
        self.viewersCount: int = option.get("viewersCount")
        self.viewers: list = option.get("viewers")
        self.canLike: bool = option["canLike"]
        self.is_watched: bool | None = option.get("isWatched")
        self.is_liked: bool | None = option.get("isLiked")
        self.canDelete: bool | None = option.get("canDelete")
        self.isHighlightCover: bool = option.get("isHighlightCover")
        self.isLastInHighlight: bool = option.get("isLastInHighlight")
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.question: dict[str, Any] | None = option.get("question")
        self.placedContents: list = option.get("placedContents")
        self.answered: int = option.get("answered")
        self.created_at = datetime.fromisoformat(option["createdAt"])
        user.scrape_manager.scraped.Stories[self.id] = self
