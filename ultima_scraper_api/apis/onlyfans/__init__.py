from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import ParseResult, urlparse

SubscriptionType = Literal["all", "active", "expired", "attention"]

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


def url_picker(
    author: "UserModel", media_item: dict[str, Any], video_quality: str = ""
) -> ParseResult | None:
    authed = author.get_authed()
    video_quality = (
        video_quality or author.get_api().get_site_settings().media_quality.video
    )
    if not media_item["canView"]:
        return
    source: dict[str, Any] = {}
    media_type: str = ""
    video_qualities = media_item.get("videoSources", {})
    if "source" in media_item:
        media_type = media_item["type"]
        source = media_item["source"]
    elif "files" in media_item:
        media_type = media_item["type"]
        source = media_item["files"]["full"]
    else:
        return
    quality_key = "source"
    url = source.get(quality_key, source.get("url"))
    if media_type == "video":
        video_qualities = dict(sorted(video_qualities.items(), reverse=False))
        for quality, quality_link in video_qualities.items():
            video_quality = video_quality.removesuffix("p")
            if quality == video_quality:
                if quality_link:
                    url = quality_link
                    break
    if authed.drm:
        has_drm = authed.drm.has_drm(media_item)
        if has_drm:
            url = has_drm
    return urlparse(url) if url else None


def preview_url_picker(media_item: dict[str, Any]):
    preview_url: str | None = None
    if "files" in media_item:
        if "preview" in media_item["files"]:
            if (
                media_item["files"]["preview"] is not None
                and "url" in media_item["files"]["preview"]
            ):
                preview_url = media_item["files"]["preview"]["url"]
    else:
        preview_url = media_item["preview"]
        return urlparse(preview_url) if preview_url else None


class SiteContent:
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        self.id: int = option["id"]
        self.author = user
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.preview_ids: list[int] = []
        self.__raw__ = option
        self._proxy: str | None = None

    def url_picker(self, media_item: dict[str, Any], video_quality: str = ""):
        return url_picker(self.get_author(), media_item, video_quality)

    def preview_url_picker(self, media_item: dict[str, Any]):
        return preview_url_picker(media_item)

    def get_author(self):
        return self.author

    def get_content_type(self):
        content_type = self.get_author().get_api().convert_api_type_to_key(self)
        return content_type

    async def refresh(self):
        func = await self.author.scrape_manager.handle_refresh(self)
        return await func(self.id)
