from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import attributes, numbered_pages, parse_time
from ultima_scraper_api.apis.darkfans.classes import (
    message_model,
    post_model,
    story_model,
)
from ultima_scraper_api.apis.darkfans.urls import APIRoutes, Routes
from ultima_scraper_api.apis.pagination import ScrapeProgress
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id
from ultima_scraper_api.managers.scrape_manager import (
    ScrapeManager,
    ScrapeProgressCallback,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.auth_model import DarkFansAuthModel
    from ultima_scraper_api.apis.darkfans.classes.message_model import MessageModel
    from ultima_scraper_api.apis.darkfans.classes.post_model import PostModel
    from ultima_scraper_api.apis.darkfans.classes.story_model import StoryModel
    from ultima_scraper_api.apis.darkfans.darkfans import DarkFansAPI  # noqa: F401

# Page sizes: the web client asks for 15; the API serves up to 50.
POST_PAGE = 50
MESSAGE_PAGE = 50
STORY_PAGE = 50


class UserModel(StreamlinedUser["DarkFansAuthModel", "DarkFansAPI"]):
    """A DarkFans user, built from any user object the API returned."""

    def __init__(self, option: dict[str, Any], authed: DarkFansAuthModel) -> None:
        user = attributes(option)
        # DarkFans ids are UUIDs; ``id`` is the archive's int key.
        self.uid: str = str(user.get("id") or 0)
        self.id: int = native_id_to_db_id(self.uid)
        self.username: str = user.get("username") or f"u{self.uid}"
        self.name: str = user.get("displayName") or self.username
        self.avatar: str | None = None
        self.header: str | None = None
        self.about: str = ""
        self.creator = False
        self.counts: dict[str, Any] = {}
        self.stories_count = 0
        self.currency: str | None = None
        self.join_date = None
        # True once a full user object (GET /user/{id} or /username/{name}) is merged.
        self.profile_loaded = False
        self.active = True
        self.is_deleted = False
        self._apply(user)
        if not authed.find_user(self.id):
            authed.add_user(self)
        self.download_info: dict[str, Any] = {}
        self.duplicate_media: list[Any] = []
        self.scrape_manager = ScrapeManager[
            "DarkFansAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def _apply(self, user: dict[str, Any]) -> None:
        self.avatar = user.get("avatar") or self.avatar
        self.header = user.get("header") or self.header
        self.about = user.get("about") or self.about
        self.creator = bool(user.get("creator", self.creator))
        self.currency = user.get("currency") or self.currency
        self.join_date = parse_time(user.get("createdAt")) or self.join_date
        for key in ("nbVideos", "nbImages", "nbLikes", "followersCount", "subscribersCount"):
            if user.get(key) is not None:
                self.counts[key] = user[key]
        if user.get("nbStories") is not None:
            self.stories_count = int(user["nbStories"] or 0)
        # Full user objects carry "type" and "roles"/"online"; members of
        # subscription rows carry only a few fields.
        if "createdAt" in user and "about" in user:
            self.profile_loaded = True

    def merge(self, option: dict[str, Any]) -> None:
        """Fill fields a richer user object knows (e.g. a full profile)."""
        user = attributes(option)
        self.username = user.get("username") or self.username
        self.name = user.get("displayName") or self.name
        self._apply(user)
        if self.profile_loaded:
            self.__raw__ = option

    def get_username(self) -> str:
        return self.username

    def get_link(self, use_username: bool = True) -> str:
        return Routes().profile(self.username)

    def is_authed_user(self) -> bool:
        return self.id == self.get_authed().id

    def is_performer(self) -> bool:
        return self.creator

    async def get_avatar(self) -> str | None:
        return self.avatar

    async def get_header(self) -> str | None:
        return self.header

    async def match_identifiers(self, identifiers: list[int | str]) -> bool:
        return any(value in identifiers for value in (self.id, self.uid, self.username))

    async def if_scraped(self):
        return any(value for _, value in self.scrape_manager.scraped)

    # --- posts -----------------------------------------------------------------------

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
        post_type: str | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[PostModel, None]:
        """All the creator's posts newest first; ``post_type`` narrows them to
        one profile tab (free, subscribers, ppv, purchased). DarkFans has no
        archived posts, so any ``label`` yields nothing."""
        if label:
            return
        authed = self.get_authed()

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            link = APIRoutes().posts(self.uid, page=number, per_page=POST_PAGE, post_type=post_type)
            result = await authed.call(link)
            return result.get("data") or [], result.get("meta") or {}

        progress = ScrapeProgress(
            self, "Posts", job_id=job_id, total_items=limit, on_progress=on_progress
        )
        seen: set[str] = set()
        async with aclosing(
            numbered_pages(page, per_page=POST_PAGE, max_items=limit, progress=progress)
        ) as values:
            async for raw in values:
                post = post_model.PostModel(attributes(raw), self)
                if post.uid in seen:
                    continue
                seen.add(post.uid)
                yield post

    async def get_post(self, identifier: str) -> PostModel | None:
        """One post by its UUID (the end of its /site/post/ URL)."""
        result = await self.get_authed().call(APIRoutes().post(str(identifier)))
        item = attributes(result.get("data"))
        if not item.get("id"):
            return None
        return post_model.PostModel(item, self)

    # --- messages --------------------------------------------------------------------

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
        cache: bool = False,
    ) -> AsyncGenerator[MessageModel, None]:
        """The chat with this user, newest first (none when there is no chat)."""
        if self.is_authed_user():
            return
        authed = self.get_authed()
        chat_id = await authed.find_chat_id(self)
        if not chat_id:
            return

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            link = APIRoutes().chat_messages(authed.user.uid, chat_id, page=number, per_page=MESSAGE_PAGE)
            result = await authed.call(link)
            return result.get("data") or [], result.get("meta") or {}

        progress = ScrapeProgress(
            self, "Messages", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        seen: set[str] = set()
        async with aclosing(
            numbered_pages(page, per_page=MESSAGE_PAGE, max_items=max_items, progress=progress)
        ) as values:
            async for raw in values:
                if not isinstance(raw, dict) or not raw.get("uuid") or raw["uuid"] in seen:
                    continue
                seen.add(raw["uuid"])
                yield message_model.MessageModel(raw, self)

    # --- stories ---------------------------------------------------------------------

    async def _iter_story_list(
        self,
        *,
        pinned: bool,
        label: str,
        on_progress: ScrapeProgressCallback | None,
        job_id: str | None,
        max_items: int | None,
    ) -> AsyncGenerator[StoryModel, None]:
        authed = self.get_authed()

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            result = await authed.call(APIRoutes().stories(self.uid, page=number, per_page=STORY_PAGE))
            return result.get("data") or [], result.get("meta") or {}

        progress = ScrapeProgress(
            self, label, job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        count = 0
        async with aclosing(numbered_pages(page, per_page=STORY_PAGE, progress=progress)) as values:
            async for raw in values:
                story = story_model.StoryModel(attributes(raw), self)
                if story.pinned is not pinned:
                    continue
                if max_items is not None and count >= max_items:
                    return
                count += 1
                yield story

    async def get_stories(
        self,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[StoryModel]:
        async with aclosing(
            self.iter_stories(on_progress=on_progress, job_id=job_id)
        ) as values:
            stories = [story async for story in values]
        self.scrape_manager.scraped.Stories = {story.id: story for story in stories}
        return stories

    async def iter_stories(
        self,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[StoryModel, None]:
        """The creator's live (unpinned) stories."""
        async with aclosing(
            self._iter_story_list(
                pinned=False, label="Stories", on_progress=on_progress, job_id=job_id, max_items=max_items
            )
        ) as values:
            async for story in values:
                yield story

    async def iter_highlight_stories(
        self,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[StoryModel, None]:
        """Stories the creator pinned to the profile (DarkFans' highlights)."""
        async with aclosing(
            self._iter_story_list(
                pinned=True, label="Highlights", on_progress=on_progress, job_id=job_id, max_items=max_items
            )
        ) as values:
            async for story in values:
                yield story
