from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import (
    SiteContent,
    from_timestamp,
    resolve_attachments,
)
from ultima_scraper_api.apis.fansly.classes.comment_model import CommentModel
from ultima_scraper_api.apis.fansly.urls import APIRoutes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class PostModel(SiteContent):
    """A timeline post. ``aggregation`` is the response holding its accountMedia."""

    def __init__(
        self,
        option: dict[str, Any],
        user: UserModel,
        aggregation: dict[str, Any],
    ) -> None:
        SiteContent.__init__(self, option, user)
        self.author = user
        self.text: str = str(option.get("content") or "")
        self.rawText: str = self.text
        self.created_at: datetime = from_timestamp(option["createdAt"])  # type: ignore[assignment]
        self.expires_at: datetime | None = from_timestamp(option.get("expiresAt"))
        self.likes_count: int = option.get("likeCount", 0)
        self.commentsCount: int = option.get("replyCount", 0)
        self.reply_to: str | None = option.get("inReplyTo")
        self.wall_ids: list[str] = option.get("wallIds") or []
        self.linkedUsers: list[dict[str, Any]] = option.get("accountMentions") or []
        self.total_tip_amount: int = option.get("totalTipAmount", 0)
        self.attachments: list[dict[str, Any]] = option.get("attachments") or []
        self._attach_media(resolve_attachments(self.attachments, aggregation))
        self.comments: list[CommentModel] = []

    async def get_comments(self):
        if not self.commentsCount:
            return self.comments
        link = APIRoutes().post_replies(self.id)
        result = await self.author.get_requester().json_request(link)
        response: dict[str, Any] = result.get("response") or {}
        authed = self.author.get_authed()
        accounts = {x["id"]: x for x in response.get("accounts") or []}
        comments: list[CommentModel] = []
        for reply in response.get("posts") or []:
            account = accounts.get(reply["accountId"])
            if account:
                comments.append(CommentModel(reply, authed.resolve_user(account)))
        self.comments = comments
        return self.comments

    def get_previews(self):
        return [x for x in self.media if int(x["id"]) in self.previews]
