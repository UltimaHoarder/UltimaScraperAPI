from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.media_model import MediaModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class StoryModel(SiteContent):
    def __init__(
        self, option: dict[str, Any], user: "UserModel", highlight: bool = False
    ) -> None:
        SiteContent.__init__(self, option, user)
        self.user_id: int = option.get("userId", user.id)
        self.is_ready: bool | None = option.get("isReady")
        self.viewersCount: int | None = option.get("viewersCount")
        self.viewers: list[Any] | None = option.get("viewers")
        self.canLike: bool = option["canLike"]
        self.is_watched: bool | None = option.get("isWatched")
        self.is_liked: bool | None = option.get("isLiked")
        self.canDelete: bool | None = option.get("canDelete")
        self.isHighlightCover: bool | None = option.get("isHighlightCover")
        self.isLastInHighlight: bool | None = option.get("isLastInHighlight")
        self.hasPost: bool = option.get("hasPost", False)
        media_data: list[dict[str, Any]] = option.get("media", [])
        self.media: list[MediaModel] = [MediaModel(m, self) for m in media_data]
        self.question: dict[str, Any] | None = option.get("question")
        self.placedContents: list[Any] | None = option.get("placedContents")
        self.answered: int | None = option.get("answered")
        self.created_at = datetime.fromisoformat(option["createdAt"])
        self.expires_at = (
            self.created_at + timedelta(hours=24) if not highlight else None
        )

        user.scrape_manager.scraped.Stories[self.id] = self
