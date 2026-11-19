"""LoyalFans (loyalfans.com) API.

Ids: users, posts, messages, stories and media have opaque string ids
(``uid``); their ``id`` is the archive key ``native_id_to_db_id(uid)`` and the
string is kept as ``uid``. Profiles are addressed by ``slug``, the username in
the profile URL.

Media URLs are signed. Unlocked post media sit under ``/endsun/`` with ``ip=``
and ``expires=`` bound to the IP that read the post (about a day), so they
must be downloaded from that IP. Stories and message covers are CloudFront
links (``Expires``/``Signature``).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel

# LoyalFans media type -> the backend's media kind.
MEDIA_KINDS = {
    "image": "photo",
    "photo": "photo",
    "video": "video",
    "audio": "audio",
    "voice": "audio",
    "gif": "gif",
}


def parse_time(value: Any) -> datetime | None:
    """Dates come as {"date": "2026-01-07 20:13:29", "timezone": "UTC", ...}."""
    if isinstance(value, dict):
        value = value.get("date")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def numbered_pages(
    fetch_page: Callable[[int], Awaitable[tuple[list[Any], dict[str, Any]]]],
    *,
    max_items: int | None = None,
    progress: ScrapeProgress | None = None,
) -> AsyncGenerator[Any, None]:
    """Page-numbered lists (page=1, 2, ...) until a page is empty or its
    ``page_meta``/``pagination`` says it was the last."""

    async def fetch(page: int | None) -> tuple[list[Any], int | None]:
        number = page or 1
        items, meta = await fetch_page(number)
        last = meta.get("last_page") if isinstance(meta, dict) else None
        more = bool(items) and (last is None or number < int(last))
        return items, (number + 1 if more else None)

    async with aclosing(paginate(fetch, max_items=max_items, progress=progress)) as values:
        async for value in values:
            yield value


class Media(dict[str, Any]):
    """A LoyalFans media dict, readable the way the backend reads media.

    The API's keys stay; ``id`` becomes the archive key of ``media_uid``,
    ``type`` the backend's kind, ``url`` the file to download (None while
    locked) and ``preview_url`` a poster or smaller image.
    """

    def __init__(
        self,
        media: dict[str, Any],
        *,
        media_uid: str,
        kind: str,
        url: str | None,
        created_at: datetime | None,
        duration: Any = None,
        preview_url: str | None = None,
        locked: bool = False,
    ) -> None:
        super().__init__(media)
        self["loyalfans_type"] = media.get("type") or media.get("media_type") or kind
        self["media_uid"] = media_uid
        self["id"] = native_id_to_db_id(media_uid)
        self["type"] = kind
        self["url"] = url
        self["preview_url"] = preview_url
        self["created_at"] = created_at
        try:
            seconds = float(duration) if duration is not None else 0.0
        except (TypeError, ValueError):
            seconds = 0.0
        if seconds:
            self["duration"] = seconds
        self["canView"] = bool(url) and not locked

    @property
    def id(self) -> int:
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


def post_media(option: dict[str, Any], created_at: datetime | None) -> list[Media]:
    """Media of a timeline or store post.

    A video post carries ``video_object`` (``video_url`` once viewable). A
    photo post carries ``photos.photos`` only once viewable; locked photo
    posts give just a count, with nothing to identify the photos by, so they
    have no media until bought. Audio and GIF posts have not been seen yet.
    """
    media: list[Media] = []
    video = option.get("video_object")
    if option.get("video") and isinstance(video, dict) and video.get("uid"):
        media.append(
            Media(
                video,
                media_uid=str(video["uid"]),
                kind="video",
                url=video.get("video_url"),
                created_at=created_at,
                duration=video.get("duration"),
                preview_url=video.get("poster"),
            )
        )
    photos = option.get("photos")
    for photo in (photos.get("photos") or []) if isinstance(photos, dict) else []:
        if not photo.get("uid"):
            continue
        images = photo.get("images") or {}
        media.append(
            Media(
                photo,
                media_uid=str(photo["uid"]),
                kind="photo",
                url=images.get("original"),
                created_at=parse_time(photo.get("created_at")) or created_at,
                preview_url=images.get("medium") or images.get("small"),
            )
        )
    return media


class SiteContent:
    """Shared by posts, messages and stories: ids, author and the URL pickers."""

    def __init__(self, uid: str, user: UserModel) -> None:
        self.uid = uid
        self.id: int = native_id_to_db_id(uid)
        self.author = user
        self.text: str = ""
        self.media: list[Media] = []
        self.previews: list[int] = []
        self.preview: list[int] = []
        self.price: float = 0.0

    def url_picker(self, media_item: Media, video_quality: str = ""):
        url = media_item.get("url")
        return urlparse(url) if url and media_item.get("canView") else None

    def preview_url_picker(self, media_item: Media):
        preview = media_item.get("preview_url")
        return urlparse(preview) if preview else None

    def get_author(self):
        return self.author
