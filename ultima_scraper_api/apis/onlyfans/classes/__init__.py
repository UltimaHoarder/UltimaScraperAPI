# type:ignore
from ultima_scraper_api.apis.onlyfans.classes import (
    auth_model,
    extras,
    media_model,
    message_model,
    only_drm,
    post_model,
    story_model,
    subscription_count_model,
    subscription_model,
    user_model,
)

content_types = (
    story_model.StoryModel | post_model.PostModel | message_model.MessageModel
)
