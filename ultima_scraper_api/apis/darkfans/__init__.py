"""DarkFans (darkfans.com) API.

Ids: users, posts, stories, chats, messages and files are UUIDs; their ``id``
is the archive key ``native_id_to_db_id(uuid)`` and the UUID is kept as
``uid``. Profiles are addressed by username.

Files. A post, story or message file is ``{fileId, provider, providerId,
type, thumbnail, teaser, ...}``; a post lists ``files`` only once viewable
(free, subscribed or bought) and otherwise just counts them in ``fileInfo``.
``provider`` says where the file is:

- ``aws-s3`` and ``loverfans-cdn``: ``providerId`` is a signed CloudFront
  link to the file (``Expires``/``Signature``).
- ``fastevo-drm``: videos. ``providerId`` is a Fastevo playback token; the
  file is a DASH manifest (``.../processed/video/content/media/master.mpd``)
  whose streams are encrypted (CENC ``cbcs``). The manifest is recorded as
  DRM media with the token as its signature, and ``teaser`` (a clear MP4
  clip) is the preview; ``fastevo.FastevoDRM`` plays the token for the
  tracks and their keys.
"""

from __future__ import annotations

import html
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel

# DarkFans file type -> the backend's media kind.
MEDIA_KINDS = {"image": "photo", "video": "video", "audio": "audio", "gif": "gif"}
# Providers whose providerId is the file's own (signed) URL.
DIRECT_PROVIDERS = {"aws-s3", "loverfans-cdn"}
DRM_PROVIDER = "fastevo-drm"


def attributes(item: Any) -> dict[str, Any]:
    """The object inside a JSON:API-style ``{"type", "attributes"}`` wrapper."""
    if isinstance(item, dict):
        inner = item.get("attributes")
        return inner if isinstance(inner, dict) else item
    return {}


def parse_time(value: Any) -> datetime | None:
    """Epoch seconds (API objects) or milliseconds (chat messages)."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1e12:
        number /= 1000
    return datetime.fromtimestamp(number, tz=timezone.utc)


def price_of(value: Any) -> float:
    """``{"amount": 1500, "currency": "USD"}`` (cents) -> 15.0."""
    if isinstance(value, dict):
        value = value.get("amount")
    try:
        return float(value or 0) / 100
    except (TypeError, ValueError):
        return 0.0


def clean_text(value: Any) -> str:
    """Message text arrives HTML-escaped (``&apos;``)."""
    return html.unescape(value) if isinstance(value, str) else ""


async def numbered_pages(
    fetch_page: Callable[[int], Awaitable[tuple[list[Any], dict[str, Any]]]],
    *,
    per_page: int,
    max_items: int | None = None,
    progress: ScrapeProgress | None = None,
) -> AsyncGenerator[Any, None]:
    """Page-numbered lists (page=1, 2, ...).

    Paging stops at ``meta.pagination.totalPages`` when the response has it,
    and otherwise (chat messages) at the first short page.
    """

    async def fetch(page: int | None) -> tuple[list[Any], int | None]:
        number = page or 1
        items, meta = await fetch_page(number)
        pagination = meta.get("pagination") if isinstance(meta, dict) else None
        total_pages = pagination.get("totalPages") if isinstance(pagination, dict) else None
        if total_pages is not None:
            more = bool(items) and number < int(total_pages)
        else:
            more = len(items) >= per_page
        return items, (number + 1 if more else None)

    async with aclosing(paginate(fetch, max_items=max_items, progress=progress)) as values:
        async for value in values:
            yield value


class Media(dict[str, Any]):
    """A DarkFans file, readable the way the backend reads media.

    The API's keys stay; ``id`` becomes the archive key of ``media_uid`` (the
    fileId), ``type`` the backend's kind, ``url`` the file to download (None
    while locked or DRM-protected) and ``preview_url`` a thumbnail or teaser.
    A DRM video carries ``drm`` = {"provider", "token", "manifest": {"dash"}},
    which the backend stores as a DRM manifest.
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
        drm: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(media)
        self["darkfans_type"] = media.get("type") or kind
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
        if drm:
            self["drm"] = drm
        else:
            self.pop("drm", None)
        # Viewable: an unlocked file, even when it is a DRM stream.
        self["canView"] = not locked and bool(url or drm)

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


def manifest_url(file: dict[str, Any]) -> str | None:
    """The DASH manifest of a Fastevo video, built from its thumbnail's host.

    Fastevo serves ``https://<host>/<rawProviderId>/processed/...``; the
    manifest needs no signature (its streams are encrypted instead).
    """
    raw_id = file.get("rawProviderId")
    for key in ("thumbnail", "teaser", "blurredTeaser"):
        link = file.get(key)
        if raw_id and isinstance(link, str) and "fastevo" in link:
            host = urlparse(link).netloc
            return f"https://{host}/{raw_id}/processed/video/content/media/master.mpd"
    return None


def file_media(
    file: dict[str, Any], created_at: datetime | None, *, locked: bool = False
) -> Media | None:
    """One file of a post, story or message (None without a fileId)."""
    file_id = file.get("fileId") or file.get("id")
    if not file_id:
        return None
    provider = file.get("provider") or ""
    provider_id = file.get("providerId")
    kind = MEDIA_KINDS.get(str(file.get("type")).lower(), "photo")
    url: str | None = None
    drm: dict[str, Any] | None = None
    if not locked and provider in DIRECT_PROVIDERS and isinstance(provider_id, str):
        url = provider_id if provider_id.startswith("http") else None
    elif not locked and provider == DRM_PROVIDER and provider_id:
        dash = manifest_url(file)
        drm = {"provider": "fastevo", "token": provider_id}
        if dash:
            # Stored as the DRM manifest; the token is what plays it.
            drm["manifest"] = {"dash": {"manifest_url": dash, "signature": provider_id}}
    preview = (
        file.get("thumbnail")
        or file.get("teaser")
        or file.get("blurredThumbnail")
        or file.get("blurredTeaser")
    )
    return Media(
        file,
        media_uid=str(file_id),
        kind=kind,
        url=url,
        created_at=created_at,
        duration=file.get("duration"),
        preview_url=preview,
        locked=locked,
        drm=drm,
    )


def files_media(files: Any, created_at: datetime | None) -> list[Media]:
    media: list[Media] = []
    for file in files if isinstance(files, list) else []:
        item = file_media(file, created_at) if isinstance(file, dict) else None
        if item is not None:
            media.append(item)
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
