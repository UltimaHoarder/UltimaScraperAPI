# Quick Start

This guide will help you get started with UltimaScraperAPI by walking through practical examples.

## Prerequisites

Before you begin, ensure you have:

1. ✅ Installed UltimaScraperAPI (see [Installation](installation.md))
2. ✅ Python 3.10 or higher
3. ✅ Basic understanding of `async`/`await` in Python
4. ✅ Valid authentication credentials for your target platform

!!! tip "Python AsyncIO"
    UltimaScraperAPI is built entirely on asyncio. All API methods are asynchronous and must be called with `await`.

## Your First Script

Here's a complete example to get you started with the OnlyFans API:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    # Step 1: Initialize configuration
    config = UltimaScraperAPIConfig()
    
    # Step 2: Create API instance
    api = OnlyFansAPI(config)
    
    # Step 3: Prepare authentication credentials
    auth_json = {
        "cookie": "auth_id=123456; sess=abcdef...",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
        "x-bc": "your_x-bc_token_here"
    }
    
    # Step 4: Login and perform operations
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ Successfully authenticated!")
            
            # Get the authenticated user's information
            me = await authed.get_authed_user()
            print(f"Logged in as: {me.name} (@{me.username})")
            
            # Get another user's information
            user = await authed.get_user("username")
            if user:
                print(f"Found user: {user.username}")
                print(f"Subscribers: {user.subscriber_count if hasattr(user, 'subscriber_count') else 'N/A'}")
                
                # Fetch their posts
                posts = await user.get_posts(limit=10)
                print(f"Retrieved {len(posts)} posts")
                
                # Iterate through posts
                for post in posts:
                    print(f"  - Post {post.id}: {post.text[:50] if post.text else '(no text)'}...")
        else:
            print("✗ Authentication failed!")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

!!! note "Context Managers"
    The `login_context()` method returns an async context manager that handles session cleanup automatically. Always use it with `async with`.

## Obtaining Authentication Credentials

!!! warning "Authentication Required"
    You need valid authentication credentials to use most API features. These must be obtained from an authenticated browser session.

### For OnlyFans

1. **Open your browser** and log into OnlyFans
2. **Open Developer Tools** (Press `F12` or right-click → Inspect)
3. **Go to the Network tab**
4. **Refresh the page** or navigate to trigger API requests
5. **Find an API request** to `onlyfans.com/api` 
6. **Click on the request** and view Headers
7. **Extract these values:**

=== "Cookie"
    Look for the `Cookie` header in the Request Headers section. Copy the entire cookie string.
    
    Example: `auth_id=123456; sess=abcdef1234567890...`

=== "User-Agent"
    Find the `User-Agent` header. Copy the full string.
    
    Example: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...`

=== "x-bc"
    Find the `x-bc` header (OnlyFans-specific authentication token).
    
    Example: `a1b2c3d4e5f6g7h8i9j0...`

!!! tip "Finding x-bc"
    The `x-bc` header is present in most OnlyFans API requests. Look for requests to endpoints like `/api2/v2/users/me`.

### Using Guest Mode (Limited)

For basic functionality without full authentication:

```python
async def guest_example():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Use guest mode - no credentials needed
    async with api.login_context(guest=True) as authed:
        if authed:
            print("✓ Connected as guest")
            # Note: Very limited operations available
            # Most features require full authentication
```

!!! warning "Guest Limitations"
    Guest mode provides very limited functionality. Most features require full authentication.

## Working with Different Platforms

UltimaScraperAPI supports multiple platforms with a unified interface.

### OnlyFans (Stable) ✅

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()
api = OnlyFansAPI(config)

auth_json = {
    "cookie": "your_cookie",
    "user_agent": "your_user_agent",
    "x-bc": "your_x_bc_token"
}

async with api.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        # Full OnlyFans API functionality available
        me = await authed.get_authed_user()
        print(f"Authenticated as: {me.username}")
```

### Fansly (Work in Progress) ⚠️ {#fansly}

```python
from ultima_scraper_api import FanslyAPI, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()
api = FanslyAPI(config)

# Fansly authentication format may differ
auth_json = {
    "cookie": "your_cookie",
    "user_agent": "your_user_agent",
    # Fansly-specific auth fields
}

async with api.login_context(auth_json) as authed:
    # Limited Fansly operations available
    # API is under active development
    pass
```

!!! warning "Fansly Status"
    Fansly support is currently in development. Not all features are available yet.

### LoyalFans (Work in Progress) ⚠️ {#loyalfans}

```python
from ultima_scraper_api import LoyalFansAPI, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()
api = LoyalFansAPI(config)

async with api.login_context(auth_json) as authed:
    # Limited LoyalFans operations
    # API is under active development
    pass
```

!!! warning "LoyalFans Status"
    LoyalFans support is currently in development. Not all features are available yet.

### Using the API Selector

You can dynamically select an API:

```python
from ultima_scraper_api import select_api, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()

# Select API by name
api = select_api("onlyfans", config)  # Returns OnlyFansAPI instance
# api = select_api("fansly", config)  # Returns FanslyAPI instance
# api = select_api("loyalfans", config)  # Returns LoyalFansAPI instance

async with api.login_context(auth_json) as authed:
    # Work with the selected API
    pass
```

## Common Operations

### Fetching User Information

```python
async with api.login_context(auth_json) as authed:
    # Get the authenticated user (yourself)
    me = await authed.get_authed_user()
    print(f"My username: {me.username}")
    print(f"My ID: {me.id}")
    
    # Get another user by username
    user = await authed.get_user("username")
    if user:
        print(f"User: {user.name} (@{user.username})")
        print(f"ID: {user.id}")
```

### Fetching Posts

```python
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    
    # Get posts with optional limit
    posts = await user.get_posts(limit=20)
    
    for post in posts:
        print(f"Post ID: {post.id}")
        print(f"Posted: {post.created_at}")
        print(f"Text: {post.text[:100] if post.text else 'No text'}")
        print(f"Media count: {len(post.media) if post.media else 0}")
        print("-" * 50)
```

### Working with Media

```python
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    posts = await user.get_posts(limit=10)
    
    for post in posts:
        if post.media:
            for media in post.media:
                print(f"Media Type: {media.media_type}")
                print(f"URL: {media.url}")
                
                # Download media content
                content = await media.download()
                
                # Save to file
                filename = f"{media.id}.{media.extension}"
                with open(filename, 'wb') as f:
                    f.write(content)
                print(f"Saved: {filename}")
```

### Fetching Messages

```python
async with api.login_context(auth_json) as authed:
    # Get messages from a specific user
    user = await authed.get_user("username")
    messages = await user.get_messages(limit=50)
    
    for message in messages:
        print(f"From: {message.from_user.username if message.from_user else 'Unknown'}")
        print(f"Text: {message.text}")
        print(f"Sent: {message.created_at}")
        
        # Check for media in messages
        if message.media:
            print(f"Contains {len(message.media)} media file(s)")
```

### Fetching Stories

```python
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    
    # Get user's stories
    stories = await user.get_stories()
    
    for story in stories:
        print(f"Story ID: {story.id}")
        print(f"Created: {story.created_at}")
        if story.media:
            print(f"Media count: {len(story.media)}")
```

## Error Handling

Always implement proper error handling to make your scripts robust:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def safe_api_call():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_x_bc"
    }
    
    try:
        async with api.login_context(auth_json) as authed:
            if not authed or not authed.is_authed():
                print("✗ Authentication failed")
                return
            
            print("✓ Authentication successful")
            
            # Try to get user
            user = await authed.get_user("username")
            if not user:
                print("✗ User not found")
                return
            
            # Fetch posts with error handling
            try:
                posts = await user.get_posts(limit=10)
                print(f"✓ Retrieved {len(posts)} posts")
            except Exception as e:
                print(f"✗ Error fetching posts: {e}")
                
    except asyncio.TimeoutError:
        print("✗ Request timed out")
    except ConnectionError:
        print("✗ Connection error - check your network")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(safe_api_call())
```

!!! tip "Best Practices"
    - Always check if `authed` and `authed.is_authed()` before making API calls
    - Use try-except blocks for network operations
    - Implement rate limiting to avoid being blocked
    - Handle timeouts gracefully
    - Log errors for debugging

## Complete Example: Download All Posts

Here's a complete working example that demonstrates multiple concepts:

```python
import asyncio
from pathlib import Path
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def download_user_content(username: str):
    """Download all posts from a user."""
    
    # Setup
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "your_cookie_here",
        "user_agent": "your_user_agent_here",
        "x-bc": "your_x_bc_here"
    }
    
    # Create download directory
    download_dir = Path(f"downloads/{username}")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        async with api.login_context(auth_json) as authed:
            if not authed or not authed.is_authed():
                print("✗ Authentication failed")
                return
            
            print(f"✓ Authenticated successfully")
            
            # Get user
            user = await authed.get_user(username)
            if not user:
                print(f"✗ User '{username}' not found")
                return
            
            print(f"✓ Found user: {user.name} (@{user.username})")
            
            # Fetch posts
            print("Fetching posts...")
            posts = await user.get_posts()
            print(f"✓ Found {len(posts)} posts")
            
            # Download media from each post
            for idx, post in enumerate(posts, 1):
                print(f"\nProcessing post {idx}/{len(posts)} (ID: {post.id})")
                
                if not post.media:
                    print("  No media in this post")
                    continue
                
                for media_idx, media in enumerate(post.media, 1):
                    try:
                        filename = f"post_{post.id}_media_{media_idx}.{media.extension}"
                        filepath = download_dir / filename
                        
                        # Skip if already downloaded
                        if filepath.exists():
                            print(f"  ⊙ Skipping {filename} (already exists)")
                            continue
                        
                        # Download
                        print(f"  ↓ Downloading {filename}...")
                        content = await media.download()
                        
                        # Save
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        print(f"  ✓ Saved {filename}")
                        
                    except Exception as e:
                        print(f"  ✗ Error downloading media: {e}")
            
            print(f"\n✓ Complete! Downloaded to: {download_dir}")
            
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(download_user_content("username"))
```

## Next Steps

Now that you understand the basics, explore more advanced topics:

- 📖 [Configuration](configuration.md) - Learn about all configuration options
- 🔐 [Authentication](../user-guide/authentication.md) - Deep dive into authentication
- 🌐 [Proxy Support](../user-guide/proxy-support.md) - Configure proxies and networks
- 🔄 [Session Management](../user-guide/session-management.md) - Manage sessions and caching
- 📚 [API Reference](../api-reference/onlyfans.md) - Complete API documentation
- 🛠️ [Working with APIs](../user-guide/working-with-apis.md) - Advanced patterns and techniques
