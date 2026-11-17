from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly.classes.message_model import MessageModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class ChatModel:
    """A conversation from GET /messaging/groups, joined with its aggregationData."""

    def __init__(
        self,
        options: dict[str, Any],
        user: UserModel,
        group: dict[str, Any] | None = None,
    ) -> None:
        self.__raw__ = options
        self.user = user
        self.group_id: int = int(options["groupId"])
        self.unread_count: int = options.get("unreadCount", 0)
        self.last_message_id: str | None = options.get("lastMessageId")
        last_message = (group or {}).get("lastMessage")
        # The group's lastMessage arrives without its accountMedia aggregation.
        self.last_message = MessageModel(last_message, user) if last_message else None
        self.messages: list[MessageModel] | None = None

    def get_authed(self) -> FanslyAuthModel:
        return self.user.get_authed()

    async def get_messages(self):
        self.messages = await self.user.get_messages(group_id=self.group_id)
        return self.messages
