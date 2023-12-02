from typing import Any

import ultima_scraper_api.apis.fansly.classes as fansly_classes
import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes
from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
from ultima_scraper_api.apis.fansly.fansly import FanslyAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

SUPPORTED_SITES = ["OnlyFans", "Fansly"]
api_types = OnlyFansAPI | FanslyAPI
authenticator_types = OnlyFansAuthenticator | FanslyAuthenticator
auth_types = onlyfans_classes.auth_model.AuthModel | fansly_classes.auth_model.AuthModel
user_types = (
    onlyfans_classes.user_model.create_user | fansly_classes.user_model.create_user
)
story_types = (
    onlyfans_classes.story_model.create_story | fansly_classes.story_model.create_story
)
post_types = (
    onlyfans_classes.post_model.create_post | fansly_classes.post_model.create_post
)
message_types = (
    onlyfans_classes.message_model.create_message
    | fansly_classes.message_model.create_message
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
