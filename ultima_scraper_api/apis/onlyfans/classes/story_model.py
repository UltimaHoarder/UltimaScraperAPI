from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user


class create_story(SiteContent):
    def __init__(self, option: dict[str, Any], user: "create_user") -> None:
        SiteContent.__init__(self, option, user)
        self.userId: int = option.get("userId")
        self.createdAt: str = option.get("createdAt")
        self.expiredAt: str = option.get("expiredAt")
        self.isReady: bool = option.get("isReady")
        self.viewersCount: int = option.get("viewersCount")
        self.viewers: list = option.get("viewers")
        self.canLike: bool = option.get("canLike")
        self.mediaCount: int = option.get("mediaCount")
        self.isWatched: bool = option.get("isWatched")
        self.isLiked: bool = option.get("isLiked")
        self.canDelete: bool = option.get("canDelete")
        self.isHighlightCover: bool = option.get("isHighlightCover")
        self.isLastInHighlight: bool = option.get("isLastInHighlight")
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.question: Any = option.get("question")
        self.placedContents: list = option.get("placedContents")
        self.answered: int = option.get("answered")
