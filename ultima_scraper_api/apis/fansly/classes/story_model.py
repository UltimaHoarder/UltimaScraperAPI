from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import (
    SiteContent,
    from_timestamp,
    resolve_attachments,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class StoryModel(SiteContent):
    """A media story (GET /mediastoriesnew); its media live in the aggregation."""

    def __init__(
        self,
        option: dict[str, Any],
        user: "UserModel",
        aggregation: dict[str, Any] | None = None,
    ) -> None:
        SiteContent.__init__(self, option, user)
        self.text: str = option.get("content") or ""
        self.created_at: datetime = from_timestamp(option["createdAt"])  # type: ignore[assignment]
        self.updated_at: datetime | None = from_timestamp(option.get("updatedAt"))
        self.expires_at: datetime | None = from_timestamp(option.get("expiresAt"))
        attachments = [
            {"contentType": option.get("contentType"), "contentId": option.get("contentId")}
        ]
        self._attach_media(resolve_attachments(attachments, aggregation or {}))
