from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import httpx

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails, endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.hightlight_model import HighlightModel
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import MassMessageModel
from ultima_scraper_api.apis.onlyfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.onlyfans.classes.post_model import PostModel
from ultima_scraper_api.apis.onlyfans.classes.story_model import StoryModel
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel
from ultima_scraper_api.config import UltimaScraperAPIConfig
from ultima_scraper_api.helpers.main_helper import is_pascal_case

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel


class OnlyFansAPI(StreamlinedAPI):
    def __init__(
        self, config: UltimaScraperAPIConfig = UltimaScraperAPIConfig()
    ) -> None:
        self.site_name: Literal["OnlyFans"] = "OnlyFans"
        site_settings = config.site_apis.get_settings(self.site_name)
        dynamic_rules_url = getattr(site_settings, "dynamic_rules_url")
        while True:
            try:
                self.dynamic_rules = httpx.get(dynamic_rules_url, timeout=300).json()
                break
            except httpx.RequestError:
                continue
        StreamlinedAPI.__init__(self, self, config)
        self.auths: dict[int, "OnlyFansAuthModel"] = {}
        self.endpoint_links = endpoint_links
        from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator

        self.authenticator = OnlyFansAuthenticator

    def find_auth(self, identifier: int):
        return self.auths.get(identifier)

    def find_user(self, identifier: int | str):
        users: list[UserModel] = []
        for auth in self.auths.values():
            user = auth.find_user(identifier)
            if user:
                users.append(user)
        return users

    async def login(self, auth_json: dict[str, Any] = {}, guest: bool = False):
        authed = None
        if auth_json:
            authed = self.find_auth(auth_json["id"])
        if not authed:
            temp_auth_details = self.create_auth_details(auth_json)
            authenticator = self.authenticator(self, temp_auth_details)
            authed = await authenticator.login(guest)
            if authed and authenticator.is_authed():
                issues = await authed.get_login_issues()
                if not guest:
                    authed.issues = issues if issues.get("data") else None
                self.add_auth(authed)
            else:
                await authenticator.close()
        return authed

    @asynccontextmanager
    async def login_context(self, auth_json: dict[str, Any] = {}, guest: bool = False):
        authed = self.find_auth(auth_json["id"])
        if not authed:
            temp_auth_details = self.create_auth_details(auth_json)
            authenticator = self.authenticator(self, temp_auth_details, guest)
            async with authenticator as temp_authed:
                if temp_authed and temp_authed.is_authed():
                    authed = temp_authed
                    issues = await authed.get_login_issues()
                    authed.issues = issues if issues.get("data") else None
                    self.add_auth(authed)
                yield authed
        else:
            yield authed

    async def remove_invalid_auths(self):
        for _, auth in self.auths.copy().items():
            if not auth.is_authed():
                await self.remove_auth(auth)

    async def remove_auth(self, auth: "OnlyFansAuthModel"):
        await auth.get_requester().active_session.close()
        del self.auths[auth.id]

    def create_auth_details(self, auth_json: dict[str, Any] = {}):
        """If you've got a auth.json file, you can load it into python and pass it through here.

        Args:
            auth_json (dict[str, Any], optional): [description]. Defaults to {}.

        Returns:
            auth_details: [auth_details object]
        """
        return AuthDetails(**auth_json).upgrade_legacy(auth_json)

    def convert_api_type_to_key(
        self,
        value: StoryModel | PostModel | MessageModel | Any,
        make_plural: bool = True,
    ):
        if isinstance(value, StoryModel):
            final_value = self.ContentTypeTransformer("Story")
        elif isinstance(value, PostModel):
            final_value = self.ContentTypeTransformer("Post")
        elif isinstance(value, MessageModel):
            final_value = self.ContentTypeTransformer("Message")
        elif isinstance(value, MassMessageModel):
            final_value = self.ContentTypeTransformer("MassMessage")
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

    class CategorizedContent:
        def __init__(self) -> None:
            self.MassMessages: dict[int, MassMessageModel] = {}
            self.Stories: dict[int, StoryModel] = {}
            self.Chats: dict[int, Any] = {}
            self.Messages: dict[int, MessageModel] = {}
            self.Highlights: dict[int, HighlightModel] = {}
            self.Posts: dict[int, PostModel] = {}

        def __iter__(self):
            for attr, value in self.__dict__.items():
                yield attr, value

        def get_keys(self):
            return [item[0] for item in self]

        def path_to_key(self, value: Path):
            for content_type, _ in self:
                for part in value.parts:
                    if content_type.lower() == part.lower():
                        return content_type

    class MediaTypes:
        def __init__(self) -> None:
            self.Images = ["photo", "image"]
            self.Videos = ["video", "stream", "gif", "application"]
            self.Audios = ["audio"]
            self.Texts = ["text"]

        def get_keys(self):
            return [item[0] for item in self.__dict__.items()]

        def find_by_value(self, value: str):
            final_media_type = None
            for media_type, alt_media_types in self.__dict__.items():
                if value in alt_media_types:
                    final_media_type = media_type
            if not final_media_type:
                raise Exception("No media type found")
            return final_media_type
