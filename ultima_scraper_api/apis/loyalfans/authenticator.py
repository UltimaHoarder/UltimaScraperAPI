from typing import Any

from user_agent import generate_user_agent

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI
from ultima_scraper_api.managers.session_manager import AuthedSession
from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails


class LoyalFansAuthenticator:
    def __init__(
        self,
        api: "LoyalFansAPI",
        auth_details: "AuthDetails" = None,
        guest: bool = False,
    ) -> None:
        self.api = api
        self.auth_details = auth_details
        self.auth_session = AuthedSession(self, api.session_manager)
        self.auth_attempt = 0
        self.max_attempts = 10
        self.errors: list["ErrorDetails"] = []
        self.active = False
        self.guest = guest
        self.__raw__: dict[str, Any] | None = None

    async def __aenter__(self):
        return await self.login(self.guest)

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self):
        await self.auth_session.active_session.close()

    def create_auth(self):
        return LoyalFansAuthModel(self)

    def create_user(self, auth: LoyalFansAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__, auth)

    async def login(self, guest: bool = False):
        auth_items = self.auth_details
        if guest and auth_items:
            auth_items.cookie.auth_id = "0"
            auth_items.user_agent = generate_user_agent()
            auth_items.active = True

        auth_session = self.auth_session
        session_manager = auth_session.get_session_manager()

        # LoyalFans specific authentication logic
        if guest:
            self.guest = True
            self.__raw__ = {"id": 0, "username": "guest"}  # Guest user data
            return self.create_auth()

        while self.auth_attempt < self.max_attempts:
            await self.process_auth()
            self.auth_attempt += 1

            if self.is_authed():
                return self.create_auth()

            if self.errors:
                error = self.errors[-1]
                if "token" in error.message:
                    break
                if "Please refresh" in error.message:
                    break

        return None

    async def process_auth(self):
        if not self.maxed_out_auth_attempts():
            # Replace with actual LoyalFans API endpoint
            link = "https://www.loyalfans.com/api/v1/auth/user/me?ngsw-bypass=true"
            json_resp = await self.auth_session.json_request(link)
            await self.resolve_auth_errors(json_resp)
            self.__raw__ = json_resp

            if not self.errors and json_resp.get("success"):
                self.auth_details.active = True
                self.auth_details.email = self.__raw__.get("email", "")
            else:
                self.auth_details.active = False
        return self

    def maxed_out_auth_attempts(self):
        return True if self.auth_attempt >= self.max_attempts else False

    def is_authed(self):
        return self.auth_details.active

    async def resolve_auth_errors(self, response: dict[str, Any]):
        if not response.get("success", True):
            error = ErrorDetails(
                code=response.get("code", 401),
                message=response.get("message", "Authentication failed"),
            )
            await api_helper.handle_error_details(error)
            self.errors.append(error)
        else:
            self.errors.clear()

    def create_request_headers(
        self,
        link: str,
        custom_cookies: str = "",
        extra_headers: dict[str, str] | None = None,
    ):
        headers = self.auth_session.headers.copy()
        if "https://www.loyalfans.com/api" in link:
            headers["authorization"] = f"Bearer {self.auth_details.authorization}"
            headers["Referer"] = "https://www.loyalfans.com/"
        if extra_headers:
            headers.update(extra_headers)
        return headers


class Cookie:
    def __init__(self):
        self.auth_id = ""


class ErrorDetails:
    def __init__(self, code: int = 0, message: str = ""):
        self.code = code
        self.message = message
