from __future__ import annotations

import asyncio
from itertools import chain, product
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
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel, recursion
from ultima_scraper_api.apis.onlyfans.classes.vault import VaultListModel
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes
from ultima_scraper_api.managers.redis import with_hooks

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

    def resolve_user(self, user_dict: dict[str, Any]):
        user = None
        if "id" in user_dict:
            user = self.find_user(user_dict["id"])
        if not user:
            user = UserModel(user_dict, self)
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
    async def get_user(self, identifier: int | str, refresh: bool = False):
        """
        Retrieves a user from the OnlyFans API based on the provided identifier.

        Args:
            identifier (int | str): The identifier of the user.
            refresh (bool, optional): Flag indicating whether to refresh the user data. Defaults to False.

        Returns:
            UserModel | None: The user data if found, None otherwise.
        """

        # Important: We need to preserve existing scraped data tied to the user in the cache.
        # When refreshing, we attach old cached data to the new user instance to maintain
        # continuity and prevent data loss or duplication.
        # So for now, we use this method to get the user data until we implemented the comments above
        cached_user = self.find_user(identifier)

        if (
            cached_user
            and not refresh
            and not self.cache.users(identifier).is_released()
        ):
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

    @with_hooks
    async def get_subscriptions(
        self,
        identifiers: list[int | str] = [],
        limit: int | None = None,
        sub_type: SubscriptionType = SubscriptionTypeEnum.ALL,
        filter_by: str = "",
        job_id: str | None = None,
    ):
        """
        Retrieves the subscriptions based on the given parameters.
        5000 offset is the maximum allowed by the API, which means anything above that will be ignored.

        Args:
            identifiers (list[int | str], optional): List of subscription identifiers. Defaults to [].
            limit (int, optional): Maximum number of subscriptions to retrieve. Defaults to 100.
           sub_type (SubscriptionType, optional): Type of subscriptions to retrieve. Defaults to "all".
             filter_by (str, optional): Filter subscriptions by a specific value. Defaults to "".
            job_id (str, optional): Job ID for progress event publishing. Defaults to None.

        Returns:
            list[SubscriptionModel]: List of SubscriptionModel objects representing the subscriptions.
        """

        if not self.cache.subscriptions.is_released():
            return self.subscriptions
        max_pagination_limit = 100  # maximum number of results per request

        subscriptions_count = await self.get_subscription_count()
        subscriptions_info = subscriptions_count.subscriptions
        match sub_type:
            case "all":
                subscription_type_count = subscriptions_info.all
            case "active":
                subscription_type_count = subscriptions_info.active
            case "expired":
                subscription_type_count = subscriptions_info.expired
            case _:
                raise ValueError(f"Invalid subscription type: {sub_type}")
        limit = limit if limit else subscription_type_count
        url = endpoint_links().list_subscriptions(
            sub_type=SubscriptionTypeEnum(sub_type), filter=filter_by
        )
        urls = endpoint_links().create_links(
            url,
            limit,
            pagination_limit=max_pagination_limit,
        )
        sort_url = "https://onlyfans.com/api2/v2/lists/following/sort"
        _sort_response = await self.auth_session.json_request(
            sort_url,
            method="POST",
            payload={"order": "expire_date", "direction": "desc", "type": "all"},
        )

        raw_subscriptions: list[Any] = []
        subscription_responses = await self.auth_session.bulk_json_requests(urls)
        raw_subscriptions = [
            raw_subscription
            for temp_raw_subscriptions in subscription_responses
            if temp_raw_subscriptions
            for raw_subscription in temp_raw_subscriptions["list"]
        ]

        # If we want find more subscriptions than the paginated requests returned, use recursion to get the rest

        raw_recursion = await recursion(
            "list_subscriptions",
            self.get_requester(),
            max_items=limit,
            query_type=sub_type,
            limit=max_pagination_limit,
            offset=len(raw_subscriptions),
            item_count=len(raw_subscriptions),
        )
        raw_subscriptions += raw_recursion
        raw_subscriptions = raw_subscriptions[:limit]

        subscriptions: list[SubscriptionModel] = []
        if identifiers:
            found_raw_subscriptions: list[dict[str, Any]] = []
            for identifier in identifiers:
                for raw_subscription in raw_subscriptions:
                    if (
                        identifier == raw_subscription["id"]
                        or identifier == raw_subscription["username"]
                    ):
                        found_raw_subscriptions.append(raw_subscription)
                        break
            raw_subscriptions = found_raw_subscriptions

        # Publish subscription processing progress to Redis
        total_subs = len(raw_subscriptions)

        # Import Redis manager for progress publishing
        from datetime import datetime, timezone

        from ultima_scraper_api.managers.redis import get_redis

        redis = get_redis()

        # Use provided job_id or fall back to "api" for standalone usage
        effective_job_id = job_id or "api"

        # Publish initial progress event
        if redis and redis.is_connected:
            await redis.publish_hook(
                {
                    "event": "subscription_processing",
                    "event_type": "started",
                    "job_id": effective_job_id,
                    "auth_id": self.id,
                    "username": self.username,
                    "total": total_subs,
                    "current": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        subscriptions = [
            SubscriptionModel(x, self.resolve_user(x), self) for x in raw_subscriptions
        ]
        with self.get_pool() as pool:
            tasks = pool.starmap(self.assign_user_to_sub, product(subscriptions))

            # Process with progress updates
            processed = 0
            for completed_task in asyncio.as_completed(tasks):
                subscription = await completed_task
                processed += 1

                # Publish progress every 10 subscriptions or at completion
                if (
                    redis
                    and redis.is_connected
                    and (processed % 10 == 0 or processed == total_subs)
                ):
                    await redis.publish_hook(
                        {
                            "event": "subscription_processing",
                            "event_type": "progress",
                            "job_id": effective_job_id,
                            "auth_id": self.id,
                            "username": self.username,
                            "total": total_subs,
                            "current": processed,
                            "current_username": (
                                subscription.user.username
                                if subscription.user
                                else "Unknown"
                            ),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        # Publish completion event
        if redis and redis.is_connected:
            await redis.publish_hook(
                {
                    "event": "subscription_processing",
                    "event_type": "finished",
                    "job_id": effective_job_id,
                    "auth_id": self.id,
                    "username": self.username,
                    "total": total_subs,
                    "current": total_subs,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        for subscription in subscriptions:
            self.add_subscription(subscription)
        return subscriptions

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

    async def get_paid_content(
        self,
        performer_id: int | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        max_pagination_limit = 50  # maximum number of results per request
        if not self.cache.paid_content.is_released():
            return self.paid_content

        items = await recursion(
            category="list_paid_content",
            requester=self.auth_session,
            max_items=limit,
            identifier=performer_id,
            limit=max_pagination_limit,
            offset=offset,
        )
        for item in items:
            content = None
            if item["responseType"] == "message":
                user = await self.get_user(item["fromUser"]["id"])
                if not user:
                    user = self.resolve_user(item["fromUser"])
                content = MessageModel(item, user)
            elif item["responseType"] == "post":
                user = self.resolve_user(item["author"])
                content = PostModel(item, user)
            if content:
                author = content.get_author()
                if performer_id:
                    if performer_id == author.id:
                        self.paid_content.append(content)
                else:
                    self.paid_content.append(content)
                if not performer_id:
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
        return await response.json()
