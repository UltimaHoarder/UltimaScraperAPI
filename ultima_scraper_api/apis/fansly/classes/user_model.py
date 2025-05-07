from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib import parse

import ultima_scraper_api.apis.fansly.classes.message_model as message_model
from ultima_scraper_api.apis import api_helper
from ultima_scraper_api.apis.fansly.classes import collection_model, post_model
from ultima_scraper_api.apis.fansly.classes.extras import ErrorDetails, endpoint_links
from ultima_scraper_api.apis.fansly.classes.hightlight_model import HighlightModel
from ultima_scraper_api.apis.fansly.classes.story_model import StoryModel
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser
from ultima_scraper_api.managers.scrape_manager import ScrapeManager

if TYPE_CHECKING:
    from ultima_scraper_api import FanslyAPI
    from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
    from ultima_scraper_api.apis.fansly.classes.post_model import PostModel


class UserModel(StreamlinedUser["FanslyAuthModel", "FanslyAPI"]):
    def __init__(
        self,
        option: dict[str, Any],
        authed: FanslyAuthModel,
    ) -> None:
        self.avatar: Any = option.get("avatar")
        self.avatar_thumbs: Any = option.get("avatarThumbs")
        self.header: Any = option.get("banner")
        self.header_size: Any = option.get("headerSize")
        self.header_thumbs: Any = option.get("headerThumbs")
        self.id: int = int(option.get("id", 9001))
        self.name: str = option.get("name")
        self.username: str = option.get("username")
        self.can_look_story: bool = option.get("canLookStory")
        self.can_comment_story: bool = option.get("canCommentStory")
        self.has_not_viewed_story: bool = option.get("hasNotViewedStory")
        self.is_verified: bool = option.get("isVerified")
        self.can_pay_internal: bool = option.get("canPayInternal")
        self.has_scheduled_stream: bool = option.get("hasScheduledStream")
        self.has_stream: bool = option.get("hasStream")
        self.has_stories: bool = option.get("hasStories")
        self.tips_enabled: bool = option.get("tipsEnabled")
        self.tips_text_enabled: bool = option.get("tipsTextEnabled")
        self.tips_min: int = option.get("tipsMin")
        self.tips_max: int = option.get("tipsMax")
        self.can_earn: bool = option.get("canEarn")
        self.can_add_subscriber: bool = option.get("canAddSubscriber")
        self.subscribe_price: int = option.get("subscribePrice")
        self.has_stripe: bool = option.get("hasStripe")
        self.is_stripe_exist: bool = option.get("isStripeExist")
        self.subscription_bundles: list[dict[Any, Any]] = option.get(
            "subscriptionTiers", []
        )
        self.can_send_chat_to_all: bool = option.get("canSendChatToAll")
        self.credits_min: int = option.get("creditsMin")
        self.credits_max: int = option.get("creditsMax")
        self.is_paywall_restriction: bool = option.get("isPaywallRestriction")
        self.unprofitable: bool = option.get("unprofitable")
        self.lists_sort: str = option.get("listsSort")
        self.lists_sort_order: str = option.get("listsSortOrder")
        self.can_create_lists: bool = option.get("canCreateLists")
        self.join_date: str = option.get("joinDate")
        self.is_referrer_allowed: bool = option.get("isReferrerAllowed")
        self.about: str = option.get("about")
        self.raw_about: str = option.get("rawAbout")
        self.website: str = option.get("website")
        self.wishlist: str = option.get("wishlist")
        self.location: str = option.get("location")
        timeline_stats = option.get("timelineStats", {})
        self.posts_count: int = option.get("postsCount", 0)
        self.archived_posts_count: int = option.get("archivedPostsCount", 0)
        self.photos_count: int = timeline_stats.get("imageCount", 0)
        self.videos_count: int = timeline_stats.get("videoCount", 0)
        self.audios_count: int = option.get("audiosCount", 0)
        self.medias_count: int = option.get("mediasCount", 0)
        self.promotions: list = option.get("promotions")
        self.last_seen: Any = option.get("lastSeen")
        self.favorited_count: int = option.get("accountMediaLikes")
        self.show_posts_in_feed: bool = option.get("showPostsInFeed")
        self.can_receive_chat_message: bool = option.get("canReceiveChatMessage")
        self._is_performer: bool = bool(self.subscription_bundles)
        self.is_real_performer: bool = option.get("isRealPerformer")
        self.is_spotify_connected: bool = option.get("isSpotifyConnected")
        self.subscribers_count: int = option.get("subscribersCount")
        self.has_pinned_posts: bool = option.get("hasPinnedPosts")
        self.can_chat: bool = option.get("canChat")
        self.call_price: int = option.get("callPrice")
        self.is_private_restriction: bool = option.get("isPrivateRestriction")
        self.following: bool = option.get("following")
        self.show_subscribers_count: bool = option.get("showSubscribersCount")
        self.show_media_count: bool = option.get("showMediaCount")
        self.subscribed: bool = option.get("subscribed", False)
        self.subscribed_by_data: Any = option.get("subscription")
        self.subscribed_on_data: Any = option.get("subscribedOnData")
        self.can_promotion: bool = option.get("canPromotion")
        self.can_create_promotion: bool = option.get("canCreatePromotion")
        self.can_create_trial: bool = option.get("canCreateTrial")
        self.is_adult_content: bool = option.get("isAdultContent")
        self.ignoring: int = option.get("ignoring", 0)
        self.can_trial_send: bool = option.get("canTrialSend")
        self.can_add_phone: bool = option.get("canAddPhone")
        self.phone_last4: Any = option.get("phoneLast4")
        self.phone_mask: Any = option.get("phoneMask")
        self.has_new_ticket_replies: dict = option.get("hasNewTicketReplies")
        self.has_internal_payments: bool = option.get("hasInternalPayments")
        self.is_credits_enabled: bool = option.get("isCreditsEnabled")
        self.credit_balance: float = (
            option["mainWallet"]["balance"] if "mainWallet" in option else 0
        )
        self.is_make_payment: bool = option.get("isMakePayment")
        self.is_otp_enabled: bool = option.get("isOtpEnabled")
        self.email: str = option.get("email")
        self.is_email_checked: bool = option.get("isEmailChecked")
        self.is_legal_approved_allowed: bool = option.get("isLegalApprovedAllowed")
        self.is_twitter_connected: bool = option.get("isTwitterConnected")
        self.twitter_username: Any = option.get("twitterUsername")
        self.is_allow_tweets: bool = option.get("isAllowTweets")
        self.is_payment_card_connected: bool = option.get("isPaymentCardConnected")
        self.referal_url: str = option.get("referalUrl")
        self.is_visible_online: bool = option.get("isVisibleOnline")
        self.subscribes_count: int = option.get("subscribesCount")
        self.can_pin_post: bool = option.get("canPinPost")
        self.has_new_alerts: bool = option.get("hasNewAlerts")
        self.has_new_hints: bool = option.get("hasNewHints")
        self.has_new_changed_price_subscriptions: bool = option.get(
            "hasNewChangedPriceSubscriptions"
        )
        self.notifications_count: int = option.get("notificationsCount")
        self.chat_messages_count: int = option.get("chatMessagesCount")
        self.is_want_comments: bool = option.get("isWantComments")
        self.watermark_text: str = option.get("watermarkText")
        self.custom_watermark_text: Any = option.get("customWatermarkText")
        self.has_watermark_photo: bool = option.get("hasWatermarkPhoto")
        self.has_watermark_video: bool = option.get("hasWatermarkVideo")
        self.can_delete: bool = option.get("canDelete")
        self.is_telegram_connected: bool = option.get("isTelegramConnected")
        self.adv_block: list = option.get("advBlock")
        self.has_purchased_posts: bool = option.get("hasPurchasedPosts")
        self.is_email_required: bool = option.get("isEmailRequired")
        self.is_payout_legal_approved: bool = option.get("isPayoutLegalApproved")
        self.payout_legal_approve_state: str = option.get("payoutLegalApproveState")
        self.payout_legal_approve_reject_reason: Any = option.get(
            "payoutLegalApproveRejectReason"
        )
        self.enabled_image_editor_for_chat: bool = option.get(
            "enabledImageEditorForChat"
        )
        self.should_receive_less_notifications: bool = option.get(
            "shouldReceiveLessNotifications"
        )
        self.can_calling: bool = option.get("canCalling")
        self.paid_feed: bool = option.get("paidFeed")
        self.can_send_sms: bool = option.get("canSendSms")
        self.can_add_friends: bool = option.get("canAddFriends")
        self.is_real_card_connected: bool = option.get("isRealCardConnected")
        self.count_priority_chat: int = option.get("countPriorityChat")
        self.has_scenario: bool = option.get("hasScenario")
        self.is_wallet_autorecharge: bool = option.get("isWalletAutorecharge")
        self.wallet_autorecharge_amount: int = option.get("walletAutorechargeAmount")
        self.wallet_autorecharge_min: int = option.get("walletAutorechargeMin")
        self.wallet_first_rebills: bool = option.get("walletFirstRebills")
        self.close_friends: int = option.get("closeFriends")
        self.can_alternative_wallet_top_up: bool = option.get(
            "canAlternativeWalletTopUp"
        )
        self.need_iv_approve: bool = option.get("needIVApprove")
        self.iv_status: Any = option.get("ivStatus")
        self.iv_fail_reason: Any = option.get("ivFailReason")
        self.can_check_docs_on_add_card: bool = option.get("canCheckDocsOnAddCard")
        self.face_id_available: bool = option.get("faceIdAvailable")
        self.iv_country: Any = option.get("ivCountry")
        self.iv_forced_verified: bool = option.get("ivForcedVerified")
        self.iv_flow: str = option.get("ivFlow")
        self.is_verified_reason: bool = option.get("isVerifiedReason")
        self.can_receive_manual_payout: bool = option.get("canReceiveManualPayout")
        self.can_receive_stripe_payout: bool = option.get("canReceiveStripePayout")
        self.manual_payout_pending_days: int = option.get("manualPayoutPendingDays")
        self.is_need_confirm_payout: bool = option.get("isNeedConfirmPayout")
        self.can_streaming: bool = option.get("canStreaming")
        self.is_scheduled_streams_allowed: bool = option.get(
            "isScheduledStreamsAllowed"
        )
        self.can_make_expire_posts: bool = option.get("canMakeExpirePosts")
        self.trial_max_days: int = option.get("trialMaxDays")
        self.trial_max_expires_days: int = option.get("trialMaxExpiresDays")
        self.message_min_price: int = option.get("messageMinPrice")
        self.message_max_price: int = option.get("messageMaxPrice")
        self.post_min_price: int = option.get("postMinPrice")
        self.post_max_price: int = option.get("postMaxPrice")
        self.stream_min_price: int = option.get("streamMinPrice")
        self.stream_max_price: int = option.get("streamMaxPrice")
        self.can_create_paid_stream: bool = option.get("canCreatePaidStream")
        self.call_min_price: int = option.get("callMinPrice")
        self.call_max_price: int = option.get("callMaxPrice")
        self.subscribe_min_price: float = option.get("subscribeMinPrice")
        self.subscribe_max_price: int = option.get("subscribeMaxPrice")
        self.bundle_max_price: int = option.get("bundleMaxPrice")
        self.unclaimed_offers_count: int = option.get("unclaimedOffersCount")
        self.claimed_offers_count: int = option.get("claimedOffersCount")
        self.withdrawal_period: str = option.get("withdrawalPeriod")
        self.can_add_story: bool = option.get("canAddStory")
        self.can_add_subscriber_by_bundle: bool = option.get("canAddSubscriberByBundle")
        self.is_suggestions_opt_out: bool = option.get("isSuggestionsOptOut")
        self.can_create_fund_raising: bool = option.get("canCreateFundRaising")
        self.min_fund_raising_target: int = option.get("minFundRaisingTarget")
        self.max_fund_raising_target: int = option.get("maxFundRaisingTarget")
        self.disputes_ratio: int = option.get("disputesRatio")
        self.vault_lists_sort: str = option.get("vaultListsSort")
        self.vault_lists_sort_order: str = option.get("vaultListsSortOrder")
        self.can_create_vault_lists: bool = option.get("canCreateVaultLists")
        self.can_make_profile_links: bool = option.get("canMakeProfileLinks")
        self.reply_on_subscribe: bool = option.get("replyOnSubscribe")
        self.payout_type: str = option.get("payoutType")
        self.min_payout_summ: int = option.get("minPayoutSumm")
        self.can_has_w9_form: bool = option.get("canHasW9Form")
        self.is_vat_required: bool = option.get("isVatRequired")
        self.is_country_vat_refundable: bool = option.get("isCountryVatRefundable")
        self.is_country_vat_number_collect: bool = option.get(
            "isCountryVatNumberCollect"
        )
        self.vat_number_name: str = option.get("vatNumberName")
        self.is_country_with_vat: bool = option.get("isCountryWithVat")
        self.connected_of_accounts: list = option.get("connectedOfAccounts")
        self.has_password: bool = option.get("hasPassword")
        self.can_connect_of_account: bool = option.get("canConnectOfAccount")
        self.pinned_posts_count: int = option.get("pinnedPostsCount")
        self.max_pinned_posts_count: int = option.get("maxPinnedPostsCount")
        # Custom
        found_user = authed.find_user(self.id)
        if not found_user:
            authed.add_user(self)
        self.is_blocked: bool = True if self.ignoring == 2 else False
        self.download_info: dict[str, Any] = {}
        self.duplicate_media = []
        self.scrape_manager = ScrapeManager[
            "FanslyAuthModel", authed.get_api().CategorizedContent
        ](authed)
        self.__raw__ = option
        self.__db_user__: Any = None
        super().__init__(authed)

    def get_username(self):
        return self.username

    def get_link(self):
        link = f"https://fansly.com/{self.username}"
        return link

    def is_authed_user(self):
        if self.id == self.get_authed().id:
            return True
        else:
            return False

    async def get_stories(self) -> list[StoryModel]:
        link = endpoint_links(identifier=self.id).stories_api
        result = await self.scrape_manager.scrape(link)
        assert isinstance(result, dict)
        final_results = [
            StoryModel(x, self) for x in result["response"]["mediaStories"]
        ]
        return final_results

    async def get_highlights(
        self, identifier="", refresh=True, limit=100, offset=0, hightlight_id=""
    ) -> list:
        api_type = "highlights"
        if not identifier:
            identifier = self.id
        if not hightlight_id:
            link = endpoint_links(
                identifier=identifier, global_limit=limit, global_offset=offset
            ).list_highlights
            results = await self.get_requester().json_request(link)
            results = await remove_errors(results)
            results = [HighlightModel(x) for x in results]
        else:
            link = endpoint_links(
                identifier=hightlight_id, global_limit=limit, global_offset=offset
            ).highlight
            results = await self.get_requester().json_request(link)
            results = [StoryModel(x) for x in results["stories"]]
        return results

    async def get_posts(
        self,
        links: Optional[list[str]] = None,
        limit: int = 10,
        offset: int = 0,
        refresh: bool = True,
    ) -> list[PostModel]:
        temp_results: list[Any] = []
        while True:
            link = endpoint_links(identifier=self.id, global_offset=offset).post_api
            response = await self.get_requester().json_request(link)
            data = response["response"]
            temp_posts = data.get("posts")
            if not temp_posts:
                break
            offset = temp_posts[-1]["id"]
            temp_results.append(data)
        results = api_helper.merge_dictionaries(temp_results)
        final_results = []
        if results:
            final_results = [
                post_model.PostModel(x, self, results) for x in results["posts"]
            ]
            for result in final_results:
                await result.get_comments()
            self.scrape_manager.scraped.Posts = final_results
        return final_results

    async def get_post(
        self, identifier: Optional[int | str] = None, limit: int = 10, offset: int = 0
    ) -> Union[PostModel, ErrorDetails]:
        if not identifier:
            identifier = self.id
        link = endpoint_links(
            identifier=identifier, global_limit=limit, global_offset=offset
        ).post_by_id
        result = await self.get_requester().json_request(link)
        if isinstance(result, dict):
            temp_result: dict[str, Any] = result
            final_result = post_model.PostModel(temp_result, self, temp_result)
            return final_result
        return result

    async def get_groups(self) -> ErrorDetails | dict[str, Any]:
        link = endpoint_links().groups_api
        response: ErrorDetails | dict[str, Any] = (
            await self.get_requester().json_request(link)
        )
        if isinstance(response, dict):
            final_response: dict[str, Any] = response["response"]
            return final_response
        return response

    async def get_messages(
        self,
        links: Optional[list[str]] = None,
        limit: int = 100000,
        before: str = "",
        cutoff_id: int | None = None,
        refresh: bool = True,
        inside_loop: bool = False,
    ):
        groups = await self.get_groups()
        if isinstance(groups, ErrorDetails):
            return []
        found_id: Optional[int] = None
        for group in groups["groups"]:
            for user in group["users"]:
                if self.id == int(user["userId"]):
                    found_id = int(user["groupId"])
                    break
        final_results: list[message_model.MessageModel] = []
        if found_id:
            if links is None:
                links = []

            link = endpoint_links(
                identifier=found_id, global_limit=limit, before_id=before
            ).message_api
            links.append(link)

            results = await self.get_requester().bulk_requests(links)
            results = [await x.json() for x in results if x]
            results = await api_helper.remove_errors(results)
            results = api_helper.merge_dictionaries(results)
            if not results:
                return []
            extras = results["response"]
            final_results = extras["messages"]

            if final_results:
                lastId = final_results[-1]["id"]
                results2 = await self.get_messages(
                    links=[links[-1]],
                    limit=limit,
                    before=lastId,
                    inside_loop=True,
                )
                final_results.extend(results2)
            if not inside_loop:
                final_results = [
                    message_model.MessageModel(x, self, extras)
                    for x in final_results
                    if x
                ]
            self.scrape_manager.scraped.Messages = final_results
        return final_results

    async def get_message_by_id(
        self, user_id=None, message_id=None, refresh=True, limit=10, offset=0
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
        if isinstance(response, dict):
            results = [x for x in response["list"] if x["id"] == message_id]
            result = results[0] if results else {}
            final_result = message_model.MessageModel(result, self)
            return final_result
        return response

    async def get_archived_stories(
        self, refresh: bool = True, limit: int = 100, offset: int = 0
    ):
        link = endpoint_links(global_limit=limit, global_offset=offset).archived_stories
        results = await self.get_requester().json_request(link)
        results = await api_helper.remove_errors(results)
        results = [StoryModel(x) for x in results]
        return results

    async def get_archived_posts(
        self,
        links: Optional[list[str]] = None,
        refresh: bool = True,
        limit: int = 10,
        offset: int = 0,
    ):
        if links is None:
            links = []
        api_count = self.archived_posts_count
        if api_count and not links:
            link = endpoint_links(
                identifier=self.id, global_limit=limit, global_offset=offset
            ).archived_posts
            ceil = math.ceil(api_count / limit)
            numbers = list(range(ceil))
            for num in numbers:
                num = num * limit
                link = link.replace(f"limit={limit}", f"limit={limit}")
                new_link = link.replace("offset=0", f"offset={num}")
                links.append(new_link)
        results = await self.scrape_manager.bulk_scrape(links)
        final_results = self.finalize_content_set(results)

        self.temp_scraped.Archived.Posts = final_results
        return final_results

    async def get_archived(self, api):
        items = []
        if self.is_me():
            item = {}
            item["type"] = "Stories"
            item["results"] = [await self.get_archived_stories()]
            items.append(item)
        item = {}
        item["type"] = "Posts"
        # item["results"] = test
        item["results"] = await self.get_archived_posts()
        items.append(item)
        return items

    async def search_chat(
        self, identifier="", text="", refresh=True, limit=10, offset=0
    ):
        if identifier:
            identifier = parse.urljoin(identifier, "messages")
        link = endpoint_links(
            identifier=identifier, text=text, global_limit=limit, global_offset=offset
        ).search_chat
        results = await self.get_requester().json_request(link)
        return results

    async def search_messages(
        self, identifier="", text="", refresh=True, limit=10, offset=0
    ):
        if identifier:
            identifier = parse.urljoin(identifier, "messages")
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
        for bundle in self.subscription_bundles:
            return bundle["price"] / 1000

    async def buy_subscription(self):
        """
        This function will subscribe to a model. If the model has a promotion available, it will use it.
        """
        subscription_price = await self.subscription_price()
        x = {
            "paymentType": "subscribe",
            "userId": self.id,
            "subscribeSource": "profile",
            "amount": subscription_price,
            "token": "",
            "unavailablePaymentGates": [],
        }
        if self.subscriber.credit_balance >= subscription_price:
            link = endpoint_links().pay
            result = await self.get_requester().json_request(
                link, method="POST", payload=x
            )
        else:
            result = ErrorDetails(
                {"code": 2011, "message": "Insufficient Credit Balance"}
            )
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
                    print
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

    async def get_collections(self):
        link = endpoint_links(identifier=self.id).collections_api
        results = await self.get_requester().json_request(link)
        return results["response"]

    async def get_collection_content(self, collection: dict[str, Any], offset: int = 0):
        temp_responses: list[dict[str, Any]] = []
        while True:
            link = endpoint_links(
                identifier=collection["id"], global_limit=25, global_offset=offset
            ).collection_api
            results = await self.get_requester().json_request(link)
            response = results["response"]
            album_content = response["albumContent"]
            if not album_content:
                break
            offset = int(album_content[-1]["id"])
            temp_responses.append(response)
        responses = api_helper.merge_dictionaries(temp_responses)
        final_result = collection_model.CollectionModel(collection, self, responses)
        return final_result

    async def get_avatar(self):
        return self.avatar["locations"][0]["location"] if self.header else None

    async def get_header(self):
        return self.header["locations"][0]["location"] if self.header else None

    def is_subscribed(self):
        pass

    def is_performer(self):
        status = False
        if self.is_performer:
            status = True
        elif self.is_real_performer:
            status = True
        elif self.can_earn:
            status = True
        return status
