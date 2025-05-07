from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from ultima_scraper_api.apis.fansly import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class MessageModel(SiteContent):
    def __init__(
        self, option: dict[str, Any], user: UserModel, extra: dict[Any, Any] = {}
    ) -> None:
        author = user.get_authed().resolve_user(option["senderId"])
        self.user = user
        SiteContent.__init__(self, option, author)
        self.responseType: Optional[str] = option.get("responseType")
        self.text: str = option["content"]
        self.lockedText: Optional[bool] = option.get("lockedText")
        self.isFree: Optional[bool] = option.get("isFree")
        self.price: int | None = option.get("price")
        self.isMediaReady: Optional[bool] = option.get("isMediaReady")
        self.media_count: Optional[int] = option.get("mediaCount")
        self.media: list[Any] = option.get("attachments", [])
        self.previews: list[dict[str, Any]] = option.get("previews", [])
        self.isTip: Optional[bool] = option.get("isTip")
        self.isReportedByMe: Optional[bool] = option.get("isReportedByMe")
        self.fromUser = user.get_authed().resolve_user(option["senderId"])
        self.isFromQueue: Optional[bool] = option.get("isFromQueue")
        self.queue_id: Optional[int] = option.get("queueId")
        self.canUnsendQueue: Optional[bool] = option.get("canUnsendQueue")
        self.unsendSecondsQueue: Optional[int] = option.get("unsendSecondsQueue")
        self.isOpened: Optional[bool] = option.get("isOpened")
        self.isNew: Optional[bool] = option.get("isNew")
        self.created_at: datetime = datetime.fromtimestamp(option["createdAt"])
        self.changedAt: Optional[str] = option.get("changedAt")
        self.cancelSeconds: Optional[int] = option.get("cancelSeconds")
        self.isLiked: Optional[bool] = option.get("isLiked")
        self.canPurchase: Optional[bool] = option.get("canPurchase")
        self.canPurchaseReason: Optional[str] = option.get("canPurchaseReason")
        self.canReport: Optional[bool] = option.get("canReport")
        self.attachments: list[dict[str, Any]] = option.get("attachments", {})
        # Custom
        final_media_ids: list[Any] = []
        for attachment in self.attachments:
            attachment_content_id = attachment["contentId"]
            match attachment["contentType"]:
                case 1:
                    final_media_ids.append(attachment_content_id)
                case 2:
                    for bundle in extra.get("accountMediaBundles", []):
                        if bundle["id"] == attachment_content_id:
                            final_media_ids.extend(bundle["accountMediaIds"])
                case 32001:
                    pass
                case _:
                    pass
        final_media: list[Any] = []
        if final_media_ids and extra:
            for final_media_id in final_media_ids:
                for account_media in extra.get("accountMedia", []):
                    if account_media["id"] == final_media_id:
                        temp_media = None
                        if "preview" in account_media:
                            temp_media = account_media["preview"]
                            self.previews.append(temp_media)
                        if (
                            account_media["media"]["locations"]
                            or account_media["media"]["variants"]
                        ):
                            temp_media = account_media["media"]
                        if temp_media:
                            final_media.append(temp_media)
        self.media = final_media
        self.user = user

    def get_author(self):
        return self.author

    def get_receiver(self):
        receiver = (
            self.author.get_authed() if self.author.id == self.user.id else self.user
        )
        return receiver

    async def link_picker(self, media: dict[Any, Any], target_quality: str):
        # There are two media results at play here.
        # The top-level `media` element itself represents the original source quality.
        # It may also contain a `variants` list entry with alternate encoding qualities.
        # Each variant has a similar structure to the main media element.
        media_url = ""
        source_media = media
        variants = media.get("variants", [])

        if target_quality == "source":
            try:
                return source_media["locations"][0]["location"]
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
            if target_quality == "source":
                return media_url

            # Return the first media <= the target quality.
            if media_quality <= int(target_quality):
                return media_url

        # If all media was > target quality, return the lowest quality/last media.
        return media_url
