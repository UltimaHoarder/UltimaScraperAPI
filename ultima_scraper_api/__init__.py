import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import ultima_scraper_api.apis.fansly.classes as fansly_classes
import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes
from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
from ultima_scraper_api.apis.loyalfans.authenticator import LoyalFansAuthenticator
from ultima_scraper_api.apis.loyalfans.loyalfans import LoyalFansAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

logger = logging.getLogger(__name__)

SUPPORTED_SITES = ["OnlyFans", "Fansly"]
SITE_LITERALS = Literal["OnlyFans", "Fansly"]
api_types = OnlyFansAPI | FanslyAPI | LoyalFansAPI
authenticator_types = (
    OnlyFansAuthenticator | FanslyAuthenticator | LoyalFansAuthenticator
)
auth_types = (
    onlyfans_classes.auth_model.OnlyFansAuthModel
    | fansly_classes.auth_model.FanslyAuthModel
)
user_types = onlyfans_classes.user_model.UserModel | fansly_classes.user_model.UserModel
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
from ultima_scraper_api.config import UltimaScraperAPIConfig


def select_api(option: str, config: UltimaScraperAPIConfig = UltimaScraperAPIConfig()):
    """Allows you to select an API

    Args:
        option (str): API name (e.g., onlyfans)
        config (Config, optional): Defaults to Config().

    Returns:
        _type_: returns in instanced API
    """
    match option.lower():
        case "onlyfans":
            return OnlyFansAPI(config)
        case "fansly":
            return FanslyAPI(config)
        case "loyalfans":
            return LoyalFansAPI(config)
        case _:
            raise Exception(f"{option} API is invalid")


def load_classes(name: str | None = None):
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


def get_site_title(site_name: str):
    match site_name.lower():
        case "onlyfans":
            return "OnlyFans"
        case "fansly":
            return "Fansly"
        case "loyalfans":
            return "LoyalFans"
        case _:
            raise Exception(f"{site_name} is invalid")


@dataclass
class ApiInstances:
    OnlyFans: OnlyFansAPI
    Fansly: FanslyAPI
    LoyalFans: LoyalFansAPI


class UltimaScraperAPI:
    def __init__(
        self, config: UltimaScraperAPIConfig = UltimaScraperAPIConfig()
    ) -> None:
        self.config = config

        # Create centralized WebSocket manager
        from ultima_scraper_api.managers.redis import get_redis, initialize_redis
        from ultima_scraper_api.managers.websocket_manager import WebSocketManager

        initialize_redis(config.settings.redis)
        redis_mgr = get_redis()

        self.websocket_manager = WebSocketManager(
            redis_manager=redis_mgr,
            config=config,
        )

        # Pass WebSocket manager to all APIs
        self.api_instances = ApiInstances(
            OnlyFans=OnlyFansAPI(config, self.websocket_manager),
            Fansly=FanslyAPI(config, self.websocket_manager),
            LoyalFans=LoyalFansAPI(config, self.websocket_manager),
        )

    async def init(self, ignore_sites: list[str] | None = None) -> None:
        for api in vars(self.api_instances).values():
            api: api_types
            if api.site_name.lower() not in [
                site.lower() for site in (ignore_sites or [])
            ]:
                await api.login(guest=True)
