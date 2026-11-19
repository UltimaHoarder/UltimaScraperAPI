from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.loyalfans import (
    MEDIA_KINDS,
    Media,
    SiteContent,
    parse_time,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel


class StoryModel(SiteContent):
    """A story (one image or video ``file``), live or kept in a highlight."""

    def __init__(
        self,
        option: dict[str, Any],
        user: UserModel,
        highlight: HighlightModel | None = None,
    ) -> None:
        SiteContent.__init__(self, str(option["uid"]), user)
        self.__raw__ = option
        self.highlight = highlight
        self.created_at: datetime | None = parse_time(option.get("created_at"))
        self.price = float(option.get("price") or 0)
        url = option.get("file")
        self.media = [
            Media(
                option,
                media_uid=self.uid,
                kind=MEDIA_KINDS.get(str(option.get("type")).lower(), "photo"),
                url=url,
                created_at=self.created_at,
                duration=option.get("duration"),
                preview_url=option.get("poster"),
            )
        ] if url else []

    def is_bought(self) -> bool:
        return bool(self.media)


class HighlightModel:
    """A highlight (POST /stories/highlights); its stories come inline."""

    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        self.__raw__ = option
        self.uid: str = str(option["uid"])
        self.title: str = option.get("title") or ""
        self.user = user
        self.stories = [StoryModel(story, user, self) for story in option.get("stories") or []]
