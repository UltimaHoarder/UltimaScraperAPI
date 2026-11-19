from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.darkfans import SiteContent, file_media, parse_time

if TYPE_CHECKING:
    from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel


class StoryModel(SiteContent):
    """A story: one ``file``. ``pinned`` stories stay on the profile."""

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        SiteContent.__init__(self, str(option["id"]), user)
        self.__raw__ = option
        self.created_at: datetime | None = parse_time(option.get("createdAt"))
        self.pinned: bool = bool(option.get("pinned"))
        self.story_type: str = option.get("type") or ""
        self.likes: int = int(option.get("nbLiked") or 0)
        file = option.get("file")
        item = file_media(file, self.created_at) if isinstance(file, dict) else None
        self.media = [item] if item is not None else []

    def is_bought(self) -> bool:
        return bool(self.media)
