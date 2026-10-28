from types import SimpleNamespace

import pytest

from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.post_model import PostModel
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

UID = "Gre3PwNWFFC7X4-2BBYcqlJzoBCMF8lxM7bfh0DMqRkhg"


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
    assert db_id != native_id_to_db_id("5e7cc513-0000-0000-009e-9e69d856010e")


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
    post = object.__new__(PostModel)
    option = {"uid": "post-uid-1", "slug": "s", "short_url": "u", "reactions": {}}
    with pytest.raises(KeyError):
        # Only the id handling matters here; the rest of the payload is absent.
        PostModel.__init__(post, option, make_user(authed))
    assert post.uid == "post-uid-1"
    assert post.id == native_id_to_db_id("post-uid-1")


@pytest.mark.asyncio
async def test_get_user_sends_slug_for_archive_id(authed):
    user = make_user(authed)
    requested: list[str] = []

    async def json_request(link):
        requested.append(link)
        return {"data": {"user": {"uid": UID, "slug": "someone"}}}

    authed.auth_session = SimpleNamespace(json_request=json_request)
    await authed.get_user(user.id)
    assert requested == [
        "https://www.loyalfans.com/api/v2/profile/star/someone?ngsw-bypass=true"
    ]


@pytest.mark.asyncio
async def test_get_user_refuses_unknown_archive_id(authed):
    with pytest.raises(ValueError, match="look it up by username"):
        await authed.get_user(native_id_to_db_id(UID))
