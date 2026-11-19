from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.loyalfans import numbered_pages
from ultima_scraper_api.apis.loyalfans.classes import (
    message_model,
    post_model,
    story_model,
)
from ultima_scraper_api.apis.loyalfans.urls import APIRoutes, Routes
from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id
from ultima_scraper_api.managers.scrape_manager import (
    ScrapeManager,
    ScrapeProgressCallback,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
    from ultima_scraper_api.apis.loyalfans.classes.message_model import MessageModel
    from ultima_scraper_api.apis.loyalfans.classes.post_model import PostModel
    from ultima_scraper_api.apis.loyalfans.classes.story_model import (
        HighlightModel,
        StoryModel,
    )
    from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI  # noqa: F401

# Page sizes: the web client asks for 4 timeline posts, 18 store videos and
# 12 highlights at a time; larger timeline pages are served the same way.
POST_PAGE = 20
STORE_PAGE = 18
HIGHLIGHT_PAGE = 12


def split_user(option: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(user, extras): a profile's ``data`` and the ``me`` response nest the
    user under "user" beside profile/counters/prices; post owners, chat
    partners and list members are bare users."""
    nested = option.get("user")
    if isinstance(nested, dict):
        return nested, option
    return option, {}


class UserModel(StreamlinedUser["LoyalFansAuthModel", "LoyalFansAPI"]):
    """A LoyalFans user, built from whichever user object the API returned."""

    def __init__(self, option: dict[str, Any], authed: LoyalFansAuthModel) -> None:
        user, extras = split_user(option)
        # LoyalFans ids are opaque strings; ``id`` is the archive's int key.
        self.uid: str = str(user.get("uid") or 0)
        self.id: int = native_id_to_db_id(self.uid)
        self.username: str = user.get("slug") or f"u{self.uid}"
        self.name: str = user.get("display_name") or user.get("name") or self.username
        self.user_type: str = user.get("user_type") or ""
        self.avatar: str | None = None
        self.header: str | None = None
        self.about: str = ""
        self.twitter: str | None = None
        self.subscription_price: float | None = None
        self.counters: dict[str, Any] = {}
        self.has_story = False
        self.has_highlights = False
        # True once a full profile (GET /profile/star/{slug}) has been merged.
        self.profile_loaded = False
        self.join_date: str | None = None
        self.active = True
        self.is_deleted = False
        self._apply(user, extras)
        if not authed.find_user(self.id):
            authed.add_user(self)
        self.download_info: dict[str, Any] = {}
        self.duplicate_media: list[Any] = []
        self.scrape_manager = ScrapeManager[
            "LoyalFansAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def _apply(self, user: dict[str, Any], extras: dict[str, Any]) -> None:
        photo = user.get("profile_photo")
        if isinstance(photo, dict):
            self.avatar = (photo.get("images") or {}).get("original") or self.avatar
        cover = user.get("cover_photo")
        if isinstance(cover, dict):
            self.header = cover.get("url_original") or cover.get("url") or self.header
        created = user.get("created_at")
        if isinstance(created, dict):
            self.join_date = created.get("date") or self.join_date
        profile = extras.get("profile")
        if isinstance(profile, dict):
            self.profile_loaded = True
            self.about = profile.get("description") or self.about
            self.twitter = profile.get("twitter") or self.twitter
        prices = extras.get("prices")
        if isinstance(prices, dict) and isinstance(prices.get("subscription_price"), dict):
            self.subscription_price = prices["subscription_price"].get("value")
        if isinstance(extras.get("counters"), dict):
            self.counters = extras["counters"]
        self.has_story = bool(extras.get("hasStory", self.has_story))
        self.has_highlights = bool(extras.get("hasHighlights", self.has_highlights))

    def merge(self, option: dict[str, Any]) -> None:
        """Fill fields a richer user object knows (e.g. a full profile)."""
        user, extras = split_user(option)
        self.username = user.get("slug") or self.username
        self.name = user.get("display_name") or user.get("name") or self.name
        self.user_type = user.get("user_type") or self.user_type
        self._apply(user, extras)
        if extras:
            self.__raw__ = option

    def get_username(self) -> str:
        return self.username

    def get_link(self, use_username: bool = False) -> str:
        if use_username:
            return Routes().profile(self.username)
        return Routes().profile_by_uid(self.uid)

    def is_authed_user(self) -> bool:
        return self.id == self.get_authed().id

    def is_performer(self) -> bool:
        return self.user_type == "model"

    async def get_avatar(self) -> str | None:
        return self.avatar

    async def get_header(self) -> str | None:
        return self.header

    async def match_identifiers(self, identifiers: list[int | str]) -> bool:
        return any(value in identifiers for value in (self.id, self.uid, self.username))

    async def if_scraped(self):
        return any(value for _, value in self.scrape_manager.scraped)

    async def get_socials(self) -> list[dict[str, Any]]:
        """The profile's linked accounts (LoyalFans profiles show only X/Twitter)."""
        if not self.twitter:
            return []
        url = self.twitter if "://" in self.twitter else f"https://{self.twitter}"
        handle = url.rstrip("/").rsplit("/", 1)[-1]
        return [{"socialMedia": "Twitter", "username": handle, "url": url}]

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
        store: bool = True,
        cache: bool = False,
    ) -> AsyncGenerator[PostModel, None]:
        """The timeline newest first, then the video store; ``limit`` caps the total.

        Store videos are posts that never appear on the timeline. The first
        timeline page can carry a promoted free post that later pages repeat,
        so posts are deduplicated by uid. LoyalFans has no archived posts, so
        any ``label`` yields nothing.
        """
        if label:
            return
        authed = self.get_authed()

        async def timeline(page: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            link = APIRoutes().timeline(self.username, limit=POST_PAGE, page=page)
            result = await authed.call(link)
            return result.get("timeline") or [], result.get("page_meta") or {}

        async def store_page(page: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            body = {"slug": self.username, "type": "video", "limit": STORE_PAGE, "page": page}
            result = await authed.call(APIRoutes().videos_store(), body)
            return result.get("list") or [], result.get("page_meta") or {}

        progress = ScrapeProgress(
            self, "Posts", job_id=job_id, total_items=limit, on_progress=on_progress
        )
        seen: set[str] = set()
        for source in [timeline, store_page] if store else [timeline]:
            async with aclosing(numbered_pages(source, progress=progress)) as values:
                async for raw in values:
                    if limit is not None and len(seen) >= limit:
                        return
                    if raw["uid"] in seen:
                        continue
                    seen.add(raw["uid"])
                    yield post_model.PostModel(raw, self)

    async def get_post(self, identifier: str) -> PostModel | None:
        """One post by its slug (the end of its URL) or uid."""
        result = await self.get_authed().call(APIRoutes().post(str(identifier)))
        item = result.get("post")
        return post_model.PostModel(item, self) if isinstance(item, dict) else None

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
        """The conversation with this user, newest first.

        Older pages follow the response's ``mid_token``; the last page has none.
        """
        if self.is_authed_user():
            return
        authed = self.get_authed()

        async def fetch(token: str | None) -> tuple[list[MessageModel], str | None]:
            result = await authed.call(APIRoutes().conversation(self.uid, token))
            raw = result.get("messages") or []
            messages = [message_model.MessageModel(item, self) for item in raw]
            return messages, (result.get("mid_token") or None) if raw else None

        progress = ScrapeProgress(
            self, "Messages", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        async with aclosing(paginate(fetch, max_items=max_items, progress=progress)) as values:
            async for message in values:
                yield message

    # --- stories and highlights ------------------------------------------------------

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
        """The creator's live stories (POST /stories {slug}), oldest first."""
        result = await self.get_authed().call(APIRoutes().stories(), {"slug": self.username})
        progress = ScrapeProgress(
            self, "Stories", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        count = 0
        for group in result.get("list") or []:
            for raw in group if isinstance(group, list) else [group]:
                owner = raw.get("owner") or {}
                if owner.get("uid") not in (None, self.uid):
                    continue
                if max_items is not None and count >= max_items:
                    break
                count += 1
                yield story_model.StoryModel(raw, self)
        await progress.page(1, count, False)

    async def get_highlights(self) -> list[HighlightModel]:
        """The creator's highlights, each with its stories."""

        async def page(number: int) -> tuple[list[HighlightModel], dict[str, Any]]:
            body = {"slug": self.username, "page": number, "limit": HIGHLIGHT_PAGE}
            result = await self.get_authed().call(APIRoutes().highlights(), body)
            items = [story_model.HighlightModel(raw, self) for raw in result.get("list") or []]
            return items, result.get("pagination") or result.get("page_meta") or {}

        async with aclosing(numbered_pages(page)) as values:
            return [highlight async for highlight in values]

    async def iter_highlight_stories(
        self,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[StoryModel, None]:
        """Every story kept in a highlight, once each (a story can sit in several)."""
        seen: set[str] = set()
        count = 0
        for highlight in await self.get_highlights():
            for story in highlight.stories:
                if story.uid in seen:
                    continue
                if max_items is not None and count >= max_items:
                    return
                seen.add(story.uid)
                count += 1
                yield story
        progress = ScrapeProgress(
            self, "Highlights", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        await progress.page(1, count, False)

