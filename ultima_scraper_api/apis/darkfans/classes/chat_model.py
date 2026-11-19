from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import parse_time

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel


class ChatModel:
    """A chat from GET /user/{me}/chat; ``user`` is the other participant."""

    def __init__(self, options: dict[str, Any], user: UserModel) -> None:
        self.__raw__ = options
        self.id: str = str(options.get("id") or "")
        self.user = user
        self.last_message: str | None = options.get("lastMessage")
        self.last_activity = parse_time(options.get("lastActivity"))
        self.unread: int = int(options.get("nbUnreadMessages") or 0)
        self.is_read: bool = not self.unread
        self.is_archived: bool = bool(options.get("archived"))
        self.is_blocked: bool = bool(options.get("blocked") or options.get("blockedByMe"))

    def get_authed(self):
        return self.user.get_authed()
