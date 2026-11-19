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


def test_loyalfans_routes_match_the_web_client():
    routes = LoyalFansRoutes()
    api = "https://www.loyalfans.com/api"
    assert routes.timeline("some one", limit=20, page=2) == (
        f"{api}/v2/social/timeline/some%20one?limit=20&page=2&ngsw-bypass=true"
    )
    assert routes.conversation("uid-1") == (
        f"{api}/v1/messages/with/uid-1?timezone=UTC&ngsw-bypass=true"
    )
    assert routes.conversation("uid-1", "a/b") == (
        f"{api}/v1/messages/with/uid-1?timezone=UTC&mid=a%2Fb&ngsw-bypass=true"
    )
    assert routes.stories() == f"{api}/v2/stories?ngsw-bypass=true"


def test_darkfans_routes_match_the_web_client():
    routes = DarkFansRoutes()
    api = "https://darkfans.com/api/v1"
    assert routes.posts("u-1", page=2, per_page=5) == f"{api}/user/u-1/posts?page=2&perPage=5"
    assert routes.posts("u-1", post_type="ppv").endswith("/posts?page=1&perPage=15&type=ppv")
    # The web client sends the flag as a word (captured: archived=false).
    assert routes.chats("u-1", archived=False).endswith("/user/u-1/chat?page=1&perPage=15&archived=false")
    assert routes.chat_messages("me", "c-1", page=3) == (
        f"{api}/user/me/chat/c-1/messages?page=3&perPage=50"
    )
    assert routes.stories("u-1") == f"{api}/user/u-1/stories?withPinned=1&page=1&perPage=15"
    assert routes.me() == f"{api}/user/info"
    assert routes.refresh_token() == f"{api}/auth/refresh"


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
