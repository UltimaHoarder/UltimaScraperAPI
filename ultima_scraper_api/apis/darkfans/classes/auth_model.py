from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.darkfans import attributes, numbered_pages
from ultima_scraper_api.apis.darkfans.classes.chat_model import ChatModel
from ultima_scraper_api.apis.darkfans.classes.extras import ErrorDetails, call_api
from ultima_scraper_api.apis.darkfans.classes.subscription_model import (
    SubscriptionModel,
)
from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel
from ultima_scraper_api.apis.darkfans.urls import APIRoutes
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.authenticator import DarkFansAuthenticator

    # Named in StreamlinedAuth's string type arguments below.
    from ultima_scraper_api.apis.darkfans.classes.extras import (  # noqa: F401
        AuthDetails,
    )
    from ultima_scraper_api.apis.darkfans.darkfans import DarkFansAPI  # noqa: F401

LIST_PAGE = 50
CHAT_PAGE = 50
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class DarkFansAuthModel(
    StreamlinedAuth["DarkFansAuthenticator", "DarkFansAPI", "AuthDetails"]
):
    def __init__(self, authenticator: DarkFansAuthenticator) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.subscriptions: list[SubscriptionModel] = []
        self.chats: list[ChatModel] | None = None
        # Partner uid -> chat id, filled by iter_chats.
        self.chat_ids: dict[str, str] = {}
        self.lists: list[dict[str, Any]] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        self.update()

    # --- requests --------------------------------------------------------------------

    async def call(self, link: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET ``link`` (or POST ``body`` as JSON); renews an expired JWT once.

        Returns the JSON, or {"error": {code, message}} for a failed call.
        """
        requester = self.get_requester()
        status, result, _ = await call_api(requester, link, body)
        if status == 401 and await self.authenticator.refresh_token():
            status, result, _ = await call_api(requester, link, body)
        if 200 <= status < 300:
            return result
        error = ErrorDetails.from_response(status, result)
        return {"error": {"code": error.code, "message": error.message or "request failed"}}

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
        raw = attributes(user_dict)
        uid = raw.get("id")
        user = self.users.get(native_id_to_db_id(str(uid))) if uid else None
        if user is None:
            return UserModel(user_dict, self)
        user.merge(user_dict)
        return user

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    def get_pool(self):
        return self.api.pool

    # --- media -----------------------------------------------------------------------

    @property
    def drm(self):
        """Fastevo playback for DRM videos (None without mp4decrypt/mp4dump)."""
        if not hasattr(self, "_drm"):
            from ultima_scraper_api.apis.darkfans.fastevo import FastevoDRM

            try:
                self._drm = FastevoDRM(self)
            except FileNotFoundError as exc:
                import logging

                logging.getLogger(__name__).warning("DarkFans DRM videos disabled: %s", exc)
                self._drm = None
        return self._drm

    @drm.setter
    def drm(self, value) -> None:
        self._drm = value

    def media_request_headers(self, url: str) -> dict[str, str]:
        """Headers a plain GET of ``url`` must send (Fastevo's tracks)."""
        from ultima_scraper_api.apis.darkfans.fastevo import media_request_headers

        return media_request_headers(url)

    def update(self):
        if self.user:
            self.id = self.user.id
            self.username = self.user.username
            self.get_auth_details().id = self.id

    async def get_authed_user(self):
        return self.user

    async def get_me(self):
        """The signed-in account again (GET /user/info)."""
        result = await self.call(APIRoutes().me())
        me = attributes(result.get("data"))
        if not me.get("id"):
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
        """A full profile by username or UUID; an archive id (int) resolves
        only through users already seen."""
        known = self.find_user(identifier)
        if known is not None and known.profile_loaded and not refresh:
            return known
        if known is not None:
            identifier = known.uid
        elif isinstance(identifier, int) or str(identifier).isdigit():
            return None
        text = str(identifier)
        link = APIRoutes().user(text) if UUID.match(text) else APIRoutes().user_by_username(text)
        result = await self.call(link)
        data = attributes(result.get("data"))
        if not data.get("id"):
            return None
        return self.resolve_user(data)

    # --- lists and subscriptions -----------------------------------------------------

    async def get_lists(
        self, refresh: bool = True, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """The account's user lists (as the API gives them)."""
        if refresh or not self.lists:
            result = await self.call(APIRoutes().user_lists(self.user.uid))
            self.lists = [attributes(item) for item in result.get("data") or []]
        lists = self.lists[offset:]
        return lists[:limit] if limit is not None else lists

    async def iter_list_users(
        self, list_id: str, *, max_items: int | None = None
    ) -> AsyncGenerator[UserModel, None]:
        """Members of one list."""

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            result = await self.call(APIRoutes().user_list_users(list_id, page=number, per_page=LIST_PAGE))
            return result.get("data") or [], result.get("meta") or {}

        async with aclosing(numbered_pages(page, per_page=LIST_PAGE, max_items=max_items)) as values:
            async for raw in values:
                item = attributes(raw)
                member = item.get("user")
                yield self.resolve_user(member if isinstance(member, dict) else item)

    async def iter_followees(self, *, max_items: int | None = None) -> AsyncGenerator[UserModel, None]:
        """Creators the account follows (free)."""

        async def page(number: int) -> tuple[list[Any], dict[str, Any]]:
            result = await self.call(APIRoutes().followees(self.user.uid, page=number, per_page=LIST_PAGE))
            return result.get("data") or [], result.get("meta") or {}

        async with aclosing(numbered_pages(page, per_page=LIST_PAGE, max_items=max_items)) as values:
            async for raw in values:
                user = attributes(raw).get("user")
                if isinstance(user, dict):
                    yield self.resolve_user(user)

    async def get_subscriptions(
        self,
        identifiers: list[int | str] | None = None,
        refresh: bool = True,
        limit: int | None = None,
        sub_type: str = "all",
        filter_by: str = "",
        job_id: str | None = None,
    ) -> list[SubscriptionModel]:
        """Paid subscriptions (valid and expired), plus followed creators
        unless ``sub_type`` is "active"/"expired", which look at paid ones only."""
        if self.guest:
            return []
        if not refresh and self.subscriptions:
            return self.subscriptions
        subscriptions: list[SubscriptionModel] = []
        seen: set[int] = set()

        async def paid_page(number: int) -> tuple[list[Any], dict[str, Any]]:
            result = await self.call(APIRoutes().subscriptions(self.user.uid, page=number, per_page=LIST_PAGE))
            return result.get("data") or [], result.get("meta") or {}

        async with aclosing(numbered_pages(paid_page, per_page=LIST_PAGE)) as values:
            async for raw in values:
                row = attributes(raw)
                if not row.get("creatorId"):
                    continue
                user = self.resolve_user(
                    {
                        "id": row["creatorId"],
                        "username": row.get("creatorUsername"),
                        "displayName": row.get("creatorDisplayUsername"),
                        "avatar": row.get("creatorAvatar"),
                        "header": row.get("creatorHeader"),
                        "creator": True,
                    }
                )
                if user.id in seen:
                    continue
                seen.add(user.id)
                subscriptions.append(SubscriptionModel(row, user, self, "subscribed"))
        if sub_type not in ("active", "expired"):
            async with aclosing(self.iter_followees()) as users:
                async for user in users:
                    if user.id in seen:
                        continue
                    seen.add(user.id)
                    subscriptions.append(SubscriptionModel({}, user, self, "following"))
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
        """Chats, latest activity first: open ones, then archived ones.

        ``query`` keeps partners whose name matches (filtered locally).
        """
        wanted = (query or "").lower()
        count = 0
        for archived in (False, True):

            async def page(number: int, archived: bool = archived) -> tuple[list[Any], dict[str, Any]]:
                link = APIRoutes().chats(self.user.uid, page=number, per_page=CHAT_PAGE, archived=archived)
                result = await self.call(link)
                return result.get("data") or [], result.get("meta") or {}

            async with aclosing(numbered_pages(page, per_page=CHAT_PAGE)) as values:
                async for raw in values:
                    chat = self._chat(attributes(raw))
                    if chat is None:
                        continue
                    user = chat.user
                    if wanted and wanted not in f"{user.username} {user.name}".lower():
                        continue
                    yield chat
                    count += 1
                    if limit is not None and count >= limit:
                        return

    def _chat(self, raw: dict[str, Any]) -> ChatModel | None:
        partner = next(
            (
                attributes(item)
                for item in raw.get("users") or []
                if attributes(item).get("id") not in (None, self.user.uid)
            ),
            None,
        )
        if partner is None or not raw.get("id"):
            return None
        chat = ChatModel(raw, self.resolve_user(partner))
        self.chat_ids[chat.user.uid] = chat.id
        return chat

    async def find_chat_id(self, user: UserModel) -> str | None:
        """The id of the chat with ``user``, from the chat list (read once)."""
        if user.uid not in self.chat_ids and self.chats is None:
            await self.get_chats()
        return self.chat_ids.get(user.uid)
