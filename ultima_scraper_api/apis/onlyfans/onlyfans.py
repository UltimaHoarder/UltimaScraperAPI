from pathlib import Path
from typing import Any, Literal, Optional, Union

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.onlyfans.classes.auth_model import AuthModel
from ultima_scraper_api.apis.onlyfans.classes.extras import (
    AuthDetails,
    OnlyFansAuthenticator,
    endpoint_links,
)
from ultima_scraper_api.apis.onlyfans.classes.message_model import create_message
from ultima_scraper_api.apis.onlyfans.classes.post_model import create_post
from ultima_scraper_api.apis.onlyfans.classes.story_model import create_story
from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user
from ultima_scraper_api.config import UltimaScraperAPIConfig


class OnlyFansAPI(StreamlinedAPI):
    def __init__(
        self, config: UltimaScraperAPIConfig = UltimaScraperAPIConfig()
    ) -> None:
        self.site_name: Literal["OnlyFans"] = "OnlyFans"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: list[AuthModel] = []
        self.users: dict[int, create_user] = {}
        self.endpoint_links = endpoint_links

    async def login(self, auth_json: dict[str, Any] = {}, guest: bool = False):
        found_auths = [x for x in self.auths if auth_json["id"] == x.id]
        if found_auths:
            authed = found_auths[0]
        else:
            temp_auth_details = self.create_auth_details(auth_json)
            authenticator = OnlyFansAuthenticator(self, temp_auth_details)
            auth = await authenticator.login(guest)
            authed = self.add_auth(auth)
            if isinstance(authed, AuthModel):
                if authed.is_authed():
                    issues = await authed.get_login_issues()
                    authed.issues = issues if issues["data"] else None
        return authed

    def add_user(self, user: create_user):
        self.users[user.id] = user

    def get_auth(self, identifier: Union[str, int]) -> Optional[AuthModel]:
        final_auth = None
        for auth in self.auths:
            if auth.id == identifier:
                final_auth = auth
            elif auth.username == identifier:
                final_auth = auth
            if final_auth:
                break
        return final_auth

    async def remove_invalid_auths(self):
        for auth in self.auths.copy():
            if not auth.is_authed():
                await self.remove_auth(auth)

    async def remove_auth(self, auth: AuthModel):
        await auth.session_manager.active_session.close()
        self.auths.remove(auth)

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
        value: create_story | create_post | create_message | Any,
        make_plural: bool = True,
    ):
        if isinstance(value, create_story):
            final_value = self.ContentTypeTransformer("Story")
        elif isinstance(value, create_post):
            final_value = self.ContentTypeTransformer("Post")
        elif isinstance(value, create_message):
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
            self.value = value

        def plural(self):
            match self.value.capitalize():
                case "Story":
                    final_value = "Stories"
                case "Post":
                    final_value = "Posts"
                case "Message":
                    final_value = "Messages"
                case _:
                    raise Exception("key not found")
            if self.value[0].isupper():
                final_value = final_value.capitalize()
            return final_value

        def singular(self):
            match self.value.capitalize():
                case "Stories":
                    final_value = "Story"
                case "Posts":
                    final_value = "Post"
                case "Messages":
                    final_value = "Message"
                case _:
                    raise Exception("key not found")
            if self.value[0].isupper():
                final_value = final_value.capitalize()
            return final_value

    class ContentTypes:
        def __init__(self) -> None:
            self.Stories = []
            self.Posts = []
            self.Chats = []
            self.Messages = []
            self.Highlights = []
            self.MassMessages = []

        def __iter__(self):
            for attr, value in self.__dict__.items():
                yield attr, value

        def get_keys(self):
            return [item[0] for item in self]

        async def response_type_to_key(self, value: str):
            result = [x[0] for x in self if x[0].lower() == f"{value}s"]
            if result:
                return result[0]

        def path_to_key(self, value: Path):
            for content_type, _ in self:
                for part in value.parts:
                    if content_type.lower() == part.lower():
                        return content_type

        def convert_to_key(self, value: str):
            match value.lower():
                case "story":
                    final_value = "Stories"
                case "post":
                    final_value = "Posts"
                case "message":
                    final_value = "Messages"
                case _:
                    raise Exception("convert_to_key not found")
            return final_value

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
