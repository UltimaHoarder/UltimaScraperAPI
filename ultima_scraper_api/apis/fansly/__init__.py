from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel

SubscriptionType = Literal["all", "active", "expired"]


def _pick_media_url(media: dict[Any, Any], target_quality: str) -> str | None:
    if target_quality == "source":
        try:
            return media["locations"][0]["location"]
        except (KeyError, IndexError):
            pass

    # Video variants can include image thumbnails; only compare matching media types.
    target_type = media.get("mimetype")
    qualities: list[tuple[int, str]] = []
    for variant in media.get("variants", []) + [media]:
        if variant.get("mimetype") != target_type:
            continue
        height = variant["height"]
        try:
            url = variant["locations"][0]["location"]
        except (KeyError, IndexError):
            continue
        qualities.append((height, url))

    if not qualities:
        return None
    for height, url in sorted(qualities, reverse=True):
        if target_quality == "source" or height <= int(target_quality):
            return url
    return url


def _has_location(media: dict[str, Any] | None) -> bool:
    """True when the picker can return a URL of the media's own type.

    A locked video often still exposes a JPEG thumbnail variant; that alone
    does not make the video downloadable.
    """
    return bool(media) and _pick_media_url(media, "source") is not None  # type: ignore[arg-type]


def resolve_account_media(
    account_media_ids: list[str],
    aggregation: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[int]]:
    """Turn accountMedia ids into downloadable media dicts.

    Accessible items yield their ``media``; locked items fall back to their
    ``preview`` (whose id is also returned in the preview list). Items with
    neither a usable media nor preview URL are dropped.
    """
    by_id = {item["id"]: item for item in aggregation.get("accountMedia") or []}
    media: list[dict[str, Any]] = []
    previews: list[int] = []
    for account_media_id in account_media_ids:
        account_media = by_id.get(account_media_id)
        if not account_media:
            continue
        full = account_media.get("media")
        preview = account_media.get("preview")
        if _has_location(full):
            media.append(full)  # type: ignore[arg-type]
        elif _has_location(preview):
            media.append(preview)  # type: ignore[arg-type]
            previews.append(int(preview["id"]))  # type: ignore[index]
    return media, previews


def resolve_attachments(
    attachments: list[dict[str, Any]],
    aggregation: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[int]]:
    """Media for post/message attachments (single media and bundles, in order)."""
    bundles = {b["id"]: b for b in aggregation.get("accountMediaBundles") or []}
    account_media_ids: list[str] = []
    for attachment in sorted(attachments, key=lambda a: a.get("pos", 0)):
        content_id = attachment.get("contentId")
        match attachment.get("contentType"):
            case 1:  # accountMedia
                account_media_ids.append(content_id)  # type: ignore[arg-type]
            case 2:  # accountMediaBundle
                bundle = bundles.get(content_id)
                if not bundle:
                    continue
                content = bundle.get("bundleContent")
                if content:
                    ordered = sorted(content, key=lambda c: c.get("pos", 0))
                    account_media_ids.extend(c["accountMediaId"] for c in ordered)
                else:
                    account_media_ids.extend(bundle.get("accountMediaIds") or [])
            case _:
                # Tip goals, polls, story links and other non-media attachments.
                pass
    return resolve_account_media(account_media_ids, aggregation)


def from_timestamp(value: float | None) -> datetime | None:
    """Fansly mixes second and millisecond epochs; both become a datetime."""
    if value is None:
        return None
    seconds = value / 1000 if value > 10_000_000_000 else value
    return datetime.fromtimestamp(seconds)


class SiteContent:
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        self.id: int = int(option["id"])
        self.author = user
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.__raw__ = option

    def url_picker(self, media_item: dict[str, Any], video_quality: str = ""):
        quality = (
            video_quality
            or self.author.get_api().get_site_settings().media_quality.video
        )
        media_url = _pick_media_url(media_item, quality)
        return urlparse(media_url) if media_url is not None else None

    async def link_picker(self, media: dict[Any, Any], target_quality: str):
        return _pick_media_url(media, target_quality)

    def preview_url_picker(self, media_item: dict[str, Any]):
        return None

    def get_author(self):
        return self.author

    def get_content_type(self):
        content_type = self.get_author().get_api().convert_api_type_to_key(self)
        return content_type

    async def refresh(self):
        func = await self.author.scrape_manager.handle_refresh(self)
        return await func(self.id)
