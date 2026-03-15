import re
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Literal

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails
from ultima_scraper_api.apis.loyalfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.loyalfans.classes.post_model import PostModel
from ultima_scraper_api.config import UltimaScraperAPIConfig
from ultima_scraper_api.managers.websocket_manager import WebSocketManager

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


def extract_auth_details_from_curl(credentials: str) -> AuthDetails:
    # Support Windows-style curl which escapes quotes with ^ and may include ^ characters
    windows_curl = credentials.replace("^", "")

    # Try -H "cookie: ..." first, fallback to -b "..." formats for cookies (both *nix and windows-style)
    cookie_match = re.search(r'-H\s*"cookie:\s*([^\"]+)"', windows_curl, re.I)
    if not cookie_match:
        cookie_match = re.search(r"-H\s*'cookie:\s*([^']+)'", windows_curl, re.I)
    if not cookie_match:
        cookie_match = re.search(r'-b\s*"([^\"]+)"', windows_curl, re.I)
    if not cookie_match:
        cookie_match = re.search(r"-b\s*'([^']+)'", windows_curl, re.I)

    options = cookie_match.group(1) if cookie_match else "N/A"
    new_dict: dict[str, Any] = {}
    for crumble in options.strip().split(";"):
        if crumble:
            split_value = crumble.strip().split("=", 1)
            if len(split_value) >= 2:
                key, value = split_value
                new_dict[key] = value
    # First try to extract an Authorization: Bearer <token> header from the curl string
    auth_match = re.search(
        r"-H\s*\"authorization:\s*Bearer\s*([^\"]+)\"", windows_curl, re.I
    )
    if not auth_match:
        auth_match = re.search(
            r"-H\s*'authorization:\s*Bearer\s*([^']+)'", windows_curl, re.I
        )
    if not auth_match:
        # Also accept header formats without surrounding quotes
        auth_match = re.search(
            r"-H\s*authorization:\s*Bearer\s*([^\s]+)", windows_curl, re.I
        )

    # Fallback: some users may provide session cookie (NEXOSESSION) instead of Authorization header
    authorization = ""
    if auth_match:
        authorization = auth_match.group(1)
    elif "NEXOSESSION" in new_dict:
        authorization = new_dict["NEXOSESSION"]

    ua_match = re.search(r'-H\s*"user-agent:\s*([^\"]+)"', windows_curl, re.I)
    if not ua_match:
        ua_match = re.search(r"-H\s*'user-agent:\s*([^']+)'", windows_curl, re.I)
    if not ua_match:
        ua_match = re.search(r"-H\s*user-agent:\s*([^\s]+)", windows_curl, re.I)

    if not (cookie_match and authorization and ua_match):
        raise ValueError(
            "Could not parse cookie, x-bc, or user-agent from curl command"
        )

    return AuthDetails(
        authorization=authorization,
        user_agent=ua_match.group(1),
    )


class LoyalFansAPI(StreamlinedAPI):
    def __init__(
        self,
        config: UltimaScraperAPIConfig = UltimaScraperAPIConfig(),
        websocket_manager: WebSocketManager | None = None,
    ) -> None:
        self.site_name: Literal["LoyalFans"] = "LoyalFans"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: dict[int, "LoyalFansAuthModel"] = {}

        # Store WebSocket manager (passed from UltimaScraperAPI)
        self.websocket_manager = (
            websocket_manager if websocket_manager else WebSocketManager(config=config)
        )
        # TODO: Implement LoyalFansWebSocket class
        self.websocket_impl_class = None  # LoyalFansWebSocket when implemented

        from ultima_scraper_api.apis.loyalfans.authenticator import (
            LoyalFansAuthenticator,
        )

        self.authenticator = LoyalFansAuthenticator

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
        auth_json: dict[str, Any] = {},
        curl_string: str | None = None,
        guest: bool = False,
    ):
        authed = None
        if auth_json:
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
        auth_json: dict[str, Any] = {},
        curl_string: str | None = None,
        guest: bool = False,
    ):
        authed = None
        if auth_json:
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

    async def remove_auth(self, auth: "LoyalFansAuthModel"):
        await auth.get_requester().active_session.close()
        del self.auths[auth.id]

    def create_auth_details(self, auth_json: dict[str, Any] = {}):
        """Create auth details from JSON configuration.

        Args:
            auth_json (dict[str, Any], optional): Authentication configuration. Defaults to {}.

        Returns:
            AuthDetails: Authentication details object
        """
        return AuthDetails(**auth_json)

    def convert_api_type_to_key(
        self,
        value: PostModel | MessageModel | Any,
        make_plural: bool = True,
    ):
        if isinstance(value, PostModel):
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
                case "Post":
                    final_value = "Posts"
                case "Message":
                    final_value = "Messages"
                case _:
                    raise Exception("key not found")
            return final_value

        def singular(self):
            match self.value:
                case "Posts":
                    final_value = "Post"
                case "Messages":
                    final_value = "Message"
                case _:
                    raise Exception("key not found")
            return final_value

    class CategorizedContent:
        def __init__(self) -> None:
            self.Messages: dict[int, MessageModel] = {}
            self.Posts: dict[int, PostModel] = {}

        def __iter__(self):
            for attr, value in self.__dict__.items():
                yield attr, value

        def get_keys(self):
            return [item[0] for item in self]

    # Use centralized MediaTypes from helpers
    from ultima_scraper_api.helpers import MediaTypes
