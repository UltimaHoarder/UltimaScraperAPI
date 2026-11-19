from typing import Any

import python_socks
from aiohttp_socks import ProxyInfo

from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.extras import (
    AuthDetails,
    ErrorDetails,
    call_api,
)
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI
from ultima_scraper_api.apis.loyalfans.urls import (
    API_URL,
    API_VERSION,
    STANDARD_URL,
    APIRoutes,
)
from ultima_scraper_api.managers.session_manager import AuthedSession

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class LoyalFansAuthenticator:
    """Signs in with the web client's session token (``AuthDetails.authorization``).

    An expired token is renewed once per failure through /auth/refresh-token
    (the web client's own path); a token the server will not renew fails the
    sign-in.
    """

    def __init__(
        self,
        api: LoyalFansAPI,
        auth_details: AuthDetails | None = None,
        guest: bool = False,
    ) -> None:
        self.api = api
        self.auth_details = auth_details or AuthDetails()
        self.auth_session = AuthedSession(self, api.session_manager)
        if self.auth_details.proxy_url:
            try:
                proxy_info = ProxyInfo(
                    *python_socks.parse_proxy_url(self.auth_details.proxy_url)
                )
                self.auth_session.active_session = (
                    self.auth_session.create_client_session(False, proxy_info)
                )
            except ValueError:
                # An unparsable proxy URL: keep the direct session.
                self.auth_details.proxy_url = None
        self.errors: list[ErrorDetails] = []
        self.guest = guest
        self.__raw__: dict[str, Any] | None = None

    async def __aenter__(self):
        return await self.login(self.guest)

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self):
        await self.auth_session.active_session.close()

    def create_auth(self):
        return LoyalFansAuthModel(self)

    def create_user(self, auth: LoyalFansAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__, auth)

    async def login(self, guest: bool = False):
        if guest:
            self.guest = True
            self.__raw__ = {"user": {"uid": "0", "slug": "guest"}}
            self.auth_details.active = True
            return self.create_auth()
        await self.process_auth()
        return self.create_auth() if self.is_authed() else None

    async def process_auth(self):
        if not self.auth_details.token:
            self.errors.append(ErrorDetails(401, "No session token"))
            self.auth_details.active = False
            return self
        status, result = await call_api(self.auth_session, APIRoutes().me())
        if status == 401 and await self.refresh_token(result):
            status, result = await call_api(self.auth_session, APIRoutes().me())
        self.errors.clear()
        me = result.get("response") if status == 200 and result.get("success") else None
        if isinstance(me, dict) and me:
            self.__raw__ = me
            self.auth_details.active = True
        else:
            self.errors.append(ErrorDetails.from_response(result or {"httpCode": status}))
            self.auth_details.active = False
        return self

    async def refresh_token(self, error: dict[str, Any] | None = None) -> bool:
        """Renew an expired session token; True when a new one was stored."""
        if error is not None and error.get("error") != "token_expired":
            return False
        status, result = await call_api(self.auth_session, APIRoutes().refresh_token(), {})
        token = result.get("token") if status == 200 and result.get("success") else None
        if not token:
            return False
        self.auth_details.authorization = str(token)
        return True

    def is_authed(self):
        return bool(self.auth_details.active)

    def create_request_headers(
        self,
        link: str,
        custom_cookies: str = "",
        extra_headers: dict[str, str] | None = None,
    ):
        headers = self.auth_session.headers.copy()
        headers["user-agent"] = self.auth_details.user_agent or DEFAULT_USER_AGENT
        if link.startswith(API_URL):
            headers["x-api-version"] = API_VERSION
            headers["referer"] = f"{STANDARD_URL}/"
            headers["origin"] = STANDARD_URL
            if self.auth_details.token and not self.guest:
                headers["authorization"] = f"Bearer {self.auth_details.token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers
