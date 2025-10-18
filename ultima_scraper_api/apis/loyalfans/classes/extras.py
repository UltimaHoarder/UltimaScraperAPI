import math
from typing import Any, Literal, Optional
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse


def format_url(url: str):
    """Format URL by properly encoding query parameters"""
    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query))
    encoded_params = urlencode(query_params)
    url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if encoded_params:
        url = f"{url}?{encoded_params}"
    return url


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
        active: bool | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.authorization = authorization
        self.user_agent = user_agent
        self.email = email
        self.active = active

    def export(self):
        """Export auth details as dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "authorization": self.authorization,
            "user_agent": self.user_agent,
            "email": self.email,
            "active": self.active,
        }


class endpoint_links:
    """API endpoint URL builder"""

    def __init__(
        self,
        identifier: Optional[int | str] = None,
        identifier2: Optional[int | str] = None,
        text: str = "",
        limit: int = 10,
        offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ):
        domain = "https://www.loyalfans.com"
        api = "/api/v2"
        self.base_url = f"{domain}{api}"

        # Basic endpoints
        self.user = f"{self.base_url}/user/me"
        self.user_by_id = f"{self.base_url}/user/{identifier}" if identifier else None
        self.user_posts = f"{self.base_url}/user/{identifier}/posts"
        self.post_by_id = f"{self.base_url}/post/{identifier}"
        self.messages = f"{self.base_url}/messages/{identifier}"
        self.message_by_id = f"{self.base_url}/message/{identifier}"

    def list_posts(
        self,
        user_id: int | str,
        limit: int = 10,
        offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> str:
        """Generate posts listing URL"""
        url = f"{self.base_url}/user/{user_id}/posts"
        params = {"limit": limit, "offset": offset, "order": sort_order}
        return format_url(f"{url}?{urlencode(params)}")

    def list_messages(
        self,
        user_id: int | str,
        limit: int = 10,
        offset: int = 0,
    ) -> str:
        """Generate messages listing URL"""
        url = f"{self.base_url}/messages/{user_id}"
        params = {"limit": limit, "offset": offset}
        return format_url(f"{url}?{urlencode(params)}")

    def create_links(
        self, url: str, api_count: int, limit: int = 10, offset: int = 0
    ) -> list[str]:
        """Create paginated list of URLs based on total count"""
        final_links: list[str] = []
        if api_count:
            ceil = math.ceil(api_count / limit)
            for num in range(ceil):
                num = num * limit
                parsed = urlparse(url)
                params = dict(parse_qs(parsed.query))
                params["limit"] = [str(limit)]
                params["offset"] = [str(num)]

                query = urlencode(params, doseq=True)
                final_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"
                final_links.append(final_url)
        return final_links


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
