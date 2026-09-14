from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from itertools import chain
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field

from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth
from ultima_scraper_api.apis.onlyfans import (
    SubscriptionType,
    SubscriptionTypeEnum,
)
from ultima_scraper_api.apis.onlyfans.classes.chat_model import ChatModel
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import (
    MassMessageStatModel,
)
from ultima_scraper_api.apis.onlyfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.onlyfans.classes.post_model import PostModel
from ultima_scraper_api.apis.onlyfans.classes.subscription_count_model import (
    SubscriptionCountModel,
)
from ultima_scraper_api.apis.onlyfans.classes.subscription_model import (
    SubscriptionModel,
)
from ultima_scraper_api.apis.onlyfans.classes.user_model import (
    UserModel,
    iter_items,
    recursion,
)
from ultima_scraper_api.apis.onlyfans.classes.vault import VaultListModel
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes
from ultima_scraper_api.managers.redis import with_hooks
from ultima_scraper_api.managers.session_manager import consume_response_json

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
    from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails
    from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM
    from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI


class SettingsModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_delete_initiated: bool = Field(alias="isDeleteInitiated")
    last_subscription_expired_at: Any | None = Field(alias="lastSubscriptionExpiredAt")
    streaming_obs_key: Any | None = Field(alias="streamingObsKey")
    streaming_obs_server: Any | None = Field(alias="streamingObsServer")
    streaming_mux_key: Any | None = Field(alias="streamingMuxKey")
    streaming_mux_server: Any | None = Field(alias="streamingMuxServer")
    streaming_mux_key_expired_at: Any | None = Field(alias="streamingMuxKeyExpiredAt")
    activity_hub_allowed: bool = Field(alias="activityHubAllowed")
    activity_hub_tokens: list[Any] = Field(alias="activityHubTokens")
    confirm_email_sent_at: Any | None = Field(alias="confirmEmailSentAt")
    hide_after_mass_messages: bool = Field(alias="hideAfterMassMessages")
    changelog_updates: int = Field(alias="changelogUpdates")
    show_full_text_in_email_notify: bool = Field(alias="showFullTextInEmailNotify")
    is_private: bool = Field(alias="isPrivate")
    blocked_countries: list[Any] = Field(alias="blockedCountries")
    blocked_states: list[Any] = Field(alias="blockedStates")
    blocked_ips: list[Any] = Field(alias="blockedIps")
    show_posts_tips: bool = Field(alias="showPostsTips")
    recommender_reward: Any | None = Field(alias="recommenderReward")
    show_friends_to_subscribers: bool = Field(alias="showFriendsToSubscribers")
    show_subscribes_offers: bool = Field(alias="showSubscribesOffers")
    disable_subscribes_offers: bool = Field(alias="disableSubscribesOffers")
    is_email_notifications_enabled: bool = Field(alias="isEmailNotificationsEnabled")
    can_accept_message_only_from_friends: bool = Field(
        alias="canAcceptMessageOnlyFromFriends"
    )
    is_auto_follow_back: bool = Field(alias="isAutoFollowBack")
    unfollow_auto_follow_back: bool = Field(alias="unfollowAutoFollowBack")
    change_email_step: Any | None = Field(alias="changeEmailStep")
    new_email: Any | None = Field(alias="newEmail")
    life_time_email_code: Any | None = Field(alias="lifeTimeEmailCode")
    co_streaming_request_from: str = Field(alias="coStreamingRequestFrom")
    has_paid_posts: bool = Field(alias="hasPaidPosts")
    is_co_streaming_allowed: bool = Field(alias="isCoStreamingAllowed")
    is_monthly_newsletters: bool = Field(alias="isMonthlyNewsletters")
    strong_otp: bool = Field(alias="strongOtp")
    phone_otp: bool = Field(alias="phoneOtp")
    app_otp: bool = Field(alias="appOtp")
    is_otp_app_connected: bool = Field(alias="isOtpAppConnected")
    is_old_login_redirect: bool = Field(alias="isOldLoginRedirect")
    face_otp: bool = Field(alias="faceOtp")
    can_socials_connect: bool = Field(alias="canSocialsConnect")
    socials_connects: list[Any] = Field(alias="socialsConnects")
    important_subscription_notifications: bool = Field(
        alias="importantSubscriptionNotifications"
    )
    is_opensea_connected: bool = Field(alias="isOpenseaConnected")
    force_face_otp: bool = Field(alias="forceFaceOtp")
    has_password: bool = Field(alias="hasPassword")
    can_add_subscriber_by_bundle: bool = Field(alias="canAddSubscriberByBundle")
    bundle_max_price: int = Field(alias="bundleMaxPrice")
    can_make_profile_links: bool = Field(alias="canMakeProfileLinks")
    is_suggestions_opt_out: bool = Field(alias="isSuggestionsOptOut")
    is_telegram_connected: bool = Field(alias="isTelegramConnected")
    reply_on_subscribe: bool = Field(alias="replyOnSubscribe")
    should_receive_less_notifications: bool = Field(
        alias="shouldReceiveLessNotifications"
    )
    avatar_header_converter_upload: bool = Field(alias="avatarHeaderConverterUpload")
    can_add_phone: bool = Field(alias="canAddPhone")
    phone_last4: Any | None = Field(alias="phoneLast4")


class OnlyFansAuthModel(
    StreamlinedAuth["OnlyFansAuthenticator", "OnlyFansAPI", "AuthDetails"]
):
    def __init__(
        self,
        authenticator: OnlyFansAuthenticator,
    ) -> None:
        self.api = authenticator.api
        self.users: dict[int, UserModel] = {}
        super().__init__(authenticator)
        self.user = authenticator.create_user(self)
        self.id = self.user.id
        self.username = self.user.username
        self.lists: list[dict[str, Any]] = []
        self.subscriptions: list[SubscriptionModel] = []
        self.chats: list[ChatModel] = []
        self.archived_stories = {}
        self.mass_message_stats: list[MassMessageStatModel] = []
        self.paid_content: list[MessageModel | PostModel] = []
        self.extras: dict[str, Any] = {}
        self.blacklist: list[str] = []
        self.guest = self.authenticator.guest
        self.drm: OnlyDRM | None = None
        self.settings: SettingsModel | None = None

        # WebSocket connection (new architecture)
        self.websocket_connection = self._create_websocket_connection()

        self.update()

        # Initialize DRM if device files are available
        self._initialize_drm()

    def _initialize_drm(self) -> None:
        """Initialize DRM module if device files are available."""
        import logging

        logger = logging.getLogger(__name__)

        # Check for DRM device files
        client_id_path = self.api.config.settings.drm.device_client_blob_filepath
        private_key_path = self.api.config.settings.drm.device_private_key_filepath

        if client_id_path is None:
            logger.debug(
                "DRM device client blob path not configured, DRM support disabled"
            )
            return

        if not client_id_path.exists():
            logger.debug(
                f"DRM client ID not found at {client_id_path}, DRM support disabled"
            )
            return

        if private_key_path is None:
            logger.debug(
                "DRM device private key path not configured, DRM support disabled"
            )
            return

        if not private_key_path.exists():
            logger.debug(
                f"DRM private key not found at {private_key_path}, DRM support disabled"
            )
            return

        try:
            from ultima_scraper_api.apis.onlyfans.classes.only_drm import OnlyDRM

            self.drm = OnlyDRM(client_id_path, private_key_path, self)
            logger.info(
                f"✓ DRM module initialized for user {self.username} (id={self.id})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize DRM module: {e}", exc_info=True)
            self.drm = None

    def _create_websocket_connection(self):
        """Create WebSocket connection using new centralized manager."""
        # Get centralized WebSocket manager from API
        ws_manager = self.api.websocket_manager
        if not ws_manager:
            raise ValueError("WebSocket manager not available on API")

        # Get site-specific WebSocket implementation class
        ws_impl_class = self.api.websocket_impl_class
        if not ws_impl_class:
            raise ValueError("WebSocket implementation class not available on API")

        # Create connection through centralized manager
        connection = ws_manager.create_connection(
            auth=self,
            websocket_impl_class=ws_impl_class,
            connection_id=f"onlyfans_{self.id}",
        )

        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"✓ WebSocket connection created for OnlyFans user {self.id}")

        return connection

    def find_user(self, identifier: int | str):
        if isinstance(identifier, int):
            user = self.users.get(identifier)
        else:
            for user in self.users.values():
                if user.username.lower() == identifier.lower():
                    break
            else:
                user = None
        return user

    def resolve_user(self, user_dict: dict[str, Any], *, cache: bool = True):
        user = None
        if "id" in user_dict:
            user = self.find_user(user_dict["id"])
        if not user:
            user = UserModel(user_dict, self, cache=cache)
        return user

    def add_user(self, user: UserModel):
        self.users[user.id] = user

    def get_pool(self):
        return self.api.pool

    def update(self):
        if self.user:
            identifier = self.user.id
            username = self.user.username
            self.id = identifier
            self.username = username
            # # This affects scripts that use the username to select profiles
            auth_details = self.get_auth_details()
            auth_details.id = identifier
            # auth_details.username = username

    @with_hooks
    async def get_authed_user(self):
        assert self.user
        return self.user

    async def get_id(self):
        assert self.user
        return self.user.id

    async def get_username(self):
        assert self.user
        return self.user.get_username()

    async def get_lists(self, refresh: bool = True, limit: int = 100, offset: int = 0):
        link = endpoint_links(global_limit=limit, global_offset=offset).lists
        json_resp: list[dict[str, Any]] = await self.get_requester().json_request(
            link
        )  # type:ignore
        self.lists = json_resp
        return json_resp

    async def get_vault_lists(self, limit: int = 100, offset: int = 0):
        link = endpoint_links().list_vault_lists(limit=limit, offset=offset)
        json_resp: list[dict[str, Any]] = await self.get_requester().json_request(
            link
        )  # type:ignore
        self.vault = VaultListModel(json_resp, self.user)  # type:ignore
        return self.vault

    async def get_vault_media(
        self, list_id: int | None = None, limit: int = 100, offset: int = 0
    ):
        max_pagination_limit = 100  # maximum number of results per request
        json_resp = await recursion(
            category="list_vault_media",
            requester=self.get_requester(),
            max_items=limit,
            identifier=list_id,
            limit=max_pagination_limit,
            offset=offset,
        )
        return json_resp

    async def send_message(
        self,
        to_user_id: int,
        text: str = "",
        *,
        lockedText: bool | None = None,
        mediaFiles: list[dict[str, Any]] | None = None,
        price: float | None = None,
        previews: list[dict[str, Any]] | None = None,
        rfTag: list[Any] | None = None,
        rfGuest: list[Any] | None = None,
        rfPartner: list[Any] | None = None,
        isForward: bool | None = None,
    ) -> dict[str, Any]:
        """Send a message to a user's chat with full OnlyFans payload support.

        Backward compatible: can be called with just (to_user_id, text).
        """
        link = endpoint_links().send_message(to_user_id)
        payload: dict[str, Any] = {"text": text}
        if lockedText is not None:
            payload["lockedText"] = lockedText
        if mediaFiles is not None:
            payload["mediaFiles"] = mediaFiles
        if price is not None:
            payload["price"] = price
        if previews is not None:
            payload["previews"] = previews
        if rfTag is not None:
            payload["rfTag"] = rfTag
        if rfGuest is not None:
            payload["rfGuest"] = rfGuest
        if rfPartner is not None:
            payload["rfPartner"] = rfPartner
        if isForward is not None:
            payload["isForward"] = isForward
        return await self.get_requester().json_request(
            link, method="POST", payload=payload
        )

    async def message_create(
        self,
        to_user_id: int,
        text: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Alias for send_message to satisfy older call sites; forwards extra payload fields."""
        return await self.send_message(to_user_id, text, **kwargs)

    async def get_blacklist(self, local_blacklists: list[str]):
        bl_ids: list[str] = []
        remote_blacklists = await self.get_lists()
        if remote_blacklists:
            for remote_blacklist in remote_blacklists:
                for local_blacklist in local_blacklists:
                    if remote_blacklist["name"].lower() == local_blacklist.lower():
                        list_users = remote_blacklist["users"]
                        if remote_blacklist["usersCount"] > 2:
                            list_id = remote_blacklist["id"]
                            list_users = await self.get_lists_users(list_id)
                        if list_users:
                            users = list_users
                            bl_ids = [x["username"] for x in users]
        return bl_ids

    async def match_identifiers(self, identifiers: list[int | str]):
        if self.id in identifiers or self.username in identifiers:
            return True
        else:
            return False

    @with_hooks
    async def get_user(
        self, identifier: int | str, refresh: bool = False, *, cache: bool = True
    ):
        """
        Retrieves a user from the OnlyFans API based on the provided identifier.

        Args:
            identifier (int | str): The identifier of the user.
            refresh (bool, optional): Flag indicating whether to refresh the user data. Defaults to False.

        Returns:
            UserModel | None: The user data if found, None otherwise.
        """

        if not cache:
            response = await self.auth_session.json_request(
                endpoint_links(identifier).users
            )
            if "error" in response:
                return None
            return UserModel(response, self, cache=False)

        # Important: We need to preserve existing scraped data tied to the user in the cache.
        # When refreshing, we attach old cached data to the new user instance to maintain
        # continuity and prevent data loss or duplication.
        # So for now, we use this method to get the user data until we implemented the comments above
        cached_user = self.find_user(identifier)

        if cached_user and not refresh and not self.cache.users(identifier).is_released():
            return cached_user

        # Fetch fresh data from API
        link = endpoint_links(identifier).users
        response = await self.auth_session.json_request(link)

        if "error" in response:
            return None

        # If we had a cached user, update their properties with fresh data
        if cached_user:
            # Update the cached user's properties with fresh API data
            cached_user.update_from_dict(response)
            self.cache.users(identifier).activate()
            return cached_user

        # Create new user model from API response
        fresh_user = self.resolve_user(response)
        self.users[fresh_user.id] = fresh_user

        self.cache.users(identifier).activate()
        return fresh_user

    async def get_lists_users(
        self,
        identifier: int,
        check: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        link = endpoint_links(
            identifier, global_limit=limit, global_offset=offset
        ).lists_users
        results: list[dict[str, Any]] = await self.auth_session.json_request(
            link
        )  # type:ignore
        if len(results) >= limit and not check:
            results2 = await self.get_lists_users(
                identifier, limit=limit, offset=limit + offset
            )
            results.extend(results2)  # type: ignore
        return results

    async def assign_user_to_sub(self, subscription_model: SubscriptionModel):
        _user = await self.get_user(subscription_model.user.id)
        return subscription_model

    async def get_subscription_count(self) -> SubscriptionCountModel:

        url = endpoint_links().subscription_count()
        result = await self.auth_session.json_request(url)
        return SubscriptionCountModel(result)

    async def iter_subscriptions(
        self,
        identifiers: list[int | str] | None = None,
        limit: int | None = None,
        sub_type: SubscriptionType = SubscriptionTypeEnum.ALL,
        filter_by: str = "",
        job_id: str | None = None,
        *,
        cache: bool = False,
        concurrency: int | None = None,
    ):
        """Yield page-owned subscriptions with bounded profile hydration.

        Streaming consumers own the returned objects. With cache=False no users,
        cache timers or subscription lists are added to the authenticated client.
        """
        from contextlib import aclosing
        from datetime import datetime, timezone

        from ultima_scraper_core import runtime_env_value
        from ultima_scraper_core.concurrency import map_unordered
        from ultima_scraper_api.managers.redis import get_redis

        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit < 0
        ):
            raise ValueError("Subscription limit must be nonnegative or None")
        if limit == 0:
            return
        if concurrency is None:
            raw_concurrency = runtime_env_value("ULTIMA_SUBSCRIPTION_HYDRATION_CONCURRENCY")
            concurrency = (
                int(raw_concurrency)
                if raw_concurrency is not None and raw_concurrency.strip()
                else self.auth_session.get_session_manager().max_threads
            )
        if (
            isinstance(concurrency, bool)
            or not isinstance(concurrency, int)
            or concurrency <= 0
        ):
            raise ValueError(
                "Subscription hydration concurrency must be a positive integer"
            )
        selected_type = SubscriptionTypeEnum(sub_type)
        counts = (await self.get_subscription_count()).subscriptions
        total = int(getattr(counts, selected_type.value)) if limit is None else limit
        if total <= 0:
            return
        identifiers_set = set(identifiers or ())
        await self.auth_session.json_request(
            "https://onlyfans.com/api2/v2/lists/following/sort",
            method="POST",
            payload={"order": "expire_date", "direction": "desc", "type": "all"},
        )
        redis = get_redis()
        processed = 0

        async def progress(event_type, *, username=None):
            if redis and redis.is_connected:
                await redis.publish_hook(
                    {
                        "event": "subscription_processing",
                        "event_type": event_type,
                        "job_id": job_id or "api",
                        "auth_id": self.id,
                        "username": self.username,
                        "total": processed if event_type == "finished" else total,
                        "current": processed,
                        "current_username": username,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        async def hydrate(indexed):
            index, raw = indexed
            user = self.resolve_user(raw) if cache else UserModel(raw, self, cache=False)
            subscription = SubscriptionModel(raw, user, self)
            refreshed = await self.get_user(user.id, refresh=True, cache=cache)
            if refreshed is not None:
                subscription.user = refreshed
                subscription.profile_refreshed = True
            else:
                subscription.profile_refreshed = False
            subscription.transient_profile = not cache
            return index, subscription

        await progress("started")
        offset = 0
        while offset < total:
            # This is the existing upstream per-request limit, independent of
            # worker/write budgets and of the total subscription count.
            request_limit = min(100, total - offset)
            response = await self.auth_session.json_request(
                endpoint_links().list_subscriptions(
                    limit=request_limit,
                    offset=offset,
                    sub_type=selected_type,
                    filter=filter_by,
                )
            )
            if isinstance(response, dict) and "error" in response:
                raise RuntimeError("Subscription page request failed")
            page = response if isinstance(response, list) else response.get("list", [])
            if not page:
                break
            page = page[:request_limit]
            selected = [
                raw
                for raw in page
                if not identifiers_set
                or raw.get("id") in identifiers_set
                or raw.get("username") in identifiers_set
            ]
            ordered = [None] * len(selected)
            async with aclosing(
                map_unordered(hydrate, enumerate(selected), limit=concurrency)
            ) as hydrated:
                async for index, subscription in hydrated:
                    ordered[index] = subscription
            for subscription in ordered:
                assert subscription is not None
                processed += 1
                if processed % 10 == 0:
                    await progress("progress", username=subscription.user.username)
                yield subscription
            offset += request_limit
            if isinstance(response, list) or not response.get("hasMore"):
                break
        await progress("finished")

    @with_hooks
    async def get_subscriptions(
        self,
        identifiers: list[int | str] = [],
        limit: int | None = None,
        sub_type: SubscriptionType = SubscriptionTypeEnum.ALL,
        filter_by: str = "",
        job_id: str | None = None,
    ):
        """Compatibility collector; archive workers use iter_subscriptions."""
        from contextlib import aclosing

        if not self.cache.subscriptions.is_released():
            return self.subscriptions
        async with aclosing(
            self.iter_subscriptions(
                identifiers=identifiers,
                limit=limit,
                sub_type=sub_type,
                filter_by=filter_by,
                job_id=job_id,
                cache=True,
            )
        ) as stream:
            subscriptions = [subscription async for subscription in stream]
        if identifiers:
            # Preserve requested identifier order and first-match semantics.
            matches = {}
            for subscription in subscriptions:
                matches.setdefault(subscription.id, subscription)
                matches.setdefault(subscription.username, subscription)
            subscriptions = [
                matches[identifier] for identifier in identifiers if identifier in matches
            ]
        known_ids = {subscription.user.id for subscription in self.subscriptions}
        for subscription in subscriptions:
            if subscription.user.id not in known_ids:
                self.subscriptions.append(subscription)
                known_ids.add(subscription.user.id)
        return subscriptions

    async def iter_chats(
        self,
        limit: int | None = None,
        offset: int = 0,
        *,
        query: str | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[ChatModel, None]:
        """Yield chats page by page without retaining users or last messages."""
        async with aclosing(
            iter_items(
                category="list_chats" if query is None else "search_chats",
                requester=self.get_requester(),
                max_items=limit,
                identifier=query,
                limit=100 if limit is None else max(1, min(100, limit)),
                offset=offset,
            )
        ) as items:
            async for item in items:
                yield ChatModel(item, self, cache=cache)

    async def get_chats(
        self,
        limit: int = 100,
        offset: int = 0,
    ):
        if not self.cache.chats.is_released():
            return self.chats

        async def mass_recursive(
            limit: int, offset: int, multiplier: int, depth: int = 1
        ):
            link = endpoint_links(global_limit=limit, global_offset=offset).list_chats

            unpredictable_links, new_offset = api_helper.calculate_the_unpredictable(
                link, offset, limit, multiplier, depth
            )
            links = unpredictable_links
            results = await self.auth_session.bulk_json_requests(links)
            items = [x["list"] for x in results]
            if not items:
                return items
            if results[-1]["hasMore"]:
                results2 = await mass_recursive(
                    limit=limit,
                    offset=limit + new_offset,
                    multiplier=multiplier,
                    depth=depth + 1,
                )
                items.extend(results2)
            else:
                self.cache.chats.activate()

            return items

        multiplier = self.auth_session.get_session_manager().max_threads
        recursive_results = await mass_recursive(limit, offset, multiplier)
        results = list(chain.from_iterable(recursive_results))
        temp_chats: set[ChatModel] = set()
        for result in results:
            temp_chats.add(ChatModel(result, self))
        chats: list[ChatModel] = list(temp_chats)
        chats.sort(key=lambda x: x.user.id, reverse=True)
        self.chats = chats
        return self.chats

    async def search_chats(self, query: str, limit: int = 100, offset: int = 0):
        items = await recursion(
            category="search_chats",
            requester=self.get_requester(),
            max_items=limit,
            identifier=query,
            limit=limit,
            offset=offset,
        )
        chats = [ChatModel(x, self) for x in items]
        return chats

    async def get_mass_message_stats(
        self,
        resume: list[dict[str, Any]] | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        if not self.cache.mass_message_stats.is_released():
            return self.mass_message_stats

        async def recursive(
            resume: list[dict[str, Any]] | None, limit: int, offset: int
        ):
            link = endpoint_links(
                global_limit=limit, global_offset=offset
            ).mass_messages_stats
            results = await self.auth_session.json_request(link)
            items = results.get("list", [])
            if not items:
                return items
            if resume:
                for item in items:
                    if any(x["id"] == item["id"] for x in resume):
                        resume.sort(key=lambda x: x["id"], reverse=True)
                        return resume
                    else:
                        resume.append(item)

            if results["hasMore"]:
                results2 = await recursive(
                    resume=resume, limit=limit, offset=limit + offset
                )
                items.extend(results2)
            else:
                self.cache.mass_message_stats.activate()
            if resume:
                items = resume

            return items

        items: list[dict[str, Any]] = await recursive(resume, limit, offset)
        items.sort(key=lambda x: x["id"], reverse=True)
        self.mass_message_stats = [MassMessageStatModel(x, self.user) for x in items]
        return self.mass_message_stats

    async def iter_paid_content(
        self,
        performer_id: int | str | None = None,
        limit: int | None = None,
        offset: int = 0,
        *,
        cache: bool = False,
    ):
        """Yield paid posts/messages without retaining the feed or its authors."""
        from contextlib import aclosing

        from ultima_scraper_api.apis.onlyfans.classes.user_model import iter_items

        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit < 0
        ):
            raise ValueError("Paid content limit must be nonnegative or None")
        # The existing upstream request size; this is not a deployment budget.
        page_size = 50
        authors = {}
        hydrated_authors = set()
        seen = 0
        async with aclosing(
            iter_items(
                "list_paid_content",
                self.auth_session,
                max_items=limit,
                identifier=performer_id,
                limit=page_size,
                offset=offset,
            )
        ) as items:
            async for item in items:
                if seen % page_size == 0:
                    authors.clear()
                    hydrated_authors.clear()
                seen += 1
                response_type = item.get("responseType")
                if response_type not in {"post", "message"}:
                    continue
                raw_user = item["fromUser" if response_type == "message" else "author"]
                author_id = int(raw_user["id"])
                user = authors.get(author_id)
                if response_type == "message" and author_id not in hydrated_authors:
                    user = await self.get_user(author_id, cache=cache) or user
                    hydrated_authors.add(author_id)
                if user is None:
                    user = (
                        self.resolve_user(raw_user)
                        if cache
                        else UserModel(raw_user, self, cache=False)
                    )
                authors[author_id] = user
                if performer_id is not None and performer_id not in {
                    user.id,
                    user.username,
                }:
                    continue
                model = MessageModel if response_type == "message" else PostModel
                yield model(item, user, cache=cache)

    async def get_paid_content(
        self,
        performer_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ):
        """Compatibility collector; workers consume iter_paid_content directly."""
        from contextlib import aclosing

        if not self.cache.paid_content.is_released():
            return self.paid_content
        async with aclosing(
            self.iter_paid_content(
                performer_id=performer_id,
                limit=limit,
                offset=offset,
                cache=True,
            )
        ) as items:
            async for item in items:
                self.paid_content.append(item)
                if performer_id is None:
                    self.cache.paid_content.activate()
        return self.paid_content

    async def get_scrapable_users(self):
        subscription_users = [x.user for x in self.subscriptions]
        return subscription_users

    async def get_login_issues(self):
        url = endpoint_links().login_issues
        response = await self.auth_session.json_request(url, method="POST")
        return response

    async def get_transactions(self, limit: int = 100, offset: int = 0):
        max_pagination_limit = 100  # maximum number of results per request
        items = await recursion(
            category="list_transactions",
            requester=self.auth_session,
            max_items=limit,
            limit=max_pagination_limit,
            offset=offset,
        )
        return items

    async def blocked_users(self, limit: int = 100, offset: int = 0):
        max_pagination_limit = 100  # maximum number of results per request
        items = await recursion(
            category="list_blocked_users",
            requester=self.auth_session,
            max_items=limit,
            limit=max_pagination_limit,
            offset=offset,
        )
        return items

    async def restricted_users(self, limit: int = 100, offset: int = 0):
        max_pagination_limit = 100  # maximum number of results per request
        items = await recursion(
            category="list_restricted_users",
            requester=self.auth_session,
            max_items=limit,
            limit=max_pagination_limit,
            offset=offset,
        )
        return items

    def add_subscription(self, subscription: SubscriptionModel):
        if subscription.user.id not in [x.user.id for x in self.subscriptions]:
            self.subscriptions.append(subscription)

    async def needs_age_verification(self):
        user = await self.get_authed_user()
        if user.is_age_verified is False:
            reverification = False
            auth_issues = self.issues
            if auth_issues:
                auth_issues_data = auth_issues["data"]
                reverification = (
                    True if auth_issues_data["source"] == "av_reverification" else False
                )
            if user.age_verification_required or reverification:
                return True
        return False

    async def get_identity_verification(self):
        url = APIRoutes().start_identity_verification()
        # login | secondary are valid sources
        payload = {"source": "login"}
        response = await self.get_requester().json_request(
            url, method="POST", payload=payload
        )

        # Extract the ID from redirectUrl
        redirect_url = response.get("redirectUrl", "")
        identity_verification_id: str | None = None
        if redirect_url and "id=" in redirect_url:
            identity_verification_id = redirect_url.split("id=")[1].split("&")[0]
        assert (
            identity_verification_id
        ), "Failed to extract identity verification ID from redirect URL"

        ondato_sessions_url = "https://idvs.api.ondato.net/v1/sessions"
        payload2 = {"identityVerificationId": identity_verification_id}
        response2 = await self.get_requester().request(
            ondato_sessions_url, method="POST", json=payload2
        )
        assert response2, "Failed to create session with Ondato sessions API"
        result2: dict[str, Any] = await response2.json()
        authorization_bearer = result2.get("accessToken")
        assert (
            authorization_bearer
        ), "Failed to retrieve access token from Ondato sessions API"
        omnichannels_url = "https://idvs.api.ondato.net/v1/omnichannels/url"
        headers = {"Authorization": f"Bearer {authorization_bearer}"}
        payload3 = {
            "identityVerificationId": identity_verification_id,
            "urlPath": f"?id={identity_verification_id}&ip-type=v4",
        }
        response3 = await self.get_requester().request(
            omnichannels_url,
            method="POST",
            json=payload3,
            custom_headers=headers,
        )
        assert response3, "Failed to retrieve omnichannel URL from Ondato API"
        result3: dict[str, Any] = await response3.json()
        short_url = result3.get("shortUrl")
        return short_url

    async def get_age_verification(self):
        if await self.needs_age_verification():
            url = APIRoutes().start_age_verification()
            result = await self.get_requester().json_request(url, method="POST")
            return result

    async def get_settings(self):
        url = APIRoutes().settings()
        result = await self.get_requester().json_request(url)
        settings = SettingsModel.model_validate(result)
        self.settings = settings
        return settings

    async def notification_settings(
        self,
        email_notifications_enabled: bool | None = None,
        monthly_newsletters: bool | None = None,
        important_subscription_notifications: bool | None = None,
    ):
        url = APIRoutes().notifications_settings()
        data: dict[str, bool] = {}
        if email_notifications_enabled is not None:
            data["isEmailNotificationsEnabled"] = email_notifications_enabled
        if monthly_newsletters is not None:
            data["isMonthlyNewsletters"] = monthly_newsletters
        if important_subscription_notifications is not None:
            data["importantSubscriptionNotifications"] = (
                important_subscription_notifications
            )
        response = await self.get_requester().request(url, method="PATCH", json=data)
        if email_notifications_enabled is not None and self.settings:
            self.settings.is_email_notifications_enabled = email_notifications_enabled
        if monthly_newsletters is not None and self.settings:
            self.settings.is_monthly_newsletters = monthly_newsletters
        if important_subscription_notifications is not None and self.settings:
            self.settings.important_subscription_notifications = (
                important_subscription_notifications
            )
        assert response, "Failed to update notification settings"
        return await consume_response_json(response)
