"""DarkFans URLs, as built by the darkfans.com web client (2026-11-16 build).

The API is same-origin (NEXT_PUBLIC_API_HOST is https://darkfans.com). User ids
are UUIDs. List routes page with ``page``/``perPage`` query parameters (the
client's ``paginate()`` copies them onto the query string) and answer
``{"data": [...], "meta": {"pagination": {...}}}``.
"""

from urllib.parse import urlencode

SCHEME = "https://"
DOMAIN = "darkfans.com"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
STANDARD_API_URL = f"{STANDARD_URL}/api/v1"


def _query(**params: object) -> str:
    present = {k: v for k, v in params.items() if v is not None and v != ""}
    return f"?{urlencode(present)}" if present else ""


class Routes:
    # These use the standard url
    def profile(self, username: str) -> str:
        return f"{STANDARD_URL}/{username}"


class APIRoutes:
    # These use the API url
    def me(self) -> str:
        return f"{STANDARD_API_URL}/user/info"

    def user(self, user_id: str) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}"

    def user_by_username(self, username: str) -> str:
        return f"{STANDARD_API_URL}/username/{username}"

    def search_users(self, query: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/search/users" + _query(
            query=query, page=page, perPage=per_page
        )

    def posts(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 15,
        post_type: str | None = None,
    ) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/posts" + _query(
            page=page, perPage=per_page, type=post_type
        )

    def post(self, post_id: str) -> str:
        return f"{STANDARD_API_URL}/post/{post_id}"

    def post_comments(self, post_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/post/{post_id}/comment" + _query(
            page=page, perPage=per_page
        )

    def stories(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/stories" + _query(
            withPinned=1, page=page, perPage=per_page
        )

    def story(self, story_id: str) -> str:
        return f"{STANDARD_API_URL}/story/{story_id}"

    def subscriptions(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 15,
    ) -> str:
        """Creators the account subscribes to."""
        return f"{STANDARD_API_URL}/user/{user_id}/subscriptions" + _query(
            status=status, page=page, perPage=per_page
        )

    def followees(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/follow/followees" + _query(
            page=page, perPage=per_page
        )

    def chats(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 15,
        archived: bool | None = None,
    ) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/chat" + _query(
            page=page,
            perPage=per_page,
            archived=None if archived is None else int(archived),
        )

    def chat_messages(
        self, user_id: str, chat_id: str, page: int = 1, per_page: int = 20
    ) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/chat/{chat_id}/messages" + _query(
            page=page, perPage=per_page
        )

    def user_lists(self, user_id: str) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/userList"

    def user_list_users(self, list_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/userList/{list_id}/users" + _query(
            page=page, perPage=per_page
        )

    def bookmarks(self, user_id: str, page: int = 1, per_page: int = 15) -> str:
        return f"{STANDARD_API_URL}/user/{user_id}/post/bookmarks" + _query(
            page=page, perPage=per_page
        )
