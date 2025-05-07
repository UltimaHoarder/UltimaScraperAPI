from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.fansly.classes.extras import AuthDetails, endpoint_links
from ultima_scraper_api.apis.fansly.classes.message_model import MessageModel
from ultima_scraper_api.apis.fansly.classes.post_model import PostModel
from ultima_scraper_api.apis.fansly.classes.story_model import StoryModel
from ultima_scraper_api.config import UltimaScraperAPIConfig

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel


class FanslyAPI(StreamlinedAPI):
    def __init__(
        self, config: UltimaScraperAPIConfig = UltimaScraperAPIConfig()
    ) -> None:
        self.site_name: Literal["Fansly"] = "Fansly"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: dict[int, "FanslyAuthModel"] = {}
        self.endpoint_links = endpoint_links
        from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator

        self.authenticator = FanslyAuthenticator

    def find_auth(self, identifier: int):
        return self.auths.get(identifier)

    def find_user(self, identifier: int | str):
        return [
            user
            for auth in self.auths.values()
            for user in (
                auth.users.values()
                if isinstance(identifier, str)
                else [auth.users.get(identifier)]
            )
            if user
            and (
                user.username.lower() == identifier.lower()
                if isinstance(identifier, str)
                else True
            )
        ]

    async def login(self, auth_json: dict[str, Any] = {}, guest: bool = False):
        authed = None
        if auth_json:
            authed = self.find_auth(auth_json["id"])
        if not authed:
            temp_auth_details = self.create_auth_details(auth_json)
            authenticator = self.authenticator(self, temp_auth_details)
            authed = await authenticator.login(guest)
            if authed and authenticator.is_authed():
                self.add_auth(authed)
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
                    self.add_auth(authed)
                yield authed
        else:
            yield authed

    async def remove_invalid_auths(self):
        for _, auth in self.auths.copy().items():
            if not auth.is_authed():
                await self.remove_auth(auth)

    async def remove_auth(self, auth: "FanslyAuthModel"):
        await auth.get_requester().active_session.close()
        del self.auths[auth.id]

    def create_auth_details(self, auth_json: dict[str, Any] = {}) -> AuthDetails:
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

        def path_to_key(self, value: Path):
            for content_type, _ in self:
                for part in value.parts:
                    if content_type.lower() == part.lower():
                        return content_type

    class MediaTypes:
        def __init__(self) -> None:
            self.Images = ["photo", "image"]
            self.Videos = ["video", "stream", "gif"]
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
