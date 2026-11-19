"""Fansly's streaming methods and media, against a fake requester (no network)."""

from contextlib import aclosing
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

import ultima_scraper_api.managers.redis as redis_module
from ultima_scraper_api.apis import site_contract as contract
from ultima_scraper_api.apis.fansly import Media, resolve_attachments
from ultima_scraper_api.apis.fansly.classes.auth_model import CHAT_PAGE, FanslyAuthModel
from ultima_scraper_api.apis.fansly.classes.user_model import UserModel

CREATOR = 300
ME = 1


class FakeRequester:
    def __init__(self, handler):
        self.handler = handler
        self.links: list[str] = []

    async def json_request(self, link):
        self.links.append(link)
        parts = urlsplit(link)
        query = {k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
        return {"success": True, "response": self.handler(parts.path, query)}


@pytest.fixture(autouse=True)
def quiet_events(monkeypatch):
    async def publish(_event):
        return None

    monkeypatch.setattr(redis_module, "publish_custom_event", publish)


def make_user(handler, user_id=CREATOR):
    requester = FakeRequester(handler)
    settings = SimpleNamespace(media_quality=SimpleNamespace(video="source"))
    authed = SimpleNamespace(id=ME, user=SimpleNamespace(id=ME))

    async def find_chat_group_id(_user):
        return 77

    authed.find_chat_group_id = find_chat_group_id
    user = object.__new__(UserModel)
    user.id = user_id
    user.username = "creator"
    user.socials = []
    user.get_requester = lambda: requester  # type: ignore[assignment]
    user.get_authed = lambda: authed  # type: ignore[assignment]
    user.get_api = lambda: SimpleNamespace(get_site_settings=lambda: settings)  # type: ignore[assignment]
    return user, requester


def media(media_id, mimetype="video/mp4", url=True, **extra):
    return {
        "id": media_id,
        "type": 2 if mimetype.startswith("video") else 1,
        "mimetype": mimetype,
        "height": 720,
        "createdAt": 1700000000,
        "locations": [{"location": f"https://cdn.test/{media_id}"}] if url else [],
        "variants": [],
        **extra,
    }


def account_media(am_id, full, *, price=0, purchased=False, preview=None):
    flags = [{"flags": 1, "price": price}] if price else []
    return {
        "id": am_id,
        "media": full,
        "preview": preview,
        "price": 0,
        "purchased": purchased,
        "access": purchased or not price,
        "permissions": {"permissionFlags": flags},
    }


async def collect(generator):
    async with aclosing(generator) as values:
        return [value async for value in values]


# --- media ----------------------------------------------------------------------


def test_media_reads_the_way_the_backend_reads_it():
    item = Media(
        media("m1", metadata='{"duration": 18.5}'),
        account_media("am1", None, price=10000),
        is_preview=False,
    )
    assert item["type"] == item.type == "video"
    assert item["fansly_type"] == 2
    assert item.id == "m1" and item.canView is True and item.duration == 18.5
    assert item.created_at == datetime.fromtimestamp(1700000000)
    assert item["price"] == 10.0 and item["purchased"] is False
    assert Media(media("g", "image/gif"), {}, is_preview=False).type == "gif"
    assert Media(media("p", "image/jpeg"), {}, is_preview=False).type == "photo"
    assert Media(media("h", "application/vnd.apple.mpegurl"), {}, is_preview=False).type == "video"


def test_price_and_purchase_state():
    aggregation = {
        "accountMedia": [
            account_media("am1", media("m1"), price=5000, purchased=True),
            account_media("am2", media("m2", url=False), price=7000, preview=media("20", "image/jpeg")),
            account_media("am3", media("m3"), price=9000),
        ],
        "accountMediaBundles": [
            {
                "id": "b1",
                "accountMediaIds": ["am3"],
                "permissions": {"permissionFlags": [{"flags": 1, "price": 2000}]},
                "purchased": True,
            }
        ],
    }
    attachments = [
        {"contentType": 1, "contentId": "am1", "pos": 0},
        {"contentType": 1, "contentId": "am2", "pos": 1},
        {"contentType": 2, "contentId": "b1", "pos": 2},
    ]
    resolved = resolve_attachments(attachments, aggregation)
    assert [m.id for m in resolved.media] == ["m1", "20", "m3"]
    assert resolved.previews == [20]
    assert [m["preview"] for m in resolved.media] == [False, True, False]
    # am1 5 + am2 7 + the bundle's 2 (it replaces am3's own price).
    assert resolved.price == 14.0
    assert resolved.bought is False  # am2 is still locked


# --- posts ----------------------------------------------------------------------


def timeline_handler(pages):
    """pages: before-cursor -> list of (post id, account id)."""

    def handler(path, query):
        assert path == f"/api/v1/timelinenew/{CREATOR}"
        posts = pages.get(query["before"], [])
        return {
            "posts": [
                {"id": pid, "accountId": str(aid), "createdAt": 1700000000, "content": "t"}
                for pid, aid in posts
            ],
            "accountMedia": [],
        }

    return handler


@pytest.mark.asyncio
async def test_iter_posts_pages_by_the_oldest_id_and_skips_reposts():
    user, requester = make_user(
        timeline_handler(
            {
                "0": [("30", CREATOR), ("29", 999)],
                "29": [("28", 999)],  # only reposts: paging continues
                "28": [("27", CREATOR)],
            }
        )
    )
    posts = await collect(user.iter_posts())
    assert [p.id for p in posts] == [30, 27]
    assert [parse_qs(urlsplit(link).query)["before"][0] for link in requester.links] == [
        "0", "29", "28", "27",
    ]
    assert all(contract.content_problems(p) == [] for p in posts)


@pytest.mark.asyncio
async def test_iter_posts_limit_and_archived_label():
    user, _ = make_user(timeline_handler({"0": [("30", CREATOR), ("29", CREATOR)]}))
    assert [p.id for p in await collect(user.iter_posts(limit=1))] == [30]
    assert await collect(user.iter_posts(label="archived")) == []


# --- messages -------------------------------------------------------------------


def messages_handler(total, page_size):
    ids = list(range(total, 0, -1))  # newest first

    def handler(path, query):
        assert path == "/api/v1/message" and query["groupId"] == "77"
        before = int(query.get("before") or 0) or total + 1
        page = [i for i in ids if i < before][: int(query["limit"])]
        assert int(query["limit"]) == page_size
        return {
            "messages": [
                {"id": str(i), "senderId": str(CREATOR), "groupId": "77", "createdAt": 1700000000}
                for i in page
            ]
        }

    return handler


@pytest.mark.asyncio
async def test_iter_messages_page_size_total_and_cutoff():
    user, _ = make_user(messages_handler(7, 3))
    assert [m.id for m in await collect(user.iter_messages(limit=3))] == [7, 6, 5, 4, 3, 2, 1]
    assert [m.id for m in await collect(user.iter_messages(limit=3, max_items=4))] == [7, 6, 5, 4]
    assert [m.id for m in await collect(user.iter_messages(limit=3, cutoff_id=3))] == [7, 6, 5, 4]
    assert [m.id for m in await collect(user.iter_messages(limit=3, offset_id=5))] == [4, 3, 2, 1]


@pytest.mark.asyncio
async def test_get_messages_limit_is_the_total():
    user, _ = make_user(messages_handler(60, 25))
    user.scrape_manager = SimpleNamespace(scraped=SimpleNamespace())  # type: ignore[assignment]
    messages = await user.get_messages(limit=30)
    assert len(messages) == 30 and messages[-1].id == 31


# --- chats and socials -------------------------------------------------------------


@pytest.mark.asyncio
async def test_iter_chats_pages_by_offset_and_searches():
    seen = []

    def handler(path, query):
        seen.append((query["offset"], query.get("search", "")))
        start = int(query["offset"])
        count = max(0, min(CHAT_PAGE, 30 - start))
        rows = [{"partnerAccountId": str(i), "groupId": str(i)} for i in range(start, start + count)]
        return {
            "data": rows,
            "aggregationData": {"accounts": [{"id": r["partnerAccountId"]} for r in rows]},
        }

    authed = object.__new__(FanslyAuthModel)
    requester = FakeRequester(handler)
    authed.get_requester = lambda: requester  # type: ignore[assignment]
    authed.resolve_user = lambda account: SimpleNamespace(id=int(account["id"]))  # type: ignore[assignment]
    chats = await collect(authed.iter_chats(query="ab"))
    assert len(chats) == 30
    assert seen == [("0", "ab"), (str(CHAT_PAGE), "ab")]
    assert len(await collect(authed.iter_chats(limit=5))) == 5


@pytest.mark.asyncio
async def test_socials_use_the_backends_payload_shape():
    user, _ = make_user(lambda *_: {})
    user.socials = [
        {"providerId": "1", "handle": "someone"},
        {"providerId": "9", "handle": "toy"},
        {"providerId": "42", "handle": "new"},
        {"providerId": "4", "handle": ""},
    ]
    assert await user.get_socials() == [
        {"socialMedia": "Twitter", "username": "someone", "providerId": "1", "url": "https://x.com/someone"},
        {"socialMedia": "Fleshlight", "username": "toy", "providerId": "9"},
        {"socialMedia": "provider 42", "username": "new", "providerId": "42"},
    ]
