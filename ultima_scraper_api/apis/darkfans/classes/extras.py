from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ultima_scraper_api.managers.session_manager import consume_response_json

if TYPE_CHECKING:
    from ultima_scraper_api.managers.session_manager import AuthedSession


class ErrorDetails:
    """An API error: ``{"code": 401, "message": "Expired JWT Token"}``,
    ``{"title", "status", "detail"}`` (problem+json) or a transport error."""

    def __init__(self, code: int = 0, message: str = "") -> None:
        self.code = code
        self.message = message

    @classmethod
    def from_response(cls, status: int, response: dict[str, Any]) -> ErrorDetails:
        error = response.get("error")
        if isinstance(error, dict):
            return cls(int(error.get("code") or status), str(error.get("message") or ""))
        message = response.get("message") or response.get("detail") or response.get("title")
        return cls(int(response.get("code") or response.get("status") or status), str(message or ""))

    async def format(self, extras: dict[str, Any]):
        return self


def parse_cookie(cookie: str) -> dict[str, str]:
    """``name=value; name=value`` as a dict (later duplicates win)."""
    cookies: dict[str, str] = {}
    for part in (cookie or "").split(";"):
        name, _, value = part.strip().partition("=")
        if name:
            cookies[name] = value
    return cookies


class AuthDetails:
    """A DarkFans sign-in: the web client's cookies.

    ``authorization`` is the ``BEARER`` cookie (a JWT that lasts an hour) and
    ``refresh_token`` the ``refresh_token`` cookie (30 days), which renews it
    through /auth/refresh. The API only takes the JWT as a cookie; an
    ``Authorization`` header is rejected.

    ``cookie`` is both as one cookie string (``BEARER=...; refresh_token=...``),
    which is how the backend stores a DarkFans sign-in; either value given on
    its own takes precedence over the one in ``cookie``.
    """

    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
        refresh_token: str = "",
        cookie: str = "",
        user_agent: str = "",
        email: str = "",
        proxy_url: str | None = None,
        active: bool | None = None,
        **_ignored: Any,
    ) -> None:
        cookies = parse_cookie(cookie)
        self.id = id
        self.username = username
        self.authorization = authorization or cookies.get("BEARER", "")
        self.refresh_token = refresh_token or cookies.get("refresh_token", "")
        self.user_agent = user_agent
        self.email = email
        self.proxy_url = proxy_url
        self.active = active

    @property
    def token(self) -> str:
        value = (self.authorization or "").strip()
        for prefix in ("bearer ", "bearer="):
            if value.lower().startswith(prefix):
                value = value[len(prefix):].strip()
        return value

    @property
    def cookie(self) -> str:
        """Both cookies as one string, the form the backend stores."""
        parts = []
        if self.token:
            parts.append(f"BEARER={self.token}")
        if self.refresh_token:
            parts.append(f"refresh_token={self.refresh_token}")
        return "; ".join(parts)

    def export(self):
        return {
            "id": self.id,
            "username": self.username,
            "authorization": self.authorization,
            "refresh_token": self.refresh_token,
            "cookie": self.cookie,
            "user_agent": self.user_agent,
            "email": self.email,
            "proxy_url": self.proxy_url,
            "active": self.active,
        }


async def call_api(
    requester: AuthedSession, link: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """(status, JSON, cookies set) for a GET, or a POST with a JSON body.

    Error statuses come back as responses, not exceptions, so the caller can
    read the API's error (e.g. {"code": 401, "message": "Expired JWT Token"}).
    """
    try:
        if body is None:
            response = await requester.request(link)
        else:
            response = await requester.request(link, "POST", json=body)
    except Exception as exc:  # noqa: BLE001 - network failures become an error dict
        return 0, {"error": {"code": 0, "message": str(exc)}}, {}
    if response is None:
        return 0, {}, {}
    cookies = {name: morsel.value for name, morsel in response.cookies.items()}
    try:
        data = await consume_response_json(response)
    except Exception:  # noqa: BLE001 - empty or non-JSON body
        data = {}
    return response.status, data if isinstance(data, dict) else {"value": data}, cookies
