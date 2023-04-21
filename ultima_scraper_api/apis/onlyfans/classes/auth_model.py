from __future__ import annotations

import asyncio
import math
from asyncio.tasks import Task
from datetime import datetime
from itertools import chain, product
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from dateutil.relativedelta import relativedelta
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.onlyfans.classes.extras import (
    AuthDetails,
    ErrorDetails,
    create_headers,
    endpoint_links,
)
from ultima_scraper_api.apis.onlyfans.classes.message_model import create_message
from ultima_scraper_api.apis.onlyfans.classes.post_model import create_post
from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user
from ultima_scraper_api.managers.session_manager import SessionManager
from user_agent import generate_user_agent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

# auth_model.py handles functions that only relate to the authenticated user
# We can create a auth_streamliner that has a parent class of create_user instead


class create_auth(create_user):
    def __init__(
        self,
        api: OnlyFansAPI,
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
            auth_items.cookie.auth_id = "0"
            auth_items.user_agent = generate_user_agent()
        link = endpoint_links().customer
        user_agent = auth_items.user_agent
        auth_id = str(auth_items.cookie.auth_id)
        # expected string error is fixed by auth_id
        dynamic_rules = self.session_manager.dynamic_rules
        a: list[Any] = [dynamic_rules, auth_id, auth_items.x_bc, user_agent, link]
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
            user = await self.get_user(auth_id)
            if isinstance(user, create_user):
                self.update(user.__dict__)
        return self

    async def process_auth(self):
        if not self.active:
            link = endpoint_links().customer
            json_resp = await self.session_manager.json_request(link)
            if json_resp:
                await self.resolve_auth_errors(json_resp)
                if not self.errors:
                    self.active = True
                    self.update(json_resp)
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
        match error_code:
            case 0:
                pass
            case _:
                await api_helper.handle_error_details(error)
        self.errors.append(error)

    async def get_lists(self, refresh: bool = True, limit: int = 100, offset: int = 0):
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        link = endpoint_links(global_limit=limit, global_offset=offset).lists
        json_resp = await self.session_manager.json_request(link)
        self.lists = json_resp
        return json_resp

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

    def find_user_by_identifier(self, identifier: int | str):
        user = [x for x in self.users if x.id == identifier or x.username == identifier]
        return user

    async def get_user(self, identifier: int | str) -> Union[create_user, ErrorDetails]:
        valid_user = self.find_user_by_identifier(identifier)
        if valid_user:
            return valid_user[0]
        else:
            link = endpoint_links(identifier).users
            response = await self.session_manager.json_request(link)
            if not isinstance(response, ErrorDetails):
                response["session_manager"] = self.session_manager
                response = create_user(response, self)
            return response

    async def get_lists_users(
        self,
        identifier: int | str,
        check: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        result, status = await api_helper.default_data(self, refresh=True)
        if status:
            return result
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
        self,
        refresh: bool = True,
        identifiers: list[int | str] = [],
        extra_info: bool = True,
        limit: int = 20,
    ) -> list[create_user]:
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        # if self.subscribesCount > 900:
        #     limit = 100
        ceil = math.ceil(self.subscribesCount / limit)
        a = list(range(ceil))
        offset_array: list[str] = []
        for b in a:
            b = b * limit
            link = endpoint_links(global_limit=limit, global_offset=b).subscriptions
            offset_array.append(link)

        results: list[list[create_user]] = []
        if not identifiers:

            async def multi(item: str):
                link = item
                subscriptions = await self.session_manager.json_request(link)
                valid_subscriptions: list[create_user] = []
                extras = {}
                extras["auth_check"] = ""
                if isinstance(subscriptions, ErrorDetails):
                    return
                subscriptions = [
                    subscription
                    for subscription in subscriptions
                    if "error" != subscription
                ]
                tasks: list[Task[create_user | ErrorDetails]] = []
                for subscription in subscriptions:
                    subscription["session_manager"] = self.session_manager
                    if extra_info:
                        task = asyncio.create_task(
                            self.get_user(subscription["username"])
                        )
                        tasks.append(task)
                results2 = await asyncio.gather(*tasks)
                for result in results2:
                    if isinstance(result, ErrorDetails):
                        continue
                    if not result:
                        pass
                    subscription2: create_user = result
                    for subscription in subscriptions:
                        if subscription["id"] != subscription2.id:
                            continue
                        subscription = subscription | subscription2.__dict__
                        subscription = create_user(subscription, self)
                        if subscription.isBlocked:
                            continue
                        valid_subscriptions.append(subscription)
                return valid_subscriptions

            # If user is a creator, add them to the subscription list
            if self.isPerformer:
                subscription = await self.convert_to_user()
                if isinstance(subscription, ErrorDetails):
                    return result
                subscription.subscribedByData = {}
                new_date = datetime.now() + relativedelta(years=1)
                subscription.subscribedByData["expiredAt"] = new_date.isoformat()
                subscriptions = [subscription]
                results.append(subscriptions)
            with self.get_pool() as pool:
                tasks = pool.starmap(multi, product(offset_array))
                results2 = await asyncio.gather(*tasks)
                results2 = list(filter(None, results2))
                results.extend(results2)
        else:
            for identifier in identifiers:
                if self.id == identifier or self.username == identifier:
                    continue
                link = endpoint_links(identifier=identifier).users
                result = await self.session_manager.json_request(link)
                if isinstance(result, ErrorDetails) or not result["subscribedBy"]:
                    continue
                subscription = create_user(result, self)
                if subscription.isBlocked:
                    continue
                results.append([subscription])
        final_results = [x for x in results if x is not None]
        final_results = list(chain(*final_results))
        self.subscriptions = final_results
        return final_results

    async def get_chats(
        self,
        links: list[str] = [],
        limit: int = 100,
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
        has_more = results[-1]["hasMore"]
        final_results = [x["list"] for x in results]
        final_results = list(chain.from_iterable(final_results))
        for result in final_results:
            result["withUser"] = create_user(result["withUser"], self)
            result["lastMessage"] = create_message(
                result["lastMessage"], result["withUser"]
            )

        if has_more:
            results2 = await self.get_chats(
                limit=limit,
                offset=new_offset,
                depth=depth + 1,
            )
            final_results.extend(results2)

        if depth == 1:
            pass

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
        limit: int = 10,
        offset: int = 0,
        inside_loop: bool = False,
    ) -> list[create_message | create_post] | ErrorDetails:
        result, status = await api_helper.default_data(self, refresh)
        if status:
            return result
        link = endpoint_links(global_limit=limit, global_offset=offset).paid_api
        final_results = await self.session_manager.json_request(link)
        if not isinstance(final_results, ErrorDetails):
            if len(final_results) > 0 and not check:
                results2 = await self.get_paid_content(
                    limit=limit, offset=limit + offset, inside_loop=True
                )
                final_results.extend(results2)
            if not inside_loop:
                temp: list[create_message | create_post] = []
                for final_result in final_results:
                    content = None
                    if final_result["responseType"] == "message":
                        user = create_user(final_result["fromUser"], self)
                        content = create_message(final_result, user)
                    elif final_result["responseType"] == "post":
                        user = create_user(final_result["author"], self)
                        content = create_post(final_result, user)
                    if content:
                        temp.append(content)
                final_results = temp
            self.paid_content = final_results
        return final_results

    async def resolve_user(self, post_id: int | None = None):
        user = None
        if post_id:
            post = await self.get_post(post_id)
            if not isinstance(post, ErrorDetails):
                user = post.author
        return user
