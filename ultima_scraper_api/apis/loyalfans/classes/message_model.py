from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


class MessageModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, option, user)

        # Basic message info
        self.uid: str = option["uid"]
        self.content: str = option.get("content", "")
        self.created_at: datetime = datetime.fromisoformat(option["created_at"]["date"])
        self.updated_at: datetime = datetime.fromisoformat(option["updated_at"]["date"])

        # Media attachments
        self.is_gif: bool = option.get("gif", False)
        self.is_photo: bool = option.get("photo", False)
        self.is_audio: bool = option.get("audio", False)
        self.is_video: bool = option.get("video", False)
        self.video_object: dict[str, Any] | None = option.get("video_object")
        self.media_count: int = option.get("media_count", 0)
        self.media: list[dict[str, Any]] = option.get("media", [])

        # Privacy & permissions
        self.privacy: dict[str, Any] = option.get("privacy", {})
        self.price: float = option.get("price", 0.0)
        self.is_bought: bool = option.get("is_bought", False)
        self.can_buy: bool = option.get("can_buy", True)
        self.can_reply: bool = option.get("can_reply", False)
        self.can_delete: bool = option.get("can_delete", False)
        self.can_report: bool = option.get("can_report", True)
        self.can_tip: bool = option.get("can_tip", True)
        self.blocked: bool = option.get("blocked", False)

        # Reactions
        self.reactions: dict[str, Any] = option.get(
            "reactions", {"total": 0, "summary": [], "reactions": [], "users_uids": []}
        )
        self.reacted: Any = option.get("reacted")

        # Store raw response
        self.__raw__ = option
        user.scrape_manager.scraped.Messages[self.id] = self

    def get_author(self) -> "UserModel":
        """Returns the message author"""
        return self.author

    def get_receiver(self) -> "UserModel":
        """Returns the message recipient"""
        receiver = (
            self.author.get_authed() if self.author.id == self.user.id else self.user
        )
        return receiver

    async def buy_ppv(self) -> dict[str, Any]:
        """Buy this message if it's PPV"""
        if not self.can_buy or not self.price:
            return {"error": "Message cannot be purchased"}

        link = f"https://www.loyalfans.com/api/v2/messages/{self.uid}/purchase"
        result = (
            await self.get_author().get_requester().json_request(link, method="POST")
        )
        return result

    async def react(self, reaction_type: str) -> dict[str, Any]:
        """Add a reaction to the message"""
        link = f"https://www.loyalfans.com/api/v2/messages/{self.uid}/react"
        payload = {"type": reaction_type}
        result = (
            await self.get_author()
            .get_requester()
            .json_request(link, method="POST", payload=payload)
        )
        return result

    async def remove_reaction(self) -> dict[str, Any]:
        """Remove reaction from message"""
        link = f"https://www.loyalfans.com/api/v2/messages/{self.uid}/react"
        result = (
            await self.get_author().get_requester().json_request(link, method="DELETE")
        )
        return result

    async def delete(self) -> dict[str, Any]:
        """Delete this message"""
        if not self.can_delete:
            return {"error": "Cannot delete message"}

        link = f"https://www.loyalfans.com/api/v2/messages/{self.uid}"
        result = (
            await self.get_author().get_requester().json_request(link, method="DELETE")
        )
        return result

    async def report(self, reason: str) -> dict[str, Any]:
        """Report this message"""
        if not self.can_report:
            return {"error": "Cannot report message"}

        link = f"https://www.loyalfans.com/api/v2/messages/{self.uid}/report"
        payload = {"reason": reason}
        result = (
            await self.get_author()
            .get_requester()
            .json_request(link, method="POST", payload=payload)
        )
        return result
