from types import SimpleNamespace

import pytest

from tests.enviroment import (
    DARKFANS_USER_ID,
    FANSLY_USER_ID,
    LOYALFANS_USER_ID,
    ONLYFANS_USER_ID,
)
from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.post_model import PostModel
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

UID = LOYALFANS_USER_ID


@pytest.fixture
def authed():
    authed = object.__new__(LoyalFansAuthModel)
    authed.users = {}
    authed.api = SimpleNamespace(CategorizedContent=lambda: SimpleNamespace())
    authed.auth_session = SimpleNamespace()
    authed.get_api = lambda: authed.api
    return authed


def make_user(authed, uid=UID, slug="someone"):
    return UserModel({"user": {"uid": uid, "slug": slug}}, authed)


def test_native_id_to_db_id_is_a_stable_positive_bigint():
    db_id = native_id_to_db_id(UID)
    assert db_id == native_id_to_db_id(UID)
    assert 0 <= db_id < 2**63
    assert db_id != native_id_to_db_id(DARKFANS_USER_ID)


@pytest.mark.parametrize("site_id", [ONLYFANS_USER_ID, FANSLY_USER_ID])
def test_integer_site_ids_fit_bigint_unhashed(site_id):
    # OnlyFans and Fansly keep their own id as the archive key.
    assert isinstance(site_id, int)
    assert 0 < site_id < 2**63


@pytest.mark.parametrize("site_id", [LOYALFANS_USER_ID, DARKFANS_USER_ID])
def test_string_site_ids_hash_to_bigint(site_id):
    assert 0 <= native_id_to_db_id(site_id) < 2**63


def test_native_id_to_db_id_rejects_empty():
    with pytest.raises(ValueError):
        native_id_to_db_id("")


def test_user_keeps_uid_and_uses_hashed_id(authed):
    user = make_user(authed)
    assert user.uid == UID
    assert user.id == native_id_to_db_id(UID)
    assert user.get_link() == f"https://www.loyalfans.com/user/{UID}"
    assert authed.users == {user.id: user}


@pytest.mark.parametrize("identifier", ["id", "uid", "username"])
def test_find_user_accepts_every_identifier(authed, identifier):
    user = make_user(authed)
    assert authed.find_user(getattr(user, identifier)) is user


def test_post_id_is_hashed_uid(authed):
    post = PostModel({"uid": "post-uid-1", "slug": "s"}, make_user(authed))
    assert post.uid == "post-uid-1"
    assert post.id == native_id_to_db_id("post-uid-1")


@pytest.mark.asyncio
async def test_get_user_sends_slug_for_archive_id(authed):
    user = make_user(authed)
    requested: list[str] = []

    async def call(link, body=None):
        requested.append(link)
        return {"data": {"user": {"uid": UID, "slug": "someone"}, "profile": {}}}

    authed.call = call
    assert await authed.get_user(user.id) is user
    assert requested == [
        "https://www.loyalfans.com/api/v2/profile/star/someone?ngsw-bypass=true"
    ]
    # The full profile is now loaded, so the next lookup is served from memory.
    assert await authed.get_user(user.id) is user
    assert len(requested) == 1


@pytest.mark.asyncio
async def test_get_user_returns_none_for_unknown_archive_id(authed):
    async def call(link, body=None):
        raise AssertionError("an archive id cannot be looked up remotely")

    authed.call = call
    assert await authed.get_user(native_id_to_db_id("someone-else")) is None
