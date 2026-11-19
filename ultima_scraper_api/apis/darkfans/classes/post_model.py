from __future__ import annotations

from contextlib import aclosing
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import (
    SiteContent,
    attributes,
    files_media,
    numbered_pages,
    parse_time,
    price_of,
)
from ultima_scraper_api.apis.darkfans.urls import APIRoutes, Routes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel

COMMENT_PAGE = 50


class PostModel(SiteContent):
    """A post (GET /user/{id}/posts, /post/{id}, /timeline).

    ``post_type`` is free, subscribers, ppv or auction. ``files`` is filled
    only once the post is viewable; a locked post counts its files in
    ``fileInfo`` but names none, so it has no media until unlocked.
    """

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        SiteContent.__init__(self, str(option["id"]), user)
        self.__raw__ = option
        self.title: str = option.get("title") or ""
        self.text: str = option.get("text") or ""
        self.created_at: datetime | None = parse_time(option.get("createdAt"))
        self.scheduled_at: datetime | None = parse_time(option.get("scheduledAt"))
        self.post_type: str = option.get("type") or ""
        self.status: str = option.get("status") or ""
        self.price = price_of(option.get("price"))
        self.purchased: bool = bool(option.get("purchasedByUser"))
        self.subscribed: bool = bool(option.get("subscribedByUser"))
        self.is_pinned: bool = option.get("pinPosition") is not None
        self.likes: int = int(option.get("likes") or 0)
        self.comments_count: int = int(option.get("nbComments") or 0)
        self.file_info: list[dict[str, Any]] = option.get("fileInfo") or []
        self.media = files_media(option.get("files"), self.created_at)
        self.comments: list[dict[str, Any]] = []

    def is_bought(self) -> bool:
        return self.purchased or bool(self.media) or not self.file_info

    def get_link(self) -> str:
        return Routes().post(self.uid)

    async def get_comments(self) -> list[dict[str, Any]]:
        """All comments ({id, userId, username, comment, createdAt})."""
        if not self.comments_count:
            return self.comments
        authed = self.author.get_authed()

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            link = APIRoutes().post_comments(self.uid, page=number, per_page=COMMENT_PAGE)
            result = await authed.call(link)
            return result.get("data") or [], result.get("meta") or {}

        async with aclosing(numbered_pages(page, per_page=COMMENT_PAGE)) as values:
            self.comments = [attributes(comment) async for comment in values]
        return self.comments
