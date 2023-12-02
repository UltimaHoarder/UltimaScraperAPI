from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans.classes.message_model import create_message

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.auth_model import AuthModel


class ChatModel:
    def __init__(self, options: dict[str, Any], authed: "AuthModel") -> None:
        self.user = authed.resolve_user(options["withUser"])
        last_message_user = authed.resolve_user(options["lastMessage"]["fromUser"])
        self.last_message = create_message(
            options["lastMessage"],
            last_message_user,
        )
        self.last_read_message_id: int = options["lastReadMessageId"]
        self.has_purchased_feed: bool = options["hasPurchasedFeed"]
        self.count_pinned_messages: int = options["countPinnedMessages"]
        self.messages: list[create_message] | None = None
