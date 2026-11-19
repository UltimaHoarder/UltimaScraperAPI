import base64
import json
from typing import Any

import python_socks
from aiohttp_socks import ProxyInfo

from ultima_scraper_api.apis.privacy.classes.auth_model import PrivacyAuthModel
from ultima_scraper_api.apis.privacy.classes.extras import AuthDetails, ErrorDetails
from ultima_scraper_api.apis.privacy.classes.user_model import UserModel
from ultima_scraper_api.apis.privacy.privacy import PrivacyAPI
from ultima_scraper_api.apis.privacy.urls import (
    STANDARD_API_URL,
    STANDARD_URL,
    APIRoutes,
)
from ultima_scraper_api.managers.session_manager import AuthedSession

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def token_claims(token: str) -> dict[str, Any]:
    """The API token's payload (uid, profile_name, exp, ...), unverified."""
    try:
        payload = token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = json.loads(decoded)
    except (IndexError, ValueError):
        return {}
    return claims if isinstance(claims, dict) else {}


class PrivacyAuthenticator:
    """Signs in with an API token (``AuthDetails.authorization``).

    The site's pages hold that token and renew it server-side; it lasts hours,
    so an expired one fails here with "Invalid Token" until it is replaced.
    """

    def __init__(
        self,
        api: PrivacyAPI,
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
        self.claims: dict[str, Any] = {}
        self.__raw__: dict[str, Any] | None = None

    async def __aenter__(self):
        return await self.login(self.guest)

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self):
        await self.auth_session.active_session.close()

    def create_auth(self):
        return PrivacyAuthModel(self)

    def create_user(self, auth: PrivacyAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__, auth)

    async def login(self, guest: bool = False):
        if guest:
            self.guest = True
            self.__raw__ = {"uid": 0}
            self.auth_details.active = True
            return self.create_auth()
        self.claims = token_claims(self.auth_details.token)
        await self.process_auth()
        if self.__raw__ is None:
            self.__raw__ = {
                "uid": self.claims.get("uid") or self.auth_details.id or 0,
                "profileName": self.claims.get("profile_name") or self.auth_details.username,
            }
        return self.create_auth()

    async def process_auth(self):
        if not self.auth_details.token:
            self.errors.append(ErrorDetails({"code": 401, "message": "No API token"}))
            self.auth_details.active = False
            return self
        result = await self.auth_session.json_request(APIRoutes().me_context())
        await self.resolve_auth_errors(result)
        self.auth_details.active = not self.errors
        if not self.errors:
            self.__raw__ = {**result, "uid": self.claims.get("uid") or self.auth_details.id or 0}
        return self

    def is_authed(self):
        return bool(self.auth_details.active)

    async def resolve_auth_errors(self, response: dict[str, Any] | Any):
        if not isinstance(response, dict) or "error" not in response:
            self.errors.clear()
            return
        error = ErrorDetails(response)
        if error.code == 401:
            error.message = "Invalid or expired API token"
        self.errors.append(error)

    def create_request_headers(
        self,
        link: str,
        custom_cookies: str = "",
        extra_headers: dict[str, str] | None = None,
    ):
        headers = self.auth_session.headers.copy()
        headers["user-agent"] = self.auth_details.user_agent or DEFAULT_USER_AGENT
        if link.startswith(STANDARD_API_URL):
            headers["origin"] = STANDARD_URL
            headers["referer"] = f"{STANDARD_URL}/"
            if self.auth_details.token and not self.guest:
                headers["authorization"] = f"Bearer {self.auth_details.token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers
