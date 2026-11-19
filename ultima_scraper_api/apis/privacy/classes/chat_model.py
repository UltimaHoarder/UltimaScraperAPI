from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ultima_scraper_api.apis.privacy.classes.user_model import UserModel


class ChatModel:
    """A room from GET /chat/rooms (or /chat/room)."""

    def __init__(self, options: dict[str, Any], user: UserModel) -> None:
        self.__raw__ = options
        self.user = user
        self.room_id: str = options["roomId"]
        self.unread_count: int = int(options.get("unreadCount") or 0)
        self.last_message: dict[str, Any] | None = options.get("lastMessage")
        self.is_pinned: bool = bool(options.get("isPinned"))

    def get_authed(self):
        return self.user.get_authed()
