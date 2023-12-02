from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user


class create_story(SiteContent):
    def __init__(self, option: dict[str, Any], user: "create_user") -> None:
        SiteContent.__init__(self, option, user)
        self.user_id: int = option["userId"]
        self.expiredAt: str = option.get("expiredAt")
        self.is_ready: bool = option["isReady"]
        self.viewersCount: int = option.get("viewersCount")
        self.viewers: list = option.get("viewers")
        self.canLike: bool = option["canLike"]
        self.mediaCount: int = option.get("mediaCount")
        self.is_watched: bool = option["isWatched"]
        self.is_liked: bool = option["isLiked"]
        self.canDelete: bool = option.get("canDelete")
        self.isHighlightCover: bool = option.get("isHighlightCover")
        self.isLastInHighlight: bool = option.get("isLastInHighlight")
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.question: Any = option.get("question")
        self.placedContents: list = option.get("placedContents")
        self.answered: int = option.get("answered")
        self.created_at = datetime.fromisoformat(option["createdAt"])
