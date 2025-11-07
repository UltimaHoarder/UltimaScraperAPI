# LoyalFans API Reference

Complete reference for the LoyalFans API implementation in UltimaScraperAPI.

!!! warning "Early Development - Limited Functionality"
    The LoyalFans API implementation is in **early development stages**. Basic authentication and profile access are functional, but most content features are still being implemented. This platform is currently **not recommended for production use**. See [Implementation Status](#implementation-status) for details.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Implementation Status](#implementation-status)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [LoyalFansAPI Class](#loyalfansapi-class)
- [LoyalFansAuthModel Class](#loyalfansauthmodel-class)
- [UserModel Class](#usermodel-class)
- [Planned Features](#planned-features)
- [Contributing](#contributing)
- [Migration Guide](#migration-guide)

---

## Overview

The LoyalFans API provides programmatic access to LoyalFans platform features through an async Python interface. The implementation follows similar patterns to OnlyFans and Fansly APIs but is currently in early development stages.

### Why LoyalFans Support?

LoyalFans is a growing creator platform with unique features. UltimaScraperAPI aims to provide consistent API access across multiple platforms, and LoyalFans support is actively being developed.

### Current Capabilities

| Feature | Status | Notes |
|---------|--------|-------|
| **Authentication** | 🟡 Partial | Basic auth working |
| **User Profiles** | 🟡 Partial | Limited data available |
| **Posts** | ❌ Planned | Not yet implemented |
| **Messages** | ❌ Planned | Not yet implemented |
| **Stories** | ❌ Planned | Not yet implemented |
| **Media Download** | ❌ Planned | Not yet implemented |
| **Subscriptions** | ❌ Planned | Not yet implemented |
| **Live Streams** | ❌ Planned | Not yet implemented |
| **WebSocket** | ❌ Planned | Not yet implemented |

---

## Implementation Status

### ✅ Implemented (Basic)

- ✅ API initialization
- ✅ Authentication structure (cookie-based)
- ✅ Context manager pattern
- ✅ Basic user profile access

### 🟡 Partial Implementation

- 🟡 **Authentication**: Basic structure exists but needs validation
- 🟡 **User Profiles**: Can fetch basic user data, but many fields may be missing
- 🟡 **Session Management**: Basic session handling implemented

### ❌ Not Yet Implemented

- ❌ **Posts/Timeline**: Cannot fetch posts yet
- ❌ **Messages/DMs**: Direct messages not available
- ❌ **Stories**: Story features not implemented
- ❌ **Media Downloads**: No download functionality
- ❌ **Subscriptions**: Cannot manage subscriptions
- ❌ **Search**: No search capabilities
- ❌ **Payments**: No payment features
- ❌ **Comments**: Comment system not implemented
- ❌ **Notifications**: No notification support
- ❌ **WebSocket**: No real-time features

### Known Limitations

!!! danger "Production Use Not Recommended"
    - API endpoints may be incomplete or untested
    - Data structures may change as development progresses
    - Error handling is minimal
    - No comprehensive test coverage yet
    - Documentation reflects planned features, not current implementation

---

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install ultima-scraper-api

# Using pip
pip install ultima-scraper-api
```

### Basic Usage (Experimental)

```python
import asyncio
from ultima_scraper_api import UltimaScraperAPI

async def main():
    """Experimental LoyalFans API usage."""
    # Initialize API
    api = UltimaScraperAPI()
    loyalfans = api.get_site_api("loyalfans")
    
    # Authentication credentials
    auth_json = {
        "cookie": "your_auth_cookie_here",
        "user_agent": "Mozilla/5.0 ...",
        "id": your_user_id  # Your LoyalFans user ID
    }
    
    # Login (experimental)
    async with loyalfans.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("Authentication successful!")
            # Note: Most features not yet implemented
        else:
            print("Authentication failed")

if __name__ == "__main__":
    asyncio.run(main())
```

!!! warning "Experimental Code"
    The above code demonstrates the intended API design. Actual functionality is limited in the current implementation.

---

## Authentication

### Obtaining Credentials

To use the LoyalFans API, you need authentication credentials from your browser session:

1. **Cookie**: Session authentication cookie
2. **User-Agent**: Browser user agent string  
3. **User ID**: Your LoyalFans user ID

See the [Authentication Guide](../user-guide/authentication.md#loyalfans) for detailed instructions.

!!! info "Authentication Status"
    Basic authentication structure is implemented but may require refinement. Full validation pending.

### login_context

Async context manager for authenticated sessions (recommended pattern).

```python
async with loyalfans.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        print("Authenticated!")
        # Perform operations (limited in current version)
    else:
        print("Authentication failed")
```

**Parameters:**

- `auth_json` (dict): Authentication credentials
  - `cookie` (str): Session cookie
  - `user_agent` (str): Browser user agent
  - `id` (int): Your user ID
- `guest` (bool, optional): Use guest mode. Default: `False`

**Returns:**

- `LoyalFansAuthModel | None`: Authenticated session or None

**Example:**

```python
auth_json = {
    "cookie": "your_session_cookie",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "id": 12345  # Your user ID
}

async with loyalfans.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        print("Login successful!")
    else:
        print("Login failed")
```

### login

Direct login method (returns auth object).

```python
authed = await loyalfans.login(auth_json, guest=False)

if authed and authed.is_authed():
    print("Authenticated")
    # Remember to close when done
    await loyalfans.remove_auth(authed)
```

**Parameters:**

- `auth_json` (dict): Authentication credentials
- `guest` (bool, optional): Use guest mode. Default: `False`

**Returns:**

- `LoyalFansAuthModel | None`: Authenticated session or None

---

## LoyalFansAPI Class

Main API class for LoyalFans operations (basic implementation).

### Initialization

```python
from ultima_scraper_api import UltimaScraperAPI, UltimaScraperAPIConfig

# Method 1: Through UltimaScraperAPI (recommended)
api = UltimaScraperAPI()
loyalfans = api.get_site_api("loyalfans")

# Method 2: Direct initialization
from ultima_scraper_api.apis.loyalfans import LoyalFansAPI

config = UltimaScraperAPIConfig()
loyalfans = LoyalFansAPI(config)
```

### Methods

#### find_auth

Find an authenticated session by user ID.

```python
authed = loyalfans.find_auth(user_id)
```

**Parameters:**

- `identifier` (int): User ID

**Returns:**

- `LoyalFansAuthModel | None`: Auth session if found

#### find_user

Find a user across all authenticated sessions.

```python
users = loyalfans.find_user("username")
# or
users = loyalfans.find_user(12345)
```

**Parameters:**

- `identifier` (int | str): User ID or username

**Returns:**

- `list[UserModel]`: List of matching users (may be empty)

---

## LoyalFansAuthModel Class

Represents an authenticated session (basic implementation).

### Attributes

```python
authed.id                    # int: Authenticated user ID (if available)
authed.username              # str: Authenticated username (if available)
authed.user                  # UserModel: User object (if available)
authed.guest                 # bool: Guest mode flag
```

!!! warning "Limited Attributes"
    Many attributes present in OnlyFans/Fansly implementations are not yet available for LoyalFans.

### Methods

#### get_user

Fetch a user by username or ID (experimental).

```python
user = await authed.get_user("username")
# or
user = await authed.get_user(12345)
```

**Parameters:**

- `identifier` (int | str): User ID or username
- `refresh` (bool, optional): Force refresh. Default: `False`

**Returns:**

- `dict | None`: User data dictionary or None

!!! note "Return Type"
    Currently returns raw API response dict instead of UserModel. This will change as development progresses.

---

## UserModel Class

User profile representation (minimal implementation).

!!! danger "Incomplete Implementation"
    The UserModel class exists but has minimal functionality. Most methods are not yet implemented.

### Expected Attributes (Planned)

```python
user.id                      # int: User ID
user.username                # str: Username
user.name                    # str: Display name
user.avatar                  # str: Avatar URL
user.cover                   # str: Cover image URL
user.about                   # str: Biography
user.posts_count             # int: Total posts (planned)
user.subscribers_count       # int: Subscriber count (planned)
```

### Planned Methods

#### get_posts (Not Implemented)

```python
# Planned signature:
posts = await user.get_posts(limit=50, offset=0)
```

**Status**: ❌ Not yet implemented

#### get_messages (Not Implemented)

```python
# Planned signature:
messages = await user.get_messages(limit=100)
```

**Status**: ❌ Not yet implemented

#### get_stories (Not Implemented)

```python
# Planned signature:
stories = await user.get_stories()
```

**Status**: ❌ Not yet implemented

---

## Planned Features

The following features are planned for future releases:

### High Priority

- [ ] **Complete Authentication** - Full auth validation and session management
- [ ] **User Profiles** - Complete profile data access
- [ ] **Posts/Timeline** - Fetch and display posts
- [ ] **Messages** - Direct message access
- [ ] **Media Downloads** - Download photos and videos
- [ ] **Subscriptions** - Subscription management

### Medium Priority

- [ ] **Stories** - Story viewing and highlights
- [ ] **Search** - User and content search
- [ ] **Comments** - Comment reading and posting
- [ ] **Favorites/Likes** - Like content
- [ ] **Collections** - Organized content access

### Low Priority

- [ ] **Live Streams** - Live stream access
- [ ] **WebSocket** - Real-time notifications
- [ ] **Payments** - Tipping and purchases
- [ ] **Account Settings** - Profile management

### Development Roadmap

| Quarter | Goals |
|---------|-------|
| **Q4 2024** | Authentication, basic profiles, posts |
| **Q1 2025** | Messages, media downloads, subscriptions |
| **Q2 2025** | Stories, search, advanced features |
| **Q3 2025** | WebSocket, live streams, full parity |

!!! info "Timeline Subject to Change"
    Development timeline depends on platform API stability and contributor availability.

---

## Contributing

We welcome contributions to LoyalFans API development!

### How to Contribute

1. **Test Endpoints** - Help identify working API endpoints
2. **Document Responses** - Document API response structures
3. **Implement Features** - Implement new features following existing patterns
4. **Write Tests** - Add test coverage for new features
5. **Report Issues** - Report bugs and inconsistencies

### Development Setup

```bash
# Clone repository
git clone https://github.com/DIGITALCRIMINAL/UltimaScraperAPI.git
cd UltimaScraperAPI

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
pytest tests/test_loyalfans.py
```

### Implementation Guidelines

Follow the same patterns as OnlyFans/Fansly implementations:

```python
# Example: Implementing get_posts()
async def get_posts(
    self,
    limit: int = 50,
    offset: int = 0,
    refresh: bool = True
) -> list[PostModel]:
    """
    Fetch user's posts.
    
    Args:
        limit: Maximum posts to fetch
        offset: Pagination offset
        refresh: Force API refresh
        
    Returns:
        List of PostModel objects
    """
    # Implementation here
    pass
```

### Testing

```bash
# Run LoyalFans-specific tests
pytest -k loyalfans

# Run with coverage
pytest --cov=ultima_scraper_api.apis.loyalfans

# Run in verbose mode
pytest -vv tests/test_loyalfans.py
```

---

## Migration Guide

### From OnlyFans/Fansly

The API design intentionally matches OnlyFans and Fansly for consistency:

```python
# Same pattern across all platforms
async with api.login_context(auth_json) as authed:
    # OnlyFans
    of_user = await authed.get_user("username")
    
    # Fansly
    fn_user = await authed.get_user("username")
    
    # LoyalFans (when implemented)
    lf_user = await authed.get_user("username")
```

### Expected API Parity

Once fully implemented, LoyalFans will support:

```python
# Common operations across all platforms
await authed.get_user(username)
await user.get_posts(limit=50)
await user.get_messages(limit=100)
await user.get_stories()
await post.favorite()

# Platform-specific features documented separately
```

---

## Limitations & Warnings

### Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No post access | Cannot fetch content | Wait for implementation |
| No message access | Cannot read DMs | Wait for implementation |
| Limited user data | Incomplete profiles | Use what's available |
| No error handling | May crash unexpectedly | Wrap in try/except |
| No test coverage | Untested code | Test thoroughly yourself |

### Production Use

!!! danger "Not Production Ready"
    **DO NOT use LoyalFans API in production:**
    
    - Incomplete implementation
    - Minimal error handling  
    - No comprehensive testing
    - API may change significantly
    - Data loss possible
    - Rate limiting not implemented
    
    **Use at your own risk!**

### Reporting Issues

If you encounter issues:

1. Check if feature is implemented (see [Implementation Status](#implementation-status))
2. Review [Troubleshooting Guide](../user-guide/troubleshooting.md)
3. Search [existing issues](https://github.com/DIGITALCRIMINAL/UltimaScraperAPI/issues)
4. Create new issue with:
   - LoyalFans API version
   - Code example
   - Expected vs actual behavior
   - Full error traceback

---

## See Also

### Internal Documentation
- **[Quick Start Guide](../getting-started/quick-start.md#loyalfans)** - Getting started
- **[Authentication Guide](../user-guide/authentication.md#loyalfans)** - Auth setup
- **[OnlyFans API Reference](onlyfans.md)** - Fully implemented API
- **[Fansly API Reference](fansly.md)** - Stable WIP API
- **[Troubleshooting](../user-guide/troubleshooting.md)** - Common issues

### External Resources
- **[LoyalFans Official Site](https://www.loyalfans.com/)** - Platform website
- **[LoyalFans Help](https://www.loyalfans.com/help)** - Official support

### Development
- **[Contributing](../development/contributing.md)** - Contribution guidelines
- **[Architecture](../development/architecture.md)** - System design
- **[Testing](../development/testing.md)** - Testing guide
- **[GitHub Repository](https://github.com/DIGITALCRIMINAL/UltimaScraperAPI)** - Source code

---

## Status Summary

**Implementation Progress: ~5%**

| Component | Progress | Status |
|-----------|----------|--------|
| Authentication | 20% | 🟡 Basic structure |
| User Profiles | 10% | 🟡 Minimal data |
| Posts | 0% | ❌ Not started |
| Messages | 0% | ❌ Not started |
| Stories | 0% | ❌ Not started |
| Media | 0% | ❌ Not started |
| **Overall** | **5%** | 🔴 Early development |

**Recommendation**: Use OnlyFans or Fansly APIs for production. LoyalFans support is for experimental/development purposes only.

**Last Updated**: October 2025

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
- `text` (str): Post text/content
- `media` (list[Media]): List of media items
- `created_at` (datetime): Creation timestamp
- `is_paid` (bool): Whether post is paid content

## Media Class

### Attributes

- `id` (str): Media ID
- `type` (str): Media type ("photo", "video")
- `url` (str): Media URL
- `thumbnail_url` (str): Thumbnail URL

### Methods

#### download

Download the media file.

```python
content = await media.download()
```

**Returns:**
- `bytes`: Media content

## Message Class

### Attributes

- `id` (str): Message ID
- `text` (str): Message text
- `created_at` (datetime): Timestamp
- `from_user` (User): Sender
- `media` (list[Media]): Attached media

## Current Limitations

!!! info "WIP Features"
    The following features are currently in development:
    
    - Stories/moments support
    - Subscription management
    - Advanced filtering
    - Live stream support
    - Full media processing

## Examples

### Basic Usage

```python
import asyncio
from ultima_scraper_api import LoyalFansAPI, UltimaScraperAPIConfig

async def fetch_loyalfans_user(username):
    config = UltimaScraperAPIConfig()
    api = LoyalFansAPI(config)
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
    }
    
    async with api.login_context(auth_json) as authed:
        user = await authed.get_user(username)
        if user:
            print(f"User: {user.username}")
            print(f"Name: {user.name}")
            
            posts = await user.get_posts(limit=50)
            print(f"Found {len(posts)} posts")

if __name__ == "__main__":
    asyncio.run(fetch_loyalfans_user("example_username"))
```

## See Also

- [Quick Start Guide](../getting-started/quick-start.md)
- [Authentication Guide](../user-guide/authentication.md)
- [OnlyFans API Reference](onlyfans.md)
