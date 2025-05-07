from typing import Any, Literal

import ultima_scraper_api.apis.fansly.classes as fansly_classes
import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes
from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

SUPPORTED_SITES = ["OnlyFans", "Fansly"]
SITE_LITERALS = Literal["OnlyFans", "Fansly"]
api_types = OnlyFansAPI | FanslyAPI
authenticator_types = OnlyFansAuthenticator | FanslyAuthenticator
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
