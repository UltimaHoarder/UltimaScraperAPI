from datetime import datetime

import pytest

from ultima_scraper_api.apis.fansly import (
    from_timestamp,
    resolve_account_media,
    resolve_attachments,
)
from ultima_scraper_api.apis.fansly.classes.extras import ErrorDetails
from ultima_scraper_api.apis.fansly.signing import client_check, cyrb53, signed_headers
from ultima_scraper_api.apis.fansly.urls import APIRoutes


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Values from the web client's own cyrb53 (main.js), run under node.
        ("", "bdcb81aee8d83"),
        ("a", "1c2ba782c97901"),
        ("necvac-govry3-tybkYz_/api/v1/account/me_123456789012345678", "9dbf9388af010"),
    ],
)
def test_cyrb53_matches_web_client(text, expected):
    assert format(cyrb53(text), "x") == expected


def test_client_check_hashes_path_only():
    device = "123456789012345678"
    with_query = client_check("https://apiv3.fansly.com/api/v1/account/me?x=1", device)
    assert with_query == client_check("https://apiv3.fansly.com/api/v1/account/me", device)
    assert with_query == "9dbf9388af010"


def test_signed_headers_need_a_device_id():
    assert signed_headers("https://apiv3.fansly.com/api/v1/account/me", "") == {}
    headers = signed_headers("https://apiv3.fansly.com/api/v1/account/me", "1", now_ms=5)
    assert headers["fansly-client-id"] == "1"
    assert headers["fansly-client-ts"] == "5"
    assert headers["fansly-client-check"] == client_check(
        "https://apiv3.fansly.com/api/v1/account/me", "1"
    )


def media(media_id, mimetype="image/jpeg", url=True, variants=()):
    return {
        "id": media_id,
        "type": 1,
        "mimetype": mimetype,
        "height": 720,
        "locations": [{"location": f"https://cdn3.fansly.com/{media_id}"}] if url else [],
        "variants": list(variants),
    }


def account_media(am_id, full, preview=None):
    return {"id": am_id, "media": full, "preview": preview, "access": bool(full["locations"])}


def test_attachments_resolve_singles_and_ordered_bundles():
    aggregation = {
        "accountMedia": [
            account_media("am1", media("m1")),
            account_media("am2", media("m2")),
            account_media("am3", media("m3")),
        ],
        "accountMediaBundles": [
            {
                "id": "b1",
                "accountMediaIds": ["am3", "am2"],
                "bundleContent": [
                    {"accountMediaId": "am2", "pos": 0},
                    {"accountMediaId": "am3", "pos": 1},
                ],
            }
        ],
    }
    attachments = [
        {"contentType": 2, "contentId": "b1", "pos": 1},
        {"contentType": 1, "contentId": "am1", "pos": 0},
        {"contentType": 7100, "contentId": "tipgoal", "pos": 2},
    ]
    resolved = resolve_attachments(attachments, aggregation)
    assert [m["id"] for m in resolved.media] == ["m1", "m2", "m3"]
    assert resolved.previews == []


def test_locked_media_falls_back_to_preview():
    locked_video = media("10", "video/mp4", url=False, variants=[media("11")])
    aggregation = {
        "accountMedia": [
            account_media("am1", locked_video, preview=media("20")),
            # A JPEG thumbnail variant does not make a locked video downloadable.
            account_media("am2", media("30", "video/mp4", url=False, variants=[media("31")])),
        ]
    }
    resolved = resolve_account_media(["am1", "am2", "missing"], aggregation)
    assert [m["id"] for m in resolved.media] == ["20"]
    assert resolved.previews == [20]


def test_from_timestamp_accepts_seconds_and_milliseconds():
    assert from_timestamp(1794832460) == datetime.fromtimestamp(1794832460)
    assert from_timestamp(1794879779000) == datetime.fromtimestamp(1794879779)
    assert from_timestamp(None) is None


def test_routes_match_the_web_client():
    routes = APIRoutes()
    assert routes.stories(42).endswith("/mediastoriesnew?accountId=42")
    assert routes.users([1, "2"]).endswith("/account?ids=1,2")
    assert routes.users(["name", 3]).endswith("/account?usernames=name,3")
    assert routes.timeline(42, before=7).endswith(
        "/timelinenew/42?before=7&after=0&wallId=&contentSearch="
    )
    assert routes.list_messages(9).endswith("/message?groupId=9&limit=25")
    assert routes.list_messages(9, before=5, limit=1).endswith(
        "/message?groupId=9&before=5&limit=1"
    )
    assert routes.list_chats(25, 50, "a b").endswith("&search=a%20b&limit=25&offset=50")


def test_error_details_read_fansly_details():
    error = ErrorDetails({"success": False, "error": {"code": 99, "details": "missing"}})
    assert (error.code, error.message) == (99, "missing")
    error = ErrorDetails({"error": {"code": 429, "message": "Too Many Requests"}})
    assert (error.code, error.message) == (429, "Too Many Requests")


@pytest.mark.asyncio
async def test_sign_in_without_a_known_account_id():
    """A curl import signs in before it knows the account, so sends no id."""
    from ultima_scraper_api.apis.fansly.fansly import FanslyAPI

    seen: list[object] = []

    class Authenticator:
        def __init__(self, api, auth_details, guest=False):
            seen.append(auth_details.id)

        async def login(self, guest=False):
            return None

        async def close(self):
            pass

        def is_authed(self):
            return False

        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            pass

    api = FanslyAPI()
    api.authenticator = Authenticator  # type: ignore[assignment]
    assert await api.login({"authorization": "token"}) is None
    async with api.login_context({"authorization": "token"}) as authed:
        assert authed is None
    assert seen == [None, None]


@pytest.mark.asyncio
async def test_a_deleted_subscription_is_named_by_its_id():
    """Fansly stops resolving a deleted account. It is named u<id>, as
    OnlyFans names its deleted accounts, so its real name stays an alias and
    two deleted accounts never share one username."""
    from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
    from ultima_scraper_api.apis.fansly.classes.auth_model import FanslyAuthModel
    from ultima_scraper_api.apis.fansly.fansly import FanslyAPI

    me = {"id": "100", "username": "me"}
    live = {"id": "200", "username": "alive", "displayName": "Alive"}
    subscription = {"status": 3, "price": 0, "createdAt": 1, "subscriptionTierId": "5"}

    class Requester:
        async def json_request(self, link, *args, **kwargs):
            if "/subscriptions" in link:
                return {
                    "success": True,
                    "response": {
                        "subscriptions": [
                            {**subscription, "id": "1", "accountId": "200", "endsAt": 9},
                            {**subscription, "id": "2", "accountId": "300", "endsAt": 8},
                            {**subscription, "id": "3", "accountId": "400", "endsAt": 7},
                        ]
                    },
                }
            raise AssertionError(link)

    api = FanslyAPI()
    authenticator = FanslyAuthenticator(api)
    authenticator.__raw__ = {"response": {"account": me}}
    try:
        authed = FanslyAuthModel(authenticator)
        authed.get_requester = lambda: Requester()  # type: ignore[method-assign]

        async def get_users(ids):
            from ultima_scraper_api.apis.fansly.classes.user_model import UserModel

            return [UserModel(live, authed)] if "200" in ids else []

        authed.get_users = get_users  # type: ignore[method-assign]
        subscriptions = await authed.get_subscriptions()
    finally:
        await authenticator.close()
    users = {s.user.id: s.user for s in subscriptions}
    assert users[200].username == "alive" and not users[200].is_deleted
    assert users[300].username == "u300" and users[300].is_deleted
    assert users[400].username == "u400" and not users[400].active
