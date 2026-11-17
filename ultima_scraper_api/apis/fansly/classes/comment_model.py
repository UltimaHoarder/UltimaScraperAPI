from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import SiteContent, from_timestamp

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class CommentModel(SiteContent):
    """A reply to a post (GET /post/{id}/replies)."""

    def __init__(self, data: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, data, user)
        self.reply_id: int = int(data["inReplyTo"])
        self.reply_root_id: int = int(data.get("inReplyToRoot") or data["inReplyTo"])
        self.text: str = data.get("content") or ""
        self.likes_count: int = data.get("likeCount", 0)
        self.created_at: datetime = from_timestamp(data["createdAt"])  # type: ignore[assignment]
