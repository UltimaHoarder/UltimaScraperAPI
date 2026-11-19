"""DarkFans URLs, as used by the darkfans.com web client (captured 2026-11-17).

DarkFans runs on the OnlySafe/LoverFans platform. The API is same-origin
(darkfans.com, or darkfans.net, which serves US visitors; both answer the same
API). User, post, story and chat ids are UUIDs. List routes page with
``page``/``perPage`` and answer ``{"data": [...], "meta": {"pagination":
{"page", "perPage", "total", "totalPages"}}}``; single objects come as
``{"data": {"type", "attributes"}}``.
"""

from urllib.parse import urlencode

SCHEME = "https://"
DOMAIN = "darkfans.com"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
API_URL = f"{STANDARD_URL}/api/v1"
# Sent as x-community-name with every API call.
COMMUNITY = "darkfans"


def _query(**params: object) -> str:
    present = {k: v for k, v in params.items() if v is not None and v != ""}
    return f"?{urlencode(present)}" if present else ""


class Routes:
    """Web pages."""

    def profile(self, username: str) -> str:
        return f"{STANDARD_URL}/{username}"

    def post(self, post_id: str) -> str:
        return f"{STANDARD_URL}/site/post/{post_id}"


class APIRoutes:
    """API endpoints (all GET unless noted)."""

    def me(self) -> str:
        return f"{API_URL}/user/info"

    def refresh_token(self) -> str:
        """POST: renews the BEARER JWT with the refresh token."""
        return f"{API_URL}/auth/refresh"

    def user(self, user_id: str) -> str:
        return f"{API_URL}/user/{user_id}"

    def user_by_username(self, username: str) -> str:
        return f"{API_URL}/username/{username}"

    def search_users(self, query: str, page: int = 1, per_page: int = 15) -> str:
        return f"{API_URL}/search/users" + _query(query=query, page=page, perPage=per_page)

    def timeline(self, cursor: int = 0, per_page: int = 15) -> str:
        """The home feed; pages by ``meta.pagination.nextCursor``."""
        return f"{API_URL}/timeline" + _query(cursor=cursor, perPage=per_page)

    def posts(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 15,
        post_type: str | None = None,
    ) -> str:
        """A creator's posts, newest first; ``post_type`` is free, subscribers,
        ppv or purchased (the profile's tabs)."""
        return f"{API_URL}/user/{user_id}/posts" + _query(
            page=page, perPage=per_page, type=post_type
        )

    def post_counters(self, user_id: str) -> str:
        return f"{API_URL}/user/{user_id}/posts/counters"

    def post(self, post_id: str) -> str:
        return f"{API_URL}/post/{post_id}"

    def post_comments(self, post_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{API_URL}/post/{post_id}/comment" + _query(page=page, perPage=per_page)

    def stories(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        """A creator's stories, live and pinned."""
        return f"{API_URL}/user/{user_id}/stories" + _query(
            withPinned=1, page=page, perPage=per_page
        )

    def story(self, story_id: str) -> str:
        return f"{API_URL}/story/{story_id}"

    def subscriptions(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 15,
    ) -> str:
        """Creators the account subscribes or subscribed to; ``status`` is
        valid or expired (all when None)."""
        return f"{API_URL}/user/{user_id}/subscriptions" + _query(
            status=status, page=page, perPage=per_page
        )

    def followees(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{API_URL}/user/{user_id}/follow/followees" + _query(
            page=page, perPage=per_page
        )

    def chats(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 15,
        archived: bool | None = None,
    ) -> str:
        return f"{API_URL}/user/{user_id}/chat" + _query(
            page=page,
            perPage=per_page,
            archived=None if archived is None else str(archived).lower(),
        )

    def chat(self, user_id: str, chat_id: str) -> str:
        return f"{API_URL}/user/{user_id}/chat/{chat_id}"

    def chat_messages(
        self, user_id: str, chat_id: str, page: int = 1, per_page: int = 50
    ) -> str:
        """Newest first; the last page is the first short one (no ``meta``)."""
        return f"{API_URL}/user/{user_id}/chat/{chat_id}/messages" + _query(
            page=page, perPage=per_page
        )

    def user_lists(self, user_id: str) -> str:
        return f"{API_URL}/user/{user_id}/userList"

    def user_list_users(self, list_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{API_URL}/userList/{list_id}/users" + _query(page=page, perPage=per_page)

    def bookmarks(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{API_URL}/user/{user_id}/post/bookmarks" + _query(
            page=page, perPage=per_page
        )
