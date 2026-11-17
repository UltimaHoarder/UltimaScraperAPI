"""Every site against what the backend reads (ultima_scraper_api.apis.site_contract).

The capability tables below are a scoreboard: when a site gains a method,
its expected set here must be updated, so progress (and regressions) show up
in review.
"""

from types import SimpleNamespace

import pytest

from ultima_scraper_api import SITE_APIS, SUPPORTED_SITES, get_site_title, select_api
from ultima_scraper_api.apis import site_contract as contract
from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
from ultima_scraper_api.apis.fansly.classes.message_model import (
    MessageModel as FanslyMessage,
)
from ultima_scraper_api.apis.fansly.classes.post_model import PostModel as FanslyPost
from ultima_scraper_api.apis.fansly.classes.user_model import UserModel as FanslyUser
from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.user_model import (
    UserModel as LoyalFansUser,
)
from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel
from ultima_scraper_api.apis.onlyfans.classes.user_model import (
    UserModel as OnlyFansUser,
)
from ultima_scraper_api.config import Sites

SITES = {
    "OnlyFans": (OnlyFansAuthModel, OnlyFansUser),
    "Fansly": (FanslyAuthModel, FanslyUser),
    "LoyalFans": (LoyalFansAuthModel, LoyalFansUser),
}

EXPECTED_AUTH = {
    "OnlyFans": {
        "me": "get_me",
        "user_lookup": "get_user",
        "subscriptions": "get_subscriptions",
        "paid_content": "iter_paid_content",
        "chats": "iter_chats",
        "transactions": "get_transactions",
        "lists": "get_lists",
    },
    "Fansly": {
        "me": "get_me",
        "user_lookup": "get_user",
        "subscriptions": "get_subscriptions",
        "paid_content": "get_paid_content",
        "chats": "get_chats",
        "transactions": "get_transactions",
        "lists": "get_lists",
    },
    "LoyalFans": {"user_lookup": "get_user", "subscriptions": "get_subscriptions"},
}
EXPECTED_USER = {
    "OnlyFans": {
        "posts": "iter_posts",
        "messages": "iter_messages",
        "stories": "iter_stories",
        "highlights": "iter_highlight_stories",
        "post_by_id": "get_post",
        "message_by_id": "get_message_by_id",
        "socials": "get_socials",
    },
    "Fansly": {
        "posts": "get_posts",
        "messages": "get_messages",
        "stories": "get_stories",
        "post_by_id": "get_post",
        "message_by_id": "get_message_by_id",
    },
    "LoyalFans": {"posts": "get_posts", "messages": "get_messages"},
}


@pytest.mark.parametrize("site", SITES)
def test_capability_scoreboard(site):
    auth_class, user_class = SITES[site]
    assert contract.capabilities(auth_class, contract.AUTH_CAPABILITIES) == EXPECTED_AUTH[site]
    assert contract.capabilities(user_class, contract.USER_CAPABILITIES) == EXPECTED_USER[site]


@pytest.mark.parametrize("site", SITES)
def test_methods_accept_the_backends_arguments(site):
    auth_class, user_class = SITES[site]
    assert contract.signature_problems(auth_class) == []
    assert contract.signature_problems(user_class) == []


def test_required_capabilities():
    assert contract.missing_required(OnlyFansAuthModel, auth=True) == []
    assert contract.missing_required(FanslyAuthModel, auth=True) == []
    # Phase 3 adds LoyalFans' get_me.
    assert contract.missing_required(LoyalFansAuthModel, auth=True) == ["me"]


def test_signature_problems_spot_a_list_returning_iterator():
    class Site:
        async def iter_posts(self, limit=None):
            return []

    assert contract.signature_problems(Site) == [
        "iter_posts is not an async generator",
        "iter_posts does not accept on_progress=",
        "iter_posts does not accept job_id=",
    ]


# --- content, read the way the backend serializer reads it -------------------


def fansly_user(user_id=10):
    settings = SimpleNamespace(media_quality=SimpleNamespace(video="source"))
    user = object.__new__(FanslyUser)
    user.id = user_id
    user.get_api = lambda: SimpleNamespace(get_site_settings=lambda: settings)
    user.get_authed = lambda: SimpleNamespace(id=1, user=SimpleNamespace(id=1))  # type: ignore[assignment]
    return user


AGGREGATION = {
    "accountMedia": [
        {
            "id": "500",
            "media": {
                "id": "501",
                "type": 2,
                "mimetype": "video/mp4",
                "height": 720,
                "locations": [{"location": "https://cdn.test/501.mp4"}],
                "variants": [],
            },
        }
    ]
}
ATTACHMENTS = [{"contentType": 1, "contentId": "500", "pos": 0}]


def test_fansly_post_is_storable():
    post = FanslyPost(
        {"id": "7", "content": "hi", "createdAt": 1700000000, "attachments": ATTACHMENTS},
        fansly_user(),
        AGGREGATION,
    )
    assert contract.content_problems(post) == []
    parsed = post.url_picker(post.media[0])
    assert parsed is not None and parsed.geturl() == "https://cdn.test/501.mp4"


def test_fansly_message_is_storable():
    message = FanslyMessage(
        {
            "id": "8",
            "senderId": "10",
            "groupId": "3",
            "content": "",
            "createdAt": 1700000000,
            "attachments": ATTACHMENTS,
        },
        fansly_user(),
        AGGREGATION,
    )
    assert contract.content_problems(message) == []


def test_content_problems_name_what_the_backend_would_lose():
    item = SimpleNamespace(id=None, media=[{"url": "x"}])
    assert contract.content_problems(item) == [
        "no id",
        "no created_at",
        "no text",
        "no get_author()",
        "media but no url_picker()",
        "media[0] has no id",
        "media[0] has no type",
    ]


# --- site registry -------------------------------------------------------------


def test_registry_covers_the_supported_sites():
    assert sorted(title for title, _ in SITE_APIS.values()) == sorted(SUPPORTED_SITES)
    for key, (title, api_class) in SITE_APIS.items():
        assert get_site_title(key.upper()) == title
        assert isinstance(select_api(title), api_class)
    with pytest.raises(ValueError):
        select_api("nope")
    with pytest.raises(ValueError):
        get_site_title("nope")


def test_site_settings_are_looked_up_by_name():
    sites = Sites()
    assert sites.get_settings("Fansly") is sites.fansly
    assert sites.get_settings("LoyalFans") is sites.loyalfans
    with pytest.raises(ValueError):
        sites.get_settings("Nope")
