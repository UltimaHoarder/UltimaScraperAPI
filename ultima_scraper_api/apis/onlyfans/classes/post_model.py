from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.comment_model import CommentModel
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.media_model import MediaModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class PostModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        SiteContent.__init__(self, option, user)
        self.responseType: str = option["responseType"]
        text: str = option.get("text", "")
        self.text = str(text or "")
        raw_text: str = option.get("rawText", "")
        self.rawText = str(raw_text or "")
        self.lockedText: bool = option.get("lockedText", False)
        self.isFavorite: bool = option.get("isFavorite", False)
        self.isReportedByMe: bool = option.get("isReportedByMe", False)
        self.canReport: bool = option.get("canReport", False)
        self.canDelete: bool = option.get("canDelete", False)
        self.canComment: bool = option.get("canComment", False)
        self.canEdit: bool = option.get("canEdit", False)
        self.isPinned: bool = option.get("isPinned", False)
        media_data: list[dict[str, Any]] = option.get("media", [])
        self.media: list[MediaModel] = [MediaModel(m) for m in media_data]
        self.favoritesCount: int = option.get("favoritesCount", 0)
        self.media_count: int = option.get("mediaCount", 0)
        self.isMediaReady: bool = option.get("isMediaReady", False)
        self.voting: dict[str, Any] = option.get("voting", {})
        self.isOpened: bool = option.get("isOpened", False)
        self.canToggleFavorite: bool = option.get("canToggleFavorite", False)
        self.streamId: int | None = option.get("streamId")
        self.price: float | None = option.get("price")
        self.hasVoting: bool = option.get("hasVoting", False)
        self.isAddedToBookmarks: bool = option.get("isAddedToBookmarks", False)
        self.isArchived: bool = option.get("isArchived", False)
        self.isDeleted: bool = option.get("isDeleted", False)
        self.hasUrl: bool = option.get("hasUrl", False)
        self.commentsCount: int = option.get("commentsCount", 0)
        self.mentionedUsers: list[dict[str, Any]] = option.get("mentionedUsers", [])
        self.linkedUsers: list[dict[str, Any]] = option.get("linkedUsers", [])
        self.linkedPosts: list[dict[str, Any]] = option.get("linkedPosts", [])
        self.canViewMedia: bool = option.get("canViewMedia", False)
        self.previews: list[int] = option.get("preview", [])
        self.canPurchase: bool = option.get("canPurchase", False)
        self.comments: list[CommentModel] = []
        self.fund_raising: dict[str, Any] | None = option.get("fundRaising")
        self.created_at: datetime = datetime.fromisoformat(option["postedAt"])
        self.postedAtPrecise: str = option["postedAtPrecise"]
        self.expiredAt: Any = option.get("expiredAt")
        user.scrape_manager.scraped.Posts[self.id] = self

    def get_author(self):
        return self.author

    async def buy_ppv(self):
        """
        This function will subscribe to a model. If the model has a promotion available, it will use it.
        """
        x: dict[str, Any] = {
            "paymentType": "post",
            "postId": self.id,
            "amount": self.price,
            "userId": self.author.id,
            "token": "",
            "unavailablePaymentGates": [],
        }

        authed = self.get_author().get_authed()
        assert authed.user.credit_balance != None
        if self.price and authed.user.credit_balance >= self.price:
            link = endpoint_links(identifier=self.id).pay
            result = (
                await self.get_author()
                .get_requester()
                .json_request(link, method="POST", payload=x)
            )
        else:
            result: dict[str, dict[str, int | str]] = {
                "error": {"code": 2011, "message": "Insufficient Credit Balance"}
            }
        return result

    async def get_comments(self):
        epl = endpoint_links()
        link = epl.list_comments(self.responseType, self.id)
        links = epl.create_links(link, self.commentsCount)
        if links:
            results: list[dict[str, Any]] = (
                await self.author.scrape_manager.bulk_scrape(links)
            )
            authed = self.author.get_authed()
            final_results = [
                CommentModel(x, authed.resolve_user(x["author"])) for x in results
            ]
            self.comments = final_results
        return self.comments

    async def favorite(self):
        link = endpoint_links(
            identifier=f"{self.responseType}s",
            identifier2=self.id,
            identifier3=self.author.id,
        ).favorite
        results = (
            await self.get_author().get_requester().json_request(link, method="POST")
        )
        self.isFavorite = True
        return results

    async def bought(self):
        return all(media.canView for media in self.media)

    def is_bought(self):
        return self.bought()

    def get_previews(self):
        return [x for x in self.media if x.id in self.previews]
