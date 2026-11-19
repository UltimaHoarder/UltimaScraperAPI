from __future__ import annotations

from contextlib import aclosing
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.loyalfans import SiteContent, parse_time, post_media
from ultima_scraper_api.apis.loyalfans.urls import APIRoutes, Routes
from ultima_scraper_api.apis.pagination import paginate

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


class PostModel(SiteContent):
    """A timeline post (social/timeline, social/post) or a video store item."""

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        SiteContent.__init__(self, str(option["uid"]), user)
        self.__raw__ = option
        self.slug: str = option.get("slug") or ""
        self.short_url: str | None = option.get("short_url")
        self.title: str = option.get("title") or ""
        self.text: str = option.get("original_content") or option.get("content") or ""
        self.created_at: datetime | None = parse_time(option.get("created_at"))
        self.updated_at: datetime | None = parse_time(option.get("updated_at"))
        self.is_pinned: bool = bool(option.get("pinned"))
        self.price = float(option.get("price") or 0)
        self.old_price: float | None = option.get("old_price")
        self.purchased: bool = bool(option.get("is_bought"))
        self.can_see: bool = bool(option.get("can_see"))
        self.post_type: str = option.get("post_type_label") or ""
        self.labels: list[Any] = option.get("labels") or []
        self.privacy: dict[str, Any] = option.get("privacy") or {}
        comments = option.get("comments")
        comments = comments if isinstance(comments, dict) else {}
        self.comments_count: int = int(comments.get("total") or 0)
        self.comments_disabled: bool = bool(comments.get("disabled"))
        self.media = post_media(option, self.created_at)
        self.comments: list[dict[str, Any]] = []

    def is_bought(self) -> bool:
        return self.purchased or self.can_see

    def get_link(self) -> str:
        return Routes().post(self.author.username, self.slug)

    async def get_comments(self) -> list[dict[str, Any]]:
        """All top-level comments (POST /api/v1/comments, by ``page_token``)."""
        if self.comments_disabled or not self.comments_count:
            return self.comments
        authed = self.author.get_authed()

        async def fetch(token: str | None) -> tuple[list[dict[str, Any]], str | None]:
            body: dict[str, Any] = {"uid": self.uid}
            if token:
                body["page_token"] = token
            result = await authed.call(APIRoutes().comments(), body)
            comments = result.get("comments") or []
            return comments, (result.get("page_token") or None) if comments else None

        async with aclosing(paginate(fetch)) as values:
            self.comments = [comment async for comment in values]
        return self.comments
