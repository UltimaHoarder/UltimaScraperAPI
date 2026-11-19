from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.loyalfans import numbered_pages
from ultima_scraper_api.apis.loyalfans.classes.chat_model import ChatModel
from ultima_scraper_api.apis.loyalfans.classes.extras import call_api
from ultima_scraper_api.apis.loyalfans.classes.subscription_model import (
    SubscriptionModel,
)
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.apis.loyalfans.urls import APIRoutes
from ultima_scraper_api.apis.pagination import paginate
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.authenticator import (
        LoyalFansAuthenticator,
    )

    # Named in StreamlinedAuth's string type arguments below.
    from ultima_scraper_api.apis.loyalfans.classes.extras import (  # noqa: F401
        AuthDetails,
    )
    from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI  # noqa: F401

# Page sizes the web client uses.
LIST_PAGE = 12
CHAT_PAGE = 20


class LoyalFansAuthModel(
    StreamlinedAuth["LoyalFansAuthenticator", "LoyalFansAPI", "AuthDetails"]
):
    def __init__(self, authenticator: LoyalFansAuthenticator) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.subscriptions: list[SubscriptionModel] = []
        self.chats: list[ChatModel] | None = None
        self.lists: list[dict[str, Any]] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        self.update()

    # --- requests --------------------------------------------------------------------

    async def call(self, link: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET ``link`` (or POST ``body`` as JSON); renews an expired token once.

        Returns the JSON, or {"error": {code, message}} for a failed call.
        """
        requester = self.get_requester()
        status, result = await call_api(requester, link, body)
        if status == 401 and await self.authenticator.refresh_token(result):
            status, result = await call_api(requester, link, body)
        if status == 200 and result.get("success", True) is not False:
            return result
        message = result.get("message") or result.get("error") or "request failed"
        return {"error": {"code": status, "message": str(message)}}

    # --- users -----------------------------------------------------------------------

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int):
            return self.users.get(identifier)
        text = str(identifier)
        if text.isdigit() and int(text) in self.users:
            return self.users[int(text)]
        lowered = text.lower()
        for user in self.users.values():
            if user.uid == text or user.username.lower() == lowered:
                return user
        return None

    def resolve_user(self, user_dict: dict[str, Any]) -> UserModel:
        """The cached user for this user object (merged), or a new one."""
        raw = user_dict.get("user") if isinstance(user_dict.get("user"), dict) else user_dict
        uid = raw.get("uid") if isinstance(raw, dict) else None
        user = self.users.get(native_id_to_db_id(str(uid))) if uid else None
        if user is None:
            return UserModel(user_dict, self)
        user.merge(user_dict)
        return user

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    def get_pool(self):
        return self.api.pool

    def update(self):
        if self.user:
            self.id = self.user.id
            self.username = self.user.username
            self.get_auth_details().id = self.id

    async def get_authed_user(self):
        return self.user

    async def get_me(self):
        """The signed-in account again (GET /auth/user/me)."""
        result = await self.call(APIRoutes().me())
        me = result.get("response")
        if not isinstance(me, dict) or not me:
            return None
        self.user.merge(me)
        self.update()
        return self.user

    async def get_id(self):
        return self.user.id

    async def get_username(self):
        return self.user.get_username()

    async def match_identifiers(self, identifiers: list[int | str]):
        return any(
            value in identifiers for value in (self.id, self.user.uid, self.username)
        )

    async def get_user(self, identifier: int | str, refresh: bool = False):
        """A full profile by username (slug); ids resolve through users already seen.

        The profile route takes a slug, and an archive id is a hash of the uid,
        so an id or uid only works for a user met before (subscriptions,
        chats, posts). A user only seen as a post owner or list member is
        fetched once to fill in the profile.
        """
        known = self.find_user(identifier)
        if known is not None and known.profile_loaded and not refresh:
            return known
        if known is not None:
            identifier = known.username
        elif isinstance(identifier, int) or str(identifier).isdigit():
            return None
        result = await self.call(APIRoutes().profile(str(identifier)))
        data = result.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("user"), dict):
            return None
        return self.resolve_user(data)

    # --- lists and subscriptions -----------------------------------------------------

    async def get_lists(
        self, refresh: bool = True, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """The account's user lists with their counts (system and custom)."""
        if refresh or not self.lists:

            async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
                result = await self.call(
                    APIRoutes().user_lists(),
                    {"page": number, "search_term": "", "limit": 16},
                )
                return result.get("user_lists") or [], result.get("page_meta") or {}

            async with aclosing(numbered_pages(page)) as values:
                self.lists = [value async for value in values]
        lists = self.lists[offset:]
        return lists[:limit] if limit is not None else lists

    async def iter_list_users(
        self, list_id: int | str, *, max_items: int | None = None
    ) -> AsyncGenerator[UserModel, None]:
        """Members of one list; ``list_id`` is an id or a system list's name."""

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            result = await self.call(
                APIRoutes().user_list_users(),
                {"id": list_id, "page": number, "limit": LIST_PAGE},
            )
            return result.get("users") or [], result.get("page_meta") or {}

        async with aclosing(numbered_pages(page, max_items=max_items)) as values:
            async for raw in values:
                yield self.resolve_user(raw)

    async def get_subscriptions(
        self,
        identifiers: list[int | str] | None = None,
        refresh: bool = True,
        limit: int | None = None,
        sub_type: str = "all",
        filter_by: str = "",
        job_id: str | None = None,
    ) -> list[SubscriptionModel]:
        """Paid subscriptions, plus followed (free) creators unless ``sub_type``
        is "active"/"expired", which look at paid ones only."""
        if self.guest:
            return []
        if not refresh and self.subscriptions:
            return self.subscriptions
        kinds = ["subscribed"] if sub_type in ("active", "expired") else ["subscribed", "following"]
        subscriptions: list[SubscriptionModel] = []
        seen: set[int] = set()
        for kind in kinds:
            async with aclosing(self.iter_list_users(kind)) as users:
                async for user in users:
                    if user.id in seen:
                        continue
                    seen.add(user.id)
                    subscriptions.append(SubscriptionModel(user.__raw__, user, self, kind))
        if identifiers:
            wanted = {str(x).lower() for x in identifiers}
            subscriptions = [
                s
                for s in subscriptions
                if {str(s.user.id), s.user.uid.lower(), s.user.username.lower()} & wanted
            ]
        if sub_type == "active":
            subscriptions = [s for s in subscriptions if s.is_active()]
        elif sub_type == "expired":
            subscriptions = [s for s in subscriptions if not s.is_active()]
        if limit is not None:
            subscriptions = subscriptions[:limit]
        self.subscriptions = subscriptions
        return subscriptions

    async def get_scrapable_users(self):
        return [subscription.user for subscription in self.subscriptions]

    # --- chats -----------------------------------------------------------------------

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
        """Conversations newest first; ``query`` keeps partners whose name matches.

        The conversations route has no search parameter, so ``query`` filters
        locally. Pages continue with the previous page's ``page_token``.
        """
        wanted = (query or "").lower()

        async def fetch(token: str | None) -> tuple[list[ChatModel], str | None]:
            body: dict[str, Any] = {"limit": CHAT_PAGE, "all": True}
            if token:
                body["page_token"] = token
            result = await self.call(APIRoutes().conversations(), body)
            raw = result.get("conversations") or []
            chats = [ChatModel(item, self.resolve_user(item["partner"])) for item in raw]
            return chats, (result.get("page_token") or None) if raw else None

        count = 0
        async with aclosing(paginate(fetch)) as values:
            async for chat in values:
                user = chat.user
                if wanted and wanted not in f"{user.username} {user.name}".lower():
                    continue
                yield chat
                count += 1
                if limit is not None and count >= limit:
                    return
