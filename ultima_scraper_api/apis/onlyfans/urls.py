import math
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse

SCHEME = "https://"
DOMAIN = "onlyfans.com"
API = "/api2/v2"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
STANDARD_API_URL = f"{STANDARD_URL}{API}"
MEDIA_URL = f"{SCHEME}cdn2.{DOMAIN}"
DRM_MEDIA_URL = f"{SCHEME}cdn3.{DOMAIN}"


class Routes:
    # These use the standard url
    def profile(self, identifier: int | str) -> str:
        return f"{STANDARD_URL}/{identifier}"

    def content(self, content_identifier: int, identifier: int | str) -> str:
        return f"{STANDARD_URL}/{identifier}/{content_identifier}"

    def chat(self, identifier: int) -> str:
        return f"{STANDARD_URL}/my/chats/chat/{identifier}"

    def age_verification(self) -> str:
        return f"{STANDARD_URL}/my/verification?source=login"


class APIRoutes:
    # These use the API url
    def me(self) -> str:
        return f"{STANDARD_API_URL}/users/me"

    def users(self, identifier: int) -> str:
        return f"{STANDARD_API_URL}/users/{identifier}"

    def blocked_users(self, limit: int = 10, offset: int = 0) -> str:
        return f"{STANDARD_API_URL}/users/blocked?limit={limit}&offset={offset}"

    def restricted_users(self, limit: int = 10, offset: int = 0) -> str:
        return f"{STANDARD_API_URL}/users/restrict?limit={limit}&offset={offset}"

    def list_archived_stories(
        self,
        limit: int = 100,
        marker_offset: int = 0,
        sort_order: Literal["publish_date_desc"] = "publish_date_desc",
    ):
        return f"{STANDARD_API_URL}/stories/archive/?limit={limit}&marker={marker_offset}&order={sort_order}"

    def list_posts(
        self,
        identifier: int | str,
        label: str = "",
        limit: int = 10,
        offset: int = 0,
        before_date: datetime | float | None = None,
        after_date: datetime | float | None = None,
    ) -> str:
        if before_date:
            before_val = (
                before_date.timestamp()
                if isinstance(before_date, datetime)
                else before_date
            )
            return (
                f"{STANDARD_API_URL}/users/{identifier}/posts?limit={limit}"
                f"&beforePublishTime={before_val}&order=publish_date_desc&format=infinite"
            )
        if after_date:
            after_val = (
                after_date.timestamp()
                if isinstance(after_date, datetime)
                else after_date
            )
            return (
                f"{STANDARD_API_URL}/users/{identifier}/posts?limit={limit}"
                f"&afterPublishTime={after_val}&order=publish_date_desc&format=infinite"
            )
        return (
            f"{STANDARD_API_URL}/users/{identifier}/posts?limit={limit}&offset={offset}"
            f"&order=publish_date_desc&skip_users_dups=0&label={label}"
        )

    def list_messages(
        self,
        chat_id: int | str,
        global_limit: int = 10,
        global_offset: int | str | None = 0,
    ) -> str:
        offset_val = "" if global_offset is None else str(global_offset)
        return (
            f"{STANDARD_API_URL}/chats/{chat_id}/messages?limit={global_limit}"
            f"&id={offset_val}&order=desc"
        )

    def list_paid_content(
        self, limit: int = 10, offset: int = 0, performer_id: int | str | None = None
    ) -> str:
        if performer_id is not None:
            return (
                f"{STANDARD_API_URL}/posts/paid/all?limit={limit}&offset={offset}"
                f"&user_id={performer_id}&format=infinite"
            )
        return (
            f"{STANDARD_API_URL}/posts/paid/all?limit={limit}&offset={offset}"
            "&format=infinite"
        )

    def list_paid_posts(
        self, limit: int = 10, offset: int = 0, performer_id: int | str | None = None
    ) -> str:
        if performer_id is not None:
            return (
                f"{STANDARD_API_URL}/posts/paid?limit={limit}&offset={offset}"
                f"&user_id={performer_id}&format=infinite"
            )
        return (
            f"{STANDARD_API_URL}/posts/paid?limit={limit}&offset={offset}"
            "&format=infinite"
        )

    def list_comments(
        self,
        content_type: str,
        content_id: Optional[int | str],
        global_limit: int = 10,
        global_offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> str:
        content_type = (
            f"{content_type}s" if not content_type.startswith("s") else content_type
        )
        return (
            f"{STANDARD_API_URL}/{content_type}/{content_id}/comments?limit={global_limit}"
            f"&offset={global_offset}&sort={sort_order}"
        )

    def list_vault_lists(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> str:
        return (
            f"{STANDARD_API_URL}/vault/lists?view=main&limit={limit}&offset={offset}"
            f"&order={sort_order}"
        )

    def list_vault_media(
        self,
        list_id: int | str,
        limit: int = 10,
        offset: int = 0,
        field: str = "recent",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> str:
        return (
            f"{STANDARD_API_URL}/vault/media?limit={limit}&offset={offset}"
            f"&order={sort_order}&field={field}&list={list_id}"
        )

    def send_message(self, user_id: int | str) -> str:
        return f"{STANDARD_API_URL}/chats/{user_id}/messages"

    def list_subscriptions(
        self,
        limit: int = 20,
        offset: int = 0,
        sub_type: str = "all",
        filter: str = "",
    ) -> str:
        return (
            f"{STANDARD_API_URL}/subscriptions/subscribes?limit={limit}&offset={offset}"
            f"&type={sub_type}&filter[{filter}]=1&format=infinite"
        )

    def like(self, content_type: str, content_id: int | str) -> str:
        content_type = (
            f"{content_type}s" if not content_type.startswith("s") else content_type
        )
        return f"{STANDARD_API_URL}/{content_type}/{content_id}/like"

    def subscription_count(self) -> str:
        url = f"{STANDARD_API_URL}/subscriptions/count/all"
        parsed = urlparse(url)
        query_params = dict(parse_qsl(parsed.query))
        encoded_params = urlencode(query_params)
        return f"{url}?{encoded_params}"

    def create_links(
        self, url: str, max_items: int, pagination_limit: int = 10, offset: int = 0
    ) -> list[str]:
        final_links: list[str] = []
        if max_items:
            pages = math.ceil(max_items / pagination_limit)
            for page in range(pages):
                current_offset = page * pagination_limit
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                limit_value = query_params.get("limit", [str(pagination_limit)])[0]
                normalized_url = url.replace(
                    f"limit={limit_value}", f"limit={pagination_limit}"
                )
                final_links.append(
                    normalized_url.replace(
                        f"offset={offset}", f"offset={current_offset}"
                    )
                )
        return final_links

    def transaction_history(self, limit: int = 10, offset: int = 0) -> str:
        return f"{STANDARD_API_URL}/payments/all/transactions?limit={limit}&offset={offset}"

    def payment_methods_vat(
        self,
        content_type: str,
        price: float | str,
        to_user: int | str,
    ) -> str:
        return (
            f"{STANDARD_API_URL}/payments/methods-vat"
            f"?type={content_type}&price={price}&toUser={to_user}"
        )

    def drm_resolver(
        self,
        media_id: int | str,
        response_type: str | None = None,
        content_id: int | str | None = None,
    ) -> str:
        normalized_type = (response_type or "").strip().lower()
        if normalized_type.endswith("ies"):
            normalized_type = f"{normalized_type[:-3]}y"
        elif normalized_type.endswith("s") and not normalized_type.endswith("ss"):
            normalized_type = normalized_type[:-1]

        if normalized_type:
            return (
                f"{STANDARD_API_URL}/users/media/{media_id}/drm/"
                f"{normalized_type}/{content_id}?type=widevine"
            )
        return f"{STANDARD_API_URL}/users/media/{media_id}/drm/?type=widevine"

    def cdn_resolver(
        self,
        directory_url: str,
        base_url: str,
        drm: bool = False,
        manifest_type: str | None = None,
    ) -> str:
        url: str | None = None
        if drm:
            assert manifest_type is not None, "manifest_type is required when drm=True"
            url = f"{DRM_MEDIA_URL}/{manifest_type}/files/{directory_url}/{base_url}"
        assert url
        return url

    def two_factor_challenge(self) -> str:
        return f"{STANDARD_API_URL}/users/otp/check"

    def start_identity_verification(self) -> str:
        # Mainly used for becoming a creator,accessing nsfw or when they lock your account and require identity verification to unlock, but can be used in other cases as well
        return f"{STANDARD_API_URL}/iv/start"

    def start_age_verification(self) -> str:
        # Used when only age verification is required, such as when trying to access NSFW content without having completed age verification on the account yet
        return f"{STANDARD_API_URL}/age-verifier/start"

    def settings(self) -> str:
        return f"{STANDARD_API_URL}/users/me/settings"

    def notifications_settings(self) -> str:
        return f"{STANDARD_API_URL}/users/settings/notifications"
