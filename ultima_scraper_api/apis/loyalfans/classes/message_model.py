from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.loyalfans import (
    MEDIA_KINDS,
    Media,
    SiteContent,
    parse_time,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


def message_media(
    option: dict[str, Any], message_uid: str, created_at: datetime | None
) -> list[Media]:
    """A message's ``media`` entries.

    They carry no id of their own, so each is keyed by the message uid and its
    ``index``. Only locked message media have been seen; the URL keys of an
    unlocked one are a best guess (the post keys ``video_url`` and
    ``images.original``, or a plain ``url``) until one is captured.
    """
    media: list[Media] = []
    for position, item in enumerate(option.get("media") or []):
        index = item.get("index", position)
        images = item.get("images") if isinstance(item.get("images"), dict) else {}
        url = item.get("video_url") or item.get("url") or images.get("original")
        media.append(
            Media(
                item,
                media_uid=str(item.get("uid") or f"{message_uid}:{index}"),
                kind=MEDIA_KINDS.get(str(item.get("media_type")).lower(), "photo"),
                url=url,
                created_at=created_at,
                duration=item.get("duration"),
                preview_url=item.get("video_cover") or images.get("medium"),
                locked=bool(item.get("is_locked")),
            )
        )
    return media


class MessageModel(SiteContent):
    """A message from /api/v1/messages/with/{partner}. ``user`` is the chat
    partner; ``own`` messages are the signed-in account's."""

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        authed = user.get_authed()
        author = authed.user if option.get("own") else user
        SiteContent.__init__(self, str(option["uid"]), author)
        self.__raw__ = option
        self.user = user
        self.fromUser = author
        self.text: str = option.get("message") or ""
        self.created_at: datetime | None = parse_time(option.get("created_at"))
        self.price = float(option.get("price") or 0)
        self.is_locked: bool = bool(option.get("is_locked"))
        self.is_expired: bool = bool(option.get("is_expired"))
        self.has_tips: bool = bool(option.get("has_tips"))
        self.media = message_media(option, self.uid, self.created_at)

    def is_bought(self) -> bool:
        return not self.is_locked

    def get_receiver(self):
        return self.user.get_authed().user if self.author is self.user else self.user
