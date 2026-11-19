"""Privacy (privacy.com.br) URLs, from the web client's live traffic (2026-11-17).

The site's web components call one API host, service.privacy.com.br, where
each backend service has its own path prefix (timelinequeries,
subscriptionmanager, chat, ...). Requests carry ``Authorization: Bearer
<token>``, the token returned by ``login()``.

Timeline routes page by ``skip``/``take`` in the path; list routes elsewhere
page by ``page`` in the query.

Videos are HLS on video.privacy.com.br. Each request for a playlist or segment
needs a token from ``video_token()`` (POST ``{"file_id": <id>}`` ->
``{"content": <token>}``), sent as the headers ``video_request_headers()``
builds. ``file_id`` is the first path segment of the video URL.
"""

from urllib.parse import urlencode, urlsplit

SCHEME = "https://"
DOMAIN = "privacy.com.br"
STANDARD_URL = f"{SCHEME}{DOMAIN}"
STANDARD_API_URL = f"{SCHEME}service.{DOMAIN}"
VIDEO_URL = f"{SCHEME}video.{DOMAIN}"
CHAT_WEBSOCKET_URL = f"wss://service-websocket.{DOMAIN}/chat/socket.io/"


def media_request_headers(url: str) -> dict[str, str]:
    """Headers a direct media file needs: image.privacy.com.br refuses a
    request that doesn't come from the site ("Access Denied", 403)."""
    host = (urlsplit(url).hostname or "").lower()
    if host == DOMAIN or host.endswith(f".{DOMAIN}"):
        return {"Referer": f"{STANDARD_URL}/", "Origin": STANDARD_URL}
    return {}


class Routes:
    # These use the standard url
    def profile(self, profile_name: str) -> str:
        return f"{STANDARD_URL}/profile/{profile_name}"

    def post(self, post_id: str, profile_name: str) -> str:
        return f"{STANDARD_URL}/post/{post_id}/{profile_name}"

    def chat(self, user_uid: int | str) -> str:
        return f"{STANDARD_URL}/chat?cid={user_uid}"


class APIRoutes:
    # These use the API url
    def login(self) -> str:
        """POST {Email, Password, ...} -> {token, expiration, profileName, mfaRequired}."""
        return f"{STANDARD_API_URL}/auth/identity/login"

    def feed(self, skip: int = 0, take: int = 10) -> str:
        """Home feed: {items: [post], recommendations: [...]}."""
        return f"{STANDARD_API_URL}/timelinequeries/feed/{skip}/{take}"

    def profile_posts(self, profile_name: str, skip: int = 0, take: int = 10) -> str:
        """A creator's timeline: {items: [post]}; each post holds its medias."""
        return f"{STANDARD_API_URL}/timelinequeries/profile/{skip}/{take}/{profile_name}"

    def public_profile_posts(self, profile_name: str, skip: int = 0, take: int = 3) -> str:
        """Signed-out preview of a timeline: a bare list of posts without medias."""
        return f"{STANDARD_API_URL}/timelinequeries/publicProfile/{profile_name}/{skip}/{take}"

    def highlights(self, profile_name: str, skip: int = 0, take: int = 15) -> str:
        return f"{STANDARD_API_URL}/timelinequeries/highlights/{skip}/{take}/{profile_name}"

    def post(self, post_id: str) -> str:
        """{item: post}."""
        return f"{STANDARD_API_URL}/timelinequeries/post/{post_id}"

    def post_comments(self, post_id: str, skip: int = 0) -> str:
        """[comment], from the timeline component's code."""
        return f"{STANDARD_API_URL}/timelinequeries/post/{post_id}/comments/{skip}"

    def me_context(self) -> str:
        """The signed-in account: {profileName, nickname, avatarUrl, userType, ...}."""
        return f"{STANDARD_API_URL}/profile/users/me/context"

    def subscriptions(
        self, page: int = 1, filter: str = "all", sort: str = "closest"
    ) -> str:
        """{items: [{status, isFree, isRecurring, endedAt, creator: {uid, handle}}]}."""
        query = urlencode({"page": page, "filter": filter, "sort": sort})
        return f"{STANDARD_API_URL}/subscriptionmanager/subscriptions/active?{query}"

    def follows(self, page: int = 0, limit: int = 30, nickname: str = "") -> str:
        """Profiles the account follows; 204 when there are none."""
        query = urlencode({"page": page, "limit": limit, "nickName": nickname})
        return f"{STANDARD_API_URL}/profile/UserFollows?{query}"

    def profile_friendships(self, profile_id: int | str, page: int = 0, limit: int = 10) -> str:
        query = urlencode({"profileId": profile_id, "page": page, "limit": limit})
        return f"{STANDARD_API_URL}/profilefriendship/ProfileFriendships/GetProfileFriendships?{query}"

    def chat_rooms(
        self,
        page: int = 1,
        filter: str = "all",
        sort: str = "newest",
        online: bool = False,
    ) -> str:
        """{rooms: [{roomId, recipient, lastMessage, unreadCount, ...}]}."""
        query = urlencode(
            {"page": page, "filter": filter, "sort": sort, "online": str(online).lower()}
        )
        return f"{STANDARD_API_URL}/chat/rooms?{query}"

    def chat_room(self, recipient_id: int | str) -> str:
        """The room with one user (by uid): {room: {...}}."""
        query = urlencode({"recipientId": recipient_id, "tempRoom": "true"})
        return f"{STANDARD_API_URL}/chat/room?{query}"

    def chat_messages(
        self,
        room_id: str,
        user_ids: list[int | str],
        before_sent_at: str | None = None,
    ) -> str:
        """[message], newest first; files carry mediaId/type/isLocked.

        ``user_ids`` are both participants' uids (own first, as the web client
        sends them). Older pages: pass the oldest message's ``sentAt`` as
        ``before_sent_at`` (the client's ``minorSentAt``).
        """
        params: list[tuple[str, str | int]] = [("roomId", room_id)]
        params += [("usersId[]", u) for u in user_ids]
        if before_sent_at:
            params.append(("minorSentAt", before_sent_at))
        # As the web client: brackets encoded, the timestamp's colons not.
        return f"{STANDARD_API_URL}/chat/messages?{urlencode(params, safe=':')}"

    def chat_image(self, media_id: str) -> str:
        return f"{STANDARD_API_URL}/media/image/chat/view/{media_id}"

    def video_token(self) -> str:
        """POST {"file_id": <video file id>} -> {"content": <token>}."""
        return f"{STANDARD_API_URL}/mediavideotoken/generate"


def video_file_id(video_url: str) -> str:
    """The file id video_token() takes: the first path segment of a video URL."""
    return urlsplit(video_url).path.strip("/").split("/")[0]


def video_request_headers(url: str, token: str) -> dict[str, str]:
    """Headers the web player adds to each HLS playlist/segment request."""
    return {"content": token, "x-content-uri": urlsplit(url).path.rsplit("/", 1)[-1]}
