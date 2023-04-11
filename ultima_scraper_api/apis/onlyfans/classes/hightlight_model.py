from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import create_user


class create_highlight(SiteContent):
    def __init__(self, option: dict[str, Any], user: "create_user") -> None:
        SiteContent.__init__(self, option, user)
        self.id: int = option["id"]
        self.userId: int = option["userId"]
        self.title: str = option["title"]
        self.coverStoryId: int = option["coverStoryId"]
        self.cover: str = option["cover"]
        self.storiesCount: int = option["storiesCount"]
        self.createdAt: str = option["createdAt"]
