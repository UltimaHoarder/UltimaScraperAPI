import asyncio
from typing import Any

import python_socks
from aiohttp_socks import ProxyInfo

from ultima_scraper_api.apis.darkfans.classes.auth_model import DarkFansAuthModel
from ultima_scraper_api.apis.darkfans.classes.extras import (
    AuthDetails,
    ErrorDetails,
    call_api,
)
from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel
from ultima_scraper_api.apis.darkfans.darkfans import DarkFansAPI
from ultima_scraper_api.apis.darkfans.urls import (
    API_URL,
    COMMUNITY,
    STANDARD_URL,
    APIRoutes,
)
from ultima_scraper_api.managers.session_manager import AuthedSession

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class DarkFansAuthenticator:
    """Signs in with the web client's cookies: ``BEARER`` (``authorization``)
    and ``refresh_token``.

    The JWT lasts an hour; when it has expired (or only a refresh token is
    given) it is renewed through POST /auth/refresh. The server answers with a
    new JWT and keeps the refresh token (seen 2026-11-17), so renewing does not
    sign out the browser the cookies came from; a rotated refresh token, if
    the server ever sends one, replaces the stored one.
    """

    def __init__(
        self,
        api: DarkFansAPI,
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
        self._refresh_lock = asyncio.Lock()

    async def __aenter__(self):
        return await self.login(self.guest)

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self):
        await self.auth_session.active_session.close()

    def create_auth(self):
        return DarkFansAuthModel(self)

    def create_user(self, auth: DarkFansAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__, auth)

    async def login(self, guest: bool = False):
        if guest:
            self.guest = True
            self.__raw__ = {"id": "0", "username": "guest"}
            self.auth_details.active = True
            return self.create_auth()
        await self.process_auth()
        return self.create_auth() if self.is_authed() else None

    async def process_auth(self):
        if not (self.auth_details.token or self.auth_details.refresh_token):
            self.errors.append(ErrorDetails(401, "No session cookie"))
            self.auth_details.active = False
            return self
        status, result = 401, {}
        if self.auth_details.token:
            status, result, _ = await call_api(self.auth_session, APIRoutes().me())
        if status == 401 and await self.refresh_token():
            status, result, _ = await call_api(self.auth_session, APIRoutes().me())
        self.errors.clear()
        data = result.get("data") if status == 200 else None
        me = data.get("attributes") if isinstance(data, dict) else None
        if isinstance(me, dict) and me.get("id"):
            self.__raw__ = me
            self.auth_details.active = True
        else:
            self.errors.append(ErrorDetails.from_response(status, result or {}))
            self.auth_details.active = False
        return self

    async def refresh_token(self, error: dict[str, Any] | None = None) -> bool:
        """Renew the JWT with the refresh token; True when a new one was stored.

        Concurrent callers share one renewal: a caller that waited finds the
        JWT already replaced and does not spend the refresh token again.
        """
        refresh = self.auth_details.refresh_token
        if not refresh:
            return False
        before = self.auth_details.token
        async with self._refresh_lock:
            if self.auth_details.token != before:
                return True
            status, result, cookies = await call_api(
                self.auth_session,
                APIRoutes().refresh_token(),
                {"refresh_token": self.auth_details.refresh_token},
            )
            if not 200 <= status < 300:
                return False
            token = result.get("token") or cookies.get("BEARER")
            if not token:
                return False
            self.auth_details.authorization = str(token)
            new_refresh = result.get("refresh_token") or cookies.get("refresh_token")
            if new_refresh:
                self.auth_details.refresh_token = str(new_refresh)
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
            headers["x-community-name"] = COMMUNITY
            headers["referer"] = f"{STANDARD_URL}/"
            headers["origin"] = STANDARD_URL
            cookies: list[str] = []
            if self.auth_details.token and not self.guest:
                cookies.append(f"BEARER={self.auth_details.token}")
            if link == APIRoutes().refresh_token() and self.auth_details.refresh_token:
                cookies.append(f"refresh_token={self.auth_details.refresh_token}")
            if cookies:
                headers["cookie"] = "; ".join(cookies)
        if extra_headers:
            headers.update(extra_headers)
        if link.startswith(API_URL):
            # Set after extra_headers so API calls send what the web client sends.
            headers["accept"] = "application/json"
        return headers
