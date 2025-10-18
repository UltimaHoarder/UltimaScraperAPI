from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


class VideoObject(TypedDict):
    poster: str
    uid: str
    duration: int
    mime: str
    views: int
    preview_option: str
    orientation: str
    size: dict[str, int]
    is_vr: bool
    vr_format: str | None
    vr_type: str | None
    video_vr: Any
    trailer_is_vr: bool
    trailer_vr_format: str | None
    trailer_vr_type: str | None


class ReactionSummary(TypedDict):
    type: str
    count: int


class Reactions(TypedDict):
    total: int
    summary: list[ReactionSummary]
    reactions: list[Any]
    users_uids: list[str]


class PostModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, option, user)
        self.uid: str = option["uid"]
        self.slug: str = option["slug"]
        self.short_url: str = option["short_url"]
        self.reactions: Reactions = option["reactions"]
        self.title: str = option.get("title", "")
        self.content: str = option.get("content", "")
        self.content_length: int = option.get("content_length", 0)
        self.hashtags: list[str] = option.get("hashtags", [])
        self.user_mentions: list[str] = option.get("user_mentions", [])
        self.original_content: str = option.get("original_content", "")
        self.birthday: bool = option.get("birthday", False)
        self.pinned: bool = option.get("pinned", False)
        self.created_at: datetime = datetime.fromisoformat(option["created_at"]["date"])
        self.updated_at: datetime = datetime.fromisoformat(option["updated_at"]["date"])
        self.expiring: Any = option.get("expiring")
        self.pinned_at: Any = option.get("pinned_at")
        self.comments_count: int = option["comments"]["total"]
        self.comments_disabled: bool = option["comments"]["disabled"]
        self.is_gif: bool = option.get("gif", False)
        self.is_photo: bool = option.get("photo", False)
        self.is_audio: bool = option.get("audio", False)
        self.is_video: bool = option.get("video", False)
        self.is_live: bool = option.get("is_live", False)
        self.been_live: bool = option.get("been_live", False)
        self.video_object: VideoObject | None = option.get("video_object")
        self.total_tips: int = option.get("total_tips", 0)
        self.privacy: dict[str, Any] = option["privacy"]
        self.price: float = option.get("price", 0.0)
        self.old_price: float | None = option.get("old_price")
        self.discount_expire_at: Any = option.get("discount_expire_at")
        self.discount_percent: int = option.get("discount_percent", 0)
        self.bookmarked: bool = option.get("bookmarked", False)
        self.post_type_label: str = option.get("post_type_label", "")
        self.is_bought: bool = option.get("is_bought", False)
        self.can_comment: bool = option.get("can_comment", False)
        self.can_like: bool = option.get("can_like", False)
        self.can_react: bool = option.get("can_react", True)
        self.can_delete: bool = option.get("can_delete", False)
        self.can_edit: bool = option.get("can_edit", False)
        self.can_report: bool = option.get("can_report", True)
        self.can_see: bool = option.get("can_see", False)
        self.can_buy: bool = option.get("can_buy", True)
        self.can_tip: bool = option.get("can_tip", True)
        self.image_placeholder: list[str] = option.get("image_placeholder", [])
        self.reacted: Any = option.get("reacted")
        self.blocked: bool = option.get("blocked", False)
        self.labels: list[str] = option.get("labels", [])

        # Store raw response
        self.__raw__ = option

    def get_author(self) -> "UserModel":
        """Returns the post author"""
        return self.author

    async def buy_ppv(self) -> dict[str, Any]:
        """Buy this post if it's PPV"""
        if not self.can_buy or not self.price:
            return {"error": "Post cannot be purchased"}

        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/purchase"
        result = (
            await self.get_author().get_requester().json_request(link, method="POST")
        )
        return result

    async def get_comments(self) -> list[dict[str, Any]]:
        """Get post comments"""
        if self.comments_disabled:
            return []

        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/comments"
        results = await self.get_author().get_requester().json_request(link)
        return results.get("comments", [])

    async def react(self, reaction_type: str) -> dict[str, Any]:
        """Add a reaction to the post"""
        if not self.can_react:
            return {"error": "Cannot react to post"}

        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/react"
        payload = {"type": reaction_type}
        result = (
            await self.get_author()
            .get_requester()
            .json_request(link, method="POST", payload=payload)
        )
        return result

    async def remove_reaction(self) -> dict[str, Any]:
        """Remove reaction from post"""
        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/react"
        result = (
            await self.get_author().get_requester().json_request(link, method="DELETE")
        )
        return result

    async def bookmark(self) -> dict[str, Any]:
        """Bookmark this post"""
        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/bookmark"
        result = (
            await self.get_author().get_requester().json_request(link, method="POST")
        )
        return result

    async def remove_bookmark(self) -> dict[str, Any]:
        """Remove bookmark from post"""
        link = f"https://www.loyalfans.com/api/v2/posts/{self.uid}/bookmark"
        result = (
            await self.get_author().get_requester().json_request(link, method="DELETE")
        )
        return result
