"""LoyalFans URLs.

Checked against the signed-in web client on 2026-11-17 (UltimaRE capture).
Many reads are POSTs with a JSON body; the body each route takes is noted.
Every API call carries ``Authorization: Bearer <session token>`` and
``X-Api-Version`` (see the authenticator).
"""

from urllib.parse import quote, urlencode

SCHEME = "https://"
DOMAIN = "www.loyalfans.com"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
API_URL = f"{STANDARD_URL}/api"
API_V1_URL = f"{API_URL}/v1"
API_V2_URL = f"{API_URL}/v2"
# The web client's build sends this with every API call.
API_VERSION = "3.4.4"


def _query(**params: object) -> str:
    """Query string with the web client's ``ngsw-bypass`` and no unset values."""
    values = {key: value for key, value in params.items() if value is not None}
    values["ngsw-bypass"] = "true"
    return urlencode(values)


class Routes:
    # These use the standard url
    def profile(self, username: str) -> str:
        return f"{STANDARD_URL}/{username}"

    def profile_by_uid(self, uid: str) -> str:
        return f"{STANDARD_URL}/user/{uid}"

    def post(self, username: str, slug: str) -> str:
        return f"{STANDARD_URL}/{username}/post/{slug}"


class APIRoutes:
    # --- account ---------------------------------------------------------------------

    def me(self) -> str:
        return f"{API_V1_URL}/auth/user/me?{_query()}"

    def refresh_token(self) -> str:
        """POST {} with the expired token: {success, token}."""
        return f"{API_V1_URL}/auth/refresh-token?{_query()}"

    def user_lists(self) -> str:
        """POST {page, search_term, limit}: {user_lists, page_meta}."""
        return f"{API_V2_URL}/user-lists?{_query()}"

    def user_list_users(self) -> str:
        """POST {id, page, limit}: {list, users, page_meta}; ``id`` is a list id
        or a system list's name ("following", "subscribed", "friends", ...)."""
        return f"{API_V2_URL}/user-lists/users?{_query()}"

    def purchases(self) -> str:
        """POST {group_by: "date"|"creator", page}: {items, page_meta}."""
        return f"{API_V2_URL}/purchases?{_query()}"

    # --- profiles and posts ----------------------------------------------------------

    def profile(self, username: str, profile_type: str = "star") -> str:
        return f"{API_V2_URL}/profile/{profile_type}/{quote(username)}?{_query()}"

    def timeline(self, username: str, limit: int = 10, page: int = 1) -> str:
        """{timeline, page_meta: {current_page, last_page, total}}, newest first."""
        query = _query(limit=limit, page=page)
        return f"{API_V2_URL}/social/timeline/{quote(username)}?{query}"

    def post(self, identifier: str) -> str:
        """One post by its slug or uid: {post}."""
        return f"{API_V1_URL}/social/post/{quote(identifier)}?{_query()}"

    def comments(self) -> str:
        """POST {uid: <post uid>, page_token?}: {comments, page_token}."""
        return f"{API_V1_URL}/comments?{_query()}"

    def videos_store(self) -> str:
        """POST {slug, type: "video", limit, page}: {list, page_meta}."""
        return f"{API_V2_URL}/videos-store?{_query()}"

    def stories(self) -> str:
        """POST {slug} for one creator, {page, limit} for the followed feed:
        {list: [[story, ...] per creator], pagination}."""
        return f"{API_V2_URL}/stories?{_query()}"

    def highlights(self) -> str:
        """POST {slug, page, limit}: {list: [{uid, title, cover, stories}]}."""
        return f"{API_V2_URL}/stories/highlights?{_query()}"

    # --- messages --------------------------------------------------------------------

    def conversations(self) -> str:
        """POST {limit, all: true, page_token?}: {conversations, page_token}."""
        return f"{API_V2_URL}/messages?{_query()}"

    def conversation(self, partner: str, mid: str | None = None) -> str:
        """One conversation, newest first; ``mid`` is the previous page's
        ``mid_token`` (absent on the last page)."""
        query = _query(timezone="UTC", mid=mid)
        return f"{API_V1_URL}/messages/with/{quote(partner)}?{query}"
