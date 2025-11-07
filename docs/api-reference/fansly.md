# Fansly API Reference

Complete reference for the Fansly API implementation in UltimaScraperAPI.

!!! warning "Work in Progress"
    The Fansly API implementation is currently under active development. While core functionality is stable, some advanced features are still being implemented. See [Current Limitations](#current-limitations) for details.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [FanslyAPI Class](#fanslyapi-class)
- [FanslyAuthModel Class](#fanslyauthmodel-class)
- [User Operations](#user-operations)
- [User Class](#user-class)
- [Post Class](#post-class)
- [Attachment Class](#attachment-class)
- [Message Class](#message-class)
- [Current Limitations](#current-limitations)
- [Complete Examples](#complete-examples)
- [Migration from OnlyFans](#migration-from-onlyfans)

---

## Overview

The Fansly API provides programmatic access to Fansly platform features through an async Python interface. The implementation follows similar patterns to the OnlyFans API while accommodating Fansly-specific features.

### Key Features

| Feature | Status | Notes |
|---------|--------|-------|
| **Authentication** | ✅ Stable | Cookie-based auth |
| **User Profiles** | ✅ Stable | Full profile access |
| **Posts** | ✅ Stable | Timeline, archived, pinned |
| **Messages** | ✅ Stable | DMs and mass messages |
| **Stories** | ✅ Stable | Stories and highlights |
| **Media Download** | ✅ Stable | Photos and videos |
| **Subscriptions** | ✅ Stable | Active and expired |
| **Collections** | 🟡 Partial | Basic support |
| **Live Streams** | ❌ Planned | Not yet implemented |
| **Vault Content** | ❌ Planned | Not yet implemented |
| **WebSocket** | ❌ Planned | Real-time notifications |

---

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install ultima-scraper-api

# Using pip
pip install ultima-scraper-api
```

### Basic Usage

```python
import asyncio
from ultima_scraper_api import UltimaScraperAPI

async def main():
    # Initialize API
    api = UltimaScraperAPI()
    fansly = api.get_site_api("fansly")
    
    # Authentication credentials
    auth_json = {
        "cookie": "your_auth_cookie_here",
        "user_agent": "Mozilla/5.0 ...",
        "x-bc": "your_token_here"
    }
    
    # Login and fetch user
    async with fansly.login_context(auth_json) as authed:
        # Get authenticated user info
        me = await authed.get_authed_user()
        print(f"Logged in as: {me.username}")
        
        # Fetch another user
        user = await authed.get_user("username")
        if user:
            print(f"User ID: {user.id}")
            print(f"Subscribers: {user.subscribers_count}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Authentication

### Obtaining Credentials

To use the Fansly API, you need authentication credentials from your browser session:

1. **Cookie**: Session authentication cookie
2. **User-Agent**: Browser user agent string
3. **X-BC**: Bearer token (Fansly-specific)

See the [Authentication Guide](../user-guide/authentication.md#fansly) for detailed instructions.

### login_context

Async context manager for authenticated sessions (recommended).

```python
async with fansly.login_context(auth_json) as authed:
    # All operations here are authenticated
    me = await authed.get_authed_user()
    # Session automatically closes on exit
```

**Parameters:**

- `auth_json` (dict): Authentication credentials
  - `cookie` (str): Session cookie
  - `user_agent` (str): Browser user agent
  - `x-bc` (str): Bearer token
  - `id` (int, optional): User ID (for cached sessions)
- `guest` (bool, optional): Use guest mode. Default: `False`

**Returns:**

- `FanslyAuthModel`: Authenticated session object

**Example:**

```python
auth_json = {
    "cookie": "auth_id=xxxx; sess=yyyy",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "x-bc": "your_bearer_token"
}

async with fansly.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        print("Authentication successful!")
        me = await authed.get_authed_user()
        print(f"Welcome, {me.username}!")
    else:
        print("Authentication failed")
```

### login

Direct login method (returns auth object).

```python
authed = await fansly.login(auth_json, guest=False)

if authed and authed.is_authed():
    # Use authed session
    me = await authed.get_authed_user()
    
    # Remember to close when done
    await fansly.remove_auth(authed)
```

**Parameters:**

- `auth_json` (dict): Authentication credentials
- `guest` (bool, optional): Use guest mode. Default: `False`

**Returns:**

- `FanslyAuthModel | None`: Authenticated session or None on failure

---

## FanslyAPI Class

Main API class for Fansly operations.

### Initialization

```python
from ultima_scraper_api import UltimaScraperAPI, UltimaScraperAPIConfig

# Method 1: Through UltimaScraperAPI
api = UltimaScraperAPI()
fansly = api.get_site_api("fansly")

# Method 2: Direct initialization
from ultima_scraper_api.apis.fansly import FanslyAPI

config = UltimaScraperAPIConfig()
fansly = FanslyAPI(config)
```

### Methods

#### find_auth

Find an authenticated session by user ID.

```python
authed = fansly.find_auth(user_id)
```

**Parameters:**

- `identifier` (int): User ID

**Returns:**

- `FanslyAuthModel | None`: Auth session if found

#### find_user

Find a user across all authenticated sessions.

```python
users = fansly.find_user("username")
# or
users = fansly.find_user(12345)
```

**Parameters:**

- `identifier` (int | str): User ID or username

**Returns:**

- `list[UserModel]`: List of matching users

---

## FanslyAuthModel Class

Represents an authenticated session with access to account operations.

### Attributes

```python
authed.id                    # int: Authenticated user ID
authed.username              # str: Authenticated username
authed.user                  # UserModel: User object
authed.subscriptions         # list[SubscriptionModel]: Active subscriptions
authed.followed_users        # list[UserModel]: Followed users
authed.paid_content          # list[MessageModel | PostModel]: Purchased content
authed.guest                 # bool: Guest mode flag
```

### Methods

#### get_authed_user

Get the authenticated user's profile.

```python
me = await authed.get_authed_user()
print(f"Username: {me.username}")
print(f"Credit Balance: ${me.credit_balance}")
```

**Returns:**

- `UserModel`: Authenticated user object

## User Operations

### get_me

Get information about the currently authenticated user.

```python
async with api.login_context(auth_json) as authed:
    me = await authed.get_me()
    print(f"Username: {me.username}")
```

**Returns:**
- `User`: Current user object

### get_user

Get information about a specific user.

```python
user = await authed.get_user("username")
```

**Parameters:**
- `username` (str): Username or user ID

**Returns:**
- `User | None`: User object or None if not found

## User Class

### Attributes

- `id` (str): User ID
- `username` (str): Username
- `display_name` (str): Display name
- `avatar` (str): Avatar URL
- `banner` (str): Banner image URL
- `bio` (str): Biography/description

### Methods

#### get_posts

Fetch user's posts.

```python
posts = await user.get_posts(limit=50, offset=0)
```

**Parameters:**
- `limit` (int, optional): Maximum posts to fetch. Default: 50
- `offset` (int, optional): Pagination offset. Default: 0

**Returns:**
- `list[Post]`: List of post objects

#### get_messages

Fetch messages with the user.

```python
messages = await user.get_messages(limit=100)
```

**Parameters:**
- `limit` (int, optional): Maximum messages to fetch

**Returns:**
- `list[Message]`: List of message objects

## Post Class

### Attributes

- `id` (str): Post ID
- `content` (str): Post content/text
- `attachments` (list[Attachment]): List of media attachments
- `created_at` (datetime): Creation timestamp

## Attachment Class

### Attributes

- `id` (str): Attachment ID
- `type` (str): Attachment type ("photo", "video")
- `url` (str): Attachment URL
- `preview_url` (str): Preview URL

### Methods

#### download

Download the attachment.

```python
content = await attachment.download()
```

**Returns:**
- `bytes`: Attachment content

## Message Class

### Attributes

- `id` (str): Message ID
- `content` (str): Message text
- `created_at` (datetime): Timestamp
- `from_user` (User): Sender
- `attachments` (list[Attachment]): Attached media

## Current Limitations

### ✅ Implemented Features

- ✅ Cookie-based authentication
- ✅ User profile access
- ✅ Timeline posts (free and paid)
- ✅ Archived posts
- ✅ Direct messages
- ✅ Stories and highlights
- ✅ Media downloads
- ✅ Subscriptions list
- ✅ Collections (basic)
- ✅ Favorites/likes

### 🟡 Partial Implementation

- 🟡 **Collections**: Basic support only, advanced features pending
- 🟡 **Search**: Limited search capabilities
- 🟡 **Notifications**: Read-only access

### ❌ Not Yet Implemented

- ❌ **Live Streams**: Live stream access not implemented
- ❌ **Vault Content**: Vault content access pending
- ❌ **WebSocket**: Real-time notifications not available
- ❌ **Payments**: Cannot initiate payments through API
- ❌ **Posting**: Cannot create new posts/messages
- ❌ **Account Settings**: Cannot modify account settings

### Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Story quality selection | Investigating | Downloads highest available |
| Collection pagination | In Progress | Fetch all at once |
| Mass message filtering | Known | Manual filtering required |

### Planned Features

- [ ] Live stream access
- [ ] Vault content support
- [ ] WebSocket for real-time updates
- [ ] Enhanced search functionality
- [ ] Comment posting
- [ ] Improved collection management

---

## Complete Examples

### Example 1: Profile Summary

```python
import asyncio
from ultima_scraper_api import UltimaScraperAPI

async def profile_summary(username: str):
    """Generate profile summary for a creator."""
    api = UltimaScraperAPI()
    fansly = api.get_site_api("fansly")
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_token"
    }
    
    async with fansly.login_context(auth_json) as authed:
        user = await authed.get_user(username)
        
        if not user:
            print(f"User '{username}' not found")
            return
        
        print(f"\n{'='*50}")
        print(f"Profile: {user.username}")
        print(f"{'='*50}")
        print(f"Display Name: {user.name}")
        print(f"Verified: {'✓' if user.is_verified else '✗'}")
        print(f"Subscribers: {user.subscribers_count:,}")
        print(f"\nContent Statistics:")
        print(f"  Posts: {user.posts_count:,}")
        print(f"  Photos: {user.photos_count:,}")
        print(f"  Videos: {user.videos_count:,}")
        print(f"\nSubscription:")
        print(f"  Price: ${user.subscribe_price / 100:.2f}/month")
        print(f"  Subscribed: {'Yes' if user.subscribed else 'No'}")
        print(f"\nFeatures:")
        print(f"  Stories: {'✓' if user.has_stories else '✗'}")
        print(f"  Streaming: {'✓' if user.has_stream else '✗'}")
        print(f"  Tips: {'✓' if user.tips_enabled else '✗'}")
        if user.tips_enabled:
            print(f"    Min: ${user.tips_min / 100:.2f}")
            print(f"    Max: ${user.tips_max / 100:.2f}")

if __name__ == "__main__":
    asyncio.run(profile_summary("example_creator"))
```

### Example 2: Content Downloader

```python
import asyncio
import aiohttp
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPI

async def download_user_content(username: str, max_posts: int = 50):
    """Download posts from a user."""
    api = UltimaScraperAPI()
    fansly = api.get_site_api("fansly")
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_token"
    }
    
    async with fansly.login_context(auth_json) as authed:
        user = await authed.get_user(username)
        
        if not user:
            print(f"User not found: {username}")
            return
        
        print(f"Fetching posts from {user.username}...")
        posts = await user.get_posts(limit=max_posts)
        print(f"Found {len(posts)} posts")
        
        download_dir = Path(f"downloads/{username}")
        download_dir.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            for i, post in enumerate(posts, 1):
                print(f"\n[{i}/{len(posts)}] Post {post.id}")
                
                if post.is_paid and not post.is_opened:
                    print("  ⚠ Paid content (not purchased)")
                    continue
                
                for j, attachment in enumerate(post.attachments):
                    if not attachment.get("locations"):
                        continue
                    
                    url = attachment["locations"][0]["location"]
                    ext = attachment["mimetype"].split("/")[-1]
                    filename = f"post_{post.id}_{j}.{ext}"
                    filepath = download_dir / filename
                    
                    if filepath.exists():
                        print(f"  ✓ Skip {filename} (exists)")
                        continue
                    
                    print(f"  ⬇ Download {filename}")
                    
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                with open(filepath, 'wb') as f:
                                    f.write(await response.read())
                                print(f"  ✓ Saved {filename}")
                            else:
                                print(f"  ✗ Failed {filename} ({response.status})")
                    except Exception as e:
                        print(f"  ✗ Error {filename}: {e}")
        
        print(f"\n✅ Download complete: {download_dir}")

if __name__ == "__main__":
    asyncio.run(download_user_content("example_creator", max_posts=20))
```

### Example 3: Subscription Manager

```python
import asyncio
from datetime import datetime
from ultima_scraper_api import UltimaScraperAPI

async def manage_subscriptions():
    """List and manage subscriptions."""
    api = UltimaScraperAPI()
    fansly = api.get_site_api("fansly")
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_token"
    }
    
    async with fansly.login_context(auth_json) as authed:
        me = await authed.get_authed_user()
        print(f"Logged in as: {me.username}")
        print(f"Credit Balance: ${me.credit_balance:.2f}\n")
        
        # Get active subscriptions
        subs = await authed.get_subscriptions(sub_type="active")
        
        print(f"Active Subscriptions: {len(subs)}")
        print("=" * 70)
        
        total_cost = 0
        
        for sub in sorted(subs, key=lambda x: x.subscribe_price, reverse=True):
            user = sub.user
            price = sub.subscribe_price / 100
            total_cost += price
            
            print(f"\n{user.username}")
            print(f"  Price: ${price:.2f}/month")
            print(f"  Posts: {user.posts_count:,}")
            print(f"  Subscribed: {sub.subscribed_at}")
            
            if user.has_stories:
                print(f"  ✓ Has stories")
            if user.has_stream:
                print(f"  ✓ Currently streaming")
        
        print(f"\n{'='*70}")
        print(f"Total Monthly Cost: ${total_cost:.2f}")
        print(f"Average per Creator: ${total_cost / len(subs):.2f}")

if __name__ == "__main__":
    asyncio.run(manage_subscriptions())
```

### Example 4: Story Viewer

```python
import asyncio
from ultima_scraper_api import UltimaScraperAPI

async def view_stories():
    """View active stories from subscriptions."""
    api = UltimaScraperAPI()
    fansly = api.get_site_api("fansly")
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_token"
    }
    
    async with fansly.login_context(auth_json) as authed:
        subs = await authed.get_subscriptions(sub_type="active")
        
        print(f"Checking stories for {len(subs)} subscriptions...\n")
        
        story_count = 0
        
        for sub in subs:
            user = sub.user
            
            if not user.has_stories:
                continue
            
            stories = await user.get_stories()
            
            if not stories:
                continue
            
            print(f"\n{user.username} - {len(stories)} stories")
            print("-" * 50)
            
            for story in stories:
                story_count += 1
                
                print(f"  Story {story.id}")
                print(f"    Created: {story.created_at}")
                print(f"    Expires: {story.expired_at}")
                print(f"    Media: {len(story.attachments)} items")
                print(f"    Watched: {'Yes' if story.is_watched else 'No'}")
        
        print(f"\n✅ Total stories: {story_count}")

if __name__ == "__main__":
    asyncio.run(view_stories())
```

---

## Migration from OnlyFans

If you're familiar with the OnlyFans API, here are key differences:

### Similarities

| Feature | OnlyFans | Fansly | Notes |
|---------|----------|--------|-------|
| Authentication | Cookie-based | Cookie-based | Same pattern |
| Context Manager | ✅ | ✅ | `login_context()` |
| User Model | ✅ | ✅ | Similar attributes |
| Posts/Messages | ✅ | ✅ | Same structure |
| Async/Await | ✅ | ✅ | Full async support |

### Key Differences

```python
# OnlyFans
auth_json = {
    "cookie": "auth_id=xxx; sess=yyy",
    "user_agent": "Mozilla/5.0 ...",
    "x-bc": "token"
}

# Fansly - Similar but check platform docs
auth_json = {
    "cookie": "auth_id=xxx; sess=yyy",
    "user_agent": "Mozilla/5.0 ...",
    "x-bc": "token"  # Fansly-specific token
}

# API endpoints are different internally
# but the interface is consistent
```

### API Parity

Most OnlyFans methods have Fansly equivalents:

```python
# Both platforms support:
await authed.get_user(username)
await user.get_posts(limit=50)
await user.get_messages(limit=100)
await user.get_stories()
await post.favorite()

# Check documentation for platform-specific features
```

---

## See Also

### Internal Documentation
- **[Quick Start Guide](../getting-started/quick-start.md#fansly)** - Getting started with Fansly
- **[Authentication Guide](../user-guide/authentication.md#fansly)** - Obtaining credentials
- **[Working with APIs](../user-guide/working-with-apis.md)** - Common patterns
- **[OnlyFans API Reference](onlyfans.md)** - Similar API for comparison
- **[Troubleshooting](../user-guide/troubleshooting.md)** - Common issues

### External Resources
- **[Fansly Official Site](https://fansly.com/)** - Platform website
- **[Fansly Help Center](https://help.fansly.com/)** - Official support

### Development
- **[Contributing](../development/contributing.md)** - Contribute to Fansly API development
- **[Architecture](../development/architecture.md)** - System design
- **[Testing](../development/testing.md)** - Testing guide
