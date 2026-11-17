import copy
from pathlib import Path
from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

API_URL = "https://apiv3.fansly.com/api/v1"


class ErrorDetails:
    def __init__(self, result: dict[str, Any]) -> None:
        error = result.get("error", result)
        self.code = error.get("code", 0)
        # Fansly answers {"code": 99, "details": "..."}; transport errors carry "message".
        self.message = error.get("message") or error.get("details") or ""

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


class AuthDetails:
    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
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
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.password = password
        self.proxy_url = proxy_url
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


def _ids(identifiers: "Sequence[int | str]") -> str:
    return ",".join(str(x) for x in identifiers)


class endpoint_links:
    """Fansly API URLs, as built by the web client (main.js)."""

    def __init__(
        self,
        identifier: str | int | None = None,
        global_limit: int = 10,
        global_offset: int = 0,
    ):
        self.full_url_path = API_URL
        self.device_id = f"{API_URL}/device/id"
        self.me = f"{API_URL}/account/me"
        self.settings = f"{API_URL}/account/settings"
        self.users_by_id = f"{API_URL}/account?ids={identifier}"
        self.users_by_username = f"{API_URL}/account?usernames={identifier}"
        self.subscriptions = f"{API_URL}/subscriptions"
        self.lists = f"{API_URL}/lists/account?itemId="
        self.stories_api = f"{API_URL}/mediastoriesnew?accountId={identifier}"
        self.collections_api = f"{API_URL}/uservault/albumsnew?accountId={identifier}"
        self.paid_api = f"{API_URL}/account/media/orders/?limit={global_limit}&offset={global_offset}"

    def list_users(self, identifiers: "Sequence[int | str]"):
        if not identifiers:
            return ""
        key = "ids" if all(str(x).isdigit() for x in identifiers) else "usernames"
        return f"{self.full_url_path}/account?{key}={_ids(identifiers)}"

    def list_followings(self, identifier: int | str, limit: int = 100, offset: int = 0):
        return f"{self.full_url_path}/account/{identifier}/following?before=0&after=0&limit={limit}&offset={offset}"

    def list_chats(self, limit: int = 25, offset: int = 0, search: str = ""):
        return (
            f"{self.full_url_path}/messaging/groups?sortOrder=1&flags=0"
            f"&subscriptionTierId=&listIds=&search={quote(search)}&limit={limit}&offset={offset}"
        )

    def list_messages(self, group_id: int | str, before: int | str = 0, limit: int = 25):
        before_part = f"&before={before}" if before and str(before) != "0" else ""
        return f"{self.full_url_path}/message?groupId={group_id}{before_part}&limit={limit}"

    def timeline(
        self,
        account_id: int | str,
        before: int | str = 0,
        wall_id: int | str = "",
        content_search: str = "",
    ):
        return (
            f"{self.full_url_path}/timelinenew/{account_id}?before={before}&after=0"
            f"&wallId={wall_id}&contentSearch={quote(content_search)}"
        )

    def posts_by_ids(self, identifiers: list[int | str] | list[int] | list[str]):
        return f"{self.full_url_path}/post?ids={_ids(identifiers)}"

    def post_replies(self, post_id: int | str):
        return f"{self.full_url_path}/post/{post_id}/replies"

    def account_media(self, identifiers: list[int | str] | list[int] | list[str]):
        return f"{self.full_url_path}/account/media?ids={_ids(identifiers)}"

    def collection_content(
        self, album_id: int | str, before: int | str = 0, limit: int = 25
    ):
        return f"{self.full_url_path}/uservault/album/content?albumId={album_id}&before={before}&after=0&limit={limit}"

    def list_items(self, list_id: int | str, limit: int = 100, before: int | str = 0):
        before_part = f"&before={before}" if before and str(before) != "0" else ""
        return f"{self.full_url_path}/lists/itemsnew?listId={list_id}&limit={limit}{before_part}"

    def transactions(self, limit: int = 100, offset: int = 0):
        return (
            f"{self.full_url_path}/payments/wallets/transactions?before=0&after=0"
            f"&limit={limit}&offset={offset}&status=&type="
        )
