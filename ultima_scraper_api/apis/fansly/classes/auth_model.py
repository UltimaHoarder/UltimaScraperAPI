from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.fansly import SubscriptionType
from ultima_scraper_api.apis.fansly.classes.chat_model import ChatModel
from ultima_scraper_api.apis.fansly.classes.message_model import MessageModel
from ultima_scraper_api.apis.fansly.classes.post_model import PostModel
from ultima_scraper_api.apis.fansly.classes.subscription_model import SubscriptionModel
from ultima_scraper_api.apis.fansly.classes.user_model import UserModel
from ultima_scraper_api.apis.fansly.urls import APIRoutes

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM

# /account?ids= accepts a batch; the web client sends its whole visible set.
USER_BATCH = 50
FOLLOWING_PAGE = 100
CHAT_PAGE = 25
ORDER_PAGE = 100


def _response(result: dict[str, Any]) -> Any:
    return result.get("response") if isinstance(result, dict) else None


class FanslyAuthModel(
    StreamlinedAuth["FanslyAuthenticator", "FanslyAPI", "AuthDetails"]
):
    def __init__(
        self,
        authenticator: FanslyAuthenticator,
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.lists: list[dict[str, Any]] = []
        self.subscriptions: list[SubscriptionModel] = []
        self.followed_users: list[UserModel] = []
        self.chats: list[ChatModel] | None = None
        self.paid_content: list[MessageModel | PostModel] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        # Fansly media are not DRM protected; kept for the shared download path.
        self.drm: OnlyDRM | None = None
        self.update()

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int) or str(identifier).isdigit():
            user = self.users.get(int(identifier))
            if user is not None:
                return user
        lowered = str(identifier).lower()
        for user in self.users.values():
            if user.username.lower() == lowered:
                return user
        return None

    def resolve_user(self, user_dict: dict[str, Any]):
        user = self.find_user(user_dict["id"])
        if not user:
            user = UserModel(user_dict, self)
        return user

    def get_pool(self):
        return self.api.pool

    def update(self):
        if self.user:
            self.id = self.user.id
            self.username = self.user.username
            auth_details = self.get_auth_details()
            auth_details.id = self.id

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    async def get_authed_user(self):
        assert self.user
        return self.user

    async def get_me(self):
        """Fetch the account's own profile again (GET /account/me)."""
        result = await self.auth_session.json_request(APIRoutes().me())
        account = (_response(result) or {}).get("account")
        if not account:
            return None
        self.users.pop(self.user.id, None)
        self.user = UserModel(account, self)
        self.update()
        return self.user

    async def get_id(self):
        assert self.user
        return self.user.id

    async def get_username(self):
        assert self.user
        return self.user.get_username()

    async def match_identifiers(self, identifiers: list[int | str]):
        return self.id in identifiers or self.username in identifiers

    async def get_users(self, identifiers: Sequence[int | str]) -> list[UserModel]:
        """Look accounts up in batches (GET /account?ids= / ?usernames=)."""
        users: list[UserModel] = []
        ids = [x for x in identifiers if str(x).isdigit()]
        names = [x for x in identifiers if not str(x).isdigit()]
        for group in (ids, names):
            for start in range(0, len(group), USER_BATCH):
                link = APIRoutes().users(group[start : start + USER_BATCH])
                result = await self.get_requester().json_request(link)
                for raw in _response(result) or []:
                    user = UserModel(raw, self)
                    self.users[user.id] = user
                    users.append(user)
        return users

    async def get_user(self, identifier: int | str, refresh: bool = False):
        if not refresh:
            cached = self.find_user(identifier)
            if cached:
                return cached
        users = await self.get_users([identifier])
        return users[0] if users else None

    async def get_followings(
        self, identifiers: list[int | str] | None = None
    ) -> list[UserModel]:
        """Accounts the authed user follows (GET /account/{id}/following)."""
        account_ids: list[str] = []
        offset = 0
        while True:
            link = APIRoutes().following(self.id, FOLLOWING_PAGE, offset)
            page = _response(await self.get_requester().json_request(link)) or []
            account_ids.extend(x["accountId"] for x in page)
            if len(page) < FOLLOWING_PAGE:
                break
            offset += FOLLOWING_PAGE
        followings = await self.get_users(account_ids)
        if identifiers:
            wanted = {str(x).lower() for x in identifiers}
            followings = [
                user
                for user in followings
                if str(user.id) in wanted or user.username.lower() in wanted
            ]
        self.followed_users = followings
        return followings

    async def get_subscriptions(
        self,
        identifiers: list[int | str] | None = None,
        refresh: bool = True,
        limit: int | None = None,
        sub_type: SubscriptionType = "all",
        filter_by: str = "",
        job_id: str | None = None,
    ) -> list[SubscriptionModel]:
        """Subscriptions from GET /subscriptions, one per subscribed account."""
        if not refresh and self.subscriptions:
            return self.subscriptions
        response = _response(
            await self.get_requester().json_request(APIRoutes().subscriptions())
        ) or {}
        raw_subscriptions: list[dict[str, Any]] = response.get("subscriptions") or []
        # Keep the latest-ending subscription per account (renewals add entries).
        latest: dict[str, dict[str, Any]] = {}
        for raw in raw_subscriptions:
            current = latest.get(raw["accountId"])
            if current is None or raw["endsAt"] > current["endsAt"]:
                latest[raw["accountId"]] = raw
        users = {user.id: user for user in await self.get_users(list(latest))}
        subscriptions: list[SubscriptionModel] = []
        for account_id, raw in latest.items():
            user = users.get(int(account_id))
            if user is None:
                # Deleted accounts no longer resolve; keep the record.
                user = UserModel({"id": account_id, "username": "unknown"}, self)
                user.active = False
            subscriptions.append(SubscriptionModel(raw, user, self))
        if identifiers:
            wanted = {str(x).lower() for x in identifiers}
            subscriptions = [
                s
                for s in subscriptions
                if str(s.user.id) in wanted or s.user.username.lower() in wanted
            ]
        match sub_type:
            case "active":
                subscriptions = [s for s in subscriptions if s.is_active()]
            case "expired":
                subscriptions = [s for s in subscriptions if not s.is_active()]
            case _:
                pass
        subscriptions.sort(key=lambda s: s.ends_at, reverse=True)
        if limit is not None:
            subscriptions = subscriptions[:limit]
        self.subscriptions = subscriptions
        return subscriptions

    async def get_chats(
        self,
        limit: int | None = None,
        offset: int = 0,
        search: str = "",
    ) -> list[ChatModel]:
        """Conversations from GET /messaging/groups, newest activity first."""
        chats: list[ChatModel] = []
        while limit is None or len(chats) < limit:
            link = APIRoutes().list_chats(CHAT_PAGE, offset, search)
            response = _response(await self.get_requester().json_request(link)) or {}
            page: list[dict[str, Any]] = response.get("data") or []
            aggregation = response.get("aggregationData") or {}
            accounts = {a["id"]: a for a in aggregation.get("accounts") or []}
            groups = {g["id"]: g for g in aggregation.get("groups") or []}
            for raw in page:
                account = accounts.get(raw["partnerAccountId"])
                if account is None:
                    continue
                user = self.resolve_user(account)
                chats.append(ChatModel(raw, user, groups.get(raw["groupId"])))
            if len(page) < CHAT_PAGE:
                break
            offset += CHAT_PAGE
        if limit is not None:
            chats = chats[:limit]
        if not search:
            self.chats = chats
        return chats

    async def find_chat_group_id(self, user: UserModel) -> int | None:
        """The DM group with ``user``, from cached chats or a username search."""
        for chat in self.chats or []:
            if chat.user.id == user.id:
                return chat.group_id
        for chat in await self.get_chats(search=user.username):
            if chat.user.id == user.id:
                return chat.group_id
        return None

    async def get_paid_content(
        self,
        performer_id: int | str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Purchased media orders (GET /account/media/orders/) from ``offset``.

        ``limit`` caps the total (None = all), as on OnlyFans.
        """
        orders: list[dict[str, Any]] = []
        while limit is None or len(orders) < limit:
            link = APIRoutes().media_orders(ORDER_PAGE, offset)
            response = _response(await self.get_requester().json_request(link)) or {}
            page: list[dict[str, Any]] = response.get("accountMediaOrders") or []
            orders.extend(page)
            if len(page) < ORDER_PAGE:
                break
            offset += ORDER_PAGE
        if performer_id is not None:
            orders = [o for o in orders if str(o.get("accountId")) == str(performer_id)]
        return orders[:limit] if limit is not None else orders

    async def get_lists(self) -> list[dict[str, Any]]:
        """The authed user's account lists (GET /lists/account)."""
        result = await self.get_requester().json_request(APIRoutes().lists())
        self.lists = _response(result) or []
        return self.lists

    async def get_lists_users(
        self, identifier: int | str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Items of one list (GET /lists/itemsnew), all pages."""
        items: list[dict[str, Any]] = []
        before: int | str = 0
        while True:
            link = APIRoutes().list_items(identifier, limit, before)
            page = _response(await self.get_requester().json_request(link)) or []
            items.extend(page)
            if len(page) < limit:
                break
            before = page[-1]["id"]
        return items

    async def get_blacklist(self, blacklists: list[str]) -> list[str]:
        """Usernames on the account lists whose label is in ``blacklists``."""
        if not blacklists:
            return []
        wanted = {name.lower() for name in blacklists}
        account_ids: list[str] = []
        for account_list in await self.get_lists():
            if (account_list.get("label") or "").lower() in wanted:
                items = await self.get_lists_users(account_list["id"])
                # Type 1 items are accounts; their id is the account id.
                account_ids.extend(item["id"] for item in items if item.get("type") == 1)
        return [user.username for user in await self.get_users(account_ids)]

    async def get_transactions(self, limit: int = 100, offset: int = 0):
        link = APIRoutes().transactions(limit, offset)
        return _response(await self.get_requester().json_request(link)) or {}

    async def get_settings(self):
        result = await self.get_requester().json_request(APIRoutes().settings())
        return _response(result) or {}

    async def get_scrapable_users(self):
        subscription_users = [x.user for x in self.subscriptions]
        return list(set(self.followed_users) | set(subscription_users))
