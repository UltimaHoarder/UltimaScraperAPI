from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import SiteContent
from datetime import datetime

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class StoryModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, option, user)
        self.userId: int = option.get("userId")
        self.expiredAt: str = option.get("expiredAt")
        self.isReady: bool = option.get("isReady")
        self.viewersCount: int = option.get("viewersCount")
        self.viewers: list = option.get("viewers")
        self.canLike: bool = option.get("canLike")
        self.media_count: int = option.get("mediaCount")
        self.isWatched: bool = option.get("isWatched")
        self.isLiked: bool = option.get("isLiked")
        self.canDelete: bool = option.get("canDelete")
        self.isHighlightCover: bool = option.get("isHighlightCover")
        self.isLastInHighlight: bool = option.get("isLastInHighlight")
        self.media: list[Any] = option.get("media", [])
        self.question: Any = option.get("question")
        self.placedContents: list = option.get("placedContents")
        self.answered: int = option.get("answered")
        self.previews: list[dict[str, Any]] = option.get("previews", [])
        self.created_at: datetime = datetime.fromtimestamp(option.get("createdAt"))
        self.updated_at: datetime = datetime.fromtimestamp(option.get("updatedAt"))
