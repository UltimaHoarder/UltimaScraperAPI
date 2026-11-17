from typing import Any

import python_socks
from aiohttp_socks import ProxyInfo
from user_agent import generate_user_agent

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
from ultima_scraper_api.apis.fansly.classes.extras import (
    API_URL,
    AuthDetails,
    ErrorDetails,
    endpoint_links,
)
from ultima_scraper_api.apis.fansly.classes.user_model import UserModel
from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
from ultima_scraper_api.apis.fansly.signing import signed_headers
from ultima_scraper_api.managers.session_manager import AuthedSession

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class FanslyAuthenticator:
    def __init__(
        self,
        api: "FanslyAPI",
        auth_details: AuthDetails = AuthDetails(),
        guest: bool = False,
    ) -> None:
        self.api = api
        self.auth_details = auth_details
        self.auth_session = AuthedSession(self, api.session_manager)
        if self.auth_details.proxy_url:
            try:
                proxy_info = ProxyInfo(
                    *python_socks.parse_proxy_url(self.auth_details.proxy_url)
                )
                self.auth_session.active_session = (
                    self.auth_session.create_client_session(False, proxy_info)
                )
            except Exception:
                pass
        self.auth_attempt = 0
        self.max_attempts = 10
        self.errors: list[ErrorDetails] = []
        self.active = False
        self.guest = guest
        # Sent as fansly-client-id and hashed into fansly-client-check.
        self.device_id = ""
        self.__raw__: dict[str, Any] | None = None

    async def __aenter__(self):
        return await self.login(self.guest)

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self):
        await self.auth_session.active_session.close()

    def create_auth(self):
        return FanslyAuthModel(self)

    def create_user(self, auth: FanslyAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__["response"]["account"], auth)

    async def login(self, guest: bool = False):
        auth_items = self.auth_details
        assert auth_items
        if guest and auth_items:
            auth_items.user_agent = generate_user_agent()
        await self.ensure_device_id()
        if guest:
            self.guest = True
            self.__raw__ = {"response": {"account": {"id": 0}}}
            # As OnlyFans' activate_guest: an open guest session counts as authed.
            self.auth_details.active = True
            return self.create_auth()

        while self.auth_attempt < self.max_attempts:
            await self.process_auth()
            self.auth_attempt += 1
            if self.is_authed():
                break
            # 400 (no/invalid session token) and 401/403 will not change on retry.
            if self.errors and self.errors[-1].code in (400, 401, 403):
                break
        if self.__raw__ is None:
            self.__raw__ = {"response": {"account": {"id": self.auth_details.id or 0}}}
        return self.create_auth()

    async def process_auth(self):
        if not self.maxed_out_auth_attempts():
            link = endpoint_links().me
            json_resp = await self.auth_session.json_request(link)
            await self.resolve_auth_errors(json_resp)
            if not self.errors:
                self.auth_details.active = True
                self.__raw__ = json_resp
            else:
                self.auth_details.active = False
                if self.auth_details.id:
                    # Keep the public profile so the inactive auth still has a user.
                    link = endpoint_links(self.auth_details.id).users_by_id
                    accounts = (await self.auth_session.json_request(link)).get("response")
                    if accounts:
                        self.__raw__ = {"response": {"account": accounts[0]}}
        return self

    async def ensure_device_id(self) -> str:
        """Fetch the device id the web client registers before its first call.

        Requests are sent unsigned until this succeeds, which the API accepts.
        """
        if not self.device_id:
            response = await self.auth_session.json_request(endpoint_links().device_id)
            device_id = response.get("response") if isinstance(response, dict) else None
            if isinstance(device_id, str):
                self.device_id = device_id
        return self.device_id

    def maxed_out_auth_attempts(self):
        return True if self.auth_attempt >= self.max_attempts else False

    def is_authed(self):
        return self.auth_details.active

    async def resolve_auth_errors(self, response: ErrorDetails | dict[str, Any]):
        # Adds an error object to self.auth.errors
        if isinstance(response, ErrorDetails):
            error = response
        elif "error" in response:
            error = response["error"]
            error = ErrorDetails(error)
        else:
            self.errors.clear()
            return
        error_message = error.message
        error_code = error.code
        if error_code == 0:
            pass
        elif error_code == 101:
            error_message = "Blocked by 2FA."
        elif error_code == 401:
            # Session/Refresh
            error_message = "Invalid Auth Info"
        error.code = error_code
        error.message = error_message
        match error_code:
            case 0:
                pass
            case _:
                await api_helper.handle_error_details(error)
        self.errors.append(error)

    def create_request_headers(
        self,
        link: str,
        custom_cookies: str = "",
        extra_headers: dict[str, str] | None = None,
    ):
        headers = self.auth_session.headers.copy()
        headers["user-agent"] = self.auth_details.user_agent or DEFAULT_USER_AGENT
        if link.startswith(API_URL):
            headers["origin"] = "https://fansly.com"
            headers["referer"] = "https://fansly.com/"
            if self.auth_details.authorization and not self.guest:
                headers["authorization"] = self.auth_details.authorization
            headers |= signed_headers(link, self.device_id)
            self.is_rate_limited = False

        if extra_headers:
            headers.update(extra_headers)
        return headers
