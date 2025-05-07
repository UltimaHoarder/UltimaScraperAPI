from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans.classes.message_model import MessageModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel


class ChatModel:
    def __init__(self, options: dict[str, Any], authed: "OnlyFansAuthModel") -> None:
        self.__raw__ = options
        self.user = authed.resolve_user(options["withUser"])
        last_message = options.get("lastMessage")
        if last_message:
            last_message_user = authed.resolve_user(options["lastMessage"]["fromUser"])
            self.last_message = MessageModel(
                options["lastMessage"],
                last_message_user,
            )
        else:
            self.last_message = None
        self.last_read_message_id: int = options["lastReadMessageId"]
        self.has_purchased_feed: bool = options["hasPurchasedFeed"]
        self.count_pinned_messages: int = options["countPinnedMessages"]
        self.messages: list[MessageModel] | None = None

    async def get_messages(self):
        self.messages = await self.user.get_messages()
        return self.messages
