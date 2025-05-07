from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import SiteContent
from ultima_scraper_api.apis.fansly.classes.comment_model import CommentModel
from ultima_scraper_api.apis.fansly.classes.extras import endpoint_links

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class PostModel(SiteContent):
    def __init__(
        self,
        option: dict[str, Any],
        user: UserModel,
        extra: dict[str, Any],
    ) -> None:
        SiteContent.__init__(self, option, user)
        self.responseType: str = option.get("responseType")
        self.author = user
        text: str = option.get("content", "")
        self.text = str(text or "")
        raw_text: str = option.get("rawText", "")
        self.rawText = str(raw_text or "")
        self.lockedText: bool = option.get("lockedText")
        self.isFavorite: bool = option.get("isFavorite")
        self.isReportedByMe: bool = option.get("isReportedByMe")
        self.canReport: bool = option.get("canReport")
        self.canDelete: bool = option.get("canDelete")
        self.canComment: bool = option.get("canComment")
        self.canEdit: bool = option.get("canEdit")
        self.isPinned: bool = option.get("isPinned")
        self.favoritesCount: int = option.get("favoritesCount")
        self.media_count: int = option.get("mediaCount")
        self.isMediaReady: bool = option.get("isMediaReady")
        self.voting: list = option.get("voting")
        self.isOpened: bool = option.get("isOpened")
        self.canToggleFavorite: bool = option.get("canToggleFavorite")
        self.streamId: Any = option.get("streamId")
        self.price: int | None = option.get("price")
        self.hasVoting: bool = option.get("hasVoting")
        self.isAddedToBookmarks: bool = option.get("isAddedToBookmarks")
        self.isArchived: bool = option.get("isArchived")
        self.isDeleted: bool = option.get("isDeleted")
        self.hasUrl: bool = option.get("hasUrl")
        self.commentsCount: int = option.get("replyCount")
        self.mentionedUsers: list = option.get("mentionedUsers")
        self.linkedUsers: list[dict[str, Any]] = option["accountMentions"]
        self.previews: list[dict[str, Any]] = option.get("previews", [])
        self.attachments: list[dict[str, Any]] = option.get("attachments", {})
        self.comments: list[CommentModel] = []
        self.created_at: datetime = datetime.fromtimestamp(option["createdAt"])
        self.postedAtPrecise: str = option.get("postedAtPrecise")
        self.expiredAt: Any = option.get("expiredAt")

        # Custom
        final_media_ids: list[Any] = []
        for attachment in self.attachments:
            attachment_content_id = attachment["contentId"]
            match attachment["contentType"]:
                case 1:
                    final_media_ids.append(attachment_content_id)
                case 2:
                    for bundle in extra["accountMediaBundles"]:
                        if bundle["id"] == attachment_content_id:
                            final_media_ids.extend(bundle["accountMediaIds"])
                case 32001:
                    pass
                case _:
                    pass
        final_media: list[Any] = []
        if final_media_ids:
            for final_media_id in final_media_ids:
                for account_media in extra["accountMedia"]:
                    if account_media["id"] == final_media_id:
                        temp_media = None
                        if "preview" in account_media:
                            temp_media = account_media["preview"]
                            if not account_media["access"]:
                                self.preview_ids.append(int(account_media["previewId"]))
                                self.previews.append(temp_media)
                        if account_media["media"]["locations"]:
                            temp_media = account_media["media"]
                        if temp_media:
                            final_media.append(temp_media)
        self.media: list[Any] = final_media
        self.canViewMedia: bool = option.get("canViewMedia")
        self.preview: list[int] = option.get("preview", [])
        self.canPurchase: bool = option.get("canPurchase")

    def get_author(self):
        return self.author

    async def get_comments(self):
        if not self.commentsCount:
            return
        epl = endpoint_links("post", self.id)
        link = epl.list_comments_api
        result: list[dict[str, Any]] = await self.author.scrape_manager.scrape(link)
        response: dict[str, Any] = result["response"]
        authed = self.author.get_authed()
        final_results = [
            CommentModel(
                x,
                await authed.resolve_user(
                    [y for y in response["accounts"] if y["id"] == x["accountId"]][0]
                ),
            )
            for x in response["posts"]
        ]
        self.comments = final_results
        return self.comments

    async def favorite(self):
        link = endpoint_links(
            identifier=f"{self.responseType}s",
            identifier2=self.id,
            identifier3=self.author.id,
        ).favorite
        results = await self.user.get_requester().json_request(link, method="POST")
        self.isFavorite = True
        return results

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
