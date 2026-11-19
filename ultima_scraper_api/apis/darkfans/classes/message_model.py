from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import (
    Media,
    SiteContent,
    attributes,
    clean_text,
    file_media,
    parse_time,
    price_of,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel


def chat_pack(option: dict[str, Any]) -> dict[str, Any]:
    """The pack (files and price) attached to a message, or {}."""
    attachment = (option.get("metadata") or {}).get("attachment") or {}
    return attributes(attachment.get("chatPack")) if attachment.get("chatPack") else {}


def pack_media(pack: dict[str, Any], created_at: datetime | None) -> list[Media]:
    """A pack's files: free and bought ones with their links, still-locked
    paid ones (listed in ``fileInfo``) by id with their thumbnail."""
    media: list[Media] = []
    seen: set[str] = set()
    for file in (pack.get("freeFiles") or []) + (pack.get("paidFiles") or []):
        item = file_media(file, created_at) if isinstance(file, dict) else None
        if item is not None and item["media_uid"] not in seen:
            seen.add(item["media_uid"])
            media.append(item)
    thumbnails = {
        str(thumb.get("fileId")): thumb
        for thumb in pack.get("thumbnails") or []
        if isinstance(thumb, dict) and thumb.get("fileId")
    }
    for info in pack.get("fileInfo") or []:
        file_id = str(info.get("id") or "")
        if not file_id or file_id in seen:
            continue
        seen.add(file_id)
        placeholder = {**thumbnails.get(file_id, {}), **info, "fileId": file_id}
        item = file_media(placeholder, created_at, locked=True)
        if item is not None:
            media.append(item)
    return media


class MessageModel(SiteContent):
    """A chat message (GET /user/{me}/chat/{chat}/messages).

    ``user`` is the chat partner; the author is whoever ``metadata.userid``
    names. Files come in an attached chat pack: free files always, paid files
    once bought (``purchased``).
    """

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        authed = user.get_authed()
        metadata = option.get("metadata") or {}
        sender = str(metadata.get("userid") or "")
        author = authed.user if sender and sender == authed.user.uid else user
        SiteContent.__init__(self, str(option["uuid"]), author)
        self.__raw__ = option
        self.user = user
        self.fromUser = author
        text = option.get("text")
        self.text: str = clean_text(text.get("text") if isinstance(text, dict) else text)
        self.created_at: datetime | None = parse_time(option.get("timestamp"))
        self.is_read: bool = option.get("read_status") == "read"
        attachment = metadata.get("attachment") or {}
        self.automated: bool = bool(attachment.get("automated"))
        pack = chat_pack(option)
        self.pack = pack
        if pack.get("text") and not self.text:
            self.text = clean_text(pack["text"])
        self.price = price_of(pack.get("price"))
        self.purchased: bool = bool(pack.get("purchased"))
        self.media = pack_media(pack, self.created_at)

    def is_bought(self) -> bool:
        return self.purchased or not self.price or all(m.canView for m in self.media)

    def get_receiver(self):
        return self.user.get_authed().user if self.author is self.user else self.user
