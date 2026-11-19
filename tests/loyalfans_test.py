"""LoyalFans models, paging and auth, against made-up data (no network)."""

from contextlib import aclosing
from types import SimpleNamespace
from typing import Any

import pytest

import ultima_scraper_api.managers.redis as redis_module
from ultima_scraper_api.apis import site_contract as contract
from ultima_scraper_api.apis.loyalfans import parse_time
from ultima_scraper_api.apis.loyalfans.authenticator import LoyalFansAuthenticator
from ultima_scraper_api.apis.loyalfans.classes.auth_model import LoyalFansAuthModel
from ultima_scraper_api.apis.loyalfans.classes.extras import AuthDetails
from ultima_scraper_api.apis.loyalfans.classes.message_model import MessageModel
from ultima_scraper_api.apis.loyalfans.classes.post_model import PostModel
from ultima_scraper_api.apis.loyalfans.classes.story_model import HighlightModel
from ultima_scraper_api.apis.loyalfans.classes.user_model import UserModel
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

ME, CREATOR = "me-uid", "creator-uid"


@pytest.fixture(autouse=True)
def quiet_events(monkeypatch):
    async def publish(_event):
        return None

    monkeypatch.setattr(redis_module, "publish_custom_event", publish)


def when(date: str) -> dict:
    return {"date": date, "timezone_type": 3, "timezone": "UTC"}


def make_authed(handler=None):
    """An auth model whose ``call`` answers from ``handler(link, body)``."""
    authed: Any = object.__new__(LoyalFansAuthModel)
    authed.users = {}
    authed.api = SimpleNamespace(CategorizedContent=lambda: SimpleNamespace())
    authed.auth_session = SimpleNamespace()
    authed.get_api = lambda: authed.api  # type: ignore[assignment]
    authed.calls = []

    async def call(link, body=None):
        authed.calls.append((link, body))
        return handler(link, body) if handler else {}

    authed.call = call  # type: ignore[assignment]
    authed.user = UserModel({"user": {"uid": ME, "slug": "me"}}, authed)
    authed.id = authed.user.id
    return authed


def creator(authed):
    return UserModel({"user": {"uid": CREATOR, "slug": "creator", "user_type": "model"}}, authed)


def video_post(uid, *, viewable=False, date="2026-11-01 10:00:00"):
    video = {"uid": f"v-{uid}", "duration": 30, "poster": f"https://cdn.test/{uid}.jpg"}
    if viewable:
        video["video_url"] = f"https://www.loyalfans.com/endsun/videos/{uid}.mp4"
    return {
        "uid": uid,
        "slug": f"slug-{uid}",
        "content": "hello",
        "created_at": when(date),
        "video": True,
        "video_object": video,
        "price": 5,
        "is_bought": False,
        "can_see": viewable,
        "comments": {"total": 0, "disabled": False},
    }


def photo_post(uid, photos):
    return {
        "uid": uid,
        "slug": f"slug-{uid}",
        "created_at": when("2026-10-01 10:00:00"),
        "photo": True,
        "photos": {"total": len(photos), "photos": photos} if photos else {"total": 3},
        "price": 0,
        "can_see": bool(photos),
    }


def test_post_media_follow_what_the_api_reveals():
    authed = make_authed()
    user = creator(authed)
    locked = PostModel(video_post("p1"), user)
    assert [(m.type, m.canView) for m in locked.media] == [("video", False)]
    assert locked.media[0].id == native_id_to_db_id("v-p1") and locked.media[0].duration == 30.0
    assert locked.url_picker(locked.media[0]) is None
    assert locked.preview_url_picker(locked.media[0]).geturl() == "https://cdn.test/p1.jpg"  # type: ignore[union-attr]
    assert locked.is_bought() is False and locked.price == 5.0

    free = PostModel(video_post("p2", viewable=True), user)
    assert free.url_picker(free.media[0]).path == "/endsun/videos/p2.mp4"  # type: ignore[union-attr]
    assert free.is_bought() is True

    photo = {"uid": "ph-1", "created_at": when("2026-09-01 00:00:00"), "images": {"original": "https://x.test/o.jpg"}}
    shown = PostModel(photo_post("p3", [photo]), user)
    assert [(m.type, m["media_uid"], m.canView) for m in shown.media] == [("photo", "ph-1", True)]
    assert shown.media[0].created_at == parse_time(when("2026-09-01 00:00:00"))
    # Locked photo posts give only a count: nothing identifies their photos.
    assert PostModel(photo_post("p4", []), user).media == []
    for post in (locked, free, shown):
        assert contract.content_problems(post) == []


def test_message_media_are_keyed_by_message_and_index():
    authed = make_authed()
    user = creator(authed)
    raw = {
        "uid": "m-1",
        "own": False,
        "message": "hi",
        "created_at": {**when("2026-01-07 20:13:29"), "timestamp": "1767816809727"},
        "is_locked": True,
        "price": 34.44,
        "media": [
            {"media_type": "video", "index": 0, "is_locked": True, "duration": 908.6, "video_cover": "https://c.test/0.jpg"},
            {"media_type": "image", "index": 1, "is_locked": True},
        ],
    }
    message = MessageModel(raw, user)
    assert message.author is user and message.get_receiver() is authed.user
    assert [m["media_uid"] for m in message.media] == ["m-1:0", "m-1:1"]
    assert [m.type for m in message.media] == ["video", "photo"]
    assert not any(m.canView for m in message.media) and message.is_bought() is False
    assert contract.content_problems(message) == []
    mine = MessageModel({**raw, "uid": "m-2", "own": True, "is_locked": False, "media": []}, user)
    assert mine.author is authed.user and mine.is_bought() is True


@pytest.mark.asyncio
async def test_iter_posts_reads_the_timeline_then_the_store_once_each():
    timeline = {
        1: ([video_post("a"), video_post("b")], {"current_page": 1, "last_page": 2}),
        # A later page repeats a promoted post from the first.
        2: ([video_post("c"), video_post("a")], {"current_page": 2, "last_page": 2}),
    }
    store = {1: ([video_post("s1")], {"current_page": 1, "last_page": 1})}

    def handler(link, body):
        if "/social/timeline/" in link:
            items, meta = timeline[int(link.split("page=")[1].split("&")[0])]
            return {"timeline": items, "page_meta": meta}
        assert body["slug"] == "creator" and body["type"] == "video"
        items, meta = store[body["page"]]
        return {"list": items, "page_meta": meta}

    user = creator(make_authed(handler))
    async with aclosing(user.iter_posts()) as values:
        assert [p.uid async for p in values] == ["a", "b", "c", "s1"]
    async with aclosing(user.iter_posts(limit=2)) as values:
        assert [p.uid async for p in values] == ["a", "b"]
    async with aclosing(user.iter_posts(label="archived")) as values:
        assert [p async for p in values] == []


@pytest.mark.asyncio
async def test_iter_messages_follows_mid_token():
    pages = {
        None: {"messages": [{"uid": "m3"}, {"uid": "m2"}], "mid_token": "older"},
        "older": {"messages": [{"uid": "m1"}]},
    }

    def handler(link, body):
        token = link.split("mid=")[1].split("&")[0] if "mid=" in link else None
        return pages[token]

    authed = make_authed(handler)
    user = creator(authed)
    async with aclosing(user.iter_messages()) as values:
        assert [m.uid async for m in values] == ["m3", "m2", "m1"]
    assert all(f"/messages/with/{CREATOR}?" in link for link, _ in authed.calls)
    async with aclosing(authed.user.iter_messages()) as values:
        assert [m async for m in values] == []


@pytest.mark.asyncio
async def test_stories_and_highlights():
    def story(uid, kind="image"):
        return {"uid": uid, "type": kind, "file": f"https://cdn.test/{uid}", "created_at": when("2026-11-12 06:36:37"), "owner": {"uid": CREATOR}}

    def handler(link, body):
        if link.split("?")[0].endswith("/stories"):
            assert body == {"slug": "creator"}
            return {"list": [[story("s1"), story("s2", "video")]]}
        highlights = [
            {"uid": "h1", "title": "one", "stories": [story("s1"), story("s3")]},
            {"uid": "h2", "title": "two", "stories": [story("s3"), story("s4")]},
        ]
        return {"list": highlights, "pagination": {"current_page": 1, "last_page": 1}}

    user = creator(make_authed(handler))
    async with aclosing(user.iter_stories()) as values:
        stories = [s async for s in values]
    assert [(s.uid, s.media[0].type) for s in stories] == [("s1", "photo"), ("s2", "video")]
    assert all(contract.content_problems(s) == [] for s in stories)
    highlights = await user.get_highlights()
    assert [type(h) for h in highlights] == [HighlightModel, HighlightModel]
    async with aclosing(user.iter_highlight_stories()) as values:
        assert [s.uid async for s in values] == ["s1", "s3", "s4"]


@pytest.mark.asyncio
async def test_chats_follow_page_tokens_and_filter_locally():
    def partner(n):
        return {"partner": {"uid": f"u{n}", "slug": f"user{n}", "display_name": f"User {n}"}, "read": True}

    def handler(link, body):
        if body.get("page_token") == "next":
            return {"conversations": [partner(3)]}
        return {"conversations": [partner(1), partner(2)], "page_token": "next"}

    authed = make_authed(handler)
    async with aclosing(authed.iter_chats()) as values:
        assert [c.user.username async for c in values] == ["user1", "user2", "user3"]
    async with aclosing(authed.iter_chats(query="User 2")) as values:
        assert [c.user.username async for c in values] == ["user2"]
    assert authed.calls[0][1] == {"limit": 20, "all": True}


@pytest.mark.asyncio
async def test_subscriptions_merge_paid_and_followed():
    members = {
        "subscribed": [{"uid": "u1", "slug": "paid", "subscription_status": {"expired_at": when("2099-01-01 00:00:00"), "is_subscribed_to": True}}],
        "following": [{"uid": "u1", "slug": "paid"}, {"uid": "u2", "slug": "free"}],
    }

    def handler(link, body):
        return {"users": members[body["id"]], "page_meta": {"current_page": 1, "last_page": 1}}

    authed = make_authed(handler)
    authed.guest = False
    authed.subscriptions = []
    subscriptions = await authed.get_subscriptions()
    assert [(s.user.username, s.kind, s.is_active()) for s in subscriptions] == [
        ("paid", "subscribed", True),
        ("free", "following", True),
    ]
    paid = await authed.get_subscriptions(sub_type="active")
    assert [s.user.username for s in paid] == ["paid"]


@pytest.mark.asyncio
async def test_call_renews_an_expired_token_once(monkeypatch):
    import ultima_scraper_api.apis.loyalfans.classes.auth_model as auth_module

    answers = [(401, {"error": "token_expired"}), (200, {"success": True, "value": 1})]
    sent = []

    async def call_api(requester, link, body=None):
        sent.append(link)
        return answers.pop(0)

    monkeypatch.setattr(auth_module, "call_api", call_api)
    authed: Any = object.__new__(LoyalFansAuthModel)
    authed.auth_session = SimpleNamespace()
    renewed = []

    async def refresh_token(error=None):
        renewed.append(error)
        return True

    authed.authenticator = SimpleNamespace(refresh_token=refresh_token)
    assert await authed.call("https://www.loyalfans.com/api/v2/x") == {"success": True, "value": 1}
    assert renewed == [{"error": "token_expired"}] and len(sent) == 2

    answers[:] = [(403, {"success": False, "message": "Forbidden"})]
    assert await authed.call("https://www.loyalfans.com/api/v2/x") == {
        "error": {"code": 403, "message": "Forbidden"}
    }


def test_request_headers_carry_the_token_and_api_version():
    authenticator: Any = object.__new__(LoyalFansAuthenticator)
    authenticator.auth_session = SimpleNamespace(headers={})
    authenticator.auth_details = AuthDetails(authorization="Bearer abc", user_agent="UA")
    authenticator.guest = False
    headers = authenticator.create_request_headers("https://www.loyalfans.com/api/v2/stories")
    assert headers["authorization"] == "Bearer abc"
    assert headers["x-api-version"] and headers["user-agent"] == "UA"
    assert "authorization" not in authenticator.create_request_headers("https://cdn.test/x.jpg")
    assert AuthDetails(authorization="abc", unknown_key=1).token == "abc"
