from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class CommentModel(SiteContent):
    def __init__(self, data: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, data, user)
        self.reply_id: int = int(data["inReplyTo"])
        self.reply_root_id: int = int(data["inReplyToRoot"])
        self.text: str = data["content"]
        self.likes_count = data["likeCount"]
        self.created_at: datetime = datetime.fromtimestamp(data["createdAt"])
