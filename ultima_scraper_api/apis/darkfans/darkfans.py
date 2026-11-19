import re
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Literal

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.darkfans.classes.extras import AuthDetails, parse_cookie
from ultima_scraper_api.apis.darkfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.darkfans.classes.post_model import PostModel
from ultima_scraper_api.apis.darkfans.classes.story_model import StoryModel
from ultima_scraper_api.apis.darkfans.urls import APIRoutes
from ultima_scraper_api.config import UltimaScraperAPIConfig
from ultima_scraper_api.managers.websocket_manager import WebSocketManager

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.auth_model import DarkFansAuthModel
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel


def extract_auth_details_from_curl(credentials: str) -> AuthDetails:
    """AuthDetails from a "Copy as cURL" of any darkfans.com API call.

    Reads the BEARER and refresh_token cookies (``-b`` or a cookie header)
    and the user agent.
    """
    text = credentials.replace("^", "")  # Windows cmd escaping
    cookie_match = re.search(r"""-(?:b|-cookie)\s+(['"])(.+?)\1""", text) or re.search(
        r"""-H\s+(['"])cookie:\s*(.+?)\1""", text, re.IGNORECASE
    )
    cookies = parse_cookie(cookie_match.group(2) if cookie_match else "")
    ua_match = re.search(r"""-H\s+(['"])user-agent:\s*(.+?)\1""", text, re.IGNORECASE)
    if not (cookies.get("BEARER") or cookies.get("refresh_token")):
        raise ValueError("No BEARER or refresh_token cookie in the curl command")
    return AuthDetails(
        authorization=cookies.get("BEARER", ""),
        refresh_token=cookies.get("refresh_token", ""),
        user_agent=ua_match.group(2) if ua_match else "",
    )


class DarkFansAPI(StreamlinedAPI):
    def __init__(
        self,
        config: UltimaScraperAPIConfig | None = None,
        websocket_manager: WebSocketManager | None = None,
    ) -> None:
        config = config or UltimaScraperAPIConfig()
        self.site_name: Literal["DarkFans"] = "DarkFans"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: dict[int, DarkFansAuthModel] = {}
        self.api_routes = APIRoutes()

        # Store WebSocket manager (passed from UltimaScraperAPI)
        self.websocket_manager = (
            websocket_manager if websocket_manager else WebSocketManager(config=config)
        )
        # No live updates yet (the site's chat runs over socket.io at chat.darkfans.*).
        self.websocket_impl_class = None

        from ultima_scraper_api.apis.darkfans.authenticator import (
            DarkFansAuthenticator,
        )

        self.authenticator = DarkFansAuthenticator

    def find_auth(self, identifier: int):
        return self.auths.get(identifier)

    def find_user(self, identifier: int | str):
        users: list[UserModel] = []
        for auth in self.auths.values():
            user = auth.find_user(identifier)
            if user:
                users.append(user)
        return users

    async def login(
        self,
        auth_json: dict[str, Any] | None = None,
        curl_string: str | None = None,
        guest: bool = False,
    ):
        auth_json = auth_json or {}
        authed = None
        if auth_json.get("id"):
            authed = self.find_auth(auth_json["id"])
        if not authed:
            if curl_string:
                temp_auth_details = extract_auth_details_from_curl(curl_string)
            else:
                temp_auth_details = self.create_auth_details(auth_json)
            authenticator = self.authenticator(self, temp_auth_details)
            authed = await authenticator.login(guest)
            if authed and authenticator.is_authed():
                self.add_auth(authed)
                # Don't close authenticator - auth model reuses its session!
            else:
                # Only close on failure (auth model wasn't created)
                await authenticator.close()
        return authed

    @asynccontextmanager
    async def login_context(
        self,
        auth_json: dict[str, Any] | None = None,
        curl_string: str | None = None,
        guest: bool = False,
    ):
        auth_json = auth_json or {}
        authed = None
        if auth_json.get("id"):
            authed = self.find_auth(auth_json["id"])
        if not authed:
            temp_auth_details = self.create_auth_details(auth_json)
            authenticator = self.authenticator(self, temp_auth_details, guest)
            async with authenticator as temp_authed:
                if temp_authed and temp_authed.is_authed():
                    authed = temp_authed
                    self.add_auth(authed)
                yield authed
        else:
            yield authed

    async def remove_invalid_auths(self):
        for _, auth in self.auths.copy().items():
            if not auth.is_authed():
                await self.remove_auth(auth)

    def create_auth_details(self, auth_json: dict[str, Any] | None = None):
        """Create auth details from JSON configuration.

        Args:
            auth_json (dict[str, Any], optional): Authentication configuration. Defaults to {}.

        Returns:
            AuthDetails: Authentication details object
        """
        return AuthDetails(**(auth_json or {}))

    def convert_api_type_to_key(
        self,
        value: PostModel | MessageModel | Any,
        make_plural: bool = True,
    ):
        if isinstance(value, StoryModel):
            final_value = self.ContentTypeTransformer("Story")
        elif isinstance(value, PostModel):
            final_value = self.ContentTypeTransformer("Post")
        elif isinstance(value, MessageModel):
            final_value = self.ContentTypeTransformer("Message")
        else:
            raise Exception("api content type not found")
        if make_plural:
            final_value = final_value.plural()
        else:
            final_value = final_value.value
        return final_value

    class ContentTypeTransformer:
        def __init__(self, value: str) -> None:
            self._original_value = value
            self.value = value.capitalize()

        def plural(self):
            match self.value:
                case "Story":
                    final_value = "Stories"
                case "Post":
                    final_value = "Posts"
                case "Message":
                    final_value = "Messages"
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
                case _:
                    raise Exception("key not found")
            return final_value

    class CategorizedContent:
        def __init__(self) -> None:
            self.Stories: dict[int, StoryModel] = {}
            self.Chats: dict[int, Any] = {}
            self.Messages: dict[int, MessageModel] = {}
            self.Posts: dict[int, PostModel] = {}

        def __iter__(self):
            for attr, value in self.__dict__.items():
                yield attr, value

        def get_keys(self):
            return [item[0] for item in self]

    # Use centralized MediaTypes from helpers
    from ultima_scraper_api.helpers import MediaTypes
