import copy
import math
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

from user_agent import generate_user_agent

from ultima_scraper_api.managers.session_manager import SessionManager

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.fansly import FanslyAPI

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
                key, value = crumble.strip().split("=")
                new_dict[key] = value
        self.auth_id = new_dict.get("auth_id", "")
        self.sess = new_dict.get("sess", "")
        self.auth_hash = new_dict.get("auth_hash", "")
        self.auth_uniq_ = new_dict.get("auth_uniq_", "")
        self.auth_uid_ = new_dict.get("auth_uid_", "")

    def format(self):
        """
        Typically used for adding cookies to requests
        """
        return self.__dict__

    def convert(self):
        new_dict = ""
        for key, value in self.__dict__.items():
            key = key.replace("auth_uniq_", f"auth_uniq_{self.auth_id}")
            key = key.replace("auth_uid_", f"auth_uid_{self.auth_id}")
            new_dict += f"{key}={value}; "
        new_dict = new_dict.strip()
        return new_dict


class AuthDetails:
    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
        user_agent: str = "",
        email: str = "",
        password: str = "",
        hashed: bool = False,
        support_2fa: bool = True,
        active: bool | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.password = password
        self.hashed = hashed
        self.support_2fa = support_2fa
        self.active = active

    def upgrade_legacy(self, options: dict[str, Any]):
        return self

    def export(self, model: Any = None):
        new_dict = copy.copy(self.__dict__)
        if model:
            for att in new_dict.copy():
                if att not in model.__annotations__:
                    del new_dict[att]
            new_dict["user_id"] = new_dict["id"]
            del new_dict["id"]
        return new_dict


class FanslyAuthenticator:
    def __init__(
        self,
        api: "FanslyAPI",
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
            auth_items.user_agent = generate_user_agent()
        link = endpoint_links().customer
        user_agent = auth_items.user_agent
        dynamic_rules = self.session_manager.dynamic_rules
        a: list[Any] = [dynamic_rules, user_agent, link]
        self.session_manager.headers = create_headers(*a)
        if guest:
            self.guest = True
            self.__raw__ = {}
            return self

        while self.auth_attempt < self.max_attempts:
            await self.process_auth()
            self.auth_attempt += 1

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
            link = endpoint_links().me
            json_resp = await self.session_manager.json_request(link)
            await self.resolve_auth_errors(json_resp)
            if not self.errors:
                self.auth_details.active = True
                self.__raw__ = json_resp
            else:
                if self.auth_details.id:
                    link = endpoint_links(self.auth_details.id).users_by_id
                    json_resp = await self.session_manager.json_request(link)
                    await self.resolve_auth_errors(json_resp)
                    self.__raw__ = json_resp
                self.auth_details.active = False
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
        return new_auth_details


class endpoint_links(object):
    def __init__(
        self,
        identifier: Optional[str | int] = None,
        identifier2: Optional[str | int] = None,
        identifier3: Optional[str | int] = None,
        text: str = "",
        global_limit: int = 10,
        global_offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
        before_id: str = "",
    ):
        domain = "https://apiv3.fansly.com"
        api = "/api/v1"
        full_url_path = f"{domain}{api}"
        self.full_url_path = full_url_path
        self.me = f"{full_url_path}/account/me"
        self.customer = f"{full_url_path}/account?ids={identifier}"
        self.settings = f"{full_url_path}/account/settings"
        self.users_by_id = f"{self.full_url_path}/account?ids={identifier}"
        self.users_by_username = f"{self.full_url_path}/account?usernames={identifier}"
        self.followings = f"{full_url_path}/account/{identifier}/following?before={global_offset}&after=0&limit=100&offset=0"
        self.subscriptions = f"{full_url_path}/subscriptions"
        self.lists = f"https://onlyfans.com/api2/v2/lists?limit={global_limit}&offset={global_offset}"
        self.lists_users = f"https://onlyfans.com/api2/v2/lists/{identifier}/users?limit={global_limit}&offset={global_offset}&query="
        self.list_chats = f"{full_url_path}/messaging/groups?sortOrder=1&flags=0&subscriptionTierId=&search=&limit={global_limit}&offset={global_offset}"
        self.post_by_id = f"https://onlyfans.com/api2/v2/posts/{identifier}"
        self.message_by_id = f"https://onlyfans.com/api2/v2/chats/{identifier}/messages?limit=10&offset=0&firstId={identifier2}&order=desc&skip_users=all&skip_users_dups=1"
        self.search_chat = f"https://onlyfans.com/api2/v2/chats/{identifier}/messages/search?query={text}"
        self.groups_api = f"{full_url_path}/group"
        self.message_api = f"{full_url_path}/message?groupId={identifier}&limit={global_limit}&before={before_id}&order=desc"
        self.search_messages = f"https://onlyfans.com/api2/v2/chats/{identifier}?limit=10&offset=0&filter=&order=activity&query={text}"
        self.mass_messages_api = f"https://onlyfans.com/api2/v2/messages/queue/stats?limit=100&offset=0&format=infinite"
        self.stories_api = (
            f"{full_url_path}/mediastoriesnew?accountId={identifier}&ngsw-bypass=true"
        )
        self.list_highlights = f"https://onlyfans.com/api2/v2/users/{identifier}/stories/highlights?limit=100&offset=0&order=desc"
        self.highlight = f"https://onlyfans.com/api2/v2/stories/highlights/{identifier}"
        self.list_posts_api = self.list_posts(identifier)
        self.post_api = f"{full_url_path}/timeline/{identifier}?before={global_offset}"
        self.collections_api = (
            f"{full_url_path}/uservault/albums?accountId={identifier}"
        )
        self.collection_api = f"{full_url_path}/uservault/album/content?albumId={identifier}&before={global_offset}&after=0&limit={global_limit}"
        self.archived_posts = f"https://onlyfans.com/api2/v2/users/{identifier}/posts/archived?limit={global_limit}&offset={global_offset}&order=publish_date_desc"
        self.archived_stories = f"https://onlyfans.com/api2/v2/stories/archive/?limit=100&offset=0&order=publish_date_desc"
        self.paid_api = f"{full_url_path}/account/media/orders/?limit={global_limit}&offset={global_offset}"
        self.pay = f"https://onlyfans.com/api2/v2/payments/pay"
        self.subscribe = f"https://onlyfans.com/api2/v2/users/{identifier}/subscribe"
        self.like = f"https://onlyfans.com/api2/v2/{identifier}/{identifier2}/like"
        self.favorite = f"https://onlyfans.com/api2/v2/{identifier}/{identifier2}/favorites/{identifier3}"
        self.transactions = (
            f"https://onlyfans.com/api2/v2/payments/all/transactions?limit=10&offset=0"
        )
        self.list_comments_api = f"{full_url_path}/{identifier}/{identifier2}/replies"
        self.two_factor = f"https://onlyfans.com/api2/v2/users/otp/check"

    def list_followings(self, identifier: int, offset: int = 0):
        return f"{self.full_url_path}/account/{identifier}/following?before=0&after=0&limit=100&offset={offset}"

    def list_users(self, identifiers: list[int | str] | list[int] | list[str]):
        identifier_type = "ids"
        if all(isinstance(x, str) and x.isalpha() for x in identifiers):
            identifier_type = "usernames"
        link = ""
        if identifiers:
            link = f"{self.full_url_path}/account?{identifier_type}={','.join([str(x) for x in identifiers])}"
        return link

    def list_posts(
        self,
        content_id: Optional[int | str],
        global_limit: int = 10,
        global_offset: int = 0,
    ):
        return f"{self.full_url_path}/timeline/{content_id}?before={global_offset}"

    def create_links(self, link: str, api_count: int, limit: int = 10, offset: int = 0):
        """
        This function will create a list of links depending on their content count.

        Example:\n
        create_links(link="base_link", api_count=50) will return a list with 5 links.
        """
        final_links: list[str] = []
        if api_count:
            ceil = math.ceil(api_count / limit)
            numbers = list(range(ceil))
            for num in numbers:
                num = num * limit
                link = link.replace(f"limit={limit}", f"limit={limit}")
                new_link = link.replace(f"offset={offset}", f"offset={num}")
                final_links.append(new_link)
        return final_links


def create_headers(
    dynamic_rules: dict[str, Any],
    auth_id: Union[str, int],
    user_agent: str = "",
    link: str = "https://onlyfans.com/",
):
    headers: dict[str, Any] = {}
    headers["user-agent"] = user_agent
    headers["referer"] = link
    headers["user-id"] = str(auth_id)
    headers["x-bc"] = ""
    for remove_header in dynamic_rules["remove_headers"]:
        headers.pop(remove_header)
    return headers


def handle_refresh(object_: object, name: str):
    final_argument = getattr(object_, name)
    return final_argument


class media_types:
    def __init__(self, option={}, assign_states=False) -> None:
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
