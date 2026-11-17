"""LoyalFans URLs.

Checked against the web client build of 2026-11-16 (UltimaRE capture). Routes
marked "not in the current web client" are kept as the code used them, but the
site's own app no longer calls them; their replacements take request bodies
that have not been captured yet.
"""

import math
from typing import Any

SCHEME = "https://"
DOMAIN = "www.loyalfans.com"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
API_URL = f"{STANDARD_URL}/api"
API_V1_URL = f"{API_URL}/v1"
API_V2_URL = f"{API_URL}/v2"


class Routes:
    # These use the standard url
    def profile(self, username: str) -> str:
        return f"{STANDARD_URL}/{username}"

    def profile_by_uid(self, uid: str) -> str:
        return f"{STANDARD_URL}/user/{uid}"


class APIRoutes:
    # These use the API url
    def me(self) -> str:
        return f"{API_V1_URL}/auth/user/me?ngsw-bypass=true"

    def profile(self, username: str, profile_type: str = "star") -> str:
        return f"{API_V2_URL}/profile/{profile_type}/{username}?ngsw-bypass=true"

    def timeline(self, username: str, limit: int = 10, page: int = 1) -> str:
        return (
            f"{API_V2_URL}/social/timeline/{username}"
            f"?limit={limit}&page={page}&ngsw-bypass=true"
        )

    def user_lists(self) -> str:
        """POST {page, search_term, limit}: the account's lists with their counts."""
        return f"{API_V2_URL}/user-lists?ngsw-bypass=true"

    def user_list_users(self) -> str:
        """POST {id, page, limit, ...}: members of one list (subscriptions live here)."""
        return f"{API_V2_URL}/user-lists/users?ngsw-bypass=true"

    def messages(self, uid: str, limit: int = 10, offset: int = 0) -> str:
        # Not in the current web client, which reads /api/v1/messages/with/{uid}.
        return f"{API_V2_URL}/messages/{uid}?limit={limit}&offset={offset}"

    def message(self, uid: str) -> str:
        # Not in the current web client (it uses /api/v2/messages/get-message/{a}/{b}).
        return f"{API_V2_URL}/messages/{uid}"

    def message_purchase(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v2/messages/buy).
        return f"{API_V2_URL}/messages/{uid}/purchase"

    def message_react(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v2/messages/react).
        return f"{API_V2_URL}/messages/{uid}/react"

    def message_report(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v1/report/message).
        return f"{API_V2_URL}/messages/{uid}/report"

    def post_purchase(self, uid: str) -> str:
        # Not in the current web client.
        return f"{API_V2_URL}/posts/{uid}/purchase"

    def post_comments(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v1/comments).
        return f"{API_V2_URL}/posts/{uid}/comments"

    def post_react(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v2/reaction).
        return f"{API_V2_URL}/posts/{uid}/react"

    def post_bookmark(self, uid: str) -> str:
        # Not in the current web client (it posts to /api/v2/bookmarks/bookmark).
        return f"{API_V2_URL}/posts/{uid}/bookmark"

    def create_payloads(
        self,
        url: str,
        payload: dict[str, Any],
        max_items: int,
        pagination_limit: int = 10,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Page payloads ({..., limit, page}) for POST-paginated routes."""
        payloads: list[dict[str, Any]] = []
        if max_items:
            for page in range(math.ceil(max_items / pagination_limit)):
                payloads.append({**payload, "limit": pagination_limit, "page": page + 1})
        return [url] * len(payloads), payloads
