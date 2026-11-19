from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


class ChatModel:
    """A conversation from POST /api/v2/messages."""

    def __init__(self, options: dict[str, Any], user: UserModel) -> None:
        self.__raw__ = options
        self.user = user
        self.last_message: dict[str, Any] | None = options.get("last_message")
        self.is_read: bool = bool(options.get("read"))
        self.is_muted: bool = bool(options.get("mute"))
        self.is_blocked: bool = bool(options.get("block") or options.get("blocked"))

    def get_authed(self):
        return self.user.get_authed()
