from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.comment_model import CommentModel
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user


class create_post(SiteContent):
    def __init__(self, option: dict[str, Any], user: create_user) -> None:
        SiteContent.__init__(self, option, user)
        self.responseType: str = option["responseType"]
        text: str = option.get("text", "")
        self.text = str(text or "")
        raw_text: str = option.get("rawText", "")
        self.rawText = str(raw_text or "")
        self.lockedText: bool = option["lockedText"]
        self.isFavorite: bool = option["isFavorite"]
        self.isReportedByMe: bool = option.get("isReportedByMe")
        self.canReport: bool = option["canReport"]
        self.canDelete: bool = option["canDelete"]
        self.canComment: bool = option["canComment"]
        self.canEdit: bool = option["canEdit"]
        self.isPinned: bool = option["isPinned"]
        self.favoritesCount: int = option["favoritesCount"]
        self.mediaCount: int = option.get("mediaCount", 0)
        self.isMediaReady: bool = option["isMediaReady"]
        self.voting: list = option["voting"]
        self.isOpened: bool = option["isOpened"]
        self.canToggleFavorite: bool = option["canToggleFavorite"]
        self.streamId: int | None = option.get("streamId")
        self.price: int | None = option.get("price")
        self.hasVoting: bool = option["hasVoting"]
        self.isAddedToBookmarks: bool = option["isAddedToBookmarks"]
        self.isArchived: bool = option["isArchived"]
        self.isDeleted: bool = option["isDeleted"]
        self.hasUrl: bool = option["hasUrl"]
        self.commentsCount: int = option["commentsCount"]
        self.mentionedUsers: list = option["mentionedUsers"]
        self.linkedUsers: list[dict[str, Any]] = option["linkedUsers"]
        self.linkedPosts: list[dict[str, Any]] = option["linkedPosts"]
        self.canViewMedia: bool = option["canViewMedia"]
        self.preview: list[int] = option.get("preview", [])
        self.canPurchase: bool = option.get("canPurchase")
        self.comments: list[CommentModel] = []
        self.created_at: datetime = datetime.fromisoformat(option["postedAt"])
        self.postedAtPrecise: str = option["postedAtPrecise"]
        self.expiredAt: Any = option.get("expiredAt")

    def get_author(self):
        return self.author

    async def get_comments(self):
        epl = endpoint_links()
        link = epl.list_comments(self.responseType, self.id)
        links = epl.create_links(link, self.commentsCount)
        if links:
            results: list[
                dict[str, Any]
            ] = await self.author.scrape_manager.bulk_scrape(links)
            authed = self.author.get_authed()
            final_results = [
                CommentModel(x, await authed.resolve_user(x["author"])) for x in results
            ]
            self.comments = final_results
        return self.comments

    async def favorite(self):
        link = endpoint_links(
            identifier=f"{self.responseType}s",
            identifier2=self.id,
            identifier3=self.author.id,
        ).favorite
        results = await self.author.get_session_manager().json_request(
            link, method="POST"
        )
        self.isFavorite = True
        return results
