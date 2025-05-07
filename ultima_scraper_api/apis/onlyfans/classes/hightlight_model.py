from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class HighlightModel(SiteContent):
    def __init__(self, options: dict[str, Any], user: "UserModel") -> None:
        SiteContent.__init__(self, options, user)
        self.id: int = options["id"]
        self.userId: int = options["userId"]
        self.title: str = options["title"]
        self.coverStoryId: int = options["coverStoryId"]
        self.cover: str = options["cover"]
        self.storiesCount: int = options["storiesCount"]
        self.createdAt: str = options["createdAt"]
        user.scrape_manager.scraped.Highlights[self.id] = self
