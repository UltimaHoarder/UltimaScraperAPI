from __future__ import annotations

import copy
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from user_agent import generate_user_agent

from ultima_scraper_api.helpers.main_helper import is_pascal_case

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.onlyfans import DynamicRulesModel


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
            key = key.replace("aws_waf_token", "aws-waf-token")
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
        proxy_url: str | None = None,
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
        self.proxy_url = proxy_url
        self.hashed = hashed
        self.support_2fa = support_2fa
        self.active = active

    def activate_guest(self):
        self.cookie.auth_id = "0"
        self.x_bc = secrets.token_bytes(20).hex()
        self.user_agent = generate_user_agent()
        self.active = True
        return self

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


def create_headers(
    dynamic_rules: DynamicRulesModel,
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
    for remove_header in dynamic_rules.remove_headers:
        remove_header = remove_header.replace("_", "-")
        headers.pop(remove_header)
    return headers


class ContentTypeTransformer:
    def __init__(self, value: str) -> None:
        self._original_value = value
        self.value = (
            self._original_value
            if is_pascal_case(self._original_value)
            else self._original_value.capitalize()
        )

    def plural(self):
        match self.value:
            case "Story":
                final_value = "Stories"
            case "Post":
                final_value = "Posts"
            case "Message":
                final_value = "Messages"
            case "MassMessage":
                final_value = "MassMessages"
            case _:
                raise Exception("key not found")
        return final_value

    def singular(self):
        match self.value:
            case "Stories":
                final_value = "Story"
            case "Posts":
                final_value = "Post"
            case "Messages":
                final_value = "Message"
            case "MassMessages":
                final_value = "MassMessage"
            case _:
                raise Exception("key not found")
        return final_value
