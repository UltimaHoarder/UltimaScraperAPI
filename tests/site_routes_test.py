from ultima_scraper_api.apis.darkfans.urls import APIRoutes as DarkFansRoutes
from ultima_scraper_api.apis.loyalfans.urls import APIRoutes as LoyalFansRoutes
from ultima_scraper_api.apis.onlyfans.urls import APIRoutes as OnlyFansRoutes
from ultima_scraper_api.apis.privacy.urls import APIRoutes as PrivacyRoutes
from ultima_scraper_api.apis.privacy.urls import video_file_id, video_request_headers

OF = "https://onlyfans.com/api2/v2"
PRIVACY = "https://service.privacy.com.br"


def test_onlyfans_content_types_are_pluralised_once():
    routes = OnlyFansRoutes()
    assert routes.like("messages", 1) == f"{OF}/messages/1/like"
    assert routes.like("post", 2) == f"{OF}/posts/2/like"
    assert routes.list_comments("post", 3).startswith(f"{OF}/posts/3/comments?")
    assert routes.favorite("post", 4, 9) == f"{OF}/posts/4/favorites/9"


def test_onlyfans_subscriptions_encode_the_filter():
    url = OnlyFansRoutes().list_subscriptions(limit=5, offset=10, sub_type="active")
    assert url == (
        f"{OF}/subscriptions/subscribes?limit=5&offset=10&type=active"
        "&filter%5B%5D=1&format=infinite"
    )


def test_onlyfans_iter_links_pages_and_trims_the_last_page():
    routes = OnlyFansRoutes()
    url = routes.list_chats(limit=10, offset=0)
    pages = list(routes.iter_links(url, 25, pagination_limit=10, exact_limit=True))
    assert pages == [
        f"{OF}/chats?limit=10&offset=0&order=recent",
        f"{OF}/chats?limit=10&offset=10&order=recent",
        f"{OF}/chats?limit=5&offset=20&order=recent",
    ]
    assert routes.create_links(url, 0) == []


def test_loyalfans_messages_carry_paging_in_the_url():
    routes = LoyalFansRoutes()
    assert routes.messages("abc", limit=5, offset=10).endswith(
        "/api/v2/messages/abc?limit=5&offset=10"
    )
    urls, payloads = routes.create_payloads("u", {"id": "subscribed"}, 25, 10)
    assert urls == ["u", "u", "u"]
    assert [p["page"] for p in payloads] == [1, 2, 3]
    assert all(p["id"] == "subscribed" and p["limit"] == 10 for p in payloads)


def test_darkfans_routes_omit_unset_filters():
    routes = DarkFansRoutes()
    assert routes.posts("u-1", page=2, per_page=5) == (
        "https://darkfans.com/api/v1/user/u-1/posts?page=2&perPage=5"
    )
    assert routes.chats("u-1", archived=False).endswith("/user/u-1/chat?page=1&perPage=15&archived=0")
    assert routes.me() == "https://darkfans.com/api/v1/user/info"


def test_privacy_routes_match_the_web_client():
    routes = PrivacyRoutes()
    assert routes.profile_posts("someone", skip=10, take=10) == (
        f"{PRIVACY}/timelinequeries/profile/10/10/someone"
    )
    assert routes.subscriptions() == (
        f"{PRIVACY}/subscriptionmanager/subscriptions/active?page=1&filter=all&sort=closest"
    )
    assert routes.chat_rooms() == (
        f"{PRIVACY}/chat/rooms?page=1&filter=all&sort=newest&online=false"
    )
    # Brackets encoded, the timestamp's colons kept, as the browser sends them.
    assert routes.chat_messages("room1", [1, 2], "2026-01-02T03:04:05.678Z") == (
        f"{PRIVACY}/chat/messages?roomId=room1&usersId%5B%5D=1&usersId%5B%5D=2"
        "&minorSentAt=2026-01-02T03:04:05.678Z"
    )


def test_privacy_video_token_inputs():
    url = "https://video.privacy.com.br/abc123/hls/file--name.m3u8"
    assert video_file_id(url) == "abc123"
    assert video_request_headers(url, "tok") == {
        "content": "tok",
        "x-content-uri": "file--name.m3u8",
    }
