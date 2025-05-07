from typing import TYPE_CHECKING, Any

from ultima_scraper_api.apis.onlyfans import SiteContent
from ultima_scraper_api.apis.onlyfans.classes.stat import MediaStatsModel
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel


class VaultItemModel(SiteContent):
    def __init__(self, option: dict[str, Any], user: UserModel) -> None:
        super().__init__(option, user)
        self.type: str = option["type"]
        self.name: str = option["name"]
        self.has_media: bool = option["hasMedia"]
        self.can_update: bool = option.get("canUpdate", False)
        self.can_delete: bool = option.get("canDelete", False)
        self.videos_count: int = option.get("videosCount", 0)
        self.photos_count: int = option.get("photosCount", 0)
        self.gifs_count: int = option.get("gifsCount", 0)
        self.audios_count: int = option.get("audiosCount", 0)
        self.medias: list[dict[str, Any]] = option.get("media", [])

    async def get_medias(self) -> list[dict[str, Any]]:
        self.medias = await self.author.get_authed().get_vault_media(self.id)
        return self.medias


class VaultListModel:
    def __init__(self, option: dict[str, Any], user: "UserModel"):
        self.list: list[VaultItemModel] = [
            VaultItemModel(item, user) for item in option["list"]
        ]
        self.all: MediaStatsModel = MediaStatsModel(option["all"])
        has_media = bool([x for x in self.all.__dict__.values() if x > 0])
        self.list.append(
            VaultItemModel(
                {"id": 0, "name": "All media", "type": "all", "hasMedia": has_media},
                user,
            )
        )

    def resolve(self, name: str = "All media", has_custom_type: bool = False):
        for item in self.list:
            if item.name == name:
                if has_custom_type and item.type == "custom":
                    return item
                return item
