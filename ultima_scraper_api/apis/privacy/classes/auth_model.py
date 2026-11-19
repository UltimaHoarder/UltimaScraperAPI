from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.pagination import paginate
from ultima_scraper_api.apis.privacy.classes.chat_model import ChatModel
from ultima_scraper_api.apis.privacy.classes.subscription_model import SubscriptionModel
from ultima_scraper_api.apis.privacy.classes.user_model import UserModel
from ultima_scraper_api.apis.privacy.urls import APIRoutes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM
    from ultima_scraper_api.apis.privacy.authenticator import PrivacyAuthenticator

    # Named in StreamlinedAuth's string type arguments below.
    from ultima_scraper_api.apis.privacy.classes.extras import AuthDetails  # noqa: F401
    from ultima_scraper_api.apis.privacy.privacy import PrivacyAPI  # noqa: F401


def _page_items(result: Any, key: str) -> list[dict[str, Any]]:
    return (result.get(key) or []) if isinstance(result, dict) else []


async def _pages(
    fetch_page, *, max_items: int | None, identity
) -> AsyncGenerator[Any, None]:
    """Page-numbered lists (page=1, 2, ...) until a page is empty or repeats.

    The page size is the server's, so a short page does not prove the end;
    a page of only already-seen entries does.
    """
    seen: set[Any] = set()

    async def fetch(page: int | None) -> tuple[list[Any], int | None]:
        number = page or 1
        items = await fetch_page(number)
        fresh = [item for item in items if identity(item) not in seen]
        seen.update(identity(item) for item in fresh)
        return fresh, (number + 1 if fresh else None)

    async with aclosing(paginate(fetch, max_items=max_items)) as values:
        async for value in values:
            yield value


class PrivacyAuthModel(StreamlinedAuth["PrivacyAuthenticator", "PrivacyAPI", "AuthDetails"]):
    def __init__(self, authenticator: PrivacyAuthenticator) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.subscriptions: list[SubscriptionModel] = []
        self.chats: list[ChatModel] | None = None
        self.rooms: dict[int, str] = {}
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        # Privacy videos are AES-128 HLS, not Widevine; kept for the shared path.
        self.drm: OnlyDRM | None = None
        self.update()

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int) or str(identifier).isdigit():
            return self.users.get(int(identifier))
        lowered = str(identifier).lower()
        for user in self.users.values():
            if user.username.lower() == lowered:
                return user
        return None

    def resolve_user(self, user_dict: dict[str, Any]) -> UserModel:
        uid = user_dict.get("uid") or user_dict.get("id")
        user = self.find_user(int(uid)) if uid else None
        if user is None:
            return UserModel(user_dict, self)
        user.merge(user_dict)
        return user

    def get_pool(self):
        return self.api.pool

    def update(self):
        if self.user:
            self.id = self.user.id
            self.username = self.user.username
            self.get_auth_details().id = self.id

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    async def get_authed_user(self):
        return self.user

    async def get_me(self):
        """The signed-in account again (GET /profile/users/me/context)."""
        context = await self.get_requester().json_request(APIRoutes().me_context())
        if not isinstance(context, dict) or "error" in context:
            return None
        self.user.merge({**context, "uid": self.id})
        self.update()
        return self.user

    async def get_id(self):
        return self.user.id

    async def get_username(self):
        return self.user.get_username()

    async def match_identifiers(self, identifiers: list[int | str]):
        return self.id in identifiers or self.username in identifiers

    async def get_user(self, identifier: int | str, refresh: bool = False):
        """A profile by name, from its newest post's creator.

        Privacy has no profile route the API can call (pages render it), so a
        profile is read off its posts; numeric ids resolve only from users
        already seen (subscriptions, chats, posts).
        """
        if not refresh:
            cached = self.find_user(identifier)
            if cached:
                return cached
        if isinstance(identifier, int) or str(identifier).isdigit():
            return self.find_user(identifier)
        name = str(identifier)
        requester = self.get_requester()
        for link in (
            APIRoutes().profile_posts(name, skip=0, take=1),
            APIRoutes().public_profile_posts(name, skip=0, take=1),
        ):
            result: Any = await requester.json_request(link)
            items = result if isinstance(result, list) else _page_items(result, "items")
            if items and items[0].get("creator"):
                return self.resolve_user(items[0]["creator"])
        return None

    async def get_subscriptions(
        self,
        identifiers: list[int | str] | None = None,
        refresh: bool = True,
        limit: int | None = None,
        sub_type: str = "all",
        filter_by: str = "",
        job_id: str | None = None,
    ) -> list[SubscriptionModel]:
        """Subscriptions from /subscriptionmanager/subscriptions/active, all pages."""
        if not refresh and self.subscriptions:
            return self.subscriptions
        requester = self.get_requester()

        async def page(number: int) -> list[dict[str, Any]]:
            link = APIRoutes().subscriptions(page=number)
            return _page_items(await requester.json_request(link), "items")

        subscriptions: list[SubscriptionModel] = []
        async with aclosing(
            _pages(page, max_items=None, identity=lambda raw: raw["creator"]["uid"])
        ) as values:
            async for raw in values:
                user = self.resolve_user(raw["creator"])
                subscriptions.append(SubscriptionModel(raw, user, self))
        if identifiers:
            wanted = {str(x).lower() for x in identifiers}
            subscriptions = [
                s
                for s in subscriptions
                if str(s.user.id) in wanted or s.user.username.lower() in wanted
            ]
        if sub_type == "active":
            subscriptions = [s for s in subscriptions if s.is_active()]
        elif sub_type == "expired":
            subscriptions = [s for s in subscriptions if not s.is_active()]
        if limit is not None:
            subscriptions = subscriptions[:limit]
        self.subscriptions = subscriptions
        return subscriptions

    async def get_chats(self, limit: int | None = None) -> list[ChatModel]:
        async with aclosing(self.iter_chats(limit=limit)) as values:
            chats = [chat async for chat in values]
        self.chats = chats
        return chats

    async def iter_chats(
        self,
        limit: int | None = None,
        *,
        query: str | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[ChatModel, None]:
        """Chat rooms newest first; ``query`` keeps rooms whose partner name matches.

        The rooms route has no search parameter, so ``query`` filters locally.
        """
        requester = self.get_requester()

        async def page(number: int) -> list[dict[str, Any]]:
            link = APIRoutes().chat_rooms(page=number)
            return _page_items(await requester.json_request(link), "rooms")

        wanted = (query or "").lower()
        count = 0
        async with aclosing(
            _pages(page, max_items=None, identity=lambda raw: raw["roomId"])
        ) as values:
            async for raw in values:
                user = self.resolve_user(raw["recipient"])
                if wanted and wanted not in f"{user.username} {user.name}".lower():
                    continue
                chat = ChatModel(raw, user)
                self.rooms[user.id] = chat.room_id
                yield chat
                count += 1
                if limit is not None and count >= limit:
                    return

    async def find_room_id(self, user: UserModel) -> str | None:
        """The chat room with ``user`` (GET /chat/room?recipientId=)."""
        if user.id in self.rooms:
            return self.rooms[user.id]
        result = await self.get_requester().json_request(APIRoutes().chat_room(user.id))
        room = result.get("room") if isinstance(result, dict) else None
        if not room or not room.get("roomId"):
            return None
        self.rooms[user.id] = room["roomId"]
        return room["roomId"]

    async def get_scrapable_users(self):
        return [subscription.user for subscription in self.subscriptions]

    def media_request_headers(self, url: str) -> dict[str, str]:
        """Headers a plain GET of ``url`` (an image) must send."""
        from ultima_scraper_api.apis.privacy.urls import media_request_headers

        return media_request_headers(url)

    def stream_downloader(self, url: str):
        """How to save ``url`` when a plain GET can't: Privacy videos are
        token-gated, encrypted HLS. A coroutine function taking the
        destination path, or None for a direct file (images)."""
        from ultima_scraper_api.apis.privacy import hls

        if not hls.is_video_playlist(url):
            return None

        async def download(destination: Path) -> Path:
            return await hls.save_video(self, url, destination)

        return download
