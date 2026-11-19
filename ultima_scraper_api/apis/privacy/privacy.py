from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.privacy.classes.extras import AuthDetails
from ultima_scraper_api.apis.privacy.classes.message_model import MessageModel
from ultima_scraper_api.apis.privacy.classes.post_model import PostModel
from ultima_scraper_api.apis.privacy.urls import APIRoutes
from ultima_scraper_api.config import UltimaScraperAPIConfig
from ultima_scraper_api.managers.websocket_manager import WebSocketManager

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.auth_model import PrivacyAuthModel


class PrivacyAPI(StreamlinedAPI):
    def __init__(
        self,
        config: UltimaScraperAPIConfig | None = None,
        websocket_manager: WebSocketManager | None = None,
    ) -> None:
        config = config or UltimaScraperAPIConfig()
        self.site_name: Literal["Privacy"] = "Privacy"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: dict[int, PrivacyAuthModel] = {}
        self.api_routes = APIRoutes()
        self.websocket_manager = (
            websocket_manager if websocket_manager else WebSocketManager(config=config)
        )
        self.websocket_impl_class = None

        from ultima_scraper_api.apis.privacy.authenticator import PrivacyAuthenticator

        self.authenticator = PrivacyAuthenticator

    def find_auth(self, identifier: int):
        return self.auths.get(identifier)

    def find_user(self, identifier: int | str):
        found = [auth.find_user(identifier) for auth in self.auths.values()]
        return [user for user in found if user]

    async def login(self, auth_json: dict[str, Any] | None = None, guest: bool = False):
        auth_json = auth_json or {}
        authed = self.find_auth(auth_json["id"]) if auth_json.get("id") else None
        if not authed:
            authenticator = self.authenticator(self, self.create_auth_details(auth_json))
            authed = await authenticator.login(guest)
            if authed and authenticator.is_authed():
                self.add_auth(authed)
            else:
                await authenticator.close()
        return authed

    @asynccontextmanager
    async def login_context(self, auth_json: dict[str, Any] | None = None, guest: bool = False):
        auth_json = auth_json or {}
        authed = self.find_auth(auth_json["id"]) if auth_json.get("id") else None
        if authed:
            yield authed
            return
        authenticator = self.authenticator(self, self.create_auth_details(auth_json), guest)
        async with authenticator as temp_authed:
            if temp_authed and temp_authed.is_authed():
                self.add_auth(temp_authed)
                yield temp_authed
            else:
                yield None

    async def remove_invalid_auths(self):
        for auth in list(self.auths.values()):
            if not auth.is_authed():
                await self.remove_auth(auth)

    def create_auth_details(self, auth_json: dict[str, Any] | None = None) -> AuthDetails:
        auth_json = auth_json or {}
        return AuthDetails(**auth_json).upgrade_legacy(auth_json)

    def convert_api_type_to_key(self, value: Any, make_plural: bool = True):
        if isinstance(value, PostModel):
            key = "Post"
        elif isinstance(value, MessageModel):
            key = "Message"
        else:
            raise TypeError(f"Not Privacy content: {type(value).__name__}")
        return f"{key}s" if make_plural else key

    class CategorizedContent:
        def __init__(self) -> None:
            self.Chats: dict[int, Any] = {}
            self.Messages: dict[int, MessageModel] = {}
            self.Posts: dict[int, PostModel] = {}

        def __iter__(self):
            yield from self.__dict__.items()

        def get_keys(self):
            return [item[0] for item in self]

        def path_to_key(self, value: Path):
            for content_type, _ in self:
                for part in value.parts:
                    if content_type.lower() == part.lower():
                        return content_type
            return None

    from ultima_scraper_api.helpers import MediaTypes
