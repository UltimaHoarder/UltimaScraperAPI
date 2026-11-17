from typing import Any


class ErrorDetails:
    """Error response handler"""

    def __init__(self, code: int = 0, message: str = "") -> None:
        self.code = code
        self.message = message

    async def format(self, extras: dict[str, Any]):
        """Format error message with additional context"""
        return self


class AuthDetails:
    """Authentication details container"""

    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        authorization: str = "",
        user_agent: str = "",
        email: str = "",
        proxy_url: str | None = None,
        active: bool | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.proxy_url = proxy_url
        self.active = active

    def export(self):
        """Export auth details as dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "authorization": self.authorization,
            "user_agent": self.user_agent,
            "email": self.email,
            "proxy_url": self.proxy_url,
            "active": self.active,
        }


def create_headers(
    authorization: str,
    user_agent: str = "",
    link: str = "https://www.loyalfans.com/",
) -> dict[str, str]:
    """Create request headers"""
    return {
        "Authorization": f"Bearer {authorization}",
        "User-Agent": user_agent,
        "Referer": link,
        "Origin": "https://www.loyalfans.com",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
