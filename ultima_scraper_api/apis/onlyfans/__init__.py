from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, TypeAlias
from urllib.parse import ParseResult, urlparse


class SubscriptionTypeEnum(str, Enum):
    ALL = "all"
    ACTIVE = "active"
    EXPIRED = "expired"
    ATTENTION = "attention"


SubscriptionType: TypeAlias = (
    Literal[
        SubscriptionTypeEnum.ALL,
        SubscriptionTypeEnum.ACTIVE,
        SubscriptionTypeEnum.EXPIRED,
        SubscriptionTypeEnum.ATTENTION,
    ]
    | str
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.media_model import MediaModel
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


def url_picker(
    author: "UserModel",
    media_item: "MediaModel",
    video_quality: str = "",
) -> ParseResult | None:
    authed = author.get_authed()
    video_quality = (
        video_quality or author.get_api().get_site_settings().media_quality.video
    )

    if not media_item.canView:
        return

    source: dict[str, Any] = {}
    media_type = media_item.type

    # Handle legacy source format or new files format
    if media_item.source:
        source = media_item.source
    elif media_item.files and media_item.files.full:
        source = {
            "url": media_item.files.full.url,
            "width": media_item.files.full.width,
            "height": media_item.files.full.height,
        }
    else:
        return

    quality_key = "source"
    url = source.get(quality_key, source.get("url"))

    if media_type == "video":
        video_qualities = dict(sorted(media_item.videoSources.items(), reverse=False))
        for quality, quality_link in video_qualities.items():
            video_quality = video_quality.removesuffix("p")
            if quality == video_quality:
                if quality_link:
                    url = quality_link
                    break

    if authed.drm:
        # DRM handler still needs dict format
        has_drm = authed.drm.has_drm(media_item.to_dict())
        if has_drm:
            url = has_drm
    return urlparse(url) if url else None


def preview_url_picker(media_item: "MediaModel"):
    preview_url: str | None = None

    if media_item.files and media_item.files.preview:
        preview_url = media_item.files.preview.url
    else:
        # Fallback to raw dict for legacy "preview" field
        preview_url = media_item.__raw__.get("preview")

    return urlparse(preview_url) if preview_url else None


class SiteContent:
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        self.id: int = option["id"]
        self.author = user
        self.__raw__ = option
        self._proxy: str | None = None

    def url_picker(self, media_item: "MediaModel", video_quality: str = ""):
        return url_picker(self.get_author(), media_item, video_quality)

    def preview_url_picker(self, media_item: "MediaModel"):
        return preview_url_picker(media_item)

    def get_author(self):
        return self.author

    def get_content_type(self):
        content_type = self.get_author().get_api().convert_api_type_to_key(self)
        return content_type

    async def refresh(self):
        func = await self.author.scrape_manager.handle_refresh(self)
        return await func(self.id)
