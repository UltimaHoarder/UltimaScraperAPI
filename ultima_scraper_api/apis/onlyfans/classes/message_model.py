from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import MassMessageModel
from ultima_scraper_api.apis.onlyfans.classes.media_model import MediaModel
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class MessageModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        author = user.get_authed().resolve_user(option["fromUser"])
        assert author, "Author not found"
        SiteContent.__init__(self, option, author)
        self.user = user
        self.responseType: str = option.get("responseType", "message")
        self.text: str = option.get("text", "")
        self.lockedText: Optional[bool] = option.get("lockedText")
        self.isFree: Optional[bool] = option.get("isFree")
        self.price: int | None = option.get("price")
        self.isMediaReady: Optional[bool] = option.get("isMediaReady")
        self.media_count: Optional[int] = option.get("mediaCount")
        media_data: list[dict[str, Any]] = option.get("media", [])
        self.media: list[MediaModel] = [MediaModel(m, self) for m in media_data]
        self.previews: list[int] = option.get("previews", [])
        self.isTip: Optional[bool] = option.get("isTip")
        self.isReportedByMe: Optional[bool] = option.get("isReportedByMe")
        self.is_from_queue: bool | None = option.get("isFromQueue")
        self.queue_id: Optional[int] = option.get("queueId")
        self.canUnsendQueue: Optional[bool] = option.get("canUnsendQueue")
        self.unsendSecondsQueue: Optional[int] = option.get("unsendSecondsQueue")
        self.isOpened: Optional[bool] = option.get("isOpened")
        self.isNew: Optional[bool] = option.get("isNew")
        self.cancelSeconds: Optional[int] = option.get("cancelSeconds")
        self.isLiked: Optional[bool] = option.get("isLiked")
        self.canPurchase: Optional[bool] = option.get("canPurchase")
        self.canPurchaseReason: Optional[str] = option.get("canPurchaseReason")
        self.canReport: Optional[bool] = option.get("canReport")
        self.expiredAt: Any = option.get("expiredAt")
        self.created_at: datetime = datetime.fromisoformat(option["createdAt"])
        self.changedAt: Optional[str] = option.get("changedAt")
        author.scrape_manager.scraped.Messages[self.id] = self
        if self.is_mass_message():
            MassMessageModel(option, self.author)

    def get_author(self):
        return self.author

    def get_receiver(self):
        receiver = (
            self.author.get_authed() if self.author.id == self.user.id else self.user
        )
        return receiver

    async def buy_message(
        self, browser_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Buy a ppv message from a model.

        Args:
            browser_data: Optional browser data dict with keys:
                - browserLanguage (str): Language code, e.g. "en-GB"
                - browserColorDepth (str): Color depth, e.g. "24"
                - browserScreenHeight (int): Screen height in pixels
                - browserScreenWidth (int): Screen width in pixels
                - timeZone (str): Timezone offset, e.g. "0"

        Returns:
            Response dict from the API. Check for "error" key to determine success.
            On success, consider calling create_scrape_download_job() to download content.
        """
        message_price = self.price

        # Use provided browser data or defaults
        if browser_data is None:
            browser_data = {
                "browserLanguage": "en-US",
                "browserColorDepth": "24",
                "browserScreenHeight": 1920,
                "browserScreenWidth": 1080,
                "timeZone": "0",
            }

        x: dict[str, float | int | str | list[Any] | None | bool | dict[str, Any]] = {
            "amount": message_price,
            "browserData": browser_data,
            "internalOnly": True,
            "messageId": self.id,
            "paymentType": "message",
            "token": "",
            "unavailablePaymentGates": [],
            "userId": self.user.id,
        }
        authed = self.get_author().get_authed()
        assert authed.user.credit_balance is not None
        assert message_price is not None
        link = endpoint_links().pay
        response = (
            await self.get_author().get_requester().request(link, method="POST", json=x)
        )
        assert response is not None, "No response from buy_message request"
        result = await response.json()
        return result

    def get_scrape_job_params(self) -> dict[str, Any]:
        """
        Get parameters needed to create a scrape+download job for this message's author.

        Returns a dict with keys:
            - site: "OnlyFans"
            - auth_id: Authenticated user's ID
            - user_id: Message author's user ID
            - username: Message author's username

        This can be passed to the backend's _create_scrape_download_job() function
        to automatically download all content (messages + mass messages) from this creator.
        """
        authed = self.get_author().get_authed()
        return {
            "site": "onlyfans",
            "auth_id": authed.user.id,
            "user_id": self.author.id,
            "username": self.author.name,
        }

    async def like_message(self) -> dict[str, Any]:
        """Toggle like/unlike on this message.

        Uses POST to like (when not currently liked) and DELETE to unlike
        (when currently liked).

        Returns:
            Response dict from the API. Check for "error" key to determine failure.
        """
        url = APIRoutes().like("messages", self.id)
        method = "DELETE" if self.isLiked else "POST"
        response = (
            await self.get_author()
            .get_requester()
            .request(url, method=method, json={"withUserId": self.user.id})
        )
        assert response is not None, "No response from like_message request"
        result = await response.json()
        # Update local state based on toggle
        if "error" not in result:
            self.isLiked = not self.isLiked
        return result

    def is_mass_message(self):
        if self.is_from_queue:
            return True
        return False

    def is_bought(self):
        if self.price and self.price > 0:
            return all(media.canView for media in self.media)
        return False

    def get_previews(self):
        return [x for x in self.media if x.id in self.previews]
