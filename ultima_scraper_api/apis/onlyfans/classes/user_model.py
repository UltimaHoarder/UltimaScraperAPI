from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from urllib import parse

import ultima_scraper_api.apis.onlyfans.classes.message_model as message_model
from ultima_scraper_api.apis.onlyfans import SubscriptionType, SubscriptionTypeEnum
from ultima_scraper_api.apis.onlyfans.classes import post_model
from ultima_scraper_api.apis.onlyfans.classes.extras import ErrorDetails, endpoint_links
from ultima_scraper_api.apis.onlyfans.classes.hightlight_model import HighlightModel
from ultima_scraper_api.apis.onlyfans.classes.mass_message_model import MassMessageModel
from ultima_scraper_api.apis.onlyfans.classes.story_model import StoryModel
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.managers.redis import with_hooks
from ultima_scraper_api.managers.scrape_manager import (
    ScrapeManager,
    ScrapeProgressCallback,
)

if TYPE_CHECKING:
    from ultima_scraper_api import OnlyFansAPI
    from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel
    from ultima_scraper_api.apis.onlyfans.classes.post_model import PostModel
    from ultima_scraper_api.managers.session_manager import AuthedSession

async def iter_items(
    category: Literal[
        "list_posts",
        "list_vault_media",
        "list_subscriptions",
        "list_paid_content",
        "list_blocked_users",
        "list_restricted_users",
        "list_transactions",
        "search_chats",
        "list_chats",
    ],
    requester: AuthedSession,
    max_items: int | None,
    identifier: int | str | None = None,
    query_type: str | None = None,
    limit: int = 10,
    offset: int = 0,
    before_date: datetime | float | None = None,
    after_date: datetime | float | None = None,
    item_count: int = 0,
) -> AsyncGenerator[dict[str, Any], None]:
    """Iterate cursor/offset pages without retaining the previous pages."""
    if limit <= 0:
        raise ValueError("Pagination limit must be positive")
    if max_items is not None and max_items < 0:
        raise ValueError("max_items must be nonnegative or None")
    while max_items is None or item_count < max_items:
        match category:
            case "list_posts":
                assert identifier
                link = endpoint_links().list_posts(
                    identifier=identifier,
                    limit=limit,
                    before_date=before_date,
                    after_date=after_date,
                )
            case "list_vault_media":
                assert identifier
                link = endpoint_links().list_vault_media(
                    list_id=identifier, limit=limit, offset=offset
                )
            case "list_subscriptions":
                link = endpoint_links().list_subscriptions(
                    limit=limit,
                    offset=offset,
                    sub_type=SubscriptionTypeEnum(query_type),
                )
            case "list_paid_content":
                link = APIRoutes().list_paid_content(
                    limit=limit, offset=offset, performer_id=identifier
                )
            case "list_blocked_users":
                link = APIRoutes().blocked_users(limit=limit, offset=offset)
            case "list_restricted_users":
                link = APIRoutes().restricted_users(limit=limit, offset=offset)
            case "list_transactions":
                link = APIRoutes().transaction_history(limit=limit, offset=offset)
            case "list_chats":
                link = endpoint_links(global_limit=limit, global_offset=offset).list_chats
            case "search_chats":
                assert isinstance(identifier, str)
                link = APIRoutes().search_chats(
                    query=identifier, limit=limit, offset=offset
                )
        result = await requester.json_request(link)
        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(f"{category} page request failed")
        items = result if isinstance(result, list) else result.get("list", [])
        if not items:
            return
        remaining = None if max_items is None else max_items - item_count
        for item in items if remaining is None else items[:remaining]:
            yield item
            item_count += 1
        if max_items is not None and item_count >= max_items:
            return
        if isinstance(result, list) or not result.get("hasMore"):
            return
        next_marker = result.get("tailMarker")
        if category == "list_posts" and (
            next_marker is None or next_marker == after_date
        ):
            raise RuntimeError("Posts pagination did not advance its tail marker")
        after_date = next_marker
        offset += limit


async def recursion(
    category: Literal[
        "list_posts",
        "list_vault_media",
        "list_subscriptions",
        "list_paid_content",
        "list_blocked_users",
        "list_restricted_users",
        "list_transactions",
        "search_chats",
        "list_chats",
    ],
    requester: AuthedSession,
    max_items: int | None,
    identifier: int | str | None = None,
    query_type: str | None = None,
    limit: int = 10,
    offset: int = 0,
    before_date: datetime | float | None = None,
    after_date: datetime | float | None = None,
    item_count: int = 0,
) -> list[dict[str, Any]]:
    """Compatibility collector; streaming callers use iter_items."""
    async with aclosing(
        iter_items(
            category,
            requester,
            max_items,
            identifier,
            query_type,
            limit,
            offset,
            before_date,
            after_date,
            item_count,
        )
    ) as items:
        return [item async for item in items]


class UserModel(StreamlinedUser["OnlyFansAuthModel", "OnlyFansAPI"]):
    """
    Relationship explanation:
    - 'subscribed_by': The authenticated user who is subscribing.
    - 'subscribed_on': The performer being subscribed to.
    When a user subscribes to a performer, 'subscribed_by' refers to the user, and 'subscribed_on' refers to the performer.
    """

    def __init__(self, option: dict[str, Any], authed: OnlyFansAuthModel, *, cache: bool = True) -> None:
        self.avatar: str | None = option.get("avatar")
        self.avatar_thumbs: list[str] | None = option.get("avatarThumbs")
        self.header: str | None = option.get("header")
        self.header_size: dict[str, int] | None = option.get("headerSize")
        self.header_thumbs: list[str] | None = option.get("headerThumbs")
        self.id: int = int(option.get("id", 0))
        self.ip: str = option.get("ip", "")
        self.name: str = option.get("name", f"u{self.id}")
        self.username: str = option.get("username", f"u{self.id}")
        self.can_look_story: bool = option.get("canLookStory", False)
        self.can_comment_story: bool = option.get("canCommentStory", False)
        self.has_not_viewed_story: bool = option.get("hasNotViewedStory", False)
        self.is_verified: bool = option.get("isVerified", False)
        self.can_pay_internal: bool = option.get("canPayInternal", False)
        self.has_scheduled_stream: bool = option.get("hasScheduledStream", False)
        self.has_stream: bool = option.get("hasStream", False)
        self.has_stories: bool = option.get("hasStories", False)
        self.tips_enabled: bool = option.get("tipsEnabled", False)
        self.tips_text_enabled: bool = option.get("tipsTextEnabled", False)
        self.tips_min: int = option.get("tipsMin", 0)
        self.tips_max: int = option.get("tipsMax", 1)
        self.can_earn: bool = option.get("canEarn", False)
        self.can_add_subscriber: bool = option.get("canAddSubscriber", False)
        self.subscribe_price: int = option.get("subscribePrice", 0)
        self.is_deleted: bool | None = option.get("isDeleted", None)
        self.is_suspended: bool | None = option.get("isSuspended", None)
        self.is_suspended_auto: bool | None = option.get("isSuspendedAuto", None)
        self.has_stripe: bool | None = option.get("hasStripe")
        self.is_stripe_exist: bool | None = option.get("isStripeExist")
        self.subscription_bundles: list[dict[str, Any]] = option.get(
            "subscriptionBundles", []
        )
        self.can_send_chat_to_all: bool | None = option.get("canSendChatToAll")
        self.credits_min: int | None = option.get("creditsMin")
        self.credits_max: int | None = option.get("creditsMax")
        self.is_paywall_restriction: bool = option.get("isPaywallRestriction", False)
        self.unprofitable: bool = option.get("unprofitable", False)
        self.lists_sort: str | None = option.get("listsSort")
        self.lists_sort_order: str | None = option.get("listsSortOrder")
        self.can_create_lists: bool | None = option.get("canCreateLists")
        self.join_date: str | None = option.get("joinDate")
        self.is_referrer_allowed: bool = option.get("isReferrerAllowed", False)
        self.about: str = option.get("about", "")
        self.raw_about: str = option.get("rawAbout", "")
        self.website: str | None = option.get("website")
        self.wishlist: str | None = option.get("wishlist")
        self.location: str | None = option.get("location")
        self.posts_count: int = option.get("postsCount", 0)
        self.archived_posts_count: int = option.get("archivedPostsCount", 0)
        self.private_archived_posts_count: int = option.get(
            "privateArchivedPostsCount", 0
        )
        self.photos_count: int = option.get("photosCount", 0)
        self.videos_count: int = option.get("videosCount", 0)
        self.audios_count: int = option.get("audiosCount", 0)
        self.medias_count: int = option.get("mediasCount", 0)
        self.mediasCount: int = option.get("mediasCount", 0)
        self.promotions: list[dict[str, Any]] = option.get("promotions", {})
        self.last_seen: Any = option.get("lastSeen")
        self.favorited_count: int = option.get("favoritedCount", 0)
        self.favorites_count: int = option.get("favoritesCount", 0)
        self.finished_streams_count: int = option.get("finishedStreamsCount", 0)
        self.show_posts_in_feed: bool = option.get("showPostsInFeed", False)
        self.can_receive_chat_message: bool = option.get("canReceiveChatMessage", False)
        self._is_performer: bool = option.get("isPerformer", False)
        self.is_real_performer: bool = option.get("isRealPerformer", False)
        self.is_spotify_connected: bool = option.get("isSpotifyConnected", False)
        self.subscribers_count: int | None = option.get("subscribersCount")
        self.has_pinned_posts: bool = option.get("hasPinnedPosts", False)
        self.can_chat: bool = option.get("canChat", False)
        self.call_price: int = option.get("callPrice", 0)
        self.is_private_restriction: bool = option.get("isPrivateRestriction", False)
        self.show_subscribers_count: bool = option.get("showSubscribersCount", False)
        self.show_media_count: bool = option.get("showMediaCount", False)
        self.subscribed_by: Any | None = option.get("subscribedBy")
        self.subscribed_by_data: Any | None = option.get("subscribedByData")
        self.subscribed_on: Any | None = option.get("subscribedOn")
        self.subscribed_on_data: Any | None = option.get("subscribedOnData")
        self.subscribed_is_expired_now: bool | None = option.get(
            "subscribedIsExpiredNow"
        )
        self.can_promotion: bool = option.get("canPromotion", False)
        self.can_create_promotion: bool = option.get("canCreatePromotion", False)
        self.can_create_trial: bool = option.get("canCreateTrial", False)
        self.is_adult_content: bool = option.get("isAdultContent", False)
        self.is_blocked: bool | None = option.get("isBlocked")
        self.can_trial_send: bool = option.get("canTrialSend", False)
        self.can_add_phone: bool | None = option.get("canAddPhone")
        self.phone_last4: Any | None = option.get("phoneLast4")
        self.phone_mask: Any | None = option.get("phoneMask")
        self.has_new_ticket_replies: dict[str, bool] | None = option.get(
            "hasNewTicketReplies"
        )
        self.has_internal_payments: bool | None = option.get("hasInternalPayments")
        self.is_credits_enabled: bool | None = option.get("isCreditsEnabled")
        self.credit_balance: float | None = option.get("creditBalance")
        self.is_make_payment: bool | None = option.get("isMakePayment")
        self.age_verification_required: bool | None = option.get(
            "ageVerificationRequired"
        )
        self.is_age_verified: bool | None = option.get("isAgeVerified")
        self.is_otp_enabled: bool | None = option.get("isOtpEnabled")
        self.email: str | None = option.get("email")
        self.is_email_checked: bool | None = option.get("isEmailChecked")
        self.is_legal_approved_allowed: bool | None = option.get(
            "isLegalApprovedAllowed"
        )
        self.is_twitter_connected: bool | None = option.get("isTwitterConnected")
        self.twitter_username: Any | None = option.get("twitterUsername")
        self.is_allow_tweets: bool | None = option.get("isAllowTweets")
        self.is_payment_card_connected: bool | None = option.get(
            "isPaymentCardConnected"
        )
        self.referal_url: str | None = option.get("referalUrl")
        self.is_visible_online: bool | None = option.get("isVisibleOnline")
        self.subscribes_count: int | None = option.get("subscribesCount", 0)
        self.can_pin_post: bool | None = option.get("canPinPost")
        self.has_new_alerts: bool | None = option.get("hasNewAlerts")
        self.has_new_hints: bool | None = option.get("hasNewHints")
        self.has_new_changed_price_subscriptions: bool | None = option.get(
            "hasNewChangedPriceSubscriptions"
        )
        self.notifications_count: int | None = option.get("notificationsCount")
        self.chat_messages_count: int | None = option.get("chatMessagesCount")
        self.is_want_comments: bool | None = option.get("isWantComments")
        self.watermark_text: str | None = option.get("watermarkText")
        self.custom_watermark_text: Any | None = option.get("customWatermarkText")
        self.has_watermark_photo: bool | None = option.get("hasWatermarkPhoto")
        self.has_watermark_video: bool | None = option.get("hasWatermarkVideo")
        self.is_telegram_connected: bool | None = option.get("isTelegramConnected")
        self.adv_block: list[str] | None = option.get("advBlock")
        self.has_purchased_posts: bool | None = option.get("hasPurchasedPosts")
        self.is_email_required: bool | None = option.get("isEmailRequired")
        self.is_payout_legal_approved: bool | None = option.get("isPayoutLegalApproved")
        self.payout_legal_approve_state: str | None = option.get(
            "payoutLegalApproveState"
        )
        self.payout_legal_approve_reject_reason: Any | None = option.get(
            "payoutLegalApproveRejectReason"
        )
        self.enabled_image_editor_for_chat: bool | None = option.get(
            "enabledImageEditorForChat"
        )
        self.should_receive_less_notifications: bool | None = option.get(
            "shouldReceiveLessNotifications"
        )
        self.can_calling: bool | None = option.get("canCalling")
        self.paid_feed: bool | None = option.get("paidFeed")
        self.can_send_sms: bool | None = option.get("canSendSms")
        self.can_add_friends: bool | None = option.get("canAddFriends")
        self.is_real_card_connected: bool | None = option.get("isRealCardConnected")
        self.count_priority_chat: int | None = option.get("countPriorityChat")
        self.count_pinned_chat: int | None = option.get("countPinnedChat")
        self.has_scenario: bool | None = option.get("hasScenario")
        self.is_wallet_autorecharge: bool | None = option.get("isWalletAutorecharge")
        self.wallet_autorecharge_amount: int | None = option.get(
            "walletAutorechargeAmount"
        )
        self.wallet_autorecharge_min: int | None = option.get("walletAutorechargeMin")
        self.wallet_first_rebills: bool | None = option.get("walletFirstRebills")
        self.can_alternative_wallet_top_up: bool | None = option.get(
            "canAlternativeWalletTopUp"
        )
        self.need_iv_approve: bool | None = option.get("needIVApprove")
        self.iv_status: Any | None = option.get("ivStatus")
        self.iv_fail_reason: Any | None = option.get("ivFailReason")
        self.can_check_docs_on_add_card: bool | None = option.get(
            "canCheckDocsOnAddCard"
        )
        self.face_id_available: bool | None = option.get("faceIdAvailable")
        self.iv_country: str | None = option.get("ivCountry")
        self.iv_forced_verified: bool | None = option.get("ivForcedVerified")
        self.iv_hide_for_performers: bool | None = option.get("ivHideForPerformers")
        self.force_face_otp: bool | None = option.get("forceFaceOtp")
        self.face_id_regular: bool | None = option.get("faceIdRegular")
        self.can_add_card: bool | None = option.get("canAddCard")
        self.is_paywall_passed: bool | None = option.get("isPaywallPassed")
        self.is_delete_initiated: bool | None = option.get("isDeleteInitiated")
        self.iv_flow: str | None = option.get("ivFlow")
        self.can_change_content_price: str | None = option.get("canChangeContentPrice")
        self.bookmark_categories_order: str | None = option.get(
            "bookmarkCategoriesOrder"
        )
        self.is_verified_reason: bool | None = option.get("isVerifiedReason")
        self.need_update_banking: bool | None = option.get("needUpdateBanking")
        self.can_receive_manual_payout: bool | None = option.get(
            "canReceiveManualPayout"
        )
        self.can_receive_stripe_payout: bool | None = option.get(
            "canReceiveStripePayout"
        )
        self.manual_payout_pending_days: int | None = option.get(
            "manualPayoutPendingDays"
        )
        self.is_need_confirm_payout: bool | None = option.get("isNeedConfirmPayout")
        self.can_streaming: bool | None = option.get("canStreaming")
        self.is_scheduled_streams_allowed: bool | None = option.get(
            "isScheduledStreamsAllowed"
        )
        self.can_make_expire_posts: bool | None = option.get("canMakeExpirePosts")
        self.trial_max_days: int | None = option.get("trialMaxDays")
        self.trial_max_expires_days: int | None = option.get("trialMaxExpiresDays")
        self.message_min_price: int | None = option.get("messageMinPrice")
        self.message_max_price: int | None = option.get("messageMaxPrice")
        self.post_min_price: int | None = option.get("postMinPrice")
        self.post_max_price: int | None = option.get("postMaxPrice")
        self.stream_min_price: int | None = option.get("streamMinPrice")
        self.stream_max_price: int | None = option.get("streamMaxPrice")
        self.can_create_paid_stream: bool | None = option.get("canCreatePaidStream")
        self.call_min_price: int | None = option.get("callMinPrice")
        self.call_max_price: int | None = option.get("callMaxPrice")
        self.subscribe_min_price: float | None = option.get("subscribeMinPrice")
        self.subscribe_max_price: int | None = option.get("subscribeMaxPrice")
        self.bundle_max_price: int | None = option.get("bundleMaxPrice")
        self.unclaimed_offers_count: int | None = option.get("unclaimedOffersCount")
        self.claimed_offers_count: int | None = option.get("claimedOffersCount")
        self.withdrawal_period: str | None = option.get("withdrawalPeriod")
        self.can_add_story: bool | None = option.get("canAddStory")
        self.can_add_subscriber_by_bundle: bool | None = option.get(
            "canAddSubscriberByBundle"
        )
        self.is_suggestions_opt_out: bool | None = option.get("isSuggestionsOptOut")
        self.can_create_fund_raising: bool | None = option.get("canCreateFundRaising")
        self.min_fund_raising_target: int | None = option.get("minFundRaisingTarget")
        self.max_fund_raising_target: int | None = option.get("maxFundRaisingTarget")
        self.disputes_ratio: int | None = option.get("disputesRatio")
        self.vault_lists_sort: str | None = option.get("vaultListsSort")
        self.vault_lists_sort_order: str | None = option.get("vaultListsSortOrder")
        self.can_create_vault_lists: bool | None = option.get("canCreateVaultLists")
        self.can_make_profile_links: bool | None = option.get("canMakeProfileLinks")
        self.reply_on_subscribe: bool | None = option.get("replyOnSubscribe")
        self.payout_type: str | None = option.get("payoutType")
        self.min_payout_summ: int | None = option.get("minPayoutSumm")
        self.can_has_w9_form: bool | None = option.get("canHasW9Form")
        self.is_vat_required: bool | None = option.get("isVatRequired")
        self.is_country_vat_refundable: bool | None = option.get(
            "isCountryVatRefundable"
        )
        self.is_country_vat_number_collect: bool | None = option.get(
            "isCountryVatNumberCollect"
        )
        self.vat_number_name: str | None = option.get("vatNumberName")
        self.is_country_with_vat: bool | None = option.get("isCountryWithVat")
        self.connected_of_accounts: list[Any] | None = option.get("connectedOfAccounts")
        self.has_password: bool | None = option.get("hasPassword")
        self.has_recently_expired: bool | None = option.get("hasRecentlyExpired")
        self.labels_sort: str | None = option.get("labelsSort")
        self.labels_sort_order: str | None = option.get("labelsSortOrder")
        self.can_connect_of_account: bool | None = option.get("canConnectOfAccount")
        self.pinned_posts_count: int | None = option.get("pinnedPostsCount")
        self.credits_min_alternatives: int | None = option.get("creditsMinAlternatives")
        self.max_pinned_posts_count: int | None = option.get("maxPinnedPostsCount")
        self.ws_url: str | None = option.get("wsUrl")
        self.ws_auth_token: str | None = option.get("wsAuthToken")
        # Custom
        found_user = authed.find_user(self.id)
        if cache and not found_user:
            authed.add_user(self)
        self.username = self.get_username()
        self.download_info: dict[str, Any] = {}
        self.duplicate_media: list[Any] = []
        self.scrape_manager = ScrapeManager[
            "OnlyFansAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def update_from_dict(self, option: dict[str, Any]) -> None:
        """Update the user's properties with fresh data from API response.

        This method re-initializes the object with new data while preserving
        cached/computed properties like scrape_manager, download_info, etc.
        """
        # Store references to cached data that shouldn't be overwritten
        preserved_data: dict[str, Any] = {
            "scrape_manager": self.scrape_manager,
            "download_info": self.download_info,
            "duplicate_media": self.duplicate_media,
            "__db_user__": self.__db_user__,
        }

        # Re-run the initialization logic with new data
        # This ensures all properties are updated consistently
        self.__init__(option, self.get_authed())

        # Restore preserved data
        for key, value in preserved_data.items():
            setattr(self, key, value)

    def get_username(self):
        if not self.username:
            self.username = f"u{self.id}"
        return self.username

    def get_link(self, use_username: bool = False):
        if use_username:
            link = f"https://onlyfans.com/{self.username}"
        else:
            link = f"https://onlyfans.com/{self.id}"
        return link

    def is_authed_user(self):
        if self.id == self.get_authed().id:
            return True
        else:
            return False

    async def get_stories(
        self,
        limit: int = 100,
        offset: int = 0,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[StoryModel]:
        """Collect stories for callers requiring the public list/cache contract."""
        async with aclosing(
            self.iter_stories(
                limit=limit,
                offset=offset,
                on_progress=on_progress,
                job_id=job_id,
                cache=True,
            )
        ) as stories:
            return [story async for story in stories]

    async def iter_stories(
        self,
        limit: int = 100,
        offset: int = 0,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[StoryModel, None]:
        """Build stories only as consumed, without retaining profile models."""
        from ultima_scraper_api.managers.redis import publish_custom_event

        if max_items is not None and max_items < 0:
            raise ValueError("max_items must be nonnegative or None")
        if max_items == 0:
            return
        # Use provided job_id or fall back to "api" for standalone usage
        effective_job_id = job_id or "api"

        links = [
            endpoint_links(
                identifier=self.id, global_limit=limit, global_offset=offset
            ).stories_api
        ]

        # Create internal progress callback that publishes events with user context
        async def _emit_progress(
            completed_pages: int, total_pages: int, items_so_far: int
        ) -> None:
            if max_items is not None:
                items_so_far = min(items_so_far, max_items)
            await publish_custom_event(
                {
                    "event": "scrape_progress",
                    "job_id": effective_job_id,
                    "username": self.username,
                    "user_id": self.id,
                    "content_type": "Stories",
                    "status": "progress",
                    "items_scraped": items_so_far,
                    "items_saved": 0,
                    "total_items": None,  # Stories count unknown upfront
                    "page": completed_pages,
                    "total_pages": total_pages,
                    "has_more": completed_pages < total_pages,
                }
            )
            if on_progress:
                await on_progress(completed_pages, total_pages, items_so_far)

        count = 0
        async with aclosing(
            self.scrape_manager.iter_scrape(
                links,
                on_progress=_emit_progress,
            )
        ) as values:
            async for value in values:
                yield StoryModel(value, self, cache=cache)
                count += 1
                if max_items is not None and count >= max_items:
                    return

    async def get_highlights(
        self,
        identifier: int | str = "",
        limit: int = 100,
        offset: int = 0,
        hightlight_id: int | str = "",
    ) -> list[HighlightModel] | list[StoryModel]:
        from ultima_scraper_api import error_types

        final_results = []
        if not identifier:
            identifier = self.id
        if not hightlight_id:
            link = endpoint_links(
                identifier=identifier, global_limit=limit, global_offset=offset
            ).list_highlights
            result: dict[str, Any] = await self.get_requester().json_request(link)
            final_results = [HighlightModel(x, self) for x in result.get("list", [])]
        else:
            link = endpoint_links(
                identifier=hightlight_id, global_limit=limit, global_offset=offset
            ).highlight
            if not self.is_deleted:
                result = await self.get_requester().json_request(link)
                if not isinstance(result, error_types):
                    final_results = [
                        StoryModel(x, self, highlight=True) for x in result["stories"]
                    ]
        return final_results

    async def iter_highlight_stories(
        self,
        limit: int = 100,
        offset: int = 0,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        highlight_id: int | str = "",
        cache: bool = False,
    ) -> AsyncGenerator[StoryModel, None]:
        """Page album IDs and consume each album without a profile-wide list.

        ``limit`` bounds the requested album page, while ``max_items`` is the
        total story selection. The upstream response for one album is retained
        only while its stories are being consumed.
        """
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("Highlight page size must be a positive integer")
        if max_items is not None and max_items < 0:
            raise ValueError("max_items must be nonnegative or None")
        if self.is_deleted or max_items == 0:
            return

        async def albums():
            if highlight_id:
                yield highlight_id
                return
            current_offset = offset
            previous_page = None
            while True:
                link = endpoint_links(
                    identifier=self.id,
                    global_limit=limit,
                    global_offset=current_offset,
                ).list_highlights
                result = await self.get_requester().json_request(link)
                if not isinstance(result, dict) or "error" in result:
                    raise RuntimeError("Highlights page request failed")
                values = result.get("list", [])
                if not values:
                    return
                page_ids = tuple(value["id"] for value in values)
                if page_ids == previous_page:
                    raise RuntimeError(
                        "Highlights pagination repeated its previous page"
                    )
                previous_page = page_ids
                for value in values:
                    if cache:
                        HighlightModel(value, self)
                    yield value["id"]
                if not result.get("hasMore", len(values) >= limit):
                    return
                current_offset += len(values)

        count = completed_albums = 0
        async with aclosing(albums()) as identifiers:
            async for identifier in identifiers:
                result = await self.get_requester().json_request(
                    endpoint_links(identifier=identifier).highlight
                )
                if not isinstance(result, dict) or "error" in result:
                    raise RuntimeError(f"Highlight {identifier} request failed")
                stories = result["stories"]
                selected = len(stories)
                if max_items is not None:
                    selected = min(selected, max_items - count)
                completed_albums += 1
                count += selected
                if on_progress:
                    more = max_items is None or count < max_items
                    await on_progress(
                        completed_albums, completed_albums + int(more), count
                    )
                for index in range(selected):
                    yield StoryModel(stories[index], self, highlight=True, cache=cache)
                if max_items is not None and count >= max_items:
                    return
        if on_progress:
            await on_progress(completed_albums, completed_albums, count)

    @with_hooks
    async def get_posts(
        self,
        label: Literal["archived", "private_archived"] | str = "",
        limit: int | None = None,
        before_date: datetime | float | None = None,
        after_date: datetime | float | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ) -> list[PostModel]:
        """Collect posts for callers requiring the historical list/cache contract."""
        async with aclosing(
            self.iter_posts(
                label=label,
                limit=limit,
                before_date=before_date,
                after_date=after_date,
                on_progress=on_progress,
                job_id=job_id,
                cache=True,
            )
        ) as items:
            return [item async for item in items]

    async def iter_posts(
        self,
        label: Literal["archived", "private_archived"] | str = "",
        limit: int | None = None,
        before_date: datetime | float | None = None,
        after_date: datetime | float | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        cache: bool = False,
    ) -> AsyncGenerator[PostModel, None]:
        from ultima_scraper_api.managers.redis import publish_custom_event

        # Use provided job_id or fall back to "api" for standalone usage
        effective_job_id = job_id or "api"

        max_pagination_limit = 50  # maximum number of results per request
        epl = endpoint_links()
        api_count = self.posts_count
        if label == "archived":
            api_count = self.archived_posts_count
        elif label == "private_archived":
            if not self.is_authed_user():
                return
            api_count = self.private_archived_posts_count
        limit = api_count if limit is None else limit
        if limit < 0:
            raise ValueError("Post limit must be nonnegative or None")
        if limit == 0:
            return

        # Create internal progress callback that publishes events with user context
        async def _emit_progress(
            completed_pages: int, total_pages: int, items_so_far: int
        ) -> None:
            await publish_custom_event(
                {
                    "event": "scrape_progress",
                    "job_id": effective_job_id,
                    "username": self.username,
                    "user_id": self.id,
                    "content_type": "Posts",
                    "status": "progress",
                    "items_scraped": items_so_far,
                    "items_saved": 0,
                    "total_items": limit,  # Expected total items from API count
                    "page": completed_pages,
                    "total_pages": total_pages,
                    "has_more": completed_pages < total_pages,
                }
            )
            # Also call external callback if provided
            if on_progress:
                await on_progress(completed_pages, total_pages, items_so_far)

        if after_date is None and before_date is None:
            link = epl.list_posts(self.id, label=label)
            source = self.scrape_manager.iter_scrape(
                epl.iter_links(
                    link, limit, pagination_limit=max_pagination_limit, exact_limit=True
                ),
                on_progress=_emit_progress,
                total_pages=(limit + max_pagination_limit - 1) // max_pagination_limit,
            )
        else:
            source = iter_items(
                category="list_posts",
                requester=self.get_requester(),
                max_items=limit,
                identifier=self.id,
                limit=max_pagination_limit,
                before_date=before_date,
                after_date=after_date,
            )
        count = 0
        async with aclosing(source) as values:
            async for value in values:
                if not isinstance(value, dict) or value.get("responseType") != "post":
                    continue
                yield post_model.PostModel(value, self, cache=cache)
                count += 1
                if count >= limit:
                    break

    async def get_post(
        self, identifier: int | str | None = None, limit: int = 10, offset: int = 0
    ) -> PostModel:
        if not identifier:
            identifier = self.id
        link = endpoint_links(
            identifier=identifier, global_limit=limit, global_offset=offset
        ).post_by_id
        result = await self.get_requester().json_request(link)
        final_result = post_model.PostModel(result, self)
        if not final_result.author.id:
            final_result.author = self.get_authed().resolve_user(
                final_result.__raw__["author"]
            )
            pass
        return final_result

    @with_hooks
    async def get_messages(
        self,
        limit: int = 20,
        offset_id: int | None = None,
        cutoff_id: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
    ):
        """Collect messages while preserving the public cache/list contract."""
        if not self.cache.messages.is_released() or self.is_deleted:
            return list(self.scrape_manager.scraped.Messages.values())
        async with aclosing(
            self.iter_messages(
                limit=limit,
                offset_id=offset_id,
                cutoff_id=cutoff_id,
                on_progress=on_progress,
                job_id=job_id,
                cache=True,
            )
        ) as items:
            result = [item async for item in items]
        if result:
            self.cache.messages.activate()
        return result

    async def iter_messages(
        self,
        limit: int = 20,
        offset_id: int | None = None,
        cutoff_id: int | None = None,
        on_progress: ScrapeProgressCallback | None = None,
        job_id: str | None = None,
        *,
        max_items: int | None = None,
        cache: bool = False,
    ) -> AsyncGenerator[message_model.MessageModel, None]:
        """Fetch one message page at a time; limit controls page size only."""
        from ultima_scraper_api.managers.redis import publish_custom_event

        if limit <= 0:
            raise ValueError("Message page size must be positive")
        if max_items is not None and max_items < 0:
            raise ValueError("max_items must be nonnegative or None")
        if self.is_authed_user() or self.is_deleted or max_items == 0:
            return
        pages_completed = 0
        total_items = 0
        while max_items is None or total_items < max_items:
            link = endpoint_links().list_messages(
                self.id, global_limit=limit, global_offset=offset_id
            )
            result = await self.get_requester().json_request(link)
            items = result.get("list", [])
            if not items:
                return
            remaining = None if max_items is None else max_items - total_items
            selected = items if remaining is None else items[:remaining]
            pages_completed += 1
            total_items += len(selected)
            has_more = bool(result.get("hasMore")) and (
                max_items is None or total_items < max_items
            )
            if cutoff_id is not None and any(item["id"] == cutoff_id for item in items):
                has_more = False  # Preserve the historical inclusive cutoff page.
            estimated_total = pages_completed + int(has_more)
            await publish_custom_event(
                {
                    "event": "scrape_progress",
                    "job_id": job_id or "api",
                    "username": self.username,
                    "user_id": self.id,
                    "content_type": "Messages",
                    "status": "progress",
                    "items_scraped": total_items,
                    "items_saved": 0,
                    "total_items": max_items,
                    "page": pages_completed,
                    "total_pages": estimated_total,
                    "has_more": has_more,
                }
            )
            if on_progress:
                await on_progress(pages_completed, estimated_total, total_items)
            for item in selected:
                yield message_model.MessageModel(item, self, cache=cache)
            if not has_more:
                return
            next_id = items[-1]["id"]
            if offset_id is not None and int(next_id) >= int(offset_id):
                raise RuntimeError("Messages pagination did not advance its cursor")
            offset_id = next_id

    async def get_mass_messages(self, message_cutoff_id: int | None = None):
        messages = await self.get_messages(cutoff_id=message_cutoff_id)
        paid_messages = [
            x
            for x in await self.get_paid_contents()
            if isinstance(x, message_model.MessageModel)
        ]
        mass_messages = [
            MassMessageModel(x.__raw__, x.get_author())
            for x in messages + paid_messages
            if x.is_mass_message() and x.get_author() == self
        ]
        return mass_messages

    async def get_message_by_id(
        self,
        user_id: int | None = None,
        message_id: int | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        if not user_id:
            user_id = self.id
        link = endpoint_links(
            identifier=user_id,
            identifier2=message_id,
            global_limit=limit,
            global_offset=offset,
        ).message_by_id
        response = await self.get_requester().json_request(link)
        temp_response: dict[str, Any] = response
        results: list[dict[str, Any]] = [
            x for x in temp_response["list"] if x["id"] == message_id
        ]
        result = results[0] if results else {}
        final_result = message_model.MessageModel(result, self)
        return final_result

    async def get_archived_stories(self, limit: int = 100, offset: int = 0):
        final_results: list[StoryModel] = []
        if self.is_authed_user() and self.is_performer():

            async def recursive(limit: int = limit, offset: int = offset):
                link = endpoint_links().list_archived_stories(
                    limit=limit, marker_offset=offset
                )
                results = await self.get_requester().json_request(link)

                items: list[dict[str, Any]] = results.get("list", [])
                if results["hasMore"]:
                    results2 = await recursive(limit=limit, offset=results["marker"])
                    items.extend(results2)
                return items

            results = await recursive()
            final_results = [StoryModel(x, self) for x in results]
        return final_results

    async def search_chat(
        self,
        identifier: int | str = "",
        text: str = "",
        refresh: bool = True,
        limit: int = 10,
        offset: int = 0,
    ):
        # Onlyfans can't do a simple search, so this is broken. If you want it to "work", don't use commas, or basically any mysql injection characters (lol)
        if identifier:
            identifier = parse.urljoin(str(identifier), "messages")
        else:
            identifier = self.id
        link = endpoint_links(
            identifier=identifier, text=text, global_limit=limit, global_offset=offset
        ).search_chat
        results = await self.get_requester().json_request(link)
        return results

    async def search_messages(
        self,
        identifier: int | str = "",
        text: str = "",
        refresh: bool = True,
        limit: int = 10,
        offset: int = 0,
    ):
        # Onlyfans can't do a simple search, so this is broken. If you want it to "work", don't use commas, or basically any mysql injection characters (lol)
        if identifier:
            identifier = parse.urljoin(str(identifier), "messages")
        text = parse.quote_plus(text)
        link = endpoint_links(
            identifier=identifier, text=text, global_limit=limit, global_offset=offset
        ).search_messages
        results = await self.get_requester().json_request(link)
        return results

    async def like(self, category: str, identifier: int):
        link = endpoint_links(identifier=category, identifier2=identifier).like
        results = await self.get_requester().json_request(link, method="POST")
        return results

    async def unlike(self, category: str, identifier: int):
        link = endpoint_links(identifier=category, identifier2=identifier).like
        results = await self.get_requester().json_request(link, method="DELETE")
        return results

    async def subscription_price(self):
        """
        Returns subscription price. This includes the promotional price.
        """
        subscription_price = self.subscribe_price
        if self.promotions:
            for promotion in self.promotions:
                promotion_price: int = promotion["price"]
                if promotion_price < subscription_price:
                    subscription_price = promotion_price
        return subscription_price

    async def get_promotions(self):
        return self.promotions

    async def buy_subscription(self):
        """
        This function will subscribe to a model. If the model has a promotion available, it will use it.
        """
        subscription_price = await self.subscription_price()
        x: dict[str, Any] = {
            "paymentType": "subscribe",
            "userId": self.id,
            "subscribeSource": "profile",
            "amount": subscription_price,
            "token": "",
            "unavailablePaymentGates": [],
        }

        authed = self.get_authed()
        assert authed.user.credit_balance is not None
        if authed.user.credit_balance >= subscription_price:
            link = endpoint_links(identifier=self.id).pay
            result = await self.get_requester().json_request(
                link, method="POST", payload=x
            )
        else:
            result: dict[str, Any] = {
                "error": {"code": 2011, "message": "Insufficient Credit Balance"}
            }
        if "error" not in result:
            self.subscribed_by = True
        return result

    def finalize_content_set(self, results: list[dict[str, Any]] | list[str]):
        final_results: list[PostModel] = []
        for result in results:
            if isinstance(result, str):
                continue
            content_type = result["responseType"]
            match content_type:
                case "post":
                    created = post_model.PostModel(result, self)
                    final_results.append(created)
                case _:
                    pass
        return final_results

    async def if_scraped(self):
        status = False
        for key, value in self.scrape_manager.scraped.__dict__.items():
            if key == "Archived":
                for _key_2, value in value.__dict__.items():
                    if value:
                        status = True
                        return status
            if value:
                status = True
                break
        return status

    async def match_identifiers(self, identifiers: list[int | str]):
        if self.id in identifiers or self.username in identifiers:
            return True
        else:
            return False

    async def get_avatar(self):
        return self.avatar

    async def get_header(self):
        return self.header

    def is_performer_subscribed_to_user(self):
        # Checks if performer is subscribed to authed user
        return self.subscribed_on

    def is_user_subscribed_to_performer(self):
        # Checks if authed user is subscribed to performer
        return self.subscribed_by

    def is_performer(self):
        status = False
        if self._is_performer:
            status = True
        elif self.is_real_performer:
            status = True
        elif self.can_earn:
            status = True
        return status

    async def get_paid_contents(self, content_type: str | None = None):
        # REMINDER THAT YOU'LL HAVE TO REFRESH CONTENT
        final_paid_content: list[PostModel | message_model.MessageModel] = []
        authed = self.get_authed()
        for paid_content in authed.paid_content:
            # Just use response to key function in ContentTypes
            if paid_content.author.id == self.id:
                if (
                    content_type is not None
                    and content_type.lower() != f"{paid_content.responseType}s"
                ):
                    continue
                final_paid_content.append(paid_content)
        return final_paid_content

    async def has_socials(self):
        # If error message, this means the user has socials, but we have to subscribe to see them
        result = bool(
            await self.get_requester().json_request(endpoint_links(self.id).socials)
        )
        return result

    async def get_socials(self):
        results: list[dict[str, Any]] | dict[str, Any] = (
            await self.get_requester().json_request(endpoint_links(self.id).socials)
        )
        if "error" in results:
            results = []
        assert isinstance(results, list)
        return results

    async def get_spotify(self):
        if self.is_spotify_connected:
            result: dict[str, Any] = await self.get_requester().json_request(
                endpoint_links(self.id).spotify
            )
            if "error" in result:
                result = {}
            return result

    async def has_spotify(self):
        # If error message, this means the user has socials, but we have to subscribe to see them
        result = bool(
            await self.get_requester().json_request(endpoint_links(self.id).spotify)
        )
        return result

    async def get_w9_form(self):
        # :)
        if self.can_has_w9_form:
            url = "https://onlyfans.com/action/download_1099"
            response = await self.get_requester().request(url)
            if response:
                return await response.read()

    async def block(self):
        block_url = endpoint_links(self.id).block
        result = await self.get_requester().json_request(block_url, method="POST")

        return result

    async def unblock(self):
        block_url = endpoint_links(self.id).block
        result = await self.get_requester().json_request(block_url, method="DELETE")

        return result
