from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import (
        create_auth,
        create_user,
    )


class SiteContent:
    def __init__(self, option: dict[str, Any], user: create_auth | create_user) -> None:
        self.id: int = option["id"]
        self.author = user
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.preview_ids:list[int] = []


    def url_picker(self, media_item: dict[str, Any], video_quality: str = ""):
        video_quality = (
            video_quality or self.author.get_api().get_site_settings().video_quality
        )
        if not media_item["canView"]:
            return
        source: dict[str, Any] = {}
        media_type: str = ""
        if "source" in media_item:
            media_type = media_item["type"]
            source = media_item["source"]
            video_qualities = media_item["videoSources"]
        elif "files" in media_item:
            media_type = media_item["type"]
            media_item = media_item["files"]
            source = media_item["source"]
            video_qualities = source["sources"]
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
        if "src" in media_item:
            url = media_item["src"]
        return urlparse(url) if url else None
        
    def preview_url_picker(self, media_item: dict[str, Any]):
        if "files" in media_item:
            if (
                "preview" in media_item["files"]
                and "url" in media_item["files"]["preview"]
            ):
                preview_url = media_item["files"]["preview"]["url"]
        else:
            preview_url = media_item["preview"]
        return urlparse(preview_url) if preview_url else None

    def get_author(self):
        return self.author

    async def refresh(self):
        func = await self.author.scrape_manager.handle_refresh(self)
        return await func(self.id)
