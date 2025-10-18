from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.authenticator import (
        LoyalFansAuthenticator,
        UserModel,
    )
    from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails
    from ultima_scraper_api.apis.loyalfans.classes.user_model import LoyalFansAPI


class LoyalFansAuthModel(
    StreamlinedAuth["LoyalFansAuthenticator", "LoyalFansAPI", "AuthDetails"]
):
    def __init__(
        self,
        authenticator: "LoyalFansAuthenticator",
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.guest = self.authenticator.guest
        # self.update()

    def update(self):
        if self.user:
            identifier = self.user.id
            username = self.user.username
            self.id = identifier
            self.username = username
            # # This affects scripts that use the username to select profiles
            auth_details = self.get_auth_details()
            auth_details.id = identifier
            # auth_details.username = username

    async def get_user(self, identifier: int | str, refresh: bool = False):
        identifier = str(identifier)
        link = f"https://www.loyalfans.com/api/v2/profile/star/thehornylena?ngsw-bypass=true"
        response = await self.auth_session.json_request(link)
        return response
