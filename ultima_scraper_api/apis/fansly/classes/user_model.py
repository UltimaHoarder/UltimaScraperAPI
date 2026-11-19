from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import from_timestamp
from ultima_scraper_api.apis.fansly.classes import (
    collection_model,
    message_model,
    post_model,
)
from ultima_scraper_api.apis.fansly.classes.extras import ErrorDetails
from ultima_scraper_api.apis.fansly.classes.story_model import StoryModel
from ultima_scraper_api.apis.fansly.urls import APIRoutes
from ultima_scraper_api.apis.pagination import ScrapeProgress, paginate
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.managers.scrape_manager import (
    ScrapeManager,
    ScrapeProgressCallback,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
    from ultima_scraper_api.apis.fansly.classes.message_model import MessageModel
    from ultima_scraper_api.apis.fansly.classes.post_model import PostModel

# Page sizes the web client uses.
MESSAGE_PAGE = 25
ALBUM_PAGE = 25

# profileSocials providerId -> (site, profile URL prefix), from the web client.
SOCIAL_PROVIDERS: dict[str, tuple[str, str]] = {
    "1": ("Twitter", "https://x.com/"),
    "3": ("Twitch", "https://twitch.tv/"),
    "4": ("Instagram", "https://instagram.com/"),
    "5": ("TikTok", "https://tiktok.com/@"),
    "6": ("YouTube", "https://youtube.com/@"),
    "8": ("Bluesky", "https://bsky.app/profile/"),
    "9": ("Fleshlight", ""),
}


def _media_url(media: dict[str, Any] | None) -> str | None:
    if not media:
        return None
    for item in [media, *(media.get("variants") or [])]:
        for location in item.get("locations") or []:
            if location.get("location"):
                return location["location"]
    return None


class UserModel(StreamlinedUser["FanslyAuthModel", "FanslyAPI"]):
    """A Fansly account (GET /account, /account/me)."""

    def __init__(self, option: dict[str, Any], authed: FanslyAuthModel) -> None:
        self.id: int = int(option.get("id", 0))
        self.is_deleted: bool = bool(option.get("isDeleted"))
        self.username: str = option.get("username") or (
            f"u{self.id}" if self.is_deleted else ""
        )
        self.name: str = option.get("displayName") or self.username
        self.about: str = option.get("about") or ""
        self.location: str = option.get("location") or ""
        self.avatar: dict[str, Any] | None = option.get("avatar")
        self.header: dict[str, Any] | None = option.get("banner")
        self.join_date: datetime | None = from_timestamp(option.get("createdAt"))
        self.last_seen: datetime | None = from_timestamp(option.get("lastSeenAt"))
        self.flags: int = option.get("flags", 0)
        self.followers_count: int = option.get("followCount", 0)
        self.subscribers_count: int = option.get("subscriberCount", 0)
        timeline_stats = option.get("timelineStats") or {}
        self.photos_count: int = timeline_stats.get("imageCount", 0)
        self.videos_count: int = timeline_stats.get("videoCount", 0)
        self.bundles_count: int = timeline_stats.get("bundleCount", 0)
        self.medias_count: int = self.photos_count + self.videos_count
        self.posts_count: int = 0
        self.archived_posts_count: int = 0
        self.audios_count: int = 0
        self.post_likes: int = option.get("postLikes", 0)
        self.favorited_count: int = option.get("accountMediaLikes", 0)
        self.walls: list[dict[str, Any]] = option.get("walls") or []
        self.pinned_posts: list[dict[str, Any]] = option.get("pinnedPosts") or []
        self.subscription_bundles: list[dict[str, Any]] = (
            option.get("subscriptionTiers") or []
        )
        self.socials: list[dict[str, Any]] = option.get("profileSocials") or []
        story_state = option.get("mediaStoryState") or {}
        self.has_stories: bool = bool(story_state.get("hasActiveStories"))
        self.streaming: dict[str, Any] | None = option.get("streaming")
        self.following: bool = bool(option.get("following"))
        # Present when the authed account is subscribed to this one.
        self.subscribed_by_data: dict[str, Any] | None = option.get("subscription")
        self.subscribed: bool = self.subscribed_by_data is not None
        self.profile_access: bool = bool(option.get("profileAccess", True))
        # Only on /account/me.
        self.email: str | None = option.get("email")
        main_wallet = option.get("mainWallet") or {}
        self.credit_balance: float = (main_wallet.get("balance") or 0) / 1000
        self.is_blocked: bool = False
        self.active = True
        self._is_performer: bool = bool(self.subscription_bundles)
        self.ws_url: str = "wss://wsv3.fansly.com/?v=3"
        if not authed.find_user(self.id):
            authed.add_user(self)
        self.download_info: dict[str, Any] = {}
        self.duplicate_media = []
        self.scrape_manager = ScrapeManager[
            "FanslyAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def get_username(self):
        return self.username

    def get_link(self):
        return f"https://fansly.com/{self.username}"

    def is_authed_user(self):
        return self.id == self.get_authed().id

    def is_performer(self):
        return self._is_performer

    async def subscription_price(self):
        """Cheapest tier price in dollars (tier prices are in thousandths)."""
        prices = [tier["price"] for tier in self.subscription_bundles if "price" in tier]
        return min(prices) / 1000 if prices else None

    async def get_avatar(self):
        return _media_url(self.avatar)

    async def get_header(self):
        return _media_url(self.header)

    async def match_identifiers(self, identifiers: list[int | str]):
        return self.id in identifiers or self.username in identifiers

    async def if_scraped(self):
        return any(value for _, value in self.scrape_manager.scraped)

    async def get_socials(self) -> list[dict[str, Any]]:
        """The profile's social handles, in the backend's social payload shape."""
        socials: list[dict[str, Any]] = []
        for entry in self.socials:
            handle = entry.get("handle")
            if not handle:
                continue
            provider = str(entry.get("providerId"))
            site, prefix = SOCIAL_PROVIDERS.get(provider, (f"provider {provider}", ""))
            social = {"socialMedia": site, "username": handle, "providerId": provider}
            if prefix:
                social["url"] = prefix + handle
            socials.append(social)
        return socials

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
        """Active stories; Fansly returns them in one response."""

        async def fetch(_cursor: int | None) -> tuple[list[StoryModel], int | None]:
            result = await self.get_requester().json_request(APIRoutes().stories(self.id))
            response = result.get("response") or {}
            aggregation = response.get("aggregationData") or response
            stories = response.get("mediaStories") or []
            return [StoryModel(story, self, aggregation) for story in stories], None

        progress = ScrapeProgress(self, "Stories", job_id=job_id, on_progress=on_progress)
        async with aclosing(paginate(fetch, max_items=max_items, progress=progress)) as values:
            async for story in values:
                yield story

    async def get_posts(
        self,
        limit: int | None = None,
        wall_id: int | str = "",
        before: int | str = 0,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[PostModel]:
        """Collect the timeline newest-first; ``before`` = the oldest post id seen."""
        async with aclosing(
            self.iter_posts(
                limit=limit,
                wall_id=wall_id,
                before=before,
                on_progress=on_progress,
                job_id=job_id,
            )
        ) as values:
            posts = [post async for post in values]
        self.scrape_manager.scraped.Posts = {post.id: post for post in posts}
        return posts

    async def iter_posts(
        self,
        limit: int | None = None,
        wall_id: int | str = "",
        before: int | str = 0,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        label: str = "",
        cache: bool = False,
    ) -> AsyncGenerator[PostModel, None]:
        """The timeline page by page, newest first; ``limit`` caps the total.

        Fansly has no archived posts, so any ``label`` yields nothing.
        """
        if label:
            return

        async def fetch(cursor: int | str | None) -> tuple[list[PostModel], int | str | None]:
            while True:
                link = APIRoutes().timeline(self.id, before=cursor or 0, wall_id=wall_id)
                result = await self.get_requester().json_request(link)
                response = result.get("response") or {}
                page = response.get("posts") or []
                if not page:
                    return [], None
                posts = [
                    post_model.PostModel(raw, self, response)
                    for raw in page
                    # Timelines can include other accounts' posts (reposts).
                    if int(raw["accountId"]) == self.id
                ]
                next_cursor = page[-1]["id"]
                if posts or next_cursor == cursor:
                    return posts, next_cursor
                # A page of only reposts: keep going rather than end paging.
                cursor = next_cursor

        progress = ScrapeProgress(
            self, "Posts", job_id=job_id, total_items=limit, on_progress=on_progress
        )
        async with aclosing(
            paginate(fetch, first_cursor=before or None, max_items=limit, progress=progress)
        ) as values:
            async for post in values:
                yield post

    async def get_post(self, identifier: int | str) -> PostModel | ErrorDetails | None:
        link = APIRoutes().posts([identifier])
        result = await self.get_requester().json_request(link)
        if "error" in result:
            return ErrorDetails(result)
        response = result.get("response") or {}
        for raw in response.get("posts") or []:
            if int(raw["id"]) == int(identifier):
                return post_model.PostModel(raw, self, response)
        return None

    async def get_messages(
        self,
        limit: int | None = None,
        offset_id: int | None = None,
        cutoff_id: int | None = None,
        group_id: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[MessageModel]:
        """Collect this user's DM history newest-first; ``limit`` caps the total."""
        async with aclosing(
            self.iter_messages(
                offset_id=offset_id,
                cutoff_id=cutoff_id,
                on_progress=on_progress,
                job_id=job_id,
                max_items=limit,
                group_id=group_id,
            )
        ) as values:
            messages = [message async for message in values]
        self.scrape_manager.scraped.Messages = {m.id: m for m in messages}
        return messages

    async def iter_messages(
        self,
        limit: int = MESSAGE_PAGE,
        offset_id: int | None = None,
        cutoff_id: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        group_id: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[MessageModel, None]:
        """This user's DM history page by page, newest first.

        ``limit`` is the page size and ``max_items`` the total, as on OnlyFans.
        Starts below ``offset_id`` when given and stops at ``cutoff_id``
        (exclusive), e.g. the newest message already stored.
        """
        if limit <= 0:
            raise ValueError("Message page size must be positive")
        if self.is_authed_user():
            return
        if group_id is None:
            group_id = await self.get_authed().find_chat_group_id(self)
        if group_id is None:
            return
        chat_id = group_id

        async def fetch(cursor: int | None) -> tuple[list[MessageModel], int | None]:
            link = APIRoutes().list_messages(chat_id, before=cursor or 0, limit=limit)
            result = await self.get_requester().json_request(link)
            response = result.get("response") or {}
            page = response.get("messages") or []
            kept = page
            if cutoff_id is not None:
                kept = [raw for raw in page if int(raw["id"]) > cutoff_id]
            messages = [message_model.MessageModel(raw, self, response) for raw in kept]
            more = len(page) == limit and len(kept) == len(page)
            return messages, (int(page[-1]["id"]) if more else None)

        progress = ScrapeProgress(
            self, "Messages", job_id=job_id, total_items=max_items, on_progress=on_progress
        )
        async with aclosing(
            paginate(fetch, first_cursor=offset_id, max_items=max_items, progress=progress)
        ) as values:
            async for message in values:
                yield message

    async def get_message_by_id(
        self, message_id: int | str, group_id: int | None = None
    ) -> MessageModel | None:
        """One message of this chat: the first page entry before ``message_id + 1``.

        The API has no working single-message route (/message/{id} is 404,
        /messages?ids= is 400), so this pages the group from just above it.
        """
        if group_id is None:
            group_id = await self.get_authed().find_chat_group_id(self)
        if group_id is None:
            return None
        link = APIRoutes().list_messages(group_id, before=int(message_id) + 1, limit=1)
        result = await self.get_requester().json_request(link)
        response = result.get("response") or {}
        for raw in response.get("messages") or []:
            if int(raw["id"]) == int(message_id):
                return message_model.MessageModel(raw, self, response)
        return None

    async def get_collections(self) -> list[dict[str, Any]]:
        """Vault albums the account shares (GET /uservault/albumsnew)."""
        link = APIRoutes().vault_albums(self.id)
        result = await self.get_requester().json_request(link)
        response = result.get("response") or {}
        return response.get("albums") or []

    async def get_collection_content(self, collection: dict[str, Any]):
        pages: list[dict[str, Any]] = []
        cursor: int | str = 0
        while True:
            link = APIRoutes().vault_album_content(
                collection["id"], before=cursor, limit=ALBUM_PAGE
            )
            result = await self.get_requester().json_request(link)
            response = result.get("response") or {}
            album_content = response.get("albumContent") or []
            if not album_content:
                break
            pages.append(response)
            if len(album_content) < ALBUM_PAGE:
                break
            cursor = album_content[-1]["id"]
        merged: dict[str, Any] = {"albumContent": [], "aggregationData": {}}
        for page in pages:
            merged["albumContent"].extend(page.get("albumContent") or [])
            for key, value in (page.get("aggregationData") or {}).items():
                if isinstance(value, list):
                    merged["aggregationData"].setdefault(key, []).extend(value)
        return collection_model.CollectionModel(collection, self, merged)
