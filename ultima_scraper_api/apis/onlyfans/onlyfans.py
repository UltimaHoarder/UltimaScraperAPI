from typing import Any, Literal, Optional, Union

from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI
from ultima_scraper_api.apis.onlyfans.classes.auth_model import create_auth
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails, endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user
from ultima_scraper_api.classes.make_settings import Config


class OnlyFansAPI(StreamlinedAPI):
    def __init__(self, config: Config = Config()) -> None:
        self.site_name: Literal["OnlyFans"] = "OnlyFans"
        StreamlinedAPI.__init__(self, self, config)
        self.auths: list[create_auth] = []
        self.users: dict[int, create_user] = {}
        self.endpoint_links = endpoint_links

    def add_user(self, user: create_auth):
        self.users[user.id] = user

    def get_auth(self, identifier: Union[str, int]) -> Optional[create_auth]:
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
            if not auth.check_authed():
                await self.remove_auth(auth)

    async def remove_auth(self, auth: create_auth):
        await auth.session_manager.active_session.close()
        self.auths.remove(auth)

    def create_auth_details(self, auth_json: dict[str, Any] = {}) -> AuthDetails:
        """If you've got a auth.json file, you can load it into python and pass it through here.

        Args:
            auth_json (dict[str, Any], optional): [description]. Defaults to {}.

        Returns:
            auth_details: [auth_details object]
        """
        return AuthDetails(**auth_json).upgrade_legacy(auth_json)

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

    class MediaTypes:
        def __init__(self) -> None:
            self.Images = ["photo"]
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
