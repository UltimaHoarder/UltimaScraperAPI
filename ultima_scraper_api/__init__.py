import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field

import ultima_scraper_api.apis.fansly.classes as fansly_classes
import ultima_scraper_api.apis.loyalfans.classes as loyalfans_classes
import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes
from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
from ultima_scraper_api.apis.loyalfans.authenticator import LoyalFansAuthenticator
from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI
from ultima_scraper_api.config import UltimaScraperAPIConfig

logger = logging.getLogger(__name__)

SUPPORTED_SITES_LITERALS = Literal["OnlyFans", "Fansly", "LoyalFans"]
SUPPORTED_SITES = list(get_args(SUPPORTED_SITES_LITERALS))
ENABLED_SITES_LITERALS = Literal["OnlyFans", "Fansly"]
CONTENT_VALUES = Literal["Free", "Paid", "All"]


def get_enabled_sites() -> list[str]:
    """Return enabled site names from ENABLED_SITES_LITERALS."""
    return [site for site in get_args(ENABLED_SITES_LITERALS)]


api_types = OnlyFansAPI | FanslyAPI | LoyalFansAPI
authenticator_types = (
    OnlyFansAuthenticator | FanslyAuthenticator | LoyalFansAuthenticator
)
auth_types = (
    onlyfans_classes.auth_model.OnlyFansAuthModel
    | fansly_classes.auth_model.FanslyAuthModel
    | loyalfans_classes.auth_model.LoyalFansAuthModel
)
user_types = (
    onlyfans_classes.user_model.UserModel
    | fansly_classes.user_model.UserModel
    | loyalfans_classes.user_model.UserModel
)
story_types = (
    onlyfans_classes.story_model.StoryModel | fansly_classes.story_model.StoryModel
)
post_types = onlyfans_classes.post_model.PostModel | fansly_classes.post_model.PostModel
message_types = (
    onlyfans_classes.message_model.MessageModel
    | fansly_classes.message_model.MessageModel
)
subscription_types = (
    onlyfans_classes.subscription_model.SubscriptionModel
    | fansly_classes.subscription_model.SubscriptionModel
)

content_types = story_types | post_types | message_types
media_types = onlyfans_classes.media_model
error_types = onlyfans_classes.extras.ErrorDetails | fansly_classes.extras.ErrorDetails


class ContentType(str, Enum):
    PROFILE = "Profile"
    STORIES = "Stories"
    HIGHLIGHTS = "Highlights"
    POSTS = "Posts"
    ARCHIVED_POSTS = "ArchivedPosts"
    CHATS = "Chats"
    MESSAGES = "Messages"
    MASS_MESSAGES = "MassMessages"
    SUBSCRIPTIONS = "Subscriptions"

    def media_kinds(self) -> set[str]:
        """Return media kinds present for this content type."""
        mapping: dict[ContentType, set[str]] = {
            ContentType.PROFILE: {MediaType.IMAGES.value},
            ContentType.STORIES: {MediaType.IMAGES.value, MediaType.VIDEOS.value},
            ContentType.HIGHLIGHTS: {MediaType.IMAGES.value, MediaType.VIDEOS.value},
            ContentType.POSTS: {
                MediaType.IMAGES.value,
                MediaType.VIDEOS.value,
                MediaType.AUDIOS.value,
            },
            ContentType.ARCHIVED_POSTS: {
                MediaType.IMAGES.value,
                MediaType.VIDEOS.value,
                MediaType.AUDIOS.value,
            },
            ContentType.CHATS: set(),
            ContentType.MESSAGES: {
                MediaType.IMAGES.value,
                MediaType.VIDEOS.value,
                MediaType.AUDIOS.value,
            },
            ContentType.MASS_MESSAGES: {
                MediaType.IMAGES.value,
                MediaType.VIDEOS.value,
                MediaType.AUDIOS.value,
            },
            ContentType.SUBSCRIPTIONS: set(),
        }
        return mapping.get(self, set())


class MediaType(str, Enum):
    IMAGES = "images"
    VIDEOS = "videos"
    AUDIOS = "audios"
    GIFS = "gifs"

    @classmethod
    def from_api_type(cls, api_type: str) -> "MediaType | None":
        """Map raw API media type (gif/photo/video/stream/audio) to MediaType."""
        mapping = {
            "gif": cls.GIFS,
            "photo": cls.IMAGES,
            "image": cls.IMAGES,
            "video": cls.VIDEOS,
            "stream": cls.VIDEOS,
            "application": cls.VIDEOS,
            "audio": cls.AUDIOS,
        }
        return mapping.get((api_type or "").lower())


class ContentOptions(BaseModel):
    profile: bool = True
    stories: bool = True
    highlights: bool = True
    posts: bool = True
    archived_posts: bool = True
    chats: bool = True
    messages: bool = True
    mass_messages: bool = True
    subscriptions: bool = True


class MediaOptions(BaseModel):
    images: bool = True
    videos: bool = True
    audios: bool = True


class ScrapeOptions(BaseModel):
    content: ContentOptions = Field(default_factory=ContentOptions)
    media: MediaOptions = Field(default_factory=MediaOptions)


def map_api_media_types(types: list[str]) -> set[str]:
    """Convert a list of raw API media type strings to a set of MediaType.value strings."""
    return {m.value for t in types if (m := MediaType.from_api_type(t))}


def select_api(option: str, config: UltimaScraperAPIConfig | None = None) -> api_types:
    """Allows you to select an API

    Args:
        option (str): API name (e.g., onlyfans)
        config (Config, optional): Defaults to Config().

    Returns:
        _type_: returns in instanced API
    """
    config = config or UltimaScraperAPIConfig()
    match option.lower():
        case "onlyfans":
            return OnlyFansAPI(config)
        case "fansly":
            return FanslyAPI(config)
        case "loyalfans":
            return LoyalFansAPI(config)
        case _:
            raise ValueError(f"{option} API is invalid")


def load_classes(name: str | None = None) -> tuple[Any, ...]:
    default_values = auth_types, user_types, post_types, message_types, error_types
    fill_values = [object] * (len(default_values) - 1)
    match name:
        case "auth":
            return (auth_types, *fill_values)
        case "user":
            return (Any, user_types, Any, Any)
        case "post":
            return (Any, Any, post_types, Any)
        case "message":
            return (Any, Any, message_types, Any)
        case "error":
            return (*fill_values, error_types)
        case _:
            return default_values


def get_site_title(site_name: str) -> str:
    match site_name.lower():
        case "onlyfans":
            return "OnlyFans"
        case "fansly":
            return "Fansly"
        case "loyalfans":
            return "LoyalFans"
        case _:
            raise ValueError(f"{site_name} is invalid")


@dataclass
class ApiInstances:
    OnlyFans: OnlyFansAPI
    Fansly: FanslyAPI
    LoyalFans: LoyalFansAPI


class UltimaScraperAPI:
    def __init__(self, config: UltimaScraperAPIConfig | None = None) -> None:
        self.config = config or UltimaScraperAPIConfig()

        # Create centralized WebSocket manager
        from ultima_scraper_api.managers.redis import get_redis, initialize_redis
        from ultima_scraper_api.managers.websocket_manager import WebSocketManager

        initialize_redis(self.config.settings.redis)
        redis_mgr = get_redis()

        self.websocket_manager = WebSocketManager(
            redis_manager=redis_mgr,
            config=self.config,
        )

        # Pass WebSocket manager to all APIs
        self.api_instances = ApiInstances(
            OnlyFans=OnlyFansAPI(self.config, self.websocket_manager),
            Fansly=FanslyAPI(self.config, self.websocket_manager),
            LoyalFans=LoyalFansAPI(self.config, self.websocket_manager),
        )

    async def init(self, ignore_sites: list[str] | None = None) -> None:
        for api in vars(self.api_instances).values():
            api: api_types
            if api.site_name.lower() not in [
                site.lower() for site in (ignore_sites or [])
            ]:
                await api.login(guest=True)
