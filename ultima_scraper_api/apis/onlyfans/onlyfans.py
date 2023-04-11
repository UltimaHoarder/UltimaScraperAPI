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
        self.subscriptions: list[create_user] = []
        self.endpoint_links = endpoint_links

    def add_auth(
        self, auth_json: dict[str, Any] = {}, only_active: bool = False
    ) -> create_auth:
        """Creates and appends an auth object to auths property

        Args:
            auth_json (dict[str, str], optional): []. Defaults to {}.
            only_active (bool, optional): [description]. Defaults to False.

        Returns:
            create_auth: [Auth object]
        """
        temp_auth_details = AuthDetails(**auth_json).upgrade_legacy(auth_json)
        auth = create_auth(
            self, max_threads=self.max_threads, auth_details=temp_auth_details
        )
        if only_active and not auth.auth_details.active:
            return auth
        auth.auth_details = temp_auth_details
        auth.extras["settings"] = self.config
        self.auths.append(auth)
        return auth

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
            class ArchivedTypes:
                def __init__(self) -> None:
                    self.Posts = []

                def __iter__(self):
                    for attr, value in self.__dict__.items():
                        yield attr, value

            self.Stories = []
            self.Posts = []
            # self.Archived = ArchivedTypes()
            self.Chats = []
            self.Messages = []
            self.Highlights = []
            self.MassMessages = []

        def __iter__(self):
            for attr, value in self.__dict__.items():
                yield attr, value

        def get_keys(self):
            return [item[0] for item in self]

        async def response_type_to_key(self, value:str):
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
        def find_by_value(self,value:str):
            final_media_type = None
            for media_type, alt_media_types in self.__dict__.items():
                if value in alt_media_types:
                    final_media_type = media_type
            if not final_media_type:
                raise Exception("No media type found")
            return final_media_type