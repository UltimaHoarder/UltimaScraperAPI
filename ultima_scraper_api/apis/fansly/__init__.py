from __future__ import annotations

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
