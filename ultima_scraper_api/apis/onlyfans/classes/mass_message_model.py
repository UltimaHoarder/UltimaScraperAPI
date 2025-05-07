from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class MassMessageStatModel:
    def __init__(self, options: dict[str, Any], user: "UserModel"):
        self.id: int = options["id"]
        self.giphy_id: str | None = options.get("giphyId", None)
        self.text: str = options.get("text", "")
        self.is_free: bool = options["isFree"]
        self.sent_count: int = options.get("sentCount", 0)
        self.viewed_count: int = options.get("viewedCount", 0)
        self.can_unsend: bool = options.get("canUnsend", False)
        self.unsend_seconds: int = options.get("unsendSeconds", 0)
        self.is_canceled: bool = options["isCanceled"]
        self.media_types: dict[str, int] | None = options["mediaTypes"]
        self.price: float = float(options.get("price", 0))
        self.purchased_count: int = options.get("purchasedCount", 0)
        self.release_forms: list[str] = options.get("releaseForms", [])
        self.created_at: datetime = datetime.fromisoformat(options["date"])
        self.expires_at = self.created_at + timedelta(0, self.unsend_seconds)

        self.mass_message: MassMessageModel | None = None
        self.author = user
        self.__raw__ = options

    async def get_mass_message(self):
        link = endpoint_links(self.id).mass_message
        result = await self.author.get_requester().json_request(link)
        self.mass_message = MassMessageModel(result, self.author, self)
        return self.mass_message


class MassMessageModel(SiteContent):
    def __init__(
        self,
        options: dict[str, Any],
        user: "UserModel",
        mass_message_stat: MassMessageStatModel | None = None,
    ) -> None:
        SiteContent.__init__(self, options, user)
        if not user.is_authed_user():
            self.id: int = options["queueId"]
        else:
            assert options["isFromQueue"]
        self.mass_message_stat = mass_message_stat
        self.text: str = options.get("text", "")
        self.raw_text: str = options.get("rawText", "")
        self.price: float = float(options.get("price", 0))
        self.previews: list[int] = options["previews"]
        self.changed_at: str = options["changedAt"]
        self.unsend_seconds: int = options.get("unsendSeconds", 0)
        self.media_count: int = options["mediaCount"]
        self.created_at: datetime = datetime.fromisoformat(options["createdAt"])
        self.expires_at = (
            self.mass_message_stat.expires_at
            if self.mass_message_stat
            else self.created_at + timedelta(0, self.unsend_seconds)
        )
        self.get_author().scrape_manager.scraped.MassMessages[self.id] = self
