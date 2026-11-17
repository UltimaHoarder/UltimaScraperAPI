from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import (
    SiteContent,
    from_timestamp,
    resolve_attachments,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class MessageModel(SiteContent):
    """A direct message. ``user`` is the chat partner; the sender may be either side."""

    def __init__(
        self,
        option: dict[str, Any],
        user: UserModel,
        aggregation: dict[str, Any] | None = None,
    ) -> None:
        authed = user.get_authed()
        sender_id = int(option["senderId"])
        author = authed.user if sender_id == authed.id else user
        SiteContent.__init__(self, option, author)
        self.user = user
        self.fromUser = author
        self.group_id: int = int(option["groupId"])
        self.text: str = option.get("content") or ""
        self.created_at: datetime = from_timestamp(option["createdAt"])  # type: ignore[assignment]
        self.reply_to: str | None = option.get("inReplyTo")
        self.total_tip_amount: int = option.get("totalTipAmount", 0)
        self.attachments: list[dict[str, Any]] = option.get("attachments") or []
        # Price is per media on Fansly (accountMedia.price); messages carry none.
        self.price: int | None = None
        self.is_from_queue: bool = False
        self.queue_id: int | None = None
        self.media, self.previews = resolve_attachments(
            self.attachments, aggregation or {}
        )

    def get_receiver(self):
        return self.user.get_authed().user if self.author is self.user else self.user

    def get_previews(self):
        return [x for x in self.media if int(x["id"]) in self.previews]
