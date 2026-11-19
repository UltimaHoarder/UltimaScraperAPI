from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.fansly import (
    SiteContent,
    from_timestamp,
    resolve_account_media,
)

if TYPE_CHECKING:
    from ultima_scraper_api.apis.fansly.classes.user_model import UserModel


class CollectionModel(SiteContent):
    """A vault album with the media of all its content pages.

    ``album`` is an entry of GET /uservault/albumsnew; ``content`` holds the
    merged pages of GET /uservault/album/content (albumContent + aggregationData).
    """

    def __init__(
        self, album: dict[str, Any], user: UserModel, content: dict[str, Any]
    ) -> None:
        SiteContent.__init__(self, album, user)
        self.author = user
        self.title: str = album.get("title") or ""
        self.text: str = album.get("description") or self.title
        self.rawText: str = self.text
        self.created_at: datetime = from_timestamp(album["createdAt"])  # type: ignore[assignment]
        self.item_count: int = album.get("itemCount", 0)
        self.album_content: list[dict[str, Any]] = content.get("albumContent") or []
        # Each album item is a media offer whose mediaOfferId is an accountMedia id.
        self._attach_media(
            resolve_account_media(
                [item["mediaOfferId"] for item in self.album_content],
                content.get("aggregationData") or {},
            )
        )
