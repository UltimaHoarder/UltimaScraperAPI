from typing import Any

from user_agent import generate_user_agent

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel
from ultima_scraper_api.apis.onlyfans.classes.extras import (
    AuthDetails,
    ErrorDetails,
    create_headers,
    endpoint_links,
)
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI
from ultima_scraper_api.managers.session_manager import AuthedSession


class OnlyFansAuthenticator:
    def __init__(
        self,
        api: "OnlyFansAPI",
        auth_details: AuthDetails = AuthDetails(),
        guest: bool = False,
    ) -> None:
        self.api = api
        self.auth_details = auth_details
        self.auth_session = AuthedSession(self, api.session_manager)
        self.auth_attempt = 0
        self.max_attempts = 10
        self.errors: list[ErrorDetails] = []
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
        return OnlyFansAuthModel(self)

    def create_user(self, auth: OnlyFansAuthModel):
        assert self.__raw__ is not None
        return UserModel(self.__raw__, auth)

    async def login(self, guest: bool = False):
        auth_items = self.auth_details
        assert auth_items
        if guest and auth_items:
            auth_items.cookie.auth_id = "0"
            auth_items.user_agent = generate_user_agent()
            auth_items.active = True
        link = endpoint_links().customer
        user_agent = auth_items.user_agent
        auth_id = str(auth_items.cookie.auth_id)
        # expected string error is fixed by auth_id
        auth_session = self.auth_session
        session_manager = auth_session.get_session_manager()
        dynamic_rules = session_manager.dynamic_rules
        a: list[Any] = [dynamic_rules, auth_id, auth_items.x_bc, user_agent, link]
        auth_session.headers = create_headers(*a)
        if guest:
            self.guest = True
            self.__raw__ = await self.auth_session.json_request(link)
            return self.create_auth()

        while self.auth_attempt < self.max_attempts:
            await self.process_auth()
            self.auth_attempt += 1

            async def resolve_auth(auth: OnlyFansAuthenticator):
                if self.errors:
                    error = self.errors[-1]
                    if error.code == 101:
                        if auth_items.support_2fa:
                            link = f"https://onlyfans.com/api2/v2/users/otp/check"
                            count = 1
                            max_count = 3
                            while count < max_count + 1:
                                print(
                                    "2FA Attempt " + str(count) + "/" + str(max_count)
                                )
                                code = input("Enter 2FA Code\n")
                                data = {"code": code, "rememberMe": True}
                                response = await self.auth_session.json_request(
                                    link, method="POST", payload=data
                                )
                                if isinstance(response, ErrorDetails):
                                    error.message = response.message
                                    count += 1
                                else:
                                    print("Success")
                                    auth.active = False
                                    auth.errors.remove(error)
                                    await self.process_auth()
                                    break

            await resolve_auth(self)
            if not self.is_authed():
                if self.errors:
                    error = self.errors[-1]
                    error_message = error.message
                    if "token" in error_message:
                        break
                    if "Code wrong" in error_message:
                        break
                    if "Please refresh" in error_message:
                        break
                continue
            if self.is_authed():
                return self.create_auth()

    async def process_auth(self):
        if not self.maxed_out_auth_attempts():
            link = endpoint_links().customer
            json_resp = await self.auth_session.json_request(link)
            await self.resolve_auth_errors(json_resp)
            self.__raw__ = json_resp
            if not self.errors and json_resp["isAuth"]:
                self.auth_details.active = True
                self.auth_details.email = self.__raw__.get("email", "")
            else:
                link = endpoint_links(self.auth_details.cookie.auth_id).users
                json_resp = await self.auth_session.json_request(link)
                await self.resolve_auth_errors(json_resp)
                self.auth_details.active = False
        return self

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
