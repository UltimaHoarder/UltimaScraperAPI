from __future__ import annotations

import asyncio
import json
from collections import deque
from itertools import chain, product
from typing import TYPE_CHECKING, Any, cast

import websockets

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.onlyfans import SubscriptionType
from ultima_scraper_api.apis.onlyfans.classes.chat_model import ChatModel
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import (
    MassMessageStatModel,
)
from ultima_scraper_api.apis.onlyfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.onlyfans.classes.post_model import PostModel
from ultima_scraper_api.apis.onlyfans.classes.subscription_model import (
    SubscriptionModel,
)
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel, recursion
from ultima_scraper_api.apis.onlyfans.classes.vault import VaultListModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
    from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM
    from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI


class OnlyFansAuthModel(
    StreamlinedAuth["OnlyFansAuthenticator", "OnlyFansAPI", "AuthDetails"]
):
    def __init__(
        self,
        authenticator: OnlyFansAuthenticator,
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.lists: list[dict[str, Any]] = []
        self.subscriptions: list[SubscriptionModel] = []
        self.chats: list[ChatModel] = []
        self.archived_stories = {}
        self.mass_message_stats: list[MassMessageStatModel] = []
        self.paid_content: list[MessageModel | PostModel] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        self.drm: OnlyDRM | None = None
        # WebSocket listener state and pub/sub
        self.websocket_task: asyncio.Task[None] | None = None
        self._ws_lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[Any]] = set()
        self._recent: deque[Any] = deque(maxlen=100)
        self.update()

    async def _listen_loop(self) -> None:
        # Prefer WS URL provided by the API/user profile, else default
        url = self.user.ws_url
        assert url

        # websockets 15.x expects `additional_headers`, not `extra_headers` or `headers`.
        # Use dedicated parameters for origin and user agent to avoid invalid headers.
        auth_details = self.get_auth_details()
        user_agent = auth_details.user_agent
        cookie_header: str = auth_details.cookie.convert()

        additional_headers: list[tuple[str, str]] = []

        additional_headers.append(("Cookie", cookie_header))

        async with websockets.connect(
            url,
            user_agent_header=user_agent,
            additional_headers=additional_headers,
            compression="deflate",
        ) as ws:

            # Send init connect frame if token is available on the user
            token = self.user.ws_auth_token
            if token:
                try:
                    await ws.send(json.dumps({"act": "connect", "token": token}))
                except Exception:
                    pass

            # Heartbeat ping (mirror browser behavior ~25s)
            async def _heartbeat():
                try:
                    while True:
                        await asyncio.sleep(25)
                        await ws.send(json.dumps({"act": "ping"}))
                except Exception:
                    return

            hb_task = asyncio.create_task(_heartbeat())

            try:
                while True:
                    msg = await ws.recv()
                    # Fan out raw message to subscribers
                    await self._publish({"type": "message", "data": msg})
            except websockets.ConnectionClosed as e:
                await self._publish(
                    {"type": "closed", "code": e.code, "reason": e.reason}
                )
            finally:
                hb_task.cancel()

    async def listen(self):
        """
        Start the OnlyFans WebSocket listener if it's not already running.
        Safe to call multiple times; subsequent calls no-op while the task is active.
        """
        async with self._ws_lock:
            if self.websocket_task and not self.websocket_task.done():
                return
            # Start a new listener task
            self.websocket_task = asyncio.create_task(self._listen_loop())
            # Small yield so the task has a chance to start before we return
            await asyncio.sleep(0)

    def is_listening(self) -> bool:
        return bool(self.websocket_task and not self.websocket_task.done())

    def subscribe(self, max_queue_size: int = 1000) -> asyncio.Queue[Any]:
        """
        Subscribe to incoming WS events. Returns an asyncio.Queue of event dicts.
        The last recent events are replayed on subscribe for context.
        """
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers.add(q)
        # Best-effort replay of recent events without blocking
        for evt in list(self._recent):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                break
        return q

    def unsubscribe(self, q: asyncio.Queue[Any]) -> None:
        self._subscribers.discard(q)
        # Drain to help GC in long-lived apps
        try:
            while not q.empty():
                q.get_nowait()
        except Exception:
            pass

    async def _publish(self, event: Any) -> None:
        # Save to rolling buffer
        self._recent.append(event)
        # Non-blocking fan-out, drop oldest on backpressure
        dead: list[asyncio.Queue[Any]] = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    # Drop one and retry to keep up
                    _ = q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int):
            user = self.users.get(identifier)
        else:
            for user in self.users.values():
                if user.username.lower() == identifier.lower():
                    break
            else:
                user = None
        return user

    def resolve_user(self, user_dict: dict[str, Any]):
        user = self.find_user(user_dict["id"])
        if not user:
            user = UserModel(user_dict, self)
        return user

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    def get_pool(self):
        return self.api.pool

    def update(self):
        if self.user:
            identifier = self.user.id
            username = self.user.username
            self.id = identifier
            self.username = username
            # # This affects scripts that use the username to select profiles
            auth_details = self.get_auth_details()
            auth_details.id = identifier
            # auth_details.username = username

    async def get_authed_user(self):
        assert self.user
        return self.user

    async def get_id(self):
        assert self.user
        return self.user.id

    async def get_username(self):
        assert self.user
        return self.user.get_username()

    async def get_lists(self, refresh: bool = True, limit: int = 100, offset: int = 0):
        link = endpoint_links(global_limit=limit, global_offset=offset).lists
        json_resp: list[dict[str, Any]] = await self.get_requester().json_request(link)
        self.lists = json_resp
        return json_resp

    async def get_vault_lists(self, limit: int = 100, offset: int = 0):
        link = endpoint_links().list_vault_lists(limit=limit, offset=offset)
        json_resp: list[dict[str, Any]] = await self.get_requester().json_request(link)
        self.vault = VaultListModel(json_resp, self.user)
        return self.vault

    async def get_vault_media(
        self, list_id: int | None = None, limit: int = 100, offset: int = 0
    ):
        json_resp = await recursion(
            category="list_vault_media",
            identifier=list_id,
            requester=self.get_requester(),
            limit=limit,
            offset=offset,
        )
        return json_resp

    async def send_message(
        self,
        to_user_id: int,
        text: str = "",
        *,
        lockedText: bool | None = None,
        mediaFiles: list[dict[str, Any]] | None = None,
        price: float | None = None,
        previews: list[dict[str, Any]] | None = None,
        rfTag: list[Any] | None = None,
        rfGuest: list[Any] | None = None,
        rfPartner: list[Any] | None = None,
        isForward: bool | None = None,
    ) -> dict[str, Any]:
        """Send a message to a user's chat with full OnlyFans payload support.

        Backward compatible: can be called with just (to_user_id, text).
        """
        link = endpoint_links().send_message(to_user_id)
        payload: dict[str, Any] = {"text": text}
        if lockedText is not None:
            payload["lockedText"] = lockedText
        if mediaFiles is not None:
            payload["mediaFiles"] = mediaFiles
        if price is not None:
            payload["price"] = price
        if previews is not None:
            payload["previews"] = previews
        if rfTag is not None:
            payload["rfTag"] = rfTag
        if rfGuest is not None:
            payload["rfGuest"] = rfGuest
        if rfPartner is not None:
            payload["rfPartner"] = rfPartner
        if isForward is not None:
            payload["isForward"] = isForward
        return await self.get_requester().json_request(link, method="POST", payload=payload)

    async def message_create(
        self,
        to_user_id: int,
        text: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Alias for send_message to satisfy older call sites; forwards extra payload fields."""
        return await self.send_message(to_user_id, text, **kwargs)

    async def get_blacklist(self, local_blacklists: list[str]):
        bl_ids: list[str] = []
        remote_blacklists = await self.get_lists()
        if remote_blacklists:
            for remote_blacklist in remote_blacklists:
                for local_blacklist in local_blacklists:
                    if remote_blacklist["name"].lower() == local_blacklist.lower():
                        list_users = remote_blacklist["users"]
                        if remote_blacklist["usersCount"] > 2:
                            list_id = remote_blacklist["id"]
                            list_users = await self.get_lists_users(list_id)
                        if list_users:
                            users = list_users
                            bl_ids = [x["username"] for x in users]
        return bl_ids

    async def match_identifiers(self, identifiers: list[int | str]):
        if self.id in identifiers or self.username in identifiers:
            return True
        else:
            return False

    async def get_user(self, identifier: int | str, refresh: bool = False):
        """
        Retrieves a user from the OnlyFans API based on the provided identifier.

        Args:
            identifier (int | str): The identifier of the user.
            refresh (bool, optional): Flag indicating whether to refresh the user data. Defaults to False.

        Returns:
            UserModel | None: The user data if found, None otherwise.
        """
        USE_NEW_CODE = False
        if USE_NEW_CODE:

            async def fetch_user():
                link = endpoint_links(identifier).users
                response = await self.auth_session.json_request(link)
                if "error" in response:
                    return None
                response["auth_session"] = self.auth_session
                return UserModel(response, self)

            if refresh:
                return await fetch_user()

            user_cache = self.cache.users(identifier)

            if not user_cache.is_released():
                valid_user = self.find_user(identifier)
                if not valid_user:
                    valid_user = await fetch_user()
            else:
                valid_user = await fetch_user()

            if valid_user:
                user_cache.activate()

            return valid_user

        # Important: We need to preserve existing scraped data tied to the user in the cache.
        # When refreshing, we attach old cached data to the new user instance to maintain
        # continuity and prevent data loss or duplication.
        # So for now, we use this method to get the user data until we implemented the comments above
        valid_user = self.find_user(identifier)
        if valid_user and not refresh:
            return valid_user
        else:
            link = endpoint_links(identifier).users
            response = await self.auth_session.json_request(link)
            if "error" in response:
                return None
            response["auth_session"] = self.auth_session
            response = UserModel(response, self)
            return response

    async def get_lists_users(
        self,
        identifier: int,
        check: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        link = endpoint_links(
            identifier, global_limit=limit, global_offset=offset
        ).lists_users
        results: list[dict[str, Any]] = await self.auth_session.json_request(
            link
        )  # type:ignore
        if len(results) >= limit and not check:
            results2 = await self.get_lists_users(
                identifier, limit=limit, offset=limit + offset
            )
            results.extend(results2)  # type: ignore
        return results

    async def assign_user_to_sub(self, raw_subscription: dict[str, Any]):
        user = await self.get_user(raw_subscription["username"])
        if not user:
            user = UserModel(raw_subscription, self)
            user.active = False
        subscription_model = SubscriptionModel(raw_subscription, user, self)
        return subscription_model

    async def get_subscriptions(
        self,
        identifiers: list[int | str] = [],
        limit: int = 100,
        sub_type: SubscriptionType = "all",
        filter_by: str = "",
    ):
        """
        Retrieves the subscriptions based on the given parameters.
        5000 offset is the maximum allowed by the API, which means anything above that will be ignored.

        Args:
            identifiers (list[int | str], optional): List of subscription identifiers. Defaults to [].
            limit (int, optional): Maximum number of subscriptions to retrieve. Defaults to 100.
           sub_type (SubscriptionType, optional): Type of subscriptions to retrieve. Defaults to "all".
             filter_by (str, optional): Filter subscriptions by a specific value. Defaults to "".

        Returns:
            list[SubscriptionModel]: List of SubscriptionModel objects representing the subscriptions.
        """
        from ultima_scraper_api.apis.onlyfans.classes.user_model import recursion

        if not self.cache.subscriptions.is_released():
            return self.subscriptions

        url = endpoint_links().subscription_count(
            sub_type=sub_type, filter_value=filter_by
        )
        result = await self.auth_session.json_request(url)
        if not filter_by:
            subscriptions_info = result["subscriptions"]
            match sub_type:
                case "all":
                    subscription_type_count = subscriptions_info[sub_type]
                case "active":
                    subscription_type_count = subscriptions_info[sub_type]
                case "expired":
                    subscription_type_count = subscriptions_info[sub_type]
                case _:
                    raise ValueError(f"Invalid subscription type: {sub_type}")
        else:
            subscription_type_count = result["count"]
        url = endpoint_links().list_subscriptions(
            limit=limit, sub_type=sub_type, filter=filter_by
        )
        urls = endpoint_links().create_links(
            url,
            api_count=subscription_type_count,
            limit=limit,
        )
        sort_url = "https://onlyfans.com/api2/v2/lists/following/sort"
        _sort_response = await self.auth_session.json_request(
            sort_url,
            method="POST",
            payload={"order": "expire_date", "direction": "desc", "type": "all"},
        )

        subscription_responses = await self.auth_session.bulk_json_requests(urls)
        raw_subscriptions: list[Any] = []
        raw_subscriptions = [
            raw_subscription
            for temp_raw_subscriptions in subscription_responses
            if temp_raw_subscriptions
            for raw_subscription in temp_raw_subscriptions["list"]
        ]

        raw_recursion = await recursion(
            "list_subscriptions",
            self.auth_session,
            query_type=sub_type,
            limit=limit,
            offset=len(urls) * limit,
        )
        raw_subscriptions += raw_recursion

        subscriptions: list[SubscriptionModel] = []
        if identifiers:
            found_raw_subscriptions: list[dict[str, Any]] = []
            for identifier in identifiers:
                for raw_subscription in raw_subscriptions:
                    if (
                        identifier == raw_subscription["id"]
                        or identifier == raw_subscription["username"]
                    ):
                        found_raw_subscriptions.append(raw_subscription)
                        break
            raw_subscriptions = found_raw_subscriptions
        with self.get_pool() as pool:
            tasks = pool.starmap(self.assign_user_to_sub, product(raw_subscriptions))
            subscriptions: list[SubscriptionModel] = await asyncio.gather(*tasks)
        self.subscriptions = subscriptions
        return self.subscriptions

    async def get_chats(
        self,
        limit: int = 100,
        offset: int = 0,
    ):
        if not self.cache.chats.is_released():
            return self.chats

        async def mass_recursive(
            limit: int, offset: int, multiplier: int, depth: int = 1
        ):
            link = endpoint_links(global_limit=limit, global_offset=offset).list_chats

            unpredictable_links, new_offset = api_helper.calculate_the_unpredictable(
                link, offset, limit, multiplier, depth
            )
            links = unpredictable_links
            results = await self.auth_session.bulk_json_requests(links)
            items = [x["list"] for x in results]
            if not items:
                return items
            if results[-1]["hasMore"]:
                results2 = await mass_recursive(
                    limit=limit,
                    offset=limit + new_offset,
                    multiplier=multiplier,
                    depth=depth + 1,
                )
                items.extend(results2)
            else:
                self.cache.chats.activate()

            return items

        multiplier = self.auth_session.get_session_manager().max_threads
        recursive_results = await mass_recursive(limit, offset, multiplier)
        results = list(chain.from_iterable(recursive_results))
        temp_chats: set[ChatModel] = set()
        for result in results:
            temp_chats.add(ChatModel(result, self))
        chats: list[ChatModel] = list(temp_chats)
        chats.sort(key=lambda x: x.user.id, reverse=True)
        self.chats = chats
        return self.chats

    async def get_mass_message_stats(
        self,
        resume: list[dict[str, Any]] | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        if not self.cache.mass_message_stats.is_released():
            return self.mass_message_stats

        async def recursive(
            resume: list[dict[str, Any]] | None, limit: int, offset: int
        ):
            link = endpoint_links(
                global_limit=limit, global_offset=offset
            ).mass_messages_stats
            results = await self.auth_session.json_request(link)
            items = results.get("list", [])
            if not items:
                return items
            if resume:
                for item in items:
                    if any(x["id"] == item["id"] for x in resume):
                        resume.sort(key=lambda x: x["id"], reverse=True)
                        return resume
                    else:
                        resume.append(item)

            if results["hasMore"]:
                results2 = await recursive(
                    resume=resume, limit=limit, offset=limit + offset
                )
                items.extend(results2)
            else:
                self.cache.mass_message_stats.activate()
            if resume:
                items = resume

            return items

        items = await recursive(resume, limit, offset)
        items.sort(key=lambda x: x["id"], reverse=True)
        self.mass_message_stats = [MassMessageStatModel(x, self.user) for x in items]
        return self.mass_message_stats

    async def get_paid_content(
        self,
        performer_id: int | str | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        if not self.cache.paid_content.is_released():
            return self.paid_content

        async def recursive(limit: int, offset: int):
            url = endpoint_links().list_paid_posts(
                limit=limit, offset=offset, performer_id=performer_id
            )
            results = await self.auth_session.json_request(url)
            items = results.get("list", [])
            if not items:
                return items
            if results["hasMore"]:
                results2 = await recursive(limit=limit, offset=limit + offset)
                items.extend(results2)
            else:
                if not performer_id:
                    self.cache.mass_message_stats.activate()
            return items

        items = await recursive(limit, offset)
        for item in items:
            content = None
            if item["responseType"] == "message":
                user = await self.get_user(item["fromUser"]["id"])
                if not user:
                    user = UserModel(item["fromUser"], self)
                content = MessageModel(item, user)
            elif item["responseType"] == "post":
                user = UserModel(item["author"], self)
                content = PostModel(item, user)
            if content:
                author = content.get_author()
                if performer_id:
                    if performer_id == author.id:
                        self.paid_content.append(content)
                    elif performer_id == author.username:
                        self.paid_content.append(content)
                else:
                    self.paid_content.append(content)
                if not performer_id:
                    self.cache.paid_content.activate()
        return self.paid_content

    async def get_scrapable_users(self):
        subscription_users = [x.user for x in self.subscriptions]
        return subscription_users

    async def get_login_issues(self):
        url = endpoint_links().login_issues
        response = await self.auth_session.json_request(url, method="POST")
        return response

    async def get_transactions(self):
        link = endpoint_links(self.id).transactions
        results = await self.get_requester().json_request(link)
        return results
