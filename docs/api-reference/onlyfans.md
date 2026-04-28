# OnlyFans API Reference

Complete API reference for the OnlyFans implementation in UltimaScraperAPI.

!!! note "Stability Status"
    The OnlyFans API is **fully supported and stable**. All documented features are production-ready.

## Overview

The OnlyFans API provides a comprehensive interface for interacting with OnlyFans content and user data. It includes:

- **Authentication**: Cookie-based and guest authentication
- **User Management**: Profile data, subscriptions, and relationships
- **Content Access**: Posts, stories, messages, highlights, and media
- **Session Management**: Connection pooling and rate limiting
- **DRM Support**: Widevine CDM integration for encrypted content

## Quick Reference

| Class | Purpose | Location |
|-------|---------|----------|
| `OnlyFansAPI` | Main API interface | `ultima_scraper_api.apis.onlyfans` |
| `OnlyFansAuthenticator` | Authentication handler | `ultima_scraper_api.apis.onlyfans.authenticator` |
| `OnlyFansAuthModel` | Authenticated session | `ultima_scraper_api.apis.onlyfans.classes.auth_model` |
| `UserModel` | User/performer profile | `ultima_scraper_api.apis.onlyfans.classes.user_model` |
| `PostModel` | Post content | `ultima_scraper_api.apis.onlyfans.classes.post_model` |
| `MessageModel` | Message content | `ultima_scraper_api.apis.onlyfans.classes.message_model` |
| `StoryModel` | Story content | `ultima_scraper_api.apis.onlyfans.classes.story_model` |
| `MediaModel` | Media files | `ultima_scraper_api.apis.onlyfans.classes.media_model` |

## Core Classes

### OnlyFansAPI

Main entry point for interacting with the OnlyFans API.

**Location:** `ultima_scraper_api.apis.onlyfans`

#### Initialization

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

# With default configuration
api = OnlyFansAPI()

# With custom configuration
config = UltimaScraperAPIConfig()
api = OnlyFansAPI(config)
```

#### Methods

##### login_context

```python
async login_context(
    auth_json: dict[str, Any] | None = None,
    guest: bool = False
) -> OnlyFansAuthModel | None
```

Context manager for authentication sessions. Automatically handles login and cleanup.

**Parameters:**

- `auth_json` (dict | None): Authentication credentials containing `id`, `cookie`, `user_agent`, and `x-bc`
- `guest` (bool): Whether to authenticate as guest (limited access)

**Returns:** `OnlyFansAuthModel` if authentication succeeds, `None` otherwise

**Example:**

```python
auth_json = {
    "id": 123456,
    "cookie": "auth_id=123456; sess=abc...",
    "user_agent": "Mozilla/5.0...",
    "x-bc": "token_here"
}

async with api.login_context(auth_json) as authed:
    if authed and authed.is_authed():
    me = await authed.get_authed_user()
        print(f"Logged in as: {me.username}")
```

##### get_site_settings

```python
get_site_settings() -> OnlyFansSiteSettings
```

Returns site-specific settings like media quality preferences.

**Returns:** `OnlyFansSiteSettings` object

**Example:**

```python
settings = api.get_site_settings()
print(f"Video quality: {settings.media_quality.video}")
```

---

### OnlyFansAuthenticator

Handles authentication and session management at a lower level.

**Location:** `ultima_scraper_api.apis.onlyfans.authenticator`

!!! tip "Use login_context Instead"
    For most use cases, prefer using `OnlyFansAPI.login_context()` which automatically manages the authenticator lifecycle.

#### Initialization

```python
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails

# Create API instance
api = OnlyFansAPI()

# Create auth details
auth_details = AuthDetails(
    cookie="auth_id=123456; sess=abc...",
    user_agent="Mozilla/5.0...",
    x_bc="token_here"
)

# Create authenticator
authenticator = OnlyFansAuthenticator(api, auth_details, guest=False)
```

#### Methods

##### login

```python
async login(guest: bool = False) -> OnlyFansAuthModel
```

Authenticate with OnlyFans and return authenticated session.

**Parameters:**

- `guest` (bool): Authenticate as guest (no credentials required)

**Returns:** `OnlyFansAuthModel` instance

**Raises:**

- `AuthenticationError`: If authentication fails
- `ConnectionError`: If network request fails

**Example:**

```python
async with authenticator:
    auth_model = await authenticator.login()
    me = await auth_model.get_authed_user()
```

##### create_auth

```python
create_auth() -> OnlyFansAuthModel
```

Creates an `OnlyFansAuthModel` instance from the authenticator.

**Returns:** `OnlyFansAuthModel` instance

##### create_signed_headers

```python
create_signed_headers(
    link: str,
    auth_id: int,
    time_: int | None = None
) -> dict[str, str]
```

Generate signed headers for OnlyFans API requests (includes dynamic signing).

**Parameters:**

- `link` (str): API endpoint URL
- `auth_id` (int): Authenticated user ID
- `time_` (int | None): Timestamp for signing (auto-generated if None)

**Returns:** Dictionary of HTTP headers

##### is_authed

```python
is_authed() -> bool
```

Check if currently authenticated.

**Returns:** `True` if authenticated, `False` otherwise

##### close

```python
async close() -> None
```

Close authenticator session and cleanup resources.

**Example:**

```python
await authenticator.close()
```

### OnlyFansAuthModel

Represents an authenticated session with full access to user data and operations.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.auth_model`

#### Attributes

```python
# Core user data
auth_model.id: int                                    # Authenticated user ID
auth_model.username: str                              # Authenticated username
auth_model.user: UserModel                            # Authenticated user object
auth_model.users: dict[int, UserModel]                # Cache of fetched users

# Collections
auth_model.subscriptions: list[SubscriptionModel]     # User's subscriptions
auth_model.lists: list[dict[str, Any]]                # User's lists
auth_model.chats: list[ChatModel]                     # User's chats
auth_model.paid_content: list[MessageModel | PostModel]  # Purchased content
auth_model.mass_message_stats: list[MassMessageStatModel]  # Mass message statistics

# Settings
auth_model.blacklist: list[str]                       # Blocked users
auth_model.guest: bool                                # Whether in guest mode
auth_model.extras: dict[str, Any]                     # Additional data
```

#### Methods

##### User Management

###### get_user

```python
async get_user(
    identifier: int | str,
    refresh: bool = False
) -> UserModel | None
```

Fetch a user by ID or username.

**Parameters:**

- `identifier` (int | str): User ID or username
- `refresh` (bool): Force refresh from API (bypass cache)

**Returns:** `UserModel` if found, `None` otherwise

**Example:**

```python
user = await auth_model.get_user("username")
if user:
    print(f"User: {user.name} (@{user.username})")
```

###### find_user

```python
find_user(identifier: int | str) -> UserModel | None
```

Find a user in the local cache (does not make API request).

**Parameters:**

- `identifier` (int | str): User ID or username

**Returns:** Cached `UserModel` if found, `None` otherwise

###### add_user

```python
add_user(user: UserModel) -> UserModel
```

Add a user to the cache.

**Parameters:**

- `user` (UserModel): User to cache

**Returns:** The cached user

###### resolve_user

```python
resolve_user(user_dict: dict[str, Any]) -> UserModel
```

Convert a user dictionary to `UserModel` instance.

**Parameters:**

- `user_dict` (dict): Raw user data from API

**Returns:** `UserModel` instance

##### Authenticated User Info

###### get_authed_user

```python
async get_authed_user() -> UserModel
```

Get the authenticated user's profile.

**Returns:** Authenticated `UserModel`

**Example:**

```python
me = await auth_model.get_authed_user()
print(f"Logged in as: {me.username}")
print(f"Balance: ${me.balance}")
```

###### get_id

```python
async get_id() -> int
```

Get the authenticated user's ID.

**Returns:** User ID

###### get_username

```python
async get_username() -> str
```

Get the authenticated user's username.

**Returns:** Username string

##### Subscriptions

###### get_subscriptions

```python
async get_subscriptions(
    identifiers: list[int | str] = [],
    limit: int | None = None,
    sub_type: SubscriptionType = SubscriptionTypeEnum.ALL,
    filter_by: str = "",
    job_id: str | None = None,
) -> list[SubscriptionModel]
```

Get subscriptions for the authenticated account.

**Parameters:**

- `identifiers` (list): Filter by specific user IDs or usernames
- `limit` (int | None): Maximum number of results (defaults to all available)
- `sub_type` (SubscriptionType): Subscription type to retrieve
- `filter_by` (str): Optional API filter value
- `job_id` (str | None): Optional job ID surfaced in progress events

**Returns:** List of `SubscriptionModel` instances

**Example:**

```python
# Get all active subscriptions
subs = await auth_model.get_subscriptions()
for sub in subs:
    print(f"Subscribed to: {sub.user.username}")

# Filter by subscription type/filter when needed
filtered = await auth_model.get_subscriptions(filter_by="expired")
```

###### get_subscription_count

```python
async get_subscription_count() -> SubscriptionCountModel
```

Get subscription counts grouped by type/status.

**Returns:** `SubscriptionCountModel`

##### Lists and Organization

###### get_lists

```python
async get_lists(
    refresh: bool = True,
    limit: int = 100,
    offset: int = 0
) -> list[dict[str, Any]]
```

Get user's custom lists.

**Parameters:**

- `refresh` (bool): Force refresh from API
- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:** List of list dictionaries

###### get_vault_lists

```python
async get_vault_lists(
    limit: int = 100,
    offset: int = 0
) -> list[dict[str, Any]]
```

Get vault lists (collections).

**Parameters:**

- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:** List of vault list dictionaries

###### get_blacklist

```python
async get_blacklist(local_blacklists: list[str] = []) -> list[str]
```

Get blocked users.

**Parameters:**

- `local_blacklists` (list): Additional local blacklist entries

**Returns:** List of blocked usernames

##### Messaging

###### get_chats

```python
async get_chats(
    limit: int = 100,
    offset: int = 0,
    refresh: bool = True
) -> list[ChatModel]
```

Get chat conversations.

**Parameters:**

- `limit` (int): Maximum results
- `offset` (int): Pagination offset
- `refresh` (bool): Force refresh from API

**Returns:** List of `ChatModel` instances

###### send_message

```python
async send_message(
    to_user_id: int,
    text: str = "",
    *,
    lockedText: bool | None = None,
    mediaFiles: list[dict[str, Any]] | None = None,
    price: float | None = None,
    previews: list[dict[str, Any]] | None = None,
    rfTag: list[Any] | None = None,
    rfGuest: list[Any] | None = None,
    rfPartner: list[Any] | None = None,
    isForward: bool | None = None,
) -> dict[str, Any]
```

Send a message to a user's chat with full OnlyFans payload support. Backward compatible: can be called with just `(to_user_id, text)`.

**Parameters:**

- `to_user_id` (int): Recipient user ID
- `text` (str): Message text
- `lockedText` (bool, optional): Whether the message text is locked behind a price
- `mediaFiles` (list[dict], optional): Media file payloads to attach
- `price` (float, optional): Price for paid messages
- `previews` (list[dict], optional): Preview media payloads
- `rfTag` / `rfGuest` / `rfPartner` (list, optional): Referral metadata fields
- `isForward` (bool, optional): Mark message as forwarded

**Returns:** Raw API response dict

**Example:**

```python
user = await auth_model.get_user("username")
response = await auth_model.send_message(user.id, "Hello!")
print(f"Message sent: {response.get('id')}")
```

###### message_create

```python
async message_create(
    to_user_id: int,
    text: str = "",
    **kwargs: Any,
) -> dict[str, Any]
```

Alias for `send_message` retained for older call sites; forwards extra payload fields.

###### search_chats

```python
async search_chats(
    query: str,
    limit: int = 100,
    offset: int = 0
) -> list[ChatModel]
```

Search chats by free-text query (added in 3.0.0b4).

**Parameters:**

- `query` (str): Search query
- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:** List of `ChatModel` instances matching the query

**Example:**

```python
chats = await auth_model.search_chats("happy birthday")
for chat in chats:
    print(f"{chat.user.username}")
```

##### Paid Content & Transactions

###### get_paid_content

```python
async get_paid_content(
    performer_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[MessageModel | PostModel]
```

Get all purchased (paid) posts and messages, optionally filtered to a single performer.

**Parameters:**

- `performer_id` (int | None): Filter to a specific performer's content
- `limit` (int | None): Maximum number of items (defaults to all available)
- `offset` (int): Pagination offset

**Returns:** List of paid `MessageModel` and `PostModel` instances

###### get_transactions

```python
async get_transactions(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]
```

Get the authenticated user's payment transaction history.

**Returns:** List of raw transaction dictionaries

##### Moderation Lists

###### blocked_users

```python
async blocked_users(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]
```

Get the authenticated user's list of blocked users.

###### restricted_users

```python
async restricted_users(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]
```

Get the authenticated user's list of restricted users.

##### Account Settings & Verification

###### get_settings

```python
async get_settings() -> SettingsModel
```

Fetch the authenticated user's full settings (notifications, privacy, OTP, payouts, etc.) as a typed `SettingsModel`.

###### notification_settings

```python
async notification_settings() -> dict[str, Any]
```

Fetch granular notification preferences.

###### needs_age_verification

```python
async needs_age_verification() -> bool
```

Returns whether the account needs to complete age verification before accessing NSFW content.

###### get_age_verification

```python
async get_age_verification() -> dict[str, Any]
```

Start or fetch the age verification flow.

###### get_identity_verification

```python
async get_identity_verification() -> dict[str, Any]
```

Start or fetch the identity verification flow (e.g. for becoming a creator or unlocking a locked account).

##### Utility Methods

###### is_authed

```python
is_authed() -> bool
```

Check if authentication is valid.

**Returns:** `True` if authenticated, `False` otherwise

### UserModel

Represents an OnlyFans user/performer profile with full access to their content.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.user_model`

#### Attributes

```python
# Basic Information
user.id: int                          # Unique user ID
user.username: str                    # Username (@handle)
user.name: str                        # Display name
user.avatar: str | None               # Avatar image URL
user.avatar_thumbs: list[str] | None  # Avatar thumbnail URLs
user.header: str | None               # Header banner image URL
user.header_thumbs: list[str] | None  # Header thumbnail URLs

# Profile Details
user.about: str | None                # Bio/description
user.location: str | None             # Location string
user.website: str | None              # Website URL
user.join_date: str | None            # Account creation date (ISO format)
user.is_verified: bool | None         # Verified account status
user.balance: float                   # Account balance (for authenticated user)

# Content Statistics
user.subscribers_count: int | None    # Number of subscribers
user.photos_count: int | None         # Total photos
user.videos_count: int | None         # Total videos
user.audios_count: int | None         # Total audio files
user.medias_count: int | None         # Total media count
user.posts_count: int | None          # Number of posts
user.archived_posts_count: int | None # Archived posts count

# Tipping Configuration
user.tips_enabled: bool               # Whether tips are enabled
user.tips_text_enabled: bool          # Text message tips enabled
user.tips_min: int                    # Minimum tip amount (cents)
user.tips_max: int                    # Maximum tip amount (cents)

# Performer Information
user.is_performer: bool               # Is a content creator
user.is_real_performer: bool          # Real performer verification
user.can_chat: bool                   # Can receive chat messages
user.call_price: int                  # Video call price (cents)
user.subscription_price: float | None # Monthly subscription price

# Relationship Status
user.subscribed_by: bool              # Authed user is subscribed to them
user.subscribed_on: bool              # They are subscribed to authed user
user.subscribed_by_data: dict | None  # Subscription metadata
user.subscribed_on_data: dict | None  # Reverse subscription metadata
user.subscribed_by_expire: str | None # Subscription expiration date
user.subscribed_is_expired_now: bool  # Whether subscription is expired

# Feature Flags
user.has_stories: bool                # Has active stories
user.has_stream: bool                 # Has live streams
user.has_pinned_posts: bool           # Has pinned posts
user.can_receive_chat_message: bool   # Can receive messages
user.is_blocked: bool | None          # Is blocked by authed user
user.can_look_story: bool             # Can view stories
```

#### Methods

##### Content Retrieval

###### get_posts

```python
async get_posts(
    label: Literal["archived", "private_archived"] | str = "",
    limit: int | None = None,
    before_date: datetime | float | None = None,
    after_date: datetime | float | None = None,
    on_progress: ScrapeProgressCallback | None = None,
    job_id: str | None = None,
) -> list[PostModel]
```

Get user's posts with pagination, label filtering, date filtering, and optional progress callbacks.

**Parameters:**

- `label` (str): `""` for default feed, `"archived"`, `"private_archived"`, or any custom label slug
- `limit` (int | None): Maximum number of posts (defaults to the user's full post count)
- `before_date` / `after_date` (datetime | float | None): Filter posts before/after a publish time
- `on_progress` (callable, optional): Async callback `(completed_pages, total_pages, items_so_far)` invoked per page
- `job_id` (str | None): Optional job identifier surfaced in published `scrape_progress` Redis events (defaults to `"api"`)

**Returns:** List of `PostModel` instances

**Example:**

```python
async def progress(done, total, items):
    print(f"Posts: page {done}/{total} — {items} fetched")

posts = await user.get_posts(limit=200, on_progress=progress)
```

###### get_archived_posts

Archived posts are fetched through `get_posts` using the `label` parameter:

```python
archived = await user.get_posts(label="archived")
private_archived = await user.get_posts(label="private_archived")  # authed user only
```

###### get_post

```python
async get_post(
    identifier: int | str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> PostModel
```

Fetch a single post by ID. If `identifier` is omitted, the user's own ID is used.

###### get_stories

```python
async get_stories(
    limit: int = 100,
    offset: int = 0,
    on_progress: ScrapeProgressCallback | None = None,
    job_id: str | None = None,
) -> list[StoryModel]
```

Get user's active stories. Supports the same `on_progress` / `job_id` callback contract as `get_posts`.

**Example:**

```python
stories = await user.get_stories()
for story in stories:
    print(f"Story {story.id} - Expires: {story.expires_at}")
```

###### get_archived_stories

```python
async get_archived_stories(
    limit: int = 100,
    offset: int = 0
) -> list[StoryModel]
```

Get user's archived stories.

**Parameters:**

- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:** List of archived `StoryModel` instances

###### get_highlights

```python
async get_highlights(
    identifier: int | str = "",
    limit: int = 100,
    offset: int = 0
) -> list[HighlightModel] | HighlightModel | None
```

Get user's story highlights.

**Parameters:**

- `identifier` (int | str): Specific highlight ID (returns single highlight)
- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:** List of highlights, single highlight, or None

###### get_messages

```python
async get_messages(
    limit: int = 20,
    offset_id: int | None = None,
    cutoff_id: int | None = None,
    on_progress: ScrapeProgressCallback | None = None,
    job_id: str | None = None,
) -> list[MessageModel]
```

Get the chat history with this user.

**Parameters:**

- `limit` (int): Page size for each request
- `offset_id` (int | None): Start pagination from a specific message ID
- `cutoff_id` (int | None): Stop pagination once this message ID is encountered
- `on_progress` / `job_id`: Progress reporting (see `get_posts`)

**Returns:** List of `MessageModel` instances

###### get_mass_messages

```python
async get_mass_messages(
    message_cutoff_id: int | None = None,
) -> list[MassMessageModel]
```

Return mass-message instances detected within this user's message history and paid content.

###### get_paid_contents

```python
async get_paid_contents(
    content_type: str | None = None,
) -> list[MessageModel | PostModel]
```

Get paid content purchased from this performer. Pass `"message"` or `"post"` to filter.

###### block / unblock

```python
async block() -> dict[str, Any]
async unblock() -> dict[str, Any]
```

Block or unblock this user.

##### Utility Methods

###### get_username

```python
get_username() -> str
```

Get the user's username.

**Returns:** Username string

###### get_link

```python
get_link(use_username: bool = False) -> str
```

Get the user's profile URL.

**Parameters:**

- `use_username` (bool): Use username instead of ID in URL

**Returns:** Profile URL string

**Example:**

```python
url = user.get_link(use_username=True)
print(f"Profile: {url}")  # https://onlyfans.com/username
```

###### is_authed_user

```python
is_authed_user() -> bool
```

Check if this user is the authenticated user.

**Returns:** `True` if this is the authenticated user, `False` otherwise

###### get_authed

```python
get_authed() -> OnlyFansAuthModel
```

Get the associated authenticated session.

**Returns:** `OnlyFansAuthModel` instance

###### get_api

```python
get_api() -> OnlyFansAPI
```

Get the associated API instance.

**Returns:** `OnlyFansAPI` instance

---

## Content Models

### PostModel

Represents a post on OnlyFans with text, media, and metadata.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.post_model`

#### Attributes

```python
post.id: int                          # Post ID
post.responseType: str                # API response type (usually "post")
post.text: str                        # Post text content
post.rawText: str                     # Raw text content
post.price: float | None              # Post price (None/0 for free)
post.isArchived: bool                 # Whether post is archived
post.created_at: datetime             # Creation timestamp
post.expiredAt: Any | None            # Expiration timestamp
post.media: list[MediaModel]          # Attached media files
post.media_count: int                 # Number of media files
post.previews: list[int]              # Preview media IDs
post.author: UserModel                # Post author
post.canViewMedia: bool               # Whether user can view media
post.isOpened: bool                   # Whether user has opened
post.isPinned: bool                   # Whether post is pinned
post.favoritesCount: int              # Number of favorites
post.commentsCount: int               # Number of comments
post.canPurchase: bool                # Whether the post can be purchased
post.promotionContent: list[PromotionContentModel]  # Promotion/tracking metadata
```

#### Methods

```python
post.get_author() -> UserModel        # Get post author
post.is_bought() -> bool              # True if the post has been purchased
                                      # (or is free) based on media visibility/price
```

`PostModel` also exposes `promotionContent`, a list of `PromotionContentModel` values for promotion/tracking metadata.

**Example:**

```python
posts = await user.get_posts(limit=10)
for post in posts:
    print(f"Post {post.id}: {post.text}")
    if post.price:
        print(f"  Price: ${post.price}")
    for media in post.media:
        print(f"  Media: {media.id} ({media.type})")
```

---

### MessageModel

Represents a direct message.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.message_model`

#### Attributes

```python
message.id: int                       # Message ID
message.text: str | None              # Message text
message.price: int | None             # Message price (for paid content)
message.get_author() -> UserModel     # Sender
message.get_receiver() -> UserModel   # Receiver
message.created_at: datetime          # Creation timestamp
message.media: list[MediaModel]       # Attached media
message.isOpened: bool | None         # Whether opened by receiver
message.isFree: bool | None           # Whether message is free
message.canPurchase: bool | None      # Whether can be purchased
message.isTip: bool | None            # Whether message is a tip
message.isLiked: bool | None          # Whether message is liked
```

**Example:**

```python
messages = await user.get_messages(limit=20)
for msg in messages:
    print(f"{msg.get_author().username}: {msg.text}")
    if msg.media:
        print(f"  {len(msg.media)} media attached")
```

#### Methods

```python
message.is_bought() -> bool                          # Whether the message has been purchased
message.is_mass_message() -> bool                    # Whether the message is from a mass send
await message.buy_message() -> dict[str, Any]        # Purchase a paid message
await message.like_message() -> dict[str, Any]       # Like / unlike toggle (server toggles state)
```

---

### StoryModel

Represents a story (temporary content).

**Location:** `ultima_scraper_api.apis.onlyfans.classes.story_model`

#### Attributes

```python
story.id: int                         # Story ID
story.user_id: int                    # Story author ID
story.created_at: datetime            # Creation timestamp
story.expires_at: datetime | None     # Expiration timestamp
story.is_ready: bool                  # Whether story is ready to view
story.is_watched: bool                # Whether user has watched
story.media: list[MediaModel]         # Story media
story.author: UserModel               # Story author
story.can_delete: bool                # Whether user can delete
```

**Example:**

```python
stories = await user.get_stories()
for story in stories:
    print(f"Story {story.id} - Expires: {story.expires_at}")
    if not story.is_watched:
        print("  (Unwatched)")
```

---

### MediaModel

Represents a media file (image, video, audio).

**Location:** `ultima_scraper_api.apis.onlyfans.classes.media_model`

#### Attributes

```python
media.id: int                         # Media ID
media.type: str                       # Media type ("photo", "video", "audio", "gif")
media.files: MediaFiles | None        # Full/thumb/preview/DRM file metadata
media.duration: int | None            # Duration in seconds (video/audio)
media.canView: bool                   # Whether user can view
media.hasError: bool                  # Whether media has error
media.videoSources: dict[str, str]    # Video quality options
```

#### Methods

##### has_drm

```python
has_drm() -> bool
```

Return whether the media has DRM metadata. Media downloads are performed by resolving a URL with `url_picker` / `content.url_picker()` and then using the authenticated session.

##### to_dict

```python
to_dict() -> dict[str, Any]
```

Return the raw API dictionary for compatibility with older scripts.

**Example:**

```python
from pathlib import Path
from ultima_scraper_api.apis.onlyfans import url_picker

download_dir = Path("downloads")
download_dir.mkdir(exist_ok=True)

for post in posts:
    for media in post.media:
        if media.canView:
            # Get media URL
            media_url = url_picker(post.get_author(), media)
            
            if media_url:
                # Download content
                response = await authed.auth_session.request(
                    media_url.geturl(),
                    premade_settings=""
                )
                
                if response:
                    content = await response.read()
                    
                    filename = download_dir / f"{media.id}.{media.type}"
                    with open(filename, "wb") as f:
                        f.write(content)
                    print(f"Downloaded: {filename}")
```

---

## Data Classes

### AuthDetails

Authentication credentials data class.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.extras`

#### Attributes

```python
auth_details.id: int = 0              # User ID
auth_details.username: str = ""       # Username
auth_details.cookie: str = ""         # Session cookie string
auth_details.user_agent: str = ""     # Browser user agent
auth_details.x_bc: str = ""           # X-BC authorization token
auth_details.user_id: str = ""        # User ID as string
auth_details.hashed: str = ""         # Hashed password (deprecated)
auth_details.support_2fa: bool = False # 2FA support
auth_details.active: bool = True      # Whether credentials are active
```

#### Methods

##### export

```python
export() -> dict[str, Any]
```

Export credentials as dictionary.

**Returns:** Dictionary with all credential fields

##### upgrade_legacy

```python
@staticmethod
upgrade_legacy(old_auth: dict) -> AuthDetails
```

Upgrade credentials from legacy format.

**Parameters:**

- `old_auth` (dict): Old format credentials

**Returns:** `AuthDetails` instance

**Example:**

```python
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails

# Create from dict
auth_details = AuthDetails(
    cookie="auth_id=123; sess=abc...",
    user_agent="Mozilla/5.0...",
    x_bc="your_token"
)

# Export back to dict
auth_dict = auth_details.export()
```

---

### CookieParser

Helper for parsing and formatting OnlyFans cookies.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.extras`

#### Methods

##### convert

```python
@staticmethod
convert(cookies: str, format: str = "dict") -> dict | str
```

Convert cookie string between formats.

**Parameters:**

- `cookies` (str): Cookie string
- `format` (str): Output format ("dict" or "string")

**Returns:** Parsed cookies as dict or formatted string

**Example:**

```python
from ultima_scraper_api.apis.onlyfans.classes.extras import CookieParser

# Convert to dict
cookies_dict = CookieParser.convert("auth_id=123; sess=abc")
print(cookies_dict)  # {"auth_id": "123", "sess": "abc"}
```

##### format

```python
@staticmethod
format(auth: dict) -> str
```

Format authentication dict as cookie string.

**Parameters:**

- `auth` (dict): Authentication dictionary

**Returns:** Formatted cookie string

---

### ErrorDetails

Error response wrapper.

**Location:** `ultima_scraper_api.apis.onlyfans.classes.extras`

#### Attributes

```python
error.error: dict[str, Any]           # Raw error data
error.message: str                    # Error message text
```

#### Methods

##### format

```python
format() -> str
```

Format error as readable string.

**Returns:** Formatted error message

**Example:**

```python
try:
    user = await auth_model.get_user("invalid")
except Exception as e:
    if hasattr(e, 'format'):
        print(f"Error: {e.format()}")
```

---

## Usage Examples

### Complete Authentication Flow

The recommended way to authenticate is using the `login_context` context manager:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    # Initialize API
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Authentication credentials
    auth_json = {
        "id": 123456,
        "cookie": "auth_id=123456; sess=abc123...",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
        "x-bc": "your-x-bc-token-here"
    }
    
    # Login with context manager
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get authenticated user info
            me = await authed.get_authed_user()
            print(f"Logged in as: {me.username}")
            print(f"Balance: ${me.balance}")
            
            # Get subscriptions
            subscriptions = await authed.get_subscriptions()
            print(f"\nSubscriptions ({len(subscriptions)}):")
            for user in subscriptions:
                print(f"  - {user.username} ({user.name})")

if __name__ == "__main__":
    asyncio.run(main())
```

### Lower-Level Authentication (Advanced)

For more control, use `OnlyFansAuthenticator` directly:

```python
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails

# Initialize API
api = OnlyFansAPI()

# Create auth details
auth_details = AuthDetails(
    cookie="auth_id=123456; sess=abc123...",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    x_bc="your-x-bc-token-here"
)

# Create authenticator
authenticator = OnlyFansAuthenticator(api, auth_details)

# Login
async with authenticator:
    auth_model = await authenticator.login()
    
    me = await auth_model.get_authed_user()
    print(f"Logged in as: {me.username}")
```

### Using cURL Import

Extract credentials from a cURL command copied from browser:

```python
from ultima_scraper_api.apis.onlyfans.authenticator import extract_auth_details_from_curl
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI

# Copy this from browser Network tab
curl_command = """
curl 'https://onlyfans.com/api2/v2/users/me' \\
  -H 'cookie: auth_id=12345; sess=abc...' \\
  -H 'user-agent: Mozilla/5.0...' \\
  -H 'x-bc: token...'
"""

# Extract credentials
auth_details = extract_auth_details_from_curl(curl_command)

# Use credentials
api = OnlyFansAPI()
authenticator = OnlyFansAuthenticator(api, auth_details)
```

### Getting User Content

Fetch posts, stories, messages, and media from users:

```python
async with api.login_context(auth_json) as authed:
    # Get a user by username
    user = await authed.get_user("username")
    if not user:
        print("User not found")
        return
    
    print(f"User: {user.name} (@{user.username})")
    print(f"Posts: {user.posts_count}")
    print(f"Subscribers: {user.subscribers_count}")
    
    # Get their posts
    posts = await user.get_posts(limit=50)
    print(f"\nFetched {len(posts)} posts")
    for post in posts:
        print(f"  Post {post.id}: {post.text[:50]}...")
        if post.media:
            print(f"    Media: {len(post.media)} files")
    
    # Get active stories
    stories = await user.get_stories()
    print(f"\nActive stories: {len(stories)}")
    for story in stories:
        print(f"  Story {story.id} - Expires: {story.expires_at}")
    
    # Get message conversation
    messages = await user.get_messages(limit=20)
    print(f"\nMessages: {len(messages)}")
    for msg in messages:
        sender = msg.get_author().username
        text = msg.text[:30] if msg.text else "[Media only]"
        print(f"  {sender}: {text}")
```

### Downloading Media

Download media files from posts, messages, or stories:

```python
import asyncio
from pathlib import Path
from ultima_scraper_api.apis.onlyfans import url_picker

authed = await onlyfans_api.login(auth_json=auth_json)

if authed and authed.is_authed():
    user = await authed.get_user("username")
    posts = await user.get_posts(limit=10)
    
    # Create download directory
    download_dir = Path("downloads") / user.username
    download_dir.mkdir(parents=True, exist_ok=True)
    
    for post in posts:
        if not post.media:
            continue
        
        print(f"\nPost {post.id}:")
        for media in post.media:
            if not media.canView:
                print(f"  {media.id}.{media.type} - LOCKED")
                continue
            
            try:
                # Get media URL
                media_url = url_picker(post.get_author(), media)
                
                if media_url:
                    # Download media
                    response = await authed.auth_session.request(
                        media_url.geturl(),
                        premade_settings=""
                    )
                    
                    if response:
                        content = await response.read()
                        
                        # Save to file
                        filepath = download_dir / f"{media.id}.{media.type}"
                        with open(filepath, "wb") as f:
                            f.write(content)
                        
                        size_mb = len(content) / (1024 * 1024)
                        print(f"  ✓ {media.id}.{media.type} ({size_mb:.2f} MB)")
                
            except Exception as e:
                print(f"  ✗ {media.id}.{media.type} - Error: {e}")
```

### Batch Processing with Progress Callbacks

Process all content with built-in pagination and optional progress callbacks:

```python
async def fetch_all_posts(user):
    """Fetch all posts from a user with automatic pagination."""
    async def progress(done_pages, total_pages, items_so_far):
        print(f"Fetched page {done_pages}/{total_pages}: {items_so_far} posts")

    return await user.get_posts(on_progress=progress)

async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    all_posts = await fetch_all_posts(user)
    print(f"Total posts: {len(all_posts)}")
```

### Concurrent User Processing

Process multiple users concurrently:

```python
async def process_user(authed, username):
    """Process a single user"""
    user = await authed.get_user(username)
    if not user:
        return {"username": username, "status": "not_found"}
    
    posts = await user.get_posts(limit=10)
    
    return {
        "username": user.username,
        "name": user.name,
        "posts_count": user.posts_count,
        "fetched_posts": len(posts),
        "status": "success"
    }

async with api.login_context(auth_json) as authed:
    usernames = ["user1", "user2", "user3", "user4"]
    
    # Process users concurrently
    tasks = [process_user(authed, username) for username in usernames]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Print results
    for result in results:
        if isinstance(result, Exception):
            print(f"Error: {result}")
        elif result["status"] == "success":
            print(f"{result['username']}: {result['fetched_posts']}/{result['posts_count']} posts")
        else:
            print(f"{result['username']}: Not found")
```

### Working with Subscriptions

Manage and filter subscriptions:

```python
async with api.login_context(auth_json) as authed:
    # Get all active subscriptions
    subs = await authed.get_subscriptions()
    print(f"Active subscriptions: {len(subs)}")
    
    # Filter by criteria
    high_post_count = [u for u in subs if (u.posts_count or 0) > 100]
    print(f"Users with >100 posts: {len(high_post_count)}")
    
    verified_users = [u for u in subs if u.is_verified]
    print(f"Verified users: {len(verified_users)}")
    
    # Get expired subscriptions
    expired = await authed.get_subscriptions(subscription_type="expired")
    print(f"Expired subscriptions: {len(expired)}")
    
    # Get specific users
    specific = await authed.get_subscriptions(
        identifiers=["user1", "user2", "user3"]
    )
    for user in specific:
        print(f"  {user.username}: ${user.subscription_price}/month")
```

### Guest Mode

Access public content without authentication:

```python
async with api.login_context(guest=True) as authed:
    # Limited access to public profiles
    user = await authed.get_user("public_username")
    if user:
        print(f"Public profile: {user.username}")
        print(f"Bio: {user.about}")
        print(f"Subscription: ${user.subscription_price}/month")
```

### Error Handling

Properly handle errors and edge cases:

```python
from aiohttp import ClientError
from ultima_scraper_api.apis.onlyfans import url_picker

authed = await onlyfans_api.login(auth_json=auth_json)

if authed and authed.is_authed():
    try:
        user = await authed.get_user("username")
        if not user:
            print("User not found or inaccessible")
            return
        
        posts = await user.get_posts(limit=10)
        
        for post in posts:
            for media in post.media:
                try:
                    if not media.canView:
                        print(f"Media {media.id} is locked")
                        continue
                    
                    # Get media URL
                    media_url = url_picker(post.get_author(), media)
                    
                    if media_url:
                        response = await authed.auth_session.request(
                            media_url.geturl(),
                            premade_settings=""
                        )
                        
                        if response:
                            content = await response.read()
                            # Process content...
                    
                except ClientError as e:
                    print(f"Download failed for {media.id}: {e}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
    
    except Exception as e:
        print(f"Fatal error: {e}")
```

---

## Helper Functions and Utilities

### URL Formatting

Format API URLs with query parameters:

```python
from ultima_scraper_api.apis.onlyfans.classes.extras import format_url

# Format URL with query params
url = format_url(
    "/api2/v2/users/123/posts",
    {"limit": 10, "offset": 0, "order": "recent"}
)
print(url)  # /api2/v2/users/123/posts?limit=10&offset=0&order=recent
```

### API Endpoints

Access OnlyFans API endpoint patterns:

```python
from ultima_scraper_api.apis.onlyfans.classes.extras import endpoint_links

links = endpoint_links()

# Access endpoint templates
print(links.users)       # User-related endpoints
print(links.posts)       # Post-related endpoints
print(links.messages)    # Message-related endpoints
print(links.stories)     # Story-related endpoints
```

### Subscription Types

Use subscription type enums for filtering:

```python
from ultima_scraper_api.apis.onlyfans import SubscriptionTypeEnum

# Get different subscription types
active_subs = await authed.get_subscriptions(
    subscription_type=SubscriptionTypeEnum.ACTIVE
)

expired_subs = await authed.get_subscriptions(
    subscription_type=SubscriptionTypeEnum.EXPIRED
)

all_subs = await authed.get_subscriptions(
    subscription_type=SubscriptionTypeEnum.ALL
)
```

---

## Error Handling and Exceptions

Common errors and how to handle them:

### Authentication Errors

```python
try:
    async with api.login_context(auth_json) as authed:
        if not authed or not authed.is_authed():
            print("Authentication failed - check credentials")
            print("- Verify cookie is valid and not expired")
            print("- Check x-bc token is current")
            print("- Ensure user-agent matches browser")
except Exception as e:
    print(f"Login error: {e}")
```

### Rate Limiting

```python
from asyncio import sleep

async def fetch_with_rate_limit(user, limit=100):
    """Fetch content with rate limiting"""
    async def progress(done_pages, total_pages, items_so_far):
        await sleep(1.0)

    return await user.get_posts(limit=limit, on_progress=progress)
```

### Network Errors

```python
from aiohttp import ClientError, ServerTimeoutError

try:
    user = await authed.get_user("username")
except ServerTimeoutError:
    print("Request timed out - server may be slow")
except ClientError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## See Also

- **[Authentication Guide](../user-guide/authentication.md)** - How to obtain credentials
- **[Working with APIs](../user-guide/working-with-apis.md)** - Common patterns and best practices
- **[Configuration](../getting-started/configuration.md)** - Configure proxies, Redis, and settings
- **[Fansly API Reference](fansly.md)** - Similar API for Fansly platform
- **[LoyalFans API Reference](loyalfans.md)** - Similar API for LoyalFans platform
- **[Helpers Reference](helpers.md)** - Utility functions and helpers
