"""DarkFans models, paging and auth, against made-up data (no network)."""

import asyncio
from contextlib import aclosing
from types import SimpleNamespace
from typing import Any

import pytest

import ultima_scraper_api.managers.redis as redis_module
from ultima_scraper_api.apis import site_contract as contract
from ultima_scraper_api.apis.darkfans import parse_time
from ultima_scraper_api.apis.darkfans.authenticator import DarkFansAuthenticator
from ultima_scraper_api.apis.darkfans.classes.auth_model import DarkFansAuthModel
from ultima_scraper_api.apis.darkfans.classes.extras import AuthDetails
from ultima_scraper_api.apis.darkfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.darkfans.classes.post_model import PostModel
from ultima_scraper_api.apis.darkfans.classes.user_model import UserModel
from ultima_scraper_api.apis.darkfans.darkfans import extract_auth_details_from_curl
from ultima_scraper_api.apis.darkfans.urls import APIRoutes
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

ME = "5e7cc513-0000-0000-0000-00000000aaaa"
CREATOR = "5e7cc513-0000-0000-0000-00000000bbbb"
FASTEVO = "https://abc.c.mp2.fastevo.net"


@pytest.fixture(autouse=True)
def quiet_events(monkeypatch):
    async def publish(_event):
        return None

    monkeypatch.setattr(redis_module, "publish_custom_event", publish)


def make_authed(handler=None):
    """An auth model whose ``call`` answers from ``handler(link, body)``."""
    authed: Any = object.__new__(DarkFansAuthModel)
    authed.users = {}
    authed.api = SimpleNamespace(CategorizedContent=lambda: SimpleNamespace())
    authed.auth_session = SimpleNamespace()
    authed.get_api = lambda: authed.api  # type: ignore[assignment]
    authed.calls = []
    authed.chats = None
    authed.chat_ids = {}

    async def call(link, body=None):
        authed.calls.append((link, body))
        return handler(link, body) if handler else {}

    authed.call = call  # type: ignore[assignment]
    authed.user = UserModel({"id": ME, "username": "me"}, authed)
    authed.id = authed.user.id
    return authed


def creator(authed):
    return UserModel({"type": "user", "attributes": {"id": CREATOR, "username": "creator", "creator": True}}, authed)


def image_file(file_id):
    return {
        "fileId": file_id,
        "provider": "aws-s3",
        "providerId": f"https://cdn.test/{file_id}.jpg?Expires=1&Signature=x",
        "type": "image",
        "duration": 0,
        "thumbnail": f"https://cdn.test/{file_id}_thumb.jpg",
    }


def drm_video(file_id, raw_id="65f0c0ffee00000000000001"):
    return {
        "fileId": file_id,
        "provider": "fastevo-drm",
        "providerId": "v4.local.token",
        "type": "video",
        "duration": 60,
        "thumbnail": f"{FASTEVO}/{raw_id}/processed/video/content/snapshots/snapshot3.webp?X-Signature=s",
        "teaser": f"{FASTEVO}/clear/v1/{raw_id}/video/gen-1/s/1/sig/",
        "rawProviderId": raw_id,
    }


def post(post_id, *, files=(), post_type="free", price=None, created=1794950663):
    return {
        "id": post_id,
        "userId": CREATOR,
        "text": "hello",
        "type": post_type,
        "price": price,
        "files": list(files),
        "fileInfo": [{"type": f["type"]} for f in files] or ([{"type": "video"}] if post_type != "free" else []),
        "purchasedByUser": False,
        "nbComments": 0,
        "createdAt": created,
    }


def page(items, number, total_pages):
    return {"data": items, "meta": {"pagination": {"page": number, "totalPages": total_pages}}}


def test_post_media_by_provider():
    authed = make_authed()
    user = creator(authed)
    free = PostModel(post("p1", files=[image_file("f-img"), drm_video("f-vid")]), user)
    photo, video = free.media
    assert photo.id == native_id_to_db_id("f-img") and photo.type == "photo"
    assert free.url_picker(photo).path == "/f-img.jpg"  # type: ignore[union-attr]
    # A DRM video is viewable but has no direct link: the backend gets its manifest.
    assert video.canView and free.url_picker(video) is None
    # The token that plays it is stored as the manifest's signature.
    assert video["drm"]["manifest"]["dash"] == {
        "manifest_url": f"{FASTEVO}/65f0c0ffee00000000000001/processed/video/content/media/master.mpd",
        "signature": "v4.local.token",
    }
    assert video.duration == 60.0 and free.preview_url_picker(video) is not None
    assert free.is_bought() and free.created_at == parse_time(1794950663)
    assert contract.content_problems(free) == []

    locked = PostModel(post("p2", post_type="ppv", price={"amount": 1500, "currency": "USD"}), user)
    assert locked.media == [] and locked.price == 15.0 and not locked.is_bought()


def test_message_packs_list_free_and_locked_files():
    authed = make_authed()
    user = creator(authed)
    raw = {
        "uuid": "m-1",
        "metadata": {
            "userid": CREATOR,
            "attachment": {
                "chatPack": {
                    "type": "chatPack",
                    "attributes": {
                        "price": {"amount": 1500, "currency": "USD"},
                        "purchased": False,
                        "freeFiles": [{**image_file("free-1"), "provider": "loverfans-cdn"}],
                        "paidFiles": [],
                        "thumbnails": [{"fileId": "paid-1", "type": "video", "blurredThumbnail": "https://cdn.test/b.jpg"}],
                        "fileInfo": [
                            {"id": "free-1", "type": "image", "free": True},
                            {"id": "paid-1", "type": "video", "duration": 431, "free": False},
                        ],
                    },
                }
            },
        },
        "text": {"text": "What&apos;s up"},
        "timestamp": 1780633500000,
        "read_status": "read",
    }
    message = MessageModel(raw, user)
    assert message.author is user and message.get_receiver() is authed.user
    assert message.text == "What's up" and message.created_at == parse_time(1780633500)
    assert [(m["media_uid"], m.canView) for m in message.media] == [("free-1", True), ("paid-1", False)]
    assert message.price == 15.0 and not message.is_bought()
    assert contract.content_problems(message) == []
    mine = MessageModel({**raw, "uuid": "m-2", "metadata": {"userid": ME}}, user)
    assert mine.author is authed.user and mine.media == [] and mine.is_bought()


@pytest.mark.asyncio
async def test_iter_posts_pages_to_total_pages():
    pages = {
        1: page([{"type": "post", "attributes": post("a")}, {"attributes": post("b")}], 1, 2),
        2: page([{"attributes": post("c")}, {"attributes": post("a")}], 2, 2),
    }

    def handler(link, body):
        return pages[int(link.split("page=")[1].split("&")[0])]

    user = creator(make_authed(handler))
    async with aclosing(user.iter_posts()) as values:
        assert [p.uid async for p in values] == ["a", "b", "c"]
    async with aclosing(user.iter_posts(limit=1)) as values:
        assert [p.uid async for p in values] == ["a"]
    async with aclosing(user.iter_posts(label="archived")) as values:
        assert [p async for p in values] == []


@pytest.mark.asyncio
async def test_iter_messages_finds_the_chat_and_stops_on_a_short_page():
    member = {"type": "user", "attributes": {"id": CREATOR, "username": "creator"}}
    chat = {"attributes": {"id": "chat-1", "users": [{"attributes": {"id": ME}}, member], "nbUnreadMessages": 0}}
    full = [{"uuid": f"m{n}", "metadata": {"userid": CREATOR}, "timestamp": n} for n in range(50)]

    def handler(link, body):
        if "/messages?" in link:
            return {"data": full if "page=1&" in link else full[:3]}
        if "archived=false" in link:
            return page([chat], 1, 1)
        return page([], 1, 0)

    authed = make_authed(handler)
    user = creator(authed)
    async with aclosing(user.iter_messages()) as values:
        messages = [m async for m in values]
    # Page 2 repeats three uuids from page 1 here; each message is yielded once.
    assert len(messages) == 50 and authed.chat_ids == {CREATOR: "chat-1"}
    assert sum("/messages?" in link for link, _ in authed.calls) == 2
    async with aclosing(authed.user.iter_messages()) as values:
        assert [m async for m in values] == []


@pytest.mark.asyncio
async def test_stories_split_live_and_pinned():
    def story(story_id, pinned):
        return {"attributes": {"id": story_id, "pinned": pinned, "createdAt": 1794920159, "file": drm_video(f"f-{story_id}")}}

    def handler(link, body):
        return page([story("s1", False), story("s2", True), story("s3", False)], 1, 1)

    user = creator(make_authed(handler))
    async with aclosing(user.iter_stories()) as values:
        live = [s async for s in values]
    async with aclosing(user.iter_highlight_stories()) as values:
        pinned = [s async for s in values]
    assert [s.uid for s in live] == ["s1", "s3"] and [s.uid for s in pinned] == ["s2"]
    assert all(contract.content_problems(s) == [] for s in live + pinned)


@pytest.mark.asyncio
async def test_subscriptions_merge_paid_and_followed():
    def handler(link, body):
        if "/subscriptions?" in link:
            rows = [
                {"attributes": {"creatorId": CREATOR, "creatorUsername": "creator", "status": "expired", "subscribedPrice": 2250}},
            ]
            return page(rows, 1, 1)
        followees = [
            {"attributes": {"user": {"attributes": {"id": CREATOR, "username": "creator"}}}},
            {"attributes": {"user": {"attributes": {"id": "free-uuid", "username": "free"}}}},
        ]
        return page(followees, 1, 1)

    authed = make_authed(handler)
    authed.guest = False
    authed.subscriptions = []
    subscriptions = await authed.get_subscriptions()
    assert [(s.user.username, s.kind, s.is_active()) for s in subscriptions] == [
        ("creator", "subscribed", False),
        ("free", "following", True),
    ]
    assert subscriptions[0].get_price() == 22.5
    assert [s.user.username for s in await authed.get_subscriptions(sub_type="expired")] == ["creator"]


@pytest.mark.asyncio
async def test_call_renews_an_expired_jwt_once(monkeypatch):
    import ultima_scraper_api.apis.darkfans.classes.auth_model as auth_module

    answers = [(401, {"code": 401, "message": "Expired JWT Token"}, {}), (200, {"data": []}, {})]

    async def call_api(requester, link, body=None):
        return answers.pop(0)

    monkeypatch.setattr(auth_module, "call_api", call_api)
    authed: Any = object.__new__(DarkFansAuthModel)
    authed.auth_session = SimpleNamespace()
    renewed = []

    async def refresh_token(error=None):
        renewed.append(True)
        return True

    authed.authenticator = SimpleNamespace(refresh_token=refresh_token)
    assert await authed.call(f"{APIRoutes().me()}") == {"data": []}
    assert renewed == [True]
    answers[:] = [(404, {"title": "An error occurred", "status": 404, "detail": "Not Found"}, {})]
    assert await authed.call(APIRoutes().me()) == {"error": {"code": 404, "message": "Not Found"}}


@pytest.mark.asyncio
async def test_refresh_stores_the_new_tokens_once(monkeypatch):
    import ultima_scraper_api.apis.darkfans.authenticator as auth_module

    sent = []

    async def call_api(requester, link, body=None):
        sent.append((link, body))
        await asyncio.sleep(0)
        return 200, {}, {"BEARER": "new-jwt", "refresh_token": "new-refresh"}

    monkeypatch.setattr(auth_module, "call_api", call_api)
    authenticator: Any = object.__new__(DarkFansAuthenticator)
    authenticator.auth_details = AuthDetails(authorization="old-jwt", refresh_token="old-refresh")
    authenticator.auth_session = SimpleNamespace()
    authenticator._refresh_lock = asyncio.Lock()
    # Two calls that both saw the expired JWT spend the refresh token once.
    assert await asyncio.gather(authenticator.refresh_token(), authenticator.refresh_token()) == [True, True]
    assert sent == [(APIRoutes().refresh_token(), {"refresh_token": "old-refresh"})]
    assert authenticator.auth_details.token == "new-jwt"
    assert authenticator.auth_details.refresh_token == "new-refresh"
    authenticator.auth_details.refresh_token = ""
    assert await authenticator.refresh_token() is False


def test_request_headers_send_the_jwt_as_a_cookie():
    authenticator: Any = object.__new__(DarkFansAuthenticator)
    authenticator.auth_session = SimpleNamespace(headers={})
    authenticator.auth_details = AuthDetails(authorization="jwt", refresh_token="rt", user_agent="UA")
    authenticator.guest = False
    headers = authenticator.create_request_headers(APIRoutes().me(), extra_headers={"accept": "*/*"})
    assert headers["cookie"] == "BEARER=jwt" and headers["x-community-name"] == "darkfans"
    assert headers["accept"] == "application/json" and headers["user-agent"] == "UA"
    assert "authorization" not in headers
    refresh = authenticator.create_request_headers(APIRoutes().refresh_token())
    assert refresh["cookie"] == "BEARER=jwt; refresh_token=rt"
    assert "cookie" not in authenticator.create_request_headers("https://cdn.test/x.jpg")


def test_curl_import_reads_the_cookies():
    curl = (
        "curl 'https://darkfans.com/api/v1/user/info' "
        "-H 'user-agent: Mozilla/5.0 Test' "
        "-b 'OS-USER=x; BEARER=jwt.value; refresh_token=rt-value'"
    )
    details = extract_auth_details_from_curl(curl)
    assert (details.token, details.refresh_token, details.user_agent) == ("jwt.value", "rt-value", "Mozilla/5.0 Test")
    with pytest.raises(ValueError):
        extract_auth_details_from_curl("curl 'https://darkfans.com/' -b 'OS-USER=x'")


def test_sign_in_round_trips_through_one_cookie_string():
    # The backend stores a DarkFans sign-in as one cookie string.
    details = AuthDetails(cookie="BEARER=jwt.value; refresh_token=rt-value", user_agent="UA")
    assert (details.token, details.refresh_token) == ("jwt.value", "rt-value")
    assert details.cookie == "BEARER=jwt.value; refresh_token=rt-value"
    assert AuthDetails(**details.export()).cookie == details.cookie
    # Values given on their own win over the cookie string's.
    assert AuthDetails(authorization="newer", cookie="BEARER=old").token == "newer"
    assert extract_auth_details_from_curl(
        "curl 'https://darkfans.com/api/v1/user/info' -b 'BEARER=a; refresh_token=b'"
    ).cookie == "BEARER=a; refresh_token=b"


@pytest.mark.asyncio
async def test_a_cookie_string_sign_in_opens_a_session():
    """The stored cookie string is not a cookie jar: opening the HTTP session
    for it once failed in aiohttp ("not enough values to unpack")."""
    from ultima_scraper_api.apis.darkfans.darkfans import DarkFansAPI

    details = AuthDetails(cookie="BEARER=jwt.value; refresh_token=rt-value", user_agent="UA")
    authenticator = DarkFansAuthenticator(DarkFansAPI(), details)
    try:
        assert len(authenticator.auth_session.active_session.cookie_jar) == 0
        headers = authenticator.create_request_headers("https://darkfans.com/api/v1/user/info")
        assert headers["cookie"] == "BEARER=jwt.value"
    finally:
        await authenticator.close()
