from __future__ import annotations

import asyncio
from datetime import datetime
from itertools import product
from typing import TYPE_CHECKING, Any, Dict

from dateutil.relativedelta import relativedelta

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.fansly import SubscriptionType
from ultima_scraper_api.apis.fansly.classes.extras import endpoint_links
from ultima_scraper_api.apis.fansly.classes.message_model import create_message
from ultima_scraper_api.apis.fansly.classes.post_model import create_post
from ultima_scraper_api.apis.fansly.classes.subscription_model import SubscriptionModel
from ultima_scraper_api.apis.fansly.classes.user_model import create_user

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
    from ultima_scraper_api.apis.fansly.classes.extras import AuthDetails
    from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM


class AuthModel(StreamlinedAuth["FanslyAuthenticator", "FanslyAPI", "AuthDetails"]):
    def __init__(
        self,
        authenticator: FanslyAuthenticator,
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, create_user] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.lists = []
        self.links = self.api.ContentTypes()
        self.subscriptions: list[SubscriptionModel] = []
        self.followed_users: list[create_user] = []
        self.chats = None
        self.archived_stories = {}
        self.mass_messages = []
        self.paid_content: list[create_message | create_post] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        self.drm: OnlyDRM | None = None
        self.update()

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

    def add_user(self, user: create_user):
        self.users[user.id] = user

    async def get_lists(self, refresh: bool = True, limit: int = 100, offset: int = 0):
        link = endpoint_links(global_limit=limit, global_offset=offset).lists
        json_resp = await self.get_requester().json_request(link)
        self.lists = json_resp
        return json_resp

    async def get_blacklist(self, blacklists: list[str]):
        bl_ids: list[str] = []
        return bl_ids
        remote_blacklists = await self.get_lists()
        if remote_blacklists:
            for remote_blacklist in remote_blacklists:
                for blacklist in blacklists:
                    if remote_blacklist["name"] == blacklist:
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

    async def get_user(self, identifier: int | str):
        valid_user = self.find_user(identifier)
        if valid_user:
            return valid_user
        else:
            identifier = str(identifier)
            if identifier.isdigit():
                url = endpoint_links(identifier).users_by_id
            else:
                url = endpoint_links(identifier).users_by_username
                pass
            response = await self.get_requester().json_request(url)
            if response["response"]:
                response["auth_session"] = self.auth_session
                response = create_user(response["response"][0], self)
            return response

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
            user = create_user(user_dict, self)
        return user

    async def get_lists_users(
        self,
        identifier: int | str,
        check: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        link = endpoint_links(
            identifier, global_limit=limit, global_offset=offset
        ).lists_users
        results = await self.get_requester().json_request(link)
        if len(results) >= limit and not check:
            results2 = await self.get_lists_users(
                identifier, limit=limit, offset=limit + offset
            )
            results.extend(results2)  # type: ignore
        return results

    async def get_followings(
        self, identifiers: list[int | str] = []
    ) -> list[create_user]:
        offset_count = 0
        followings: list[dict[str, Any]] = []
        while True:
            followings_link = endpoint_links().list_followings(self.id, offset_count)
            temp_followings: dict[str, Any] = await self.get_requester().json_request(
                followings_link
            )
            account_ids = temp_followings["response"]
            if account_ids:
                followings.extend(account_ids)
                offset_count += 100
            else:
                break
        final_followings: list[create_user] = []
        if followings:
            followings_id: str = ",".join([x["accountId"] for x in followings])
            customer_link = endpoint_links(followings_id).customer
            temp_followings = await self.get_requester().json_request(customer_link)
            if identifiers:
                final_followings = [
                    create_user(x, self)
                    for x in temp_followings["response"]
                    for identifier in identifiers
                    if x["username"].lower() == identifier or x["id"] == identifier
                ]
            else:
                final_followings = [
                    create_user(x, self) for x in temp_followings["response"]
                ]
            for following in final_followings:
                if not following.subscribedByData:
                    new_date = datetime.now() + relativedelta(years=10)
                    new_date = int(new_date.timestamp() * 1000)
                    following.subscribedByData = {}
                    following.subscribedByData["endsAt"] = new_date
        self.followed_users = final_followings
        return final_followings

    async def get_subscription(
        self, identifier: int | str = "", custom_list: list[SubscriptionModel] = []
    ) -> SubscriptionModel | None:
        subscriptions = (
            await self.get_subscriptions(refresh=False)
            if not custom_list
            else custom_list
        )
        valid = None
        for subscription in subscriptions:
            if (
                identifier == subscription.user.username
                or identifier == subscription.user.id
            ):
                valid = subscription
                break
        return valid

    async def get_subscriptions(
        self,
        refresh: bool = True,
        identifiers: list[int | str] = [],
        sub_type: SubscriptionType = "all",
    ):
        subscriptions_link = endpoint_links().subscriptions
        temp_subscriptions = await self.get_requester().json_request(subscriptions_link)
        raw_subscriptions = temp_subscriptions["response"]["subscriptions"]

        async def assign_user_to_sub(raw_subscription: Dict[str, Any]):
            user = await self.get_user(raw_subscription["accountId"])
            if isinstance(user, dict):
                user = create_user(raw_subscription, self)
                user.active = False
            subscription_model = SubscriptionModel(raw_subscription, user, self)
            return subscription_model

        subscriptions: list[SubscriptionModel] = []
        with self.get_pool() as pool:
            tasks = pool.starmap(assign_user_to_sub, product(raw_subscriptions))
            subscriptions: list[SubscriptionModel] = await asyncio.gather(*tasks)
            if identifiers:
                found_subscriptions: list[SubscriptionModel] = []
                for identifier in identifiers:
                    for subscription in subscriptions:
                        if (
                            identifier == subscription.user.id
                            or identifier == subscription.user.username
                        ):
                            found_subscriptions.append(subscription)
                            break
                subscriptions = found_subscriptions

        match sub_type:
            case "all":
                pass
            case "active":
                subscriptions = [x for x in subscriptions if x.ends_at > datetime.now()]
            case "expired":
                subscriptions = [x for x in subscriptions if x.ends_at < datetime.now()]
        return subscriptions

    async def get_chats(
        self,
        links: list[str] = [],
        limit: int = 25,
        offset: int = 0,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        multiplier = self.auth_session.get_session_manager().max_threads
        temp_limit = limit
        temp_offset = offset
        link = endpoint_links(
            identifier=self.id, global_limit=temp_limit, global_offset=temp_offset
        ).list_chats
        unpredictable_links, new_offset = api_helper.calculate_the_unpredictable(
            link, offset, limit, multiplier, depth
        )
        links = unpredictable_links if depth != 1 else links + unpredictable_links

        results = await self.get_requester().bulk_json_requests(links)
        has_more = results[-1]["response"]["data"]
        final_results = api_helper.merge_dictionaries(results)["response"]

        if has_more:
            results2 = await self.get_chats(
                limit=temp_limit,
                offset=new_offset,
                depth=depth + 1,
            )
            final_results = api_helper.merge_dictionaries([final_results, results2])
        if depth == 1:
            aggregationData = final_results["aggregationData"]
            for result in final_results["data"]:
                for account in aggregationData["accounts"]:
                    if result["partnerAccountId"] == account["id"]:
                        result["withUser"] = create_user(account, self)
                for group in aggregationData["groups"]:
                    found_user = [
                        x
                        for x in group["users"]
                        if x["userId"] == result["partnerAccountId"]
                    ]
                    last_message = group.get("lastMessage")
                    if found_user and last_message:
                        result["lastMessage"] = create_message(
                            last_message, result["withUser"]
                        )
            final_results = final_results["data"]
            final_results.sort(key=lambda x: x["withUser"].id, reverse=True)
        self.chats = final_results
        return final_results

    async def get_paid_content(
        self,
        performer_id: int | str | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        if not self.cache.paid_content.is_released():
            return self.paid_content
        link = endpoint_links(global_limit=limit, global_offset=offset).paid_api
        result = await self.get_requester().json_request(link)
        final_results = result["response"]["accountMediaOrders"]
        return final_results

    async def get_scrapable_users(self):
        followed_users = self.followed_users
        subscription_users = [x.user for x in self.subscriptions]
        unique_users = list(set(followed_users) | set(subscription_users))
        return unique_users
