"""Privacy (privacy.com.br) API.

Ids: users have a numeric ``uid`` (the same number in posts, chats and
subscriptions), which is their ``id``. Posts, messages and media have string
ids (UUIDs, Mongo ids); their ``id`` is the archive key
``native_id_to_db_id(<string>)`` and the string is kept as ``uid``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.user_model import UserModel

# Privacy media type -> the backend's media kind.
MEDIA_KINDS = {"image": "photo", "video": "video", "audio": "audio", "gif": "gif"}


def parse_time(value: str | None) -> datetime | None:
    """ISO timestamps as the API sends them (``2026-11-17T12:22:23.950Z``)."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_duration(value: Any) -> float | None:
    """Video lengths come as seconds or as ``[HH:]MM:SS``."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value) or None
    seconds = 0.0
    try:
        for part in str(value).split(":"):
            seconds = seconds * 60 + float(part)
    except ValueError:
        return None
    return seconds or None


def parse_price(value: Any) -> tuple[float, str | None]:
    """(amount, currency): posts send {amount, currencyCode, ...}, messages a number."""
    if isinstance(value, dict):
        return float(value.get("amount") or 0), value.get("currencyCode")
    try:
        return float(value or 0), None
    except (TypeError, ValueError):
        return 0.0, None


class Media(dict[str, Any]):
    """A Privacy media dict, readable the way the backend reads media.

    The API's keys stay; ``id`` becomes the archive key of ``mediaId`` (kept
    as ``media_id``), ``type`` the backend's kind and ``url`` the file to
    download (an HLS playlist for videos, see ``urls.video_request_headers``).
    """

    def __init__(
        self,
        media: dict[str, Any],
        *,
        url: str | None,
        created_at: datetime | None,
    ) -> None:
        super().__init__(media)
        media_id = str(media.get("mediaId") or media.get("id") or "")
        self["media_id"] = media_id
        self["id"] = native_id_to_db_id(media_id) if media_id else None
        raw_type = str(media.get("type") or media.get("mediaType") or "")
        self["privacy_type"] = raw_type
        self["type"] = MEDIA_KINDS.get(raw_type.split("/")[0].lower(), "photo")
        self["url"] = url
        self["created_at"] = created_at
        duration = parse_duration(media.get("time") or media.get("totalTime"))
        if duration:
            self["duration"] = duration
        self["canView"] = bool(url) and not media.get("isLocked")
        self["drm"] = bool(media.get("drmMediaId"))

    @property
    def id(self) -> int | None:
        return self["id"]

    @property
    def type(self) -> str:
        return self["type"]

    @property
    def canView(self) -> bool:
        return self["canView"]

    @property
    def created_at(self) -> datetime | None:
        return self["created_at"]

    @property
    def duration(self) -> float | None:
        return self.get("duration")


class SiteContent:
    """Shared by posts and messages: ids, author and the URL pickers."""

    def __init__(self, uid: str, user: UserModel) -> None:
        self.uid = uid
        self.id: int = native_id_to_db_id(uid)
        self.author = user
        self.media: list[Media] = []
        self.previews: list[int] = []
        self.preview: list[int] = []
        self.price: float = 0.0

    def url_picker(self, media_item: Media, video_quality: str = ""):
        url = media_item.get("url")
        return urlparse(url) if url and media_item.get("canView") else None

    def preview_url_picker(self, media_item: Media):
        thumb = media_item.get("thumbUrl") or media_item.get("coverUrl")
        return urlparse(thumb) if thumb else None

    def get_author(self):
        return self.author
