from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class CommentModel(SiteContent):
    def __init__(self, data: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, data, user)
        self.text: str = data["text"]
        self.giphy_id: int = data["giphyId"]
        self.can_like = data["canLike"]
        self.likes_count = data["likesCount"]
        self.isLikedByAuthor: bool = data["isLikedByAuthor"]
        self.created_at: datetime = datetime.fromisoformat(data["postedAt"])
        self.updated_at: datetime = datetime.fromisoformat(data["changedAt"])
