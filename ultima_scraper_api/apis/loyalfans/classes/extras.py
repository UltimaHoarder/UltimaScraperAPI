from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ultima_scraper_api.managers.session_manager import consume_response_json

if TYPE_CHECKING:
    from ultima_scraper_api.managers.session_manager import AuthedSession


class ErrorDetails:
    """An API error ({error: {code, message}} or {success: false, message})."""

    def __init__(self, code: int = 0, message: str = "") -> None:
        self.code = code
        self.message = message

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> ErrorDetails:
        error = response.get("error")
        if isinstance(error, dict):
            return cls(int(error.get("code") or 0), str(error.get("message") or ""))
        code = int(response.get("httpCode") or response.get("code") or 401)
        return cls(code, str(response.get("message") or error or "Authentication failed"))

    async def format(self, extras: dict[str, Any]):
        return self


class AuthDetails:
    """A LoyalFans sign-in: the web client's session token (``authorization``).

    The token is what the site keeps as ``sessionToken``; the API renews it
    through /auth/refresh-token when it expires, and ``authorization`` is
    updated in place.
    """

    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
        user_agent: str = "",
        email: str = "",
        proxy_url: str | None = None,
        active: bool | None = None,
        **_ignored: Any,
    ) -> None:
        self.id = id
        self.username = username
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.proxy_url = proxy_url
        self.active = active

    @property
    def token(self) -> str:
        value = (self.authorization or "").strip()
        return value[7:].strip() if value.lower().startswith("bearer ") else value

    def export(self):
        return {
            "id": self.id,
            "username": self.username,
            "authorization": self.authorization,
            "user_agent": self.user_agent,
            "email": self.email,
            "proxy_url": self.proxy_url,
            "active": self.active,
        }


async def call_api(
    requester: AuthedSession, link: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    """(status, JSON) for a GET, or a POST with a JSON body when ``body`` is given.

    Error statuses (400/401/403/404) come back as responses, not exceptions,
    so the caller can read the API's error (e.g. {"error": "token_expired"}).
    """
    try:
        if body is None:
            response = await requester.request(link)
        else:
            response = await requester.request(link, "POST", json=body)
    except Exception as exc:  # noqa: BLE001 - network failures become an error dict
        return 0, {"error": {"code": 0, "message": str(exc)}}
    if response is None:
        return 0, {}
    try:
        data = await consume_response_json(response)
    except Exception:  # noqa: BLE001 - empty or non-JSON body
        data = {}
    return response.status, data if isinstance(data, dict) else {"value": data}
