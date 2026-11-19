from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.privacy import Media, SiteContent, parse_price, parse_time

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.user_model import UserModel


class MessageModel(SiteContent):
    """A chat message. ``user`` is the chat partner; the sender may be either side.

    ``file_urls`` maps a file's mediaId to its resolved URL (chat files carry
    only ids; the user model resolves them before building the message).
    """

    def __init__(
        self,
        option: dict[str, Any],
        user: UserModel,
        file_urls: dict[str, str] | None = None,
    ) -> None:
        authed = user.get_authed()
        sender_id = int(option.get("senderId") or 0)
        author = authed.user if sender_id == authed.id else user
        SiteContent.__init__(self, str(option["_id"]), author)
        self.__raw__ = option
        self.user = user
        self.fromUser = author
        self.room_id: str = option.get("roomId") or ""
        self.text: str = option.get("content") or ""
        self.created_at: datetime | None = parse_time(option.get("sentAt"))
        self.sent_at: str | None = option.get("sentAt")
        self.price, currency = parse_price(option.get("price"))
        self.currency: str | None = option.get("currencyCode") or currency
        self.is_locked: bool = bool(option.get("isLocked"))
        self.seen: bool = bool(option.get("seen"))
        urls = file_urls or {}
        self.media = [
            Media(file, url=urls.get(file.get("mediaId") or ""), created_at=self.created_at)
            for file in option.get("files") or []
            # Locked files arrive without an id; nothing identifies them yet.
            if file.get("mediaId")
        ]

    def is_bought(self) -> bool:
        return not self.is_locked

    def get_receiver(self):
        return self.user.get_authed().user if self.author is self.user else self.user
