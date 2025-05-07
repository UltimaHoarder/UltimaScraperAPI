from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel

SubscriptionType = Literal["all", "active", "expired"]


class SiteContent:
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        self.id: int = int(option["id"])
        self.author = user
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.preview_ids: list[int] = []
        self.__raw__ = option

    def url_picker(self, media_item: dict[str, Any], video_quality: str = ""):
        # There are two media results at play here.
        # The top-level `media` element itself represents the original source quality.
        # It may also contain a `variants` list entry with alternate encoding qualities.
        # Each variant has a similar structure to the main media element.
        video_quality = (
            video_quality
            or self.author.get_api().get_site_settings().media_quality.video
        )
        media_url = ""
        source_media = media_item
        variants = media_item.get("variants", [])
        quality_key = "source"

        if quality_key == "source":
            try:
                url_string: str = source_media["locations"][0]["location"]
                return urlparse(url_string)
            except (KeyError, IndexError):
                pass

        # Track the target type as videos may also include thumbnail image variants.
        target_type = source_media.get("mimetype")

        qualities: list[tuple[int, str]] = []
        for variant in variants + [source_media]:
            if variant.get("mimetype") != target_type:
                continue

            media_quality = variant["height"]
            try:
                media_url = variant["locations"][0]["location"]
            except (KeyError, IndexError):
                continue
            qualities.append((media_quality, media_url))

        if not qualities:
            return

        # Iterate the media from highest to lowest quality.
        for media_quality, media_url in sorted(qualities, reverse=True):
            # If there was no "source" quality media, return the highest quality/first media.
            if quality_key == "source":
                return urlparse(media_url)

            # Return the first media <= the target quality.
            if media_quality <= int(quality_key):
                return urlparse(media_url)

        # If all media was > target quality, return the lowest quality/last media.
        return urlparse(media_url)

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
