from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate
from ultima_scraper_api.apis.privacy.classes import message_model, post_model
from ultima_scraper_api.apis.privacy.urls import APIRoutes, Routes
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.managers.scrape_manager import (
    ScrapeManager,
    ScrapeProgressCallback,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.auth_model import PrivacyAuthModel
    from ultima_scraper_api.apis.privacy.classes.message_model import MessageModel
    from ultima_scraper_api.apis.privacy.classes.post_model import PostModel
    from ultima_scraper_api.apis.privacy.privacy import PrivacyAPI  # noqa: F401

# Page size the web client uses for profile timelines.
POST_PAGE = 10


def normalize_user(option: dict[str, Any]) -> dict[str, Any]:
    """One shape for the user objects the API returns.

    Post ``creator``: {aid, uid, nickname, profileName, avatarUrl, verified};
    chat ``recipient``: {id, name, profileName, avatar, isCreator, guid, ...};
    subscription ``creator``: {uid, handle}; ``me/context``: {profileName, ...}.
    """
    uid = option.get("uid") or option.get("id") or 0
    username = option.get("profileName") or option.get("handle") or ""
    return {
        **option,
        "uid": int(uid),
        "username": username,
        "name": option.get("nickname") or option.get("name") or username,
        "aid": (option.get("aid") or option.get("guid") or "").lower(),
        "avatar": option.get("avatarUrl") or option.get("avatar"),
        "verified": bool(option.get("verified") or option.get("isVerified")),
        "is_creator": bool(option.get("isCreator", option.get("aid") is not None)),
    }


class UserModel(StreamlinedUser["PrivacyAuthModel", "PrivacyAPI"]):
    """A Privacy profile, built from whichever user object the API returned."""

    def __init__(self, option: dict[str, Any], authed: PrivacyAuthModel) -> None:
        data = normalize_user(option)
        self.id: int = data["uid"]
        self.username: str = data["username"]
        self.name: str = data["name"]
        self.aid: str = data["aid"]
        self.avatar: str | None = data["avatar"]
        self.header: str | None = None
        self.verified: bool = data["verified"]
        self._is_performer: bool = data["is_creator"]
        self.join_date = None
        self.subscription_price = None
        self.active = True
        self.is_deleted = False
        if not authed.find_user(self.id):
            authed.add_user(self)
        self.scrape_manager = ScrapeManager[
            "PrivacyAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def merge(self, option: dict[str, Any]) -> None:
        """Fill fields a richer user object knows (e.g. a post creator's aid)."""
        data = normalize_user(option)
        self.username = self.username or data["username"]
        self.name = data["name"] if data["name"] != data["username"] else self.name
        self.aid = self.aid or data["aid"]
        self.avatar = data["avatar"] or self.avatar
        self.verified = self.verified or data["verified"]
        self._is_performer = self._is_performer or data["is_creator"]

    def get_username(self):
        return self.username

    def get_link(self):
        return Routes().profile(self.username)

    def is_authed_user(self):
        return self.id == self.get_authed().id

    def is_performer(self):
        return self._is_performer

    async def get_avatar(self):
        return self.avatar

    async def get_header(self):
        return self.header

    async def match_identifiers(self, identifiers: list[int | str]):
        return self.id in identifiers or self.username in identifiers

    async def if_scraped(self):
        return any(value for _, value in self.scrape_manager.scraped)

    # --- posts -------------------------------------------------------------------

    async def get_posts(
        self,
        limit: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[PostModel]:
        async with aclosing(
            self.iter_posts(limit=limit, on_progress=on_progress, job_id=job_id)
        ) as values:
            posts = [post async for post in values]
        self.scrape_manager.scraped.Posts = {post.id: post for post in posts}
        return posts

    async def iter_posts(
        self,
        limit: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        label: str = "",
        cache: bool = False,
    ) -> AsyncGenerator[PostModel, None]:
        """The profile timeline page by page, newest first; ``limit`` caps the total.

        Privacy has no archived posts, so any ``label`` yields nothing.
        """
        if label:
            return

        async def fetch(skip: int | None) -> tuple[list[PostModel], int | None]:
            start = skip or 0
            link = APIRoutes().profile_posts(self.username, skip=start, take=POST_PAGE)
            result = await self.get_requester().json_request(link)
            items = (result.get("items") or []) if isinstance(result, dict) else []
            posts = [post_model.PostModel(item, self) for item in items]
            return posts, (start + len(items) if len(items) == POST_PAGE else None)

        progress = ScrapeProgress(
            self, "Posts", job_id=job_id, total_items=limit, on_progress=on_progress
        )
        async with aclosing(paginate(fetch, max_items=limit, progress=progress)) as values:
            async for post in values:
                yield post

    async def get_post(self, identifier: str) -> PostModel | None:
        """One post by its uid (the UUID in its URL)."""
        result = await self.get_requester().json_request(APIRoutes().post(str(identifier)))
        item = result.get("item") if isinstance(result, dict) else None
        return post_model.PostModel(item, self) if item else None

    # --- messages ----------------------------------------------------------------

    async def get_messages(
        self,
        limit: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[MessageModel]:
        async with aclosing(
            self.iter_messages(max_items=limit, on_progress=on_progress, job_id=job_id)
        ) as values:
            messages = [message async for message in values]
        self.scrape_manager.scraped.Messages = {m.id: m for m in messages}
        return messages

    async def iter_messages(
        self,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        room_id: str | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[MessageModel, None]:
        """The chat with this user page by page, newest first.

        Pages go back by the oldest message's ``sentAt``. Unlocked chat images
        are resolved to their URLs here, since messages carry only their ids.
        """
        authed = self.get_authed()
        if self.is_authed_user():
            return
        if room_id is None:
            room_id = await authed.find_room_id(self)
        if room_id is None:
            return
        chat_room = room_id
        participants: list[int | str] = [authed.id, self.id]

        async def fetch(before: str | None) -> tuple[list[MessageModel], str | None]:
            link = APIRoutes().chat_messages(chat_room, participants, before)
            page: Any = await self.get_requester().json_request(link)
            if not isinstance(page, list) or not page:
                return [], None
            urls = await self._resolve_file_urls(page)
            messages = [message_model.MessageModel(raw, self, urls) for raw in page]
            return messages, page[-1].get("sentAt")

        progress = ScrapeProgress(
            self, "Messages", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        async with aclosing(paginate(fetch, max_items=max_items, progress=progress)) as values:
            async for message in values:
                yield message

    async def _resolve_file_urls(self, page: list[dict[str, Any]]) -> dict[str, str]:
        """mediaId -> URL for the unlocked images in a page of messages.

        Unlocked chat videos are not resolved: no account seen so far had one,
        so their route is unconfirmed.
        """
        urls: dict[str, str] = {}
        for raw in page:
            for file in raw.get("files") or []:
                media_id = file.get("mediaId")
                if not media_id or file.get("isLocked") or file.get("type") != "image":
                    continue
                url = await self._get_text(APIRoutes().chat_image(media_id))
                if url:
                    urls[media_id] = url
        return urls

    async def _get_text(self, link: str) -> str | None:
        # The image view route answers a JSON string as text/plain.
        response = await self.get_requester().request(link)
        if response is None or response.status != 200:
            return None
        text = await response.text()
        try:
            value = json.loads(text)
        except ValueError:
            value = text
        return value if isinstance(value, str) and value.startswith("http") else None
