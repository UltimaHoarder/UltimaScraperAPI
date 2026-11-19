"""Privacy models, auth and HLS, against made-up data (no network)."""

import base64
import json
from contextlib import aclosing
from types import SimpleNamespace

import pytest
from Crypto.Cipher import AES

import ultima_scraper_api.managers.redis as redis_module
from ultima_scraper_api.apis import site_contract as contract
from ultima_scraper_api.apis.privacy import parse_duration, parse_price
from ultima_scraper_api.apis.privacy.authenticator import token_claims
from ultima_scraper_api.apis.privacy.classes.auth_model import PrivacyAuthModel
from ultima_scraper_api.apis.privacy.classes.message_model import MessageModel
from ultima_scraper_api.apis.privacy.classes.post_model import PostModel
from ultima_scraper_api.apis.privacy.classes.user_model import UserModel, normalize_user
from ultima_scraper_api.apis.privacy import hls
from ultima_scraper_api.apis.privacy.hls import (
    HlsError,
    decrypt_segment,
    is_video_playlist,
    iter_video,
    parse_playlist,
)
from ultima_scraper_api.helpers.site_ids import native_id_to_db_id

ME, CREATOR = 1000, 2000


@pytest.fixture(autouse=True)
def quiet_events(monkeypatch):
    async def publish(_event):
        return None

    monkeypatch.setattr(redis_module, "publish_custom_event", publish)


def make_user(requester=None, uid=CREATOR, name="creator"):
    authed = SimpleNamespace(id=ME, user=SimpleNamespace(id=ME), rooms={})
    user = object.__new__(UserModel)
    user.id = uid
    user.username = name
    user.get_authed = lambda: authed  # type: ignore[assignment]
    user.get_requester = lambda: requester  # type: ignore[assignment]
    return user, authed


def post(post_id="p-1", medias=None, price=None):
    return {
        "postId": post_id,
        "publishedDate": "2026-11-17T12:22:23.950Z",
        "description": "hello",
        "creator": {"uid": str(CREATOR), "profileName": "creator", "aid": "AID"},
        "price": price,
        "isUnlocked": True,
        "purchaseStatus": False,
        "medias": medias or [],
    }


def test_users_normalize_from_every_shape():
    creator = normalize_user({"aid": "A-1", "uid": "7", "nickname": "Nick", "profileName": "nick7"})
    recipient = normalize_user({"id": 7, "name": "Nick", "profileName": "nick7", "isCreator": True, "guid": "A-1"})
    subscription = normalize_user({"uid": "7", "handle": "nick7"})
    assert creator["uid"] == recipient["uid"] == subscription["uid"] == 7
    assert creator["username"] == recipient["username"] == subscription["username"] == "nick7"
    assert creator["aid"] == recipient["aid"] == "a-1"


def test_prices_and_durations():
    assert parse_price({"amount": 2.49, "currencyCode": "GBP"}) == (2.49, "GBP")
    assert parse_price(1.5) == (1.5, None)
    assert parse_price(None) == (0.0, None)
    assert parse_duration("01:02:03") == 3723.0
    assert parse_duration("00:15") == 15.0
    assert parse_duration(12) == 12.0
    assert parse_duration("") is None


def test_post_is_storable_and_keeps_string_ids():
    user, _ = make_user()
    item = PostModel(
        post(
            medias=[
                {"mediaId": "m-1", "type": "image", "url": "https://image.test/1", "isLocked": False},
                {"mediaId": "m-2", "type": "video", "url": "https://video.test/f/hls/v.m3u8", "time": "00:30", "isLocked": False},
                {"mediaId": "m-3", "type": "video", "url": None, "isLocked": True},
            ],
            price={"amount": 0, "currencyCode": "GBP"},
        ),
        user,
    )
    assert item.uid == "p-1" and item.id == native_id_to_db_id("p-1")
    assert [m.type for m in item.media] == ["photo", "video", "video"]
    assert item.media[0].id == native_id_to_db_id("m-1") and item.media[0]["media_id"] == "m-1"
    assert item.media[1].duration == 30.0
    assert [item.url_picker(m) is not None for m in item.media] == [True, True, False]
    assert contract.content_problems(item) == []


def test_message_author_and_resolved_files():
    user, authed = make_user()
    authed.user = SimpleNamespace(id=ME)
    raw = {
        "_id": "msg-1",
        "senderId": CREATOR,
        "content": "hi",
        "sentAt": "2026-11-07T02:22:43.591Z",
        "price": 2.49,
        "currencyCode": "GBP",
        "isLocked": True,
        "files": [
            {"mediaId": "f-1", "type": "image", "isLocked": False},
            {"type": "video", "isLocked": True},  # locked files have no id
        ],
    }
    message = MessageModel(raw, user, {"f-1": "https://image.test/f1"})
    assert message.author is user and message.get_receiver() is authed.user
    assert [m["media_id"] for m in message.media] == ["f-1"]
    assert message.url_picker(message.media[0]).geturl() == "https://image.test/f1"  # type: ignore[union-attr]
    assert message.price == 2.49 and message.is_bought() is False
    assert contract.content_problems(message) == []
    mine = MessageModel({**raw, "_id": "msg-2", "senderId": ME}, user)
    assert mine.author is authed.user


class Requester:
    def __init__(self, handler):
        self.handler = handler
        self.links = []

    async def json_request(self, link):
        self.links.append(link)
        return self.handler(link)


@pytest.mark.asyncio
async def test_iter_posts_pages_by_skip():
    pages = {0: [post(f"p{i}") for i in range(10)], 10: [post("p10")]}
    requester = Requester(lambda link: {"items": pages.get(int(link.split("/profile/")[1].split("/")[0]), [])})
    user, _ = make_user(requester)
    async with aclosing(user.iter_posts()) as values:
        posts = [p async for p in values]
    assert [p.uid for p in posts] == [f"p{i}" for i in range(11)]
    assert [link.split("/profile/")[1] for link in requester.links] == ["0/10/creator", "10/10/creator"]


@pytest.mark.asyncio
async def test_iter_messages_pages_back_by_sent_at():
    newest_first = [
        {"_id": f"m{i}", "senderId": CREATOR, "sentAt": f"2026-11-0{i}T00:00:00.000Z"}
        for i in range(5, 0, -1)
    ]

    def handler(link):
        if "minorSentAt=" not in link:
            return newest_first[:3]
        before = link.split("minorSentAt=")[1]
        return [m for m in newest_first if m["sentAt"] < before][:3]

    user, authed = make_user(Requester(handler))
    authed.rooms[CREATOR] = "room-1"

    async def find_room_id(_user):
        return "room-1"

    authed.find_room_id = find_room_id
    async with aclosing(user.iter_messages()) as values:
        messages = [m async for m in values]
    assert [m.uid for m in messages] == ["m5", "m4", "m3", "m2", "m1"]


@pytest.mark.asyncio
async def test_chats_page_until_repeat_and_filter_locally():
    rooms = [
        {"roomId": f"r{i}", "recipient": {"id": i, "profileName": f"user{i}", "name": f"User {i}"}}
        for i in range(1, 4)
    ]
    authed = object.__new__(PrivacyAuthModel)
    authed.users = {}
    authed.rooms = {}
    # The server keeps answering page 1's rooms past the end.
    authed.get_requester = lambda: Requester(lambda link: {"rooms": rooms})  # type: ignore[assignment]
    authed.resolve_user = lambda raw: SimpleNamespace(  # type: ignore[assignment]
        id=raw["id"], username=raw["profileName"], name=raw["name"]
    )
    async with aclosing(authed.iter_chats()) as values:
        assert [c.room_id for c in [c async for c in values]] == ["r1", "r2", "r3"]
    async with aclosing(authed.iter_chats(query="user2")) as values:
        assert [c.room_id for c in [c async for c in values]] == ["r2"]
    assert authed.rooms == {1: "r1", 2: "r2", 3: "r3"}


def test_token_claims_are_read_without_verification():
    payload = base64.urlsafe_b64encode(json.dumps({"uid": "77", "profile_name": "me"}).encode()).rstrip(b"=")
    assert token_claims(f"h.{payload.decode()}.s") == {"uid": "77", "profile_name": "me"}
    assert token_claims("not-a-jwt") == {}


# --- HLS --------------------------------------------------------------------------

KEY = bytes(range(16))


def encrypt(data: bytes, sequence: int) -> bytes:
    pad = 16 - len(data) % 16
    return AES.new(KEY, AES.MODE_CBC, sequence.to_bytes(16, "big")).encrypt(data + bytes([pad]) * pad)


def test_playlists_parse_variants_keys_and_sequence():
    master = parse_playlist(
        "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=700000,RESOLUTION=640x360\nlow.m3u8\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=4000000,CODECS=\"avc1,mp4a\"\nhigh.m3u8\n",
        "https://video.test/f1/hls/master.m3u8",
    )
    assert max(master.variants) == (4000000, "https://video.test/f1/hls/high.m3u8")
    media = parse_playlist(
        "#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:5\n#EXT-X-KEY:METHOD=AES-128,URI=\"https://key.test/k/1\"\n"
        "#EXTINF:6,\na.ts\n#EXTINF:6,\nb.ts\n#EXT-X-ENDLIST\n",
        "https://video.test/f1/hls/high.m3u8",
    )
    assert [(url.rsplit("/", 1)[1], seq) for url, seq, _ in media.segments] == [("a.ts", 5), ("b.ts", 6)]
    assert media.segments[0][2].uri == "https://key.test/k/1"  # type: ignore[union-attr]
    assert decrypt_segment(encrypt(b"x" * 20, 5), KEY, (5).to_bytes(16, "big")) == b"x" * 20


@pytest.mark.asyncio
async def test_iter_video_sends_token_headers_and_refreshes_once():
    files = {
        "https://video.test/f1/hls/master.m3u8": b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nv.m3u8\n",
        "https://video.test/f1/hls/v.m3u8": (
            b"#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-KEY:METHOD=AES-128,URI=\"https://key.test/k\"\n"
            b"#EXTINF:6,\ns0.ts\n#EXTINF:6,\ns1.ts\n"
        ),
        "https://key.test/k": KEY,
        "https://video.test/f1/hls/s0.ts": encrypt(b"segment-0", 0),
        "https://video.test/f1/hls/s1.ts": encrypt(b"segment-1", 1),
    }
    tokens = iter(["old", "new"])
    seen = []

    async def token_source(file_id):
        assert file_id == "f1"
        return next(tokens)

    async def fetch(url, headers):
        seen.append((url.rsplit("/", 1)[1], headers["content"], headers["x-content-uri"]))
        if url.endswith("s1.ts") and headers["content"] == "old":
            return 423, b""  # the first token expired mid-download
        return 200, files[url]

    async with aclosing(iter_video("https://video.test/f1/hls/master.m3u8", fetch, token_source)) as chunks:
        assert [c async for c in chunks] == [b"segment-0", b"segment-1"]
    assert ("s0.ts", "old", "s0.ts") in seen and ("s1.ts", "new", "s1.ts") in seen
    assert ("k", "old", "k") in seen


@pytest.mark.asyncio
async def test_iter_video_without_a_token_fails_clearly():
    async def token_source(_file_id):
        return None

    async def fetch(_url, _headers):
        raise AssertionError("must not fetch")

    with pytest.raises(HlsError, match="No video token"):
        async with aclosing(iter_video("https://video.test/f1/hls/m.m3u8", fetch, token_source)) as chunks:
            [c async for c in chunks]


def test_only_video_playlists_need_the_site_downloader():
    authed = object.__new__(PrivacyAuthModel)
    assert is_video_playlist("https://video.privacy.com.br/f1/hls/master.m3u8?x=1")
    assert not is_video_playlist("https://cdn.privacy.com.br/image.jpg")
    assert authed.stream_downloader("https://cdn.privacy.com.br/image.jpg") is None
    assert callable(authed.stream_downloader("https://video.privacy.com.br/f1/hls/master.m3u8"))


@pytest.mark.asyncio
async def test_save_video_remuxes_an_mp4_destination(tmp_path, monkeypatch):
    calls = []

    async def download_video(_authed, url, destination):
        calls.append(("download", url, destination.name))
        destination.write_bytes(b"ts")
        return destination

    async def remux_to_mp4(source, destination):
        calls.append(("remux", source.name, destination.name))
        destination.write_bytes(source.read_bytes() + b"->mp4")
        return destination

    monkeypatch.setattr(hls, "download_video", download_video)
    monkeypatch.setattr(hls, "remux_to_mp4", remux_to_mp4)
    url = "https://video.privacy.com.br/f1/hls/master.m3u8"
    saved = await hls.save_video(object(), url, tmp_path / "clip.mp4")
    assert saved.read_bytes() == b"ts->mp4"
    assert calls == [("download", url, "clip.ts"), ("remux", "clip.ts", "clip.mp4")]
    assert not (tmp_path / "clip.ts").exists()  # the stream is a temporary
    # Any other destination keeps the transport stream itself.
    calls.clear()
    await hls.save_video(object(), url, tmp_path / "clip.ts")
    assert calls == [("download", url, "clip.ts")]


def test_media_files_are_requested_from_the_site():
    from ultima_scraper_api.apis.privacy.urls import media_request_headers

    expected = {"Referer": "https://privacy.com.br/", "Origin": "https://privacy.com.br"}
    assert media_request_headers("https://image.privacy.com.br/eyJrZXkiOiJhIn0=") == expected
    assert media_request_headers("https://privacy.com.br/x.jpg") == expected
    assert media_request_headers("https://cdn.example.test/a.jpg") == {}
    assert media_request_headers("https://notprivacy.com.br/a.jpg") == {}
