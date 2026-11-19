from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, NamedTuple
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


PPV_PERMISSION = 1  # permissionFlags entry whose price unlocks the item


def _media_kind(mimetype: str) -> str:
    """The backend's media kind for a Fansly mimetype (HLS/DASH are video)."""
    if mimetype == "image/gif":
        return "gif"
    major = mimetype.split("/", 1)[0]
    if major in ("image", "audio"):
        return "photo" if major == "image" else "audio"
    return "video"


def _metadata(media: dict[str, Any]) -> dict[str, Any]:
    raw = media.get("metadata")
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def unlock_price(item: dict[str, Any]) -> float:
    """Dollars to unlock an accountMedia or bundle (prices are in thousandths)."""
    flags = (item.get("permissions") or {}).get("permissionFlags") or []
    prices = [
        flag.get("price") or 0
        for flag in flags
        if flag.get("flags") == PPV_PERMISSION
    ]
    return max([item.get("price") or 0, *prices]) / 1000


def is_unlocked(item: dict[str, Any]) -> bool:
    return bool(item.get("purchased") or item.get("access"))


class Media(dict[str, Any]):
    """A Fansly media dict, readable the way the backend reads media.

    The API's keys stay (the URL pickers read them), except ``type``, which
    becomes the backend's kind (photo/video/gif/audio); Fansly's own number is
    kept as ``fansly_type``. The attributes are the fields the backend reads
    with ``getattr``.
    """

    def __init__(
        self,
        media: dict[str, Any],
        account_media: dict[str, Any],
        *,
        is_preview: bool,
    ) -> None:
        super().__init__(media)
        self["fansly_type"] = media.get("type")
        self["type"] = _media_kind(media.get("mimetype") or "")
        self["created_at"] = from_timestamp(media.get("createdAt"))
        duration = _metadata(media).get("duration")
        if duration:
            self["duration"] = float(duration)
        # Everything kept here has a URL; a locked item is kept only through
        # its preview, which, like an OnlyFans free preview, can be viewed.
        self["canView"] = True
        self["preview"] = is_preview
        self["account_media_id"] = account_media.get("id")
        self["price"] = unlock_price(account_media)
        self["purchased"] = is_unlocked(account_media)

    @property
    def id(self) -> str:
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


class ResolvedMedia(NamedTuple):
    media: list[Media]
    previews: list[int]
    # Dollars to unlock everything referenced, and whether it all is unlocked.
    price: float
    bought: bool


def resolve_account_media(
    account_media_ids: list[str],
    aggregation: dict[str, Any],
    *,
    bundles: list[dict[str, Any]] | None = None,
) -> ResolvedMedia:
    """Turn accountMedia ids into downloadable media.

    Accessible items yield their ``media``; locked items fall back to their
    ``preview`` (whose id is also returned in the preview list). Items with
    neither a usable media nor preview URL are dropped, but still count
    towards the price. A priced ``bundle`` replaces its members' prices.
    """
    by_id = {item["id"]: item for item in aggregation.get("accountMedia") or []}
    media: list[Media] = []
    previews: list[int] = []
    priced: list[dict[str, Any]] = [b for b in bundles or [] if unlock_price(b)]
    in_priced_bundle = {
        member
        for bundle in priced
        for member in _bundle_members(bundle)
    }
    for account_media_id in account_media_ids:
        account_media = by_id.get(account_media_id)
        if not account_media:
            continue
        if account_media_id not in in_priced_bundle and unlock_price(account_media):
            priced.append(account_media)
        full = account_media.get("media")
        preview = account_media.get("preview")
        if _has_location(full):
            media.append(Media(full, account_media, is_preview=False))  # type: ignore[arg-type]
        elif _has_location(preview):
            media.append(Media(preview, account_media, is_preview=True))  # type: ignore[arg-type]
            previews.append(int(preview["id"]))  # type: ignore[index]
    price = sum(unlock_price(item) for item in priced)
    return ResolvedMedia(media, previews, price, all(is_unlocked(i) for i in priced))


def _bundle_members(bundle: dict[str, Any]) -> list[str]:
    content = bundle.get("bundleContent")
    if content:
        return [c["accountMediaId"] for c in sorted(content, key=lambda c: c.get("pos", 0))]
    return list(bundle.get("accountMediaIds") or [])


def resolve_attachments(
    attachments: list[dict[str, Any]],
    aggregation: dict[str, Any],
) -> ResolvedMedia:
    """Media for post/message attachments (single media and bundles, in order)."""
    bundles = {b["id"]: b for b in aggregation.get("accountMediaBundles") or []}
    account_media_ids: list[str] = []
    attached_bundles: list[dict[str, Any]] = []
    for attachment in sorted(attachments, key=lambda a: a.get("pos", 0)):
        content_id = attachment.get("contentId")
        match attachment.get("contentType"):
            case 1:  # accountMedia
                account_media_ids.append(content_id)  # type: ignore[arg-type]
            case 2:  # accountMediaBundle
                bundle = bundles.get(content_id)
                if not bundle:
                    continue
                attached_bundles.append(bundle)
                account_media_ids.extend(_bundle_members(bundle))
            case _:
                # Tip goals, polls, story links and other non-media attachments.
                pass
    return resolve_account_media(account_media_ids, aggregation, bundles=attached_bundles)


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
        self.media: list[Media] = []
        self.previews: list[int] = []
        self.preview: list[int] = []
        self.price: float = 0.0
        self._bought = True
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

    def _attach_media(self, resolved: ResolvedMedia) -> None:
        self.media = resolved.media
        self.previews = resolved.previews
        self.preview = resolved.previews
        # Fansly prices media, not posts: the content's price is what its
        # locked media cost together, in dollars.
        self.price = resolved.price
        self._bought = resolved.bought

    def is_bought(self) -> bool:
        """Whether every priced item here is purchased or otherwise unlocked."""
        return self._bought

    def get_content_type(self):
        content_type = self.get_author().get_api().convert_api_type_to_key(self)
        return content_type

    async def refresh(self):
        func = await self.author.scrape_manager.handle_refresh(self)
        return await func(self.id)
