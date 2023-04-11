from __future__ import annotations

import asyncio
from datetime import datetime
from itertools import chain, product
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from dateutil.relativedelta import relativedelta
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.fansly.classes.extras import (
    AuthDetails,
    ErrorDetails,
    create_headers,
    endpoint_links,
)
from ultima_scraper_api.apis.fansly.classes.message_model import create_message
from ultima_scraper_api.apis.fansly.classes.post_model import create_post
from ultima_scraper_api.apis.fansly.classes.user_model import create_user
from ultima_scraper_api.managers.session_manager import SessionManager
from user_agent import generate_user_agent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.fansly import FanslyAPI


class create_auth(create_user):
    def __init__(
        self,
        api: FanslyAPI,
        option: dict[str, Any] = {},
        max_threads: int = -1,
        auth_details: AuthDetails = AuthDetails(),
    ) -> None:
        self.api = api
        self.users: set[create_user] = set()
        self.auth_details = auth_details
        self.session_manager = self._SessionManager(self, max_threads=max_threads)
        create_user.__init__(self, option, self)
        if not self.username:
            self.username = f"u{self.id}"
        self.lists = []
        self.links = api.ContentTypes()
        self.subscriptions: list[create_user] = []
        self.chats = None
        self.archived_stories = {}
        self.mass_messages = []
        self.paid_content: list[create_message | create_post] = []
        self.auth_attempt = 0
        self.guest = False
        self.active: bool = False
        self.errors: list[ErrorDetails] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []

    class _SessionManager(SessionManager):
        def __init__(
            self,
            auth: create_auth,
            headers: dict[str, Any] = {},
            proxies: list[str] = [],
            max_threads: int = -1,
            use_cookies: bool = True,
        ) -> None:
            SessionManager.__init__(
                self, auth, headers, proxies, max_threads, use_cookies
            )

    def get_pool(self):
        return self.api.pool

    async def convert_to_user(self):
        user = await self.get_user(self.username)
        for k, _v in user.__dict__.items():
            setattr(user, k, getattr(self, k))
        return user

    def update(self, data: Dict[str, Any]):
        data = data["response"][0]
        if not data["username"]:
            data["username"] = f"u{data['id']}"
        for key, value in data.items():
            found_attr = hasattr(self, key)
            if found_attr:
                setattr(self, key, value)

    async def login(self, max_attempts: int = 10, guest: bool = False):
        auth_items = self.auth_details
        if not auth_items:
            return self
        if guest and auth_items:
            auth_items.user_agent = generate_user_agent()
        link = endpoint_links().customer
        user_agent = auth_items.user_agent
        dynamic_rules = self.session_manager.dynamic_rules
        a: list[Any] = [dynamic_rules, user_agent, link]
        self.session_manager.headers = create_headers(*a)
        if guest:
            self.guest = True
            return self

        while self.auth_attempt < max_attempts + 1:
            await self.process_auth()
            self.auth_attempt += 1

            async def resolve_auth(auth: create_auth):
                if self.errors:
                    error = self.errors[-1]
                    print(error.message)
                    if error.code == 101:
                        if auth_items.support_2fa:
                            link = f"https://onlyfans.com/api2/v2/users/otp/check"
                            count = 1
                            max_count = 3
                            while count < max_count + 1:
                                print(
                                    "2FA Attempt " + str(count) + "/" + str(max_count)
                                )
                                code = input("Enter 2FA Code\n")
                                data = {"code": code, "rememberMe": True}
                                response = await self.session_manager.json_request(
                                    link, method="POST", payload=data
                                )
                                if isinstance(response, ErrorDetails):
                                    error.message = response.message
                                    count += 1
                                else:
                                    print("Success")
                                    auth.active = False
                                    auth.errors.remove(error)
                                    await self.process_auth()
                                    break

            await resolve_auth(self)
            if not self.active:
                if self.errors:
                    error = self.errors[-1]
                    error_message = error.message
                    if "token" in error_message:
                        break
                    if "Code wrong" in error_message:
                        break
                    if "Please refresh" in error_message:
                        break
                else:
                    print("Auth 404'ed")
                continue
            else:
                break
        if not self.active:
            user = await self.get_user(self.id)
            if isinstance(user, create_user):
                self.update(user.__dict__)
        return self

    async def process_auth(self):
        if not self.active:
            link = endpoint_links().settings
            response = await self.session_manager.json_request(link)
            if isinstance(response, dict):
                final_response: dict[str, Any] = response
                link = endpoint_links(final_response["response"]["accountId"]).customer
                final_response = await self.session_manager.json_request(link)
                await self.resolve_auth_errors(final_response)
                if not self.errors:
                    # merged = self.__dict__ | final_response
                    # self = create_auth(merged,self.pool,self.session_manager.max_threads)
                    self.active = True
                    self.update(final_response)
            else:
                # 404'ed
                self.active = False
        return self

    async def resolve_auth_errors(self, response: ErrorDetails | dict[str, Any]):
        # Adds an error object to self.auth.errors
        if isinstance(response, ErrorDetails):
            error = response
        elif "error" in response:
            error = response["error"]
            error = ErrorDetails(error)
        else:
            self.errors.clear()
            return
        error_message = error.message
        error_code = error.code
        if error_code == 0:
            pass
        elif error_code == 101:
            error_message = "Blocked by 2FA."
        elif error_code == 401:
            # Session/Refresh
            pass
        error.code = error_code
        error.message = error_message
        self.errors.append(error)

    async def get_lists(self, refresh: bool = True, limit: int = 100, offset: int = 0):
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        link = endpoint_links(global_limit=limit, global_offset=offset).lists
        results = await self.session_manager.json_request(link)
        self.lists = results
        return results

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

    def find_user_by_identifier(self, identifier: int | str):
        user = [x for x in self.users if x.id == identifier or x.username == identifier]
        return user

    async def get_user(self, identifier: int | str) -> Union[create_user, ErrorDetails]:
        link = endpoint_links().list_users([identifier])
        response = await self.session_manager.json_request(link)
        if not isinstance(response, ErrorDetails):
            if response["response"]:
                response["session_manager"] = self.session_manager
                response = create_user(response["response"][0], self)
            else:
                response = ErrorDetails({"code": 69, "message": "User Doesn't Exist"})
        return response

    async def get_lists_users(
        self,
        identifier: int | str,
        check: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        if not self.active:
            return
        link = endpoint_links(
            identifier, global_limit=limit, global_offset=offset
        ).lists_users
        results = await self.session_manager.json_request(link)
        if len(results) >= limit and not check:
            results2 = await self.get_lists_users(
                identifier, limit=limit, offset=limit + offset
            )
            results.extend(results2)
        return results

    async def get_followings(self, identifiers: list[int | str]) -> list[create_user]:
        offset_count = 0
        followings: list[dict[str, Any]] = []
        while True:
            followings_link = endpoint_links().list_followings(self.id, offset_count)
            temp_followings: dict[str, Any] = await self.session_manager.json_request(
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
            temp_followings = await self.session_manager.json_request(customer_link)
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
        return final_followings

    async def get_subscription(
        self, identifier: int | str = "", custom_list: list[create_user] = []
    ) -> create_user | None:
        subscriptions = (
            await self.get_subscriptions(refresh=False)
            if not custom_list
            else custom_list
        )
        valid = None
        for subscription in subscriptions:
            if identifier == subscription.username or identifier == subscription.id:
                valid = subscription
                break
        return valid

    async def get_subscriptions(
        self, refresh: bool = True, identifiers: list[int | str] = []
    ) -> list[create_user]:
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        subscriptions_link = endpoint_links().subscriptions
        temp_subscriptions = await self.session_manager.json_request(subscriptions_link)
        subscriptions = temp_subscriptions["response"]["subscriptions"]

        # If user is a creator, add them to the subscription list
        results: list[list[create_user]] = []
        if self.isPerformer:
            subscription = await self.convert_to_user()
            if isinstance(subscription, ErrorDetails):
                return result
            subscription.subscribedByData = {}
            new_date = datetime.now() + relativedelta(years=1)
            subscription.subscribedByData["expiredAt"] = new_date.isoformat()
            subscriptions_ = [subscription]
            results.append(subscriptions_)
        if not identifiers:

            async def multi(item: dict[str, Any]):
                subscription = await self.get_user(item["accountId"])
                valid_subscriptions: list[create_user] = []

                if (
                    isinstance(subscription, create_user)
                    and subscription.following
                    and not subscription.subscribedByData
                ):
                    new_date = datetime.now() + relativedelta(years=1)
                    new_date = int(new_date.timestamp() * 1000)
                    subscription.subscribedByData = {}
                    subscription.subscribedByData["endsAt"] = new_date
                    valid_subscriptions.append(subscription)
                return valid_subscriptions

            with self.get_pool() as pool:
                tasks = pool.starmap(multi, product(subscriptions))
                results += await asyncio.gather(*tasks)
        else:
            for identifier in identifiers:
                results_2 = await self.get_user(identifier)
                results_2 = await api_helper.remove_errors(results_2)
                if isinstance(results_2, create_user):
                    x = [x for x in subscriptions if x["accountId"] == results_2.id]
                    if x:
                        results_2.subscribedByData = {}
                        results_2.subscribedByData["endsAt"] = x[0]["endsAt"]
                    results.append([results_2])
        results = [x for x in results if x is not None]
        results = list(chain(*results))
        self.subscriptions = results
        return results

    async def get_chats(
        self,
        links: list[str] = [],
        limit: int = 25,
        offset: int = 0,
        depth: int = 1,
        refresh: bool = True,
    ) -> list[dict[str, Any]]:
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        multiplier = self.session_manager.max_threads
        temp_limit = limit
        temp_offset = offset
        link = endpoint_links(
            identifier=self.id, global_limit=temp_limit, global_offset=temp_offset
        ).list_chats
        unpredictable_links, new_offset = api_helper.calculate_the_unpredictable(
            link, offset, limit, multiplier, depth
        )
        links = unpredictable_links if depth != 1 else links + unpredictable_links

        results = await self.session_manager.bulk_json_requests(links)
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

    async def get_mass_messages(
        self,
        resume: Optional[list[dict[str, Any]]] = None,
        refresh: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        link = endpoint_links(
            global_limit=limit, global_offset=offset
        ).mass_messages_api
        results = await self.session_manager.json_request(link)
        items = results.get("list", [])
        if not items:
            return items
        if resume:
            for item in items:
                if any(x["id"] == item["id"] for x in resume):
                    resume.sort(key=lambda x: x["id"], reverse=True)
                    self.mass_messages = resume
                    return resume
                else:
                    resume.append(item)

        if results["hasMore"]:
            results2 = self.get_mass_messages(
                resume=resume, limit=limit, offset=limit + offset
            )
            items.extend(results2)
        if resume:
            items = resume

        items.sort(key=lambda x: x["id"], reverse=True)
        self.mass_messages = items
        return items

    async def get_paid_content(
        self,
        check: bool = False,
        refresh: bool = True,
        limit: int = 99,
        offset: int = 0,
        inside_loop: bool = False,
    ) -> list[create_message | create_post]:
        return []

    async def resolve_user(self, post_id: int | None = None):
        user = None
        if post_id:
            post = await self.get_post(post_id)
            if not isinstance(post, ErrorDetails):
                user = post.author
        return user
