import copy
import math
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, Union
from urllib.parse import parse_qs, urlparse

from ultima_scraper_api.managers.session_manager import SessionManager
from user_agent import generate_user_agent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

from ultima_scraper_api.apis import api_helper


class ErrorDetails:
    def __init__(self, result: dict[str, Any]) -> None:
        error = result["error"] if "error" in result else result
        self.code = error["code"]
        self.message = error["message"]

    async def format(self, extras: dict[str, Any]):
        match self.code:
            case 0:
                match self.message:
                    case "User not found":
                        link = Path(extras["link"])
                        self.message = f"{link.name} not found"
                    case _:
                        pass
            case _:
                pass
        return self


class CookieParser:
    def __init__(self, options: str) -> None:
        new_dict: dict[str, Any] = {}
        for crumble in options.strip().split(";"):
            if crumble:
                split_value = crumble.strip().split("=", 1)
                if len(split_value) >= 2:
                    key, value = split_value
                    new_dict[key] = value
        self.auth_id = new_dict.get("auth_id", "")
        self.sess = new_dict.get("sess", "")
        self.auth_hash = new_dict.get("auth_hash", "")
        self.auth_uniq_ = new_dict.get("auth_uniq_", "")
        self.auth_uid_ = new_dict.get("auth_uid_", "")
        self.aws_waf_token = new_dict.get("aws-waf-token", "")

    def format(self):
        """
        Typically used for adding cookies to requests
        """
        final_dict = self.__dict__.copy()
        final_dict["aws-waf-token"] = final_dict["aws_waf_token"]
        final_dict.pop("aws_waf_token")
        return final_dict

    def convert(self):
        new_dict = ""
        for key, value in self.__dict__.items():
            key = key.replace("auth_uniq_", f"auth_uniq_{self.auth_id}")
            key = key.replace("auth_uid_", f"auth_uid_{self.auth_id}")
            key = key.replace("aws_waf_token", f"aws-waf-token")
            new_dict += f"{key}={value}; "
        new_dict = new_dict.strip()
        return new_dict


class AuthDetails:
    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        cookie: str = "",
        x_bc: str = "",
        user_agent: str = "",
        email: str = "",
        password: str = "",
        hashed: bool = False,
        support_2fa: bool = True,
        active: bool | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.cookie = CookieParser(cookie)
        self.x_bc = x_bc
        self.user_agent = user_agent
        self.email = email
        self.password = password
        self.hashed = hashed
        self.support_2fa = support_2fa
        self.active = active

    def upgrade_legacy(self, options: dict[str, Any]):
        if "cookie" not in options:
            self = legacy_auth_details(options).upgrade(self)
        return self

    def export(self, model: Any = None):
        new_dict = copy.copy(self.__dict__)
        cookie = self.cookie.convert()
        results = [
            x for x in cookie.replace(" ", "").split(";") if x and x.split("=")[1]
        ]
        new_dict["cookie"] = cookie if results else ""
        if model:
            for att in new_dict.copy():
                if att not in model.__annotations__:
                    del new_dict[att]
            new_dict["user_id"] = new_dict["id"]
            del new_dict["id"]
        return new_dict


class OnlyFansAuthenticator:
    def __init__(
        self,
        api: "OnlyFansAPI",
        auth_details: AuthDetails = AuthDetails(),
        max_threads: int = -1,
    ) -> None:
        self.api = api
        self.auth_details = auth_details
        self.session_manager = SessionManager(self, max_threads=max_threads)
        self.auth_attempt = 0
        self.max_attempts = 10
        self.errors: list[ErrorDetails] = []
        self.active = False
        self.guest = False
        self.__raw__: dict[str, Any] | None = None

    async def login(self, guest: bool = False):
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
            self.__raw__ = {}
            return self

        while self.auth_attempt < self.max_attempts:
            await self.process_auth()
            self.auth_attempt += 1

            async def resolve_auth(auth: OnlyFansAuthenticator):
                if self.errors:
                    error = self.errors[-1]
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
            if not self.is_authed():
                if self.errors:
                    error = self.errors[-1]
                    error_message = error.message
                    if "token" in error_message:
                        break
                    if "Code wrong" in error_message:
                        break
                    if "Please refresh" in error_message:
                        break
                continue
            else:
                break
        return self

    async def process_auth(self):
        if not self.maxed_out_auth_attempts():
            link = endpoint_links().customer
            json_resp = await self.session_manager.json_request(link)
            await self.resolve_auth_errors(json_resp)
            if not self.errors:
                self.auth_details.active = True
                self.__raw__ = json_resp
            else:
                link = endpoint_links(self.auth_details.cookie.auth_id).users
                json_resp = await self.session_manager.json_request(link)
                await self.resolve_auth_errors(json_resp)
                self.auth_details.active = False
                self.__raw__ = json_resp
        return self

    def maxed_out_auth_attempts(self):
        return True if self.auth_attempt >= self.max_attempts else False

    def is_authed(self):
        return self.auth_details.active

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
            error_message = "Invalid Auth Info"
        error.code = error_code
        error.message = error_message
        match error_code:
            case 0:
                pass
            case _:
                await api_helper.handle_error_details(error)
        self.errors.append(error)


class legacy_auth_details:
    def __init__(self, option: dict[str, Any] = {}):
        self.username = option.get("username", "")
        self.auth_id = option.get("auth_id", "")
        self.sess = option.get("sess", "")
        self.user_agent = option.get("user_agent", "")
        self.auth_hash = option.get("auth_hash", "")
        self.auth_uniq_ = option.get("auth_uniq_", "")
        self.x_bc = option.get("x_bc", "")
        self.email = option.get("email", "")
        self.password = option.get("password", "")
        self.hashed = option.get("hashed", False)
        self.support_2fa = option.get("support_2fa", True)
        self.active = option.get("active", True)

    def upgrade(self, new_auth_details: AuthDetails):
        new_dict = ""
        for key, value in self.__dict__.items():
            value = value if value != None else ""
            skippable = ["username", "user_agent"]
            if key not in skippable:
                new_dict += f"{key}={value}; "
        new_dict = new_dict.strip()
        new_auth_details.cookie = CookieParser(new_dict)
        return new_auth_details


class endpoint_links(object):
    def __init__(
        self,
        identifier: Optional[int | str] = None,
        identifier2: Optional[int | str] = None,
        identifier3: Optional[int | str] = None,
        text: str = "",
        global_limit: int = 10,
        global_offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ):
        domain = "https://onlyfans.com"
        api = "/api2/v2"
        full_url_path = f"{domain}{api}"
        self.full_url_path = full_url_path
        self.login_issues = f"{full_url_path}/issues/login"
        self.customer = f"https://onlyfans.com/api2/v2/users/me"
        self.users = f"https://onlyfans.com/api2/v2/users/{identifier}"
        self.subscriptions = f"{full_url_path}/subscriptions/subscribes?limit={global_limit}&offset={global_offset}&type={identifier}"
        self.lists = f"https://onlyfans.com/api2/v2/lists?limit=100&offset=0"
        self.lists_users = f"https://onlyfans.com/api2/v2/lists/{identifier}/users?limit={global_limit}&offset={global_offset}&query="
        self.list_chats = f"https://onlyfans.com/api2/v2/chats?limit={global_limit}&offset={global_offset}&order=desc"
        self.post_by_id = f"https://onlyfans.com/api2/v2/posts/{identifier}"
        self.message_by_id = f"https://onlyfans.com/api2/v2/chats/{identifier}/messages?limit=10&offset=0&firstId={identifier2}&order=desc&skip_users=all&skip_users_dups=1"
        self.search_chat = f"https://onlyfans.com/api2/v2/chats/{identifier}/messages/search?query={text}"
        self.message_api = f"https://onlyfans.com/api2/v2/chats/{identifier}/messages?limit={global_limit}&id={global_offset}"
        self.search_messages = f"https://onlyfans.com/api2/v2/chats/{identifier}?limit=10&offset=0&filter=&order=activity&query={text}"
        self.mass_messages_api = f"https://onlyfans.com/api2/v2/messages/queue/stats?limit=100&offset=0&format=infinite"
        self.stories_api = f"https://onlyfans.com/api2/v2/users/{identifier}/stories?limit=100&offset=0&order=desc"
        self.list_highlights = f"https://onlyfans.com/api2/v2/users/{identifier}/stories/highlights?limit=100&offset=0&order=desc"
        self.highlight = f"https://onlyfans.com/api2/v2/stories/highlights/{identifier}"
        self.list_posts_api = self.list_posts(identifier)
        self.archived_posts = f"https://onlyfans.com/api2/v2/users/{identifier}/posts/archived?limit={global_limit}&offset={global_offset}&order=publish_date_desc"
        self.archived_stories = f"https://onlyfans.com/api2/v2/stories/archive/?limit=100&offset=0&order=publish_date_desc"
        self.paid_api = f"https://onlyfans.com/api2/v2/posts/paid?limit={global_limit}&offset={global_offset}"
        self.pay = f"https://onlyfans.com/api2/v2/payments/pay"
        self.subscribe = f"https://onlyfans.com/api2/v2/users/{identifier}/subscribe"
        self.like = f"https://onlyfans.com/api2/v2/{identifier}/{identifier2}/like"
        self.favorite = f"https://onlyfans.com/api2/v2/{identifier}/{identifier2}/favorites/{identifier3}"
        self.transactions = (
            f"https://onlyfans.com/api2/v2/payments/all/transactions?limit=10&offset=0"
        )
        self.list_comments_api = f"{full_url_path}/{identifier}/{identifier2}/comments?limit={global_limit}&offset={global_offset}&sort={sort_order}"
        self.subscription_count = f"{full_url_path}/subscriptions/count/all"
        self.socials = f"{full_url_path}/users/{identifier}/social/buttons"
        self.spotify = f"{full_url_path}/users/{identifier}/social/spotify"
        self.two_factor = f"{full_url_path}/users/otp/check"
        self.drm_server = f"{full_url_path}/users/media/{identifier}/drm/{identifier2}/{identifier3}?type=widevine"

    def list_posts(
        self,
        content_id: Optional[int | str],
        global_limit: int = 10,
        global_offset: int = 0,
    ):
        return f"{self.full_url_path}/users/{content_id}/posts?limit={global_limit}&offset={global_offset}&order=publish_date_desc&skip_users_dups=0"

    def list_comments(
        self,
        content_type: str,
        content_id: Optional[int | str],
        global_limit: int = 10,
        global_offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ):
        content_type = f"{content_type}s" if content_type[0] != "s" else content_type
        return f"{self.full_url_path}/{content_type}/{content_id}/comments?limit={global_limit}&offset={global_offset}&sort={sort_order}"

    def create_links(self, url: str, api_count: int, limit: int = 10, offset: int = 0):
        """
        This function will create a list of links depending on their content count.

        Example:\n
        create_links(link="base_link", api_count=50) will return a list with 5 links if limit=10.
        """
        final_links: list[str] = []
        if api_count:
            ceil = math.ceil(api_count / limit)
            numbers = list(range(ceil))
            for num in numbers:
                num = num * limit
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                limit_value = query_params["limit"][0]
                url = url.replace(f"limit={limit_value}", f"limit={limit}")
                new_link = url.replace(f"offset={offset}", f"offset={num}")
                final_links.append(new_link)
        return final_links


def create_headers(
    dynamic_rules: dict[str, Any],
    auth_id: Union[str, int],
    x_bc: str,
    user_agent: str = "",
    link: str = "https://onlyfans.com/",
):
    headers: dict[str, Any] = {}
    headers["user-agent"] = user_agent
    headers["referer"] = link
    headers["x-bc"] = x_bc
    headers["user-id"] = str(auth_id)
    for remove_header in dynamic_rules["remove_headers"]:
        headers.pop(remove_header)
    return headers


class media_types:
    def __init__(
        self, option: dict[str, Any] = {}, assign_states: bool = False
    ) -> None:
        self.Images = option.get("Images", [])
        self.Videos = option.get("Videos", [])
        self.Audios = option.get("Audios", [])
        self.Texts = option.get("Texts", [])
        if assign_states:
            for k, v in self:
                setattr(self, k, assign_states())

    def remove_empty(self):
        copied = copy.deepcopy(self)
        for k, v in copied:
            if not v:
                delattr(self, k)
            print
        return self

    def get_status(self) -> list:
        x = []
        for key, item in self:
            for key2, item2 in item:
                new_status = list(chain.from_iterable(item2))
                x.extend(new_status)
        return x

    def extract(self, string: str) -> list:
        a = self.get_status()
        source_list = [getattr(x, string, None) for x in a]
        x = list(set(source_list))
        return x

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value
