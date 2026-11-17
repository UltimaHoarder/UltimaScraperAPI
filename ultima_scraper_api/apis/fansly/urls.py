"""Fansly URLs, as built by the fansly.com web client (main.js)."""

from collections.abc import Sequence
from urllib.parse import quote

SCHEME = "https://"
DOMAIN = "fansly.com"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
STANDARD_API_URL = f"{SCHEME}apiv3.{DOMAIN}/api/v1"
WEBSOCKET_URL = f"wss://wsv3.{DOMAIN}/?v=3"


def _ids(identifiers: Sequence[int | str]) -> str:
    return ",".join(str(x) for x in identifiers)


class Routes:
    # These use the standard url
    def profile(self, username: str) -> str:
        return f"{STANDARD_URL}/{username}"

    def post(self, post_id: int | str) -> str:
        return f"{STANDARD_URL}/post/{post_id}"

    def chat(self, group_id: int | str) -> str:
        return f"{STANDARD_URL}/messages/{group_id}"


class APIRoutes:
    # These use the API url
    def device_id(self) -> str:
        return f"{STANDARD_API_URL}/device/id"

    def me(self) -> str:
        return f"{STANDARD_API_URL}/account/me"

    def settings(self) -> str:
        return f"{STANDARD_API_URL}/account/settings"

    def users(self, identifiers: Sequence[int | str]) -> str:
        """GET /account by ids, or by usernames when any identifier is not numeric."""
        key = "ids" if all(str(x).isdigit() for x in identifiers) else "usernames"
        return f"{STANDARD_API_URL}/account?{key}={_ids(identifiers)}"

    def following(self, account_id: int | str, limit: int = 100, offset: int = 0) -> str:
        return (
            f"{STANDARD_API_URL}/account/{account_id}/following"
            f"?before=0&after=0&limit={limit}&offset={offset}"
        )

    def subscriptions(self) -> str:
        return f"{STANDARD_API_URL}/subscriptions"

    def lists(self) -> str:
        """Lists of the authed account (``itemId`` filters to lists holding one)."""
        return f"{STANDARD_API_URL}/lists/account?itemId="

    def list_items(self, list_id: int | str, limit: int = 100, before: int | str = 0) -> str:
        before_part = f"&before={before}" if before and str(before) != "0" else ""
        return f"{STANDARD_API_URL}/lists/itemsnew?listId={list_id}&limit={limit}{before_part}"

    def stories(self, account_id: int | str) -> str:
        return f"{STANDARD_API_URL}/mediastoriesnew?accountId={account_id}"

    def timeline(
        self,
        account_id: int | str,
        before: int | str = 0,
        wall_id: int | str = "",
        content_search: str = "",
    ) -> str:
        return (
            f"{STANDARD_API_URL}/timelinenew/{account_id}?before={before}&after=0"
            f"&wallId={wall_id}&contentSearch={quote(content_search)}"
        )

    def posts(self, identifiers: Sequence[int | str]) -> str:
        return f"{STANDARD_API_URL}/post?ids={_ids(identifiers)}"

    def post_replies(self, post_id: int | str) -> str:
        return f"{STANDARD_API_URL}/post/{post_id}/replies"

    def list_chats(self, limit: int = 25, offset: int = 0, search: str = "") -> str:
        return (
            f"{STANDARD_API_URL}/messaging/groups?sortOrder=1&flags=0"
            f"&subscriptionTierId=&listIds=&search={quote(search)}&limit={limit}&offset={offset}"
        )

    def list_messages(self, group_id: int | str, before: int | str = 0, limit: int = 25) -> str:
        before_part = f"&before={before}" if before and str(before) != "0" else ""
        return f"{STANDARD_API_URL}/message?groupId={group_id}{before_part}&limit={limit}"

    def vault_albums(self, account_id: int | str) -> str:
        return f"{STANDARD_API_URL}/uservault/albumsnew?accountId={account_id}"

    def vault_album_content(
        self, album_id: int | str, before: int | str = 0, limit: int = 25
    ) -> str:
        return (
            f"{STANDARD_API_URL}/uservault/album/content?albumId={album_id}"
            f"&before={before}&after=0&limit={limit}"
        )

    def media_orders(self, limit: int = 100, offset: int = 0) -> str:
        """Purchased media (the web client's account media orders)."""
        return f"{STANDARD_API_URL}/account/media/orders/?limit={limit}&offset={offset}"

    def transactions(self, limit: int = 100, offset: int = 0) -> str:
        return (
            f"{STANDARD_API_URL}/payments/wallets/transactions?before=0&after=0"
            f"&limit={limit}&offset={offset}&status=&type="
        )
