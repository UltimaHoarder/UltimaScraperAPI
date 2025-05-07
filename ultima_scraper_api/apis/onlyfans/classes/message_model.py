from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import MassMessageModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class MessageModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        author = user.get_authed().resolve_user(option["fromUser"])
        assert author, "Author not found"
        SiteContent.__init__(self, option, author)
        self.user = user
        self.responseType: Optional[str] = option.get("responseType")
        self.text: str = option.get("text", "")
        self.lockedText: Optional[bool] = option.get("lockedText")
        self.isFree: Optional[bool] = option.get("isFree")
        self.price: int | None = option.get("price")
        self.isMediaReady: Optional[bool] = option.get("isMediaReady")
        self.media_count: Optional[int] = option.get("mediaCount")
        self.media: list[dict[str, Any]] = option.get("media", [])
        self.previews: list[dict[str, Any]] = option.get("previews", [])
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
        self.created_at: datetime = datetime.fromisoformat(option["createdAt"])
        self.changedAt: Optional[str] = option.get("changedAt")
        author.scrape_manager.scraped.Messages[self.id] = self
        if self.is_mass_message():
            MassMessageModel(option, self.user)

    def get_author(self):
        return self.author

    def get_receiver(self):
        receiver = (
            self.author.get_authed() if self.author.id == self.user.id else self.user
        )
        return receiver

    async def buy_message(self):
        """
        This function will buy a ppv message from a model.
        """
        message_price = self.price
        x: dict[str, float | int | str | list[Any] | None] = {
            "amount": message_price,
            "messageId": self.id,
            "paymentType": "message",
            "token": "",
            "unavailablePaymentGates": [],
        }
        authed = self.get_author().get_authed()
        assert authed.user.credit_balance != None
        link = endpoint_links().pay
        result = (
            await self.get_author()
            .get_requester()
            .json_request(link, method="POST", payload=x)
        )
        return result

    def is_mass_message(self):
        if self.is_from_queue:
            return True
        return False
