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

    def list_subscriptions(
        self,
        limit: int = 20,
        offset: int = 0,
        filter: str = "",
    ):
        url = format_url(f"{self.base_url}/user-lists/users?ngsw-bypass=true")
        return url

    def subscription_count(self):
        url = f"{self.base_url}/user-lists?ngsw-bypass=true"
        parsed = urlparse(url)
        query_params = dict(parse_qsl(parsed.query))

        encoded_params = urlencode(query_params)
        url = f"{url}?{encoded_params}"
        return url

    def create_links(
        self, url: str, max_items: int, pagination_limit: int = 10, offset: int = 0
    ):
        """
        This function will create a list of links depending on their content count.

        Example:\n
        create_links(link="base_link", limit=100) will return a list with 2 link(s) if pagination_limit=50.
        """
        final_links: list[str] = []
        if max_items:
            ceil = math.ceil(max_items / pagination_limit)
            numbers = list(range(ceil))
            for num in numbers:
                num = num * pagination_limit
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                limit_value = query_params["limit"][0]
                url = url.replace(f"limit={limit_value}", f"limit={pagination_limit}")
                new_link = url.replace(f"offset={offset}", f"offset={num}")
                final_links.append(new_link)
        return final_links

    def create_payloads(
        self,
        url: str,
        payload: dict[str, Any],
        max_items: int,
        pagination_limit: int = 10,
    ):

        final_payloads: list[dict[str, Any]] = []
        if max_items:
            ceil = math.ceil(max_items / pagination_limit)
            numbers = list(range(ceil))
            for num in numbers:
                new_payload = payload.copy()
                new_payload["limit"] = pagination_limit
                new_payload["page"] = num + 1
                final_payloads.append(new_payload)
        urls = [url] * len(final_payloads)
        return urls, final_payloads


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
