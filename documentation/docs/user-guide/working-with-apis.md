# Working with APIs

This comprehensive guide covers all aspects of working with UltimaScraperAPI, including async patterns, context managers, API operations, and best practices.

## Overview

UltimaScraperAPI is built entirely on `asyncio` for high-performance asynchronous operations. All API interactions are asynchronous and must be properly awaited.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Async/Await** | All API methods are asynchronous coroutines |
| **Context Managers** | Automatic resource cleanup with `async with` |
| **Sessions** | Persistent HTTP sessions for efficiency |
| **Models** | Pydantic models for type-safe data |

## Understanding Async Patterns

### Why Async?

UltimaScraperAPI uses asyncio for several reasons:

- 🚀 **Performance**: Handle multiple requests concurrently
- 💾 **Efficiency**: Non-blocking I/O operations
- ⚡ **Scalability**: Process thousands of items efficiently
- 🔄 **Real-time**: Support for WebSocket connections

### Basic Async Structure

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    """All API operations must be inside async functions."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "...",
        "user_agent": "...",
        "x-bc": "..."
    }
    
    # Use async with for context management
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # All API calls must be awaited
            me = await authed.get_authed_user()
            print(f"Logged in as: {me.username}")

# Entry point - runs the async main function
if __name__ == "__main__":
    asyncio.run(main())
```

!!! tip "Running Async Code"
    - Use `asyncio.run()` at the entry point
    - Inside async functions, use `await` for async operations
    - Never mix sync and async code incorrectly

## Context Managers

UltimaScraperAPI uses async context managers to handle resource cleanup automatically.

### The `login_context()` Pattern

```python
async with api.login_context(auth_json) as authed:
    # Context is active - session is open
    # All operations happen here
    user = await authed.get_authed_user()
    
# Context exits - session is automatically closed
# Resources are cleaned up
```

**Benefits:**

- ✅ Automatic session cleanup
- ✅ Proper connection handling
- ✅ Exception-safe resource management
- ✅ No memory leaks

### Without Context Manager (Not Recommended)

```python
# ❌ Manual resource management - easy to forget cleanup
api = OnlyFansAPI(config)
authed = await api.login(auth_json)
# ... do work ...
await authed.close()  # Must remember to close!
```

### Nested Context Managers

Working with multiple resources:

```python
async def multi_platform():
    """Work with multiple platforms simultaneously."""
    config = UltimaScraperAPIConfig()
    
    of_api = OnlyFansAPI(config)
    fansly_api = FanslyAPI(config)
    
    of_auth = {...}  # OnlyFans credentials
    fansly_auth = {...}  # Fansly credentials
    
    # Nested contexts - both are cleaned up properly
    async with of_api.login_context(of_auth) as of_authed:
        async with fansly_api.login_context(fansly_auth) as fansly_authed:
            # Both sessions active
            if of_authed and of_authed.is_authed():
                of_user = await of_authed.get_authed_user()
                print(f"OnlyFans: {of_user.username}")
            
            if fansly_authed and fansly_authed.is_authed():
                fansly_user = await fansly_authed.get_authed_user()
                print(f"Fansly: {fansly_user.username}")
    
    # Both sessions closed and cleaned up
```

## Common API Operations

### Getting User Information

#### Authenticated User (Yourself)

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def get_my_info():
    """Get information about the authenticated user."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}  # Your credentials
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get your own user information
            me = await authed.get_authed_user()
            
            print(f"Username: {me.username}")
            print(f"Display Name: {me.name}")
            print(f"User ID: {me.id}")
            print(f"Email: {me.email if hasattr(me, 'email') else 'N/A'}")
            print(f"Verified: {me.is_verified if hasattr(me, 'is_verified') else 'N/A'}")

asyncio.run(get_my_info())
```

#### Other Users

```python
async def get_other_user():
    """Get information about another user."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get another user by username
            user = await authed.get_user("username")
            
            if user:
                print(f"Found: {user.name} (@{user.username})")
                print(f"ID: {user.id}")
                print(f"Posts: {user.posts_count if hasattr(user, 'posts_count') else 'N/A'}")
                print(f"Subscribers: {user.subscriber_count if hasattr(user, 'subscriber_count') else 'N/A'}")
            else:
                print("User not found")

asyncio.run(get_other_user())
```

### Fetching Posts

#### Basic Post Fetching

```python
async def fetch_posts():
    """Fetch posts from a user."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get user
            user = await authed.get_user("username")
            if not user:
                print("User not found")
                return
            
            # Fetch posts (with optional limit)
            posts = await user.get_posts(limit=50)
            
            print(f"Retrieved {len(posts)} posts\n")
            
            for idx, post in enumerate(posts, 1):
                print(f"Post #{idx}")
                print(f"  ID: {post.id}")
                print(f"  Date: {post.created_at}")
                print(f"  Text: {post.text[:100] if post.text else '(no text)'}...")
                print(f"  Media: {len(post.media) if post.media else 0} items")
                print(f"  Likes: {post.likes_count if hasattr(post, 'likes_count') else 'N/A'}")
                print(f"  Comments: {post.comments_count if hasattr(post, 'comments_count') else 'N/A'}")
                print()

asyncio.run(fetch_posts())
```

#### Filtering Posts

```python
async def filter_posts():
    """Filter posts by specific criteria."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("username")
            posts = await user.get_posts()
            
            # Filter posts with media
            posts_with_media = [p for p in posts if p.media and len(p.media) > 0]
            print(f"Posts with media: {len(posts_with_media)}")
            
            # Filter posts with videos
            posts_with_video = [
                p for p in posts 
                if p.media and any(m.media_type == "video" for m in p.media)
            ]
            print(f"Posts with videos: {len(posts_with_video)}")
            
            # Filter free vs paid posts
            free_posts = [p for p in posts if not p.price or p.price == 0]
            paid_posts = [p for p in posts if p.price and p.price > 0]
            print(f"Free posts: {len(free_posts)}")
            print(f"Paid posts: {len(paid_posts)}")

asyncio.run(filter_posts())
```

### Working with Messages

```python
async def fetch_messages():
    """Fetch messages from a user."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get user
            user = await authed.get_user("username")
            if not user:
                print("User not found")
                return
            
            # Fetch messages (with optional limit)
            messages = await user.get_messages(limit=100)
            
            print(f"Retrieved {len(messages)} messages\n")
            
            for msg in messages:
                sender = "Me" if msg.is_from_me else user.username
                print(f"[{msg.created_at}] {sender}: {msg.text}")
                
                if msg.media:
                    print(f"  📎 {len(msg.media)} attachment(s)")

asyncio.run(fetch_messages())
```

### Downloading Media

#### Basic Media Download

```python
import asyncio
from pathlib import Path
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def download_media():
    """Download media from posts."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    # Create download directory
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("username")
            posts = await user.get_posts(limit=10)
            
            for post in posts:
                if not post.media:
                    continue
                
                print(f"Downloading from post {post.id}...")
                
                for media in post.media:
                    try:
                        # Download media content
                        content = await media.download()
                        
                        # Generate filename
                        filename = f"post_{post.id}_media_{media.id}.{media.extension}"
                        filepath = download_dir / filename
                        
                        # Save to file
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        print(f"  ✓ Saved: {filename}")
                        
                    except Exception as e:
                        print(f"  ✗ Error downloading media {media.id}: {e}")

asyncio.run(download_media())
```

#### Advanced Media Download with Progress

```python
async def download_with_progress():
    """Download media with progress tracking."""
    from alive_progress import alive_bar
    
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("username")
            posts = await user.get_posts()
            
            # Count total media items
            total_media = sum(len(p.media) for p in posts if p.media)
            print(f"Found {total_media} media items to download")
            
            with alive_bar(total_media) as bar:
                for post in posts:
                    if not post.media:
                        continue
                    
                    for media in post.media:
                        try:
                            content = await media.download()
                            
                            filename = f"post_{post.id}_{media.id}.{media.extension}"
                            filepath = download_dir / filename
                            
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            
                            bar()  # Update progress
                            
                        except Exception as e:
                            print(f"\nError: {e}")
                            bar()

asyncio.run(download_with_progress())
```

### Working with Stories

```python
async def fetch_stories():
    """Fetch and download stories from a user."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("username")
            
            # Get user's active stories
            stories = await user.get_stories()
            
            print(f"Found {len(stories)} active stories")
            
            for story in stories:
                print(f"\nStory ID: {story.id}")
                print(f"Created: {story.created_at}")
                print(f"Expires: {story.expires_at if hasattr(story, 'expires_at') else 'N/A'}")
                
                if story.media:
                    print(f"Media items: {len(story.media)}")
                    for media in story.media:
                        print(f"  - {media.media_type}: {media.url}")

asyncio.run(fetch_stories())
```

### Getting Subscriptions

```python
async def list_subscriptions():
    """List all active subscriptions."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get all subscriptions
            subscriptions = await authed.get_subscriptions()
            
            print(f"You have {len(subscriptions)} active subscriptions\n")
            
            for sub in subscriptions:
                user = sub.user if hasattr(sub, 'user') else None
                if user:
                    print(f"• {user.name} (@{user.username})")
                    print(f"  Subscribed since: {sub.subscribed_at if hasattr(sub, 'subscribed_at') else 'N/A'}")
                    print(f"  Expires: {sub.expires_at if hasattr(sub, 'expires_at') else 'N/A'}")
                    print(f"  Price: ${sub.price if hasattr(sub, 'price') else 'N/A'}")
                    print()

asyncio.run(list_subscriptions())
```

## Platform-Specific Features

### OnlyFans (Stable) ✅

OnlyFans API is fully functional with comprehensive features:

=== "Posts & Content"
    ```python
    # Get posts
    posts = await user.get_posts(limit=100)
    
    # Get archived posts
    archived = await user.get_archived_posts()
    
    # Get highlights
    highlights = await user.get_highlights()
    
    # Get stories
    stories = await user.get_stories()
    ```

=== "Messages"
    ```python
    # Get messages with a user
    messages = await user.get_messages(limit=200)
    
    # Get all conversations
    conversations = await authed.get_conversations()
    ```

=== "Subscriptions"
    ```python
    # Get active subscriptions
    subscriptions = await authed.get_subscriptions()
    
    # Get subscription info for specific user
    sub_info = await user.get_subscription()
    ```

=== "Media Download"
    ```python
    # Download media from any content
    for post in posts:
        if post.media:
            for media in post.media:
                content = await media.download()
                # Save content...
    ```

### Fansly (Work in Progress) ⚠️

```python
import asyncio
from ultima_scraper_api import FanslyAPI, UltimaScraperAPIConfig

async def fansly_example():
    """Fansly API usage (limited functionality)."""
    config = UltimaScraperAPIConfig()
    api = FanslyAPI(config)
    
    fansly_auth = {
        "cookie": "...",
        "user_agent": "..."
    }
    
    async with api.login_context(fansly_auth) as authed:
        if authed and authed.is_authed():
            # Basic operations available
            me = await authed.get_authed_user()
            print(f"Fansly user: {me.username}")
            
            # Additional features in development
            # Check documentation for updates

asyncio.run(fansly_example())
```

!!! warning "Fansly Development Status"
    Fansly support is actively being developed. Available features are limited and may change.

### LoyalFans (Work in Progress) ⚠️

```python
import asyncio
from ultima_scraper_api import LoyalFansAPI, UltimaScraperAPIConfig

async def loyalfans_example():
    """LoyalFans API usage (limited functionality)."""
    config = UltimaScraperAPIConfig()
    api = LoyalFansAPI(config)
    
    loyalfans_auth = {
        "cookie": "...",
        "user_agent": "..."
    }
    
    async with api.login_context(loyalfans_auth) as authed:
        if authed and authed.is_authed():
            # Basic operations available
            me = await authed.get_authed_user()
            print(f"LoyalFans user: {me.username}")
            
            # Additional features in development
            # Check documentation for updates

asyncio.run(loyalfans_example())
```

!!! warning "LoyalFans Development Status"
    LoyalFans support is actively being developed. Available features are limited and may change.

## Advanced Patterns

### Pagination

Handle large datasets efficiently with pagination:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def fetch_all_posts_paginated(user, batch_size=50):
    """Fetch all posts using pagination."""
    all_posts = []
    offset = 0
    
    while True:
        # Fetch batch
        posts = await user.get_posts(limit=batch_size, offset=offset)
        
        if not posts:
            # No more posts
            break
        
        all_posts.extend(posts)
        print(f"Fetched {len(posts)} posts (total: {len(all_posts)})")
        
        # Move to next batch
        offset += batch_size
        
        # Be nice to the API - add delay
        await asyncio.sleep(1)
    
    return all_posts

async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("username")
            all_posts = await fetch_all_posts_paginated(user)
            print(f"\nTotal posts retrieved: {len(all_posts)}")

asyncio.run(main())
```

### Concurrent Operations

Process multiple items concurrently for better performance:

```python
async def concurrent_user_fetch():
    """Fetch multiple users concurrently."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    usernames = ["user1", "user2", "user3", "user4", "user5"]
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Create tasks for concurrent execution
            tasks = [authed.get_user(username) for username in usernames]
            
            # Execute all tasks concurrently
            users = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for username, user in zip(usernames, users):
                if isinstance(user, Exception):
                    print(f"✗ {username}: Error - {user}")
                elif user:
                    print(f"✓ {username}: {user.name}")
                else:
                    print(f"✗ {username}: Not found")

asyncio.run(concurrent_user_fetch())
```

### Batch Processing

Process items in batches to control concurrency:

```python
async def batch_process_users(authed, usernames, batch_size=5):
    """Process users in batches to avoid overwhelming the API."""
    results = []
    
    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}...")
        
        # Process batch concurrently
        tasks = [authed.get_user(username) for username in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results.extend(batch_results)
        
        # Delay between batches
        if i + batch_size < len(usernames):
            await asyncio.sleep(2)
    
    return results

async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    usernames = [f"user{i}" for i in range(20)]  # 20 users
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            users = await batch_process_users(authed, usernames, batch_size=5)
            
            successful = [u for u in users if not isinstance(u, Exception) and u]
            print(f"\nSuccessfully fetched: {len(successful)}/{len(usernames)}")

asyncio.run(main())
```

### Rate Limiting

Implement rate limiting to avoid overwhelming the API and getting blocked:

```python
import asyncio
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    """Rate limiter to control request frequency."""
    
    def __init__(self, max_requests: int, time_window: timedelta):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window for rate limiting
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def acquire(self):
        """Wait if necessary to stay within rate limit."""
        now = datetime.now()
        
        # Remove expired requests from the window
        while self.requests and now - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        # If at limit, wait for oldest request to expire
        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] + self.time_window - now).total_seconds()
            if wait_time > 0:
                print(f"Rate limit reached, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                # Recursively try again after waiting
                await self.acquire()
        
        # Record this request
        self.requests.append(now)

# Usage example
async def rate_limited_fetch():
    """Fetch users with rate limiting."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    # Allow 10 requests per minute
    limiter = RateLimiter(max_requests=10, time_window=timedelta(minutes=1))
    
    usernames = [f"user{i}" for i in range(20)]
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            for username in usernames:
                # Wait if necessary
                await limiter.acquire()
                
                # Make request
                user = await authed.get_user(username)
                if user:
                    print(f"✓ Fetched: {user.username}")

asyncio.run(rate_limited_fetch())
```

### Exponential Backoff

Handle temporary errors with exponential backoff:

```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_backoff(
    coro_func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        coro_func: Coroutine function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Result from successful execution
    
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await coro_func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed")
    
    # All retries exhausted
    raise last_exception

# Usage
async def fetch_with_retry():
    """Fetch user with automatic retry."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Wrap the API call with retry logic
            user = await retry_with_backoff(
                lambda: authed.get_user("username"),
                max_retries=3,
                base_delay=1.0
            )
            
            if user:
                print(f"✓ Successfully fetched: {user.username}")

asyncio.run(fetch_with_retry())
```

### Caching Results

Implement caching to reduce redundant API calls:

```python
import asyncio
import time
from typing import Dict, Tuple, Optional, Any

class APICache:
    """Simple time-based cache for API results."""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired - remove from cache
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Store value in cache with current timestamp."""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached data."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get number of cached items."""
        return len(self.cache)

# Usage
async def cached_api_calls():
    """Use caching to avoid redundant API calls."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    # Create cache with 5-minute TTL
    cache = APICache(ttl=300)
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            username = "someuser"
            
            # First call - fetches from API
            cached = cache.get(f"user:{username}")
            if cached:
                print("✓ Using cached data")
                user = cached
            else:
                print("↓ Fetching from API...")
                user = await authed.get_user(username)
                cache.set(f"user:{username}", user)
            
            print(f"User: {user.username}")
            
            # Second call - uses cache
            cached = cache.get(f"user:{username}")
            if cached:
                print("✓ Using cached data (no API call!)")
                user = cached

asyncio.run(cached_api_calls())
```

## Error Handling

### Comprehensive Error Handling

```python
import asyncio
from aiohttp import ClientError, ClientResponseError
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def robust_api_call():
    """API calls with comprehensive error handling."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    try:
        async with api.login_context(auth_json) as authed:
            if not authed or not authed.is_authed():
                raise ValueError("Authentication failed")
            
            try:
                # Attempt API operation
                user = await authed.get_user("username")
                
                if user:
                    print(f"✓ Success: {user.username}")
                else:
                    print("User not found")
                    
            except ClientResponseError as e:
                # HTTP errors (4xx, 5xx)
                if e.status == 404:
                    print("✗ User not found (404)")
                elif e.status == 429:
                    print("✗ Rate limited (429) - slow down!")
                elif e.status >= 500:
                    print(f"✗ Server error ({e.status}) - try again later")
                else:
                    print(f"✗ HTTP error {e.status}: {e.message}")
                    
            except ClientError as e:
                # Connection errors, timeouts, etc.
                print(f"✗ Connection error: {e}")
                
            except asyncio.TimeoutError:
                print("✗ Request timed out")
                
            except Exception as e:
                # Catch-all for unexpected errors
                print(f"✗ Unexpected error: {type(e).__name__}: {e}")
                
    except KeyboardInterrupt:
        print("\n✗ Interrupted by user")
    except Exception as e:
        print(f"✗ Fatal error: {e}")

asyncio.run(robust_api_call())
```

### Error Handler Decorator

```python
from functools import wraps
from typing import Callable, TypeVar, Any

T = TypeVar('T')

def handle_api_errors(default_return: Any = None):
    """Decorator to handle common API errors."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ClientResponseError as e:
                print(f"HTTP {e.status}: {e.message}")
                return default_return
            except ClientError as e:
                print(f"Connection error: {e}")
                return default_return
            except asyncio.TimeoutError:
                print("Request timed out")
                return default_return
            except Exception as e:
                print(f"Unexpected error: {e}")
                return default_return
        return wrapper
    return decorator

# Usage
@handle_api_errors(default_return=None)
async def fetch_user_safe(authed, username: str):
    """Fetch user with automatic error handling."""
    return await authed.get_user(username)

async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {...}
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Errors are handled automatically
            user = await fetch_user_safe(authed, "username")
            if user:
                print(f"Got user: {user.username}")

asyncio.run(main())
```

## Understanding Data Models

UltimaScraperAPI uses Pydantic models for type-safe data structures.

### Common Model Attributes

#### User Model

```python
# Accessing user attributes
user.id              # int: Unique user ID
user.username        # str: Username (handle)
user.name            # str: Display name
user.avatar          # str: Avatar URL
user.header          # str: Header/banner URL
user.bio             # str: User biography
user.location        # str: User location
user.website         # str: Website URL
user.is_verified     # bool: Verification status
user.posts_count     # int: Number of posts
user.photos_count    # int: Number of photos
user.videos_count    # int: Number of videos
user.subscriber_count # int: Number of subscribers
```

#### Post Model

```python
# Accessing post attributes
post.id              # int: Unique post ID
post.text            # str: Post text/caption
post.price           # float: Price (0 for free posts)
post.is_paid         # bool: Whether post is paid
post.created_at      # datetime: Creation timestamp
post.media           # List[Media]: Media items
post.likes_count     # int: Number of likes
post.comments_count  # int: Number of comments
post.is_archived     # bool: Whether post is archived
```

#### Media Model

```python
# Accessing media attributes
media.id             # int: Unique media ID
media.media_type     # str: Type (photo, video, audio)
media.url            # str: Media URL
media.preview_url    # str: Preview/thumbnail URL
media.extension      # str: File extension
media.duration       # int: Duration in seconds (video/audio)
media.width          # int: Width in pixels
media.height         # int: Height in pixels
media.size           # int: File size in bytes
```

#### Message Model

```python
# Accessing message attributes
message.id           # int: Unique message ID
message.text         # str: Message text
message.price        # float: Price (for paid messages)
message.is_from_me   # bool: Whether you sent it
message.created_at   # datetime: Creation timestamp
message.media        # List[Media]: Attached media
message.from_user    # User: Sender
message.to_user      # User: Recipient
```

## Best Practices

### 1. Always Use Context Managers ✅

```python
# ✓ Good - automatic cleanup
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")

# ✗ Bad - manual cleanup required
authed = await api.login(auth_json)
user = await authed.get_user("username")
await authed.close()  # Easy to forget!
```

### 2. Implement Proper Error Handling ✅

```python
# ✓ Good - handles errors gracefully
try:
    user = await authed.get_user("username")
except ClientResponseError as e:
    print(f"HTTP error: {e.status}")
except Exception as e:
    print(f"Error: {e}")

# ✗ Bad - crashes on any error
user = await authed.get_user("username")
```

### 3. Use Rate Limiting ✅

```python
# ✓ Good - respects API limits
limiter = RateLimiter(max_requests=10, time_window=timedelta(minutes=1))
for username in usernames:
    await limiter.acquire()
    user = await authed.get_user(username)

# ✗ Bad - may get rate limited or blocked
for username in usernames:
    user = await authed.get_user(username)  # Too fast!
```

### 4. Cache When Appropriate ✅

```python
# ✓ Good - caches results
cache = APICache(ttl=300)
cached = cache.get(f"user:{username}")
if not cached:
    cached = await authed.get_user(username)
    cache.set(f"user:{username}", cached)

# ✗ Bad - fetches same data repeatedly
for i in range(10):
    user = await authed.get_user("username")  # Same call 10 times!
```

### 5. Use Batch Operations ✅

```python
# ✓ Good - processes in batches
tasks = [authed.get_user(u) for u in batch]
results = await asyncio.gather(*tasks)

# ✗ Bad - sequential processing
results = []
for username in usernames:
    user = await authed.get_user(username)  # Slow!
    results.append(user)
```

### 6. Handle Pagination Properly ✅

```python
# ✓ Good - fetches all data
all_posts = []
offset = 0
while True:
    posts = await user.get_posts(limit=50, offset=offset)
    if not posts:
        break
    all_posts.extend(posts)
    offset += 50

# ✗ Bad - only gets first page
posts = await user.get_posts(limit=50)  # Missing rest!
```

### 7. Validate Authentication ✅

```python
# ✓ Good - checks authentication
async with api.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        # Proceed with operations
        pass
    else:
        print("Authentication failed!")

# ✗ Bad - assumes authentication worked
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")  # May fail!
```

### 8. Use Type Hints ✅

```python
# ✓ Good - clear types
from typing import List, Optional

async def fetch_users(authed, usernames: List[str]) -> List[Optional[User]]:
    tasks = [authed.get_user(u) for u in usernames]
    return await asyncio.gather(*tasks)

# ✗ Bad - unclear types
async def fetch_users(authed, usernames):
    tasks = [authed.get_user(u) for u in usernames]
    return await asyncio.gather(*tasks)
```

### 9. Log Important Operations ✅

```python
import logging

# ✓ Good - logs operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_user(authed, username: str):
    logger.info(f"Fetching user: {username}")
    user = await authed.get_user(username)
    if user:
        logger.info(f"✓ Found: {user.username}")
    else:
        logger.warning(f"✗ Not found: {username}")
    return user

# ✗ Bad - silent operations
async def fetch_user(authed, username: str):
    return await authed.get_user(username)
```

### 10. Handle Resource Cleanup ✅

```python
# ✓ Good - ensures cleanup
try:
    async with api.login_context(auth_json) as authed:
        # Do work
        pass
finally:
    # Additional cleanup if needed
    print("Cleanup complete")

# ✗ Bad - resources may leak
authed = await api.login(auth_json)
# Do work (if error occurs, session never closed!)
```

## Complete Example

Here's a complete example incorporating all best practices:

```python
import asyncio
import logging
from pathlib import Path
from datetime import timedelta
from typing import List, Optional
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentDownloader:
    """Professional content downloader with best practices."""
    
    def __init__(self, config: UltimaScraperAPIConfig):
        self.config = config
        self.cache = APICache(ttl=300)
        self.rate_limiter = RateLimiter(
            max_requests=10,
            time_window=timedelta(minutes=1)
        )
    
    async def download_user_content(
        self,
        api: OnlyFansAPI,
        auth_json: dict,
        username: str,
        output_dir: Path
    ):
        """Download all content from a user."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with api.login_context(auth_json) as authed:
                if not authed or not authed.is_authed():
                    logger.error("Authentication failed")
                    return
                
                logger.info(f"Authenticated successfully")
                
                # Fetch user with rate limiting
                await self.rate_limiter.acquire()
                user = await self._fetch_user_cached(authed, username)
                
                if not user:
                    logger.error(f"User not found: {username}")
                    return
                
                logger.info(f"Found user: {user.name} (@{user.username})")
                
                # Fetch posts with pagination
                posts = await self._fetch_all_posts(user)
                logger.info(f"Retrieved {len(posts)} posts")
                
                # Download media
                await self._download_media(posts, output_dir)
                
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
        except Exception as e:
            logger.exception(f"Error: {e}")
    
    async def _fetch_user_cached(self, authed, username: str):
        """Fetch user with caching."""
        cached = self.cache.get(f"user:{username}")
        if cached:
            logger.info(f"Using cached user data")
            return cached
        
        try:
            user = await authed.get_user(username)
            self.cache.set(f"user:{username}", user)
            return user
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            return None
    
    async def _fetch_all_posts(self, user):
        """Fetch all posts with pagination."""
        all_posts = []
        offset = 0
        batch_size = 50
        
        while True:
            try:
                await self.rate_limiter.acquire()
                posts = await user.get_posts(limit=batch_size, offset=offset)
                
                if not posts:
                    break
                
                all_posts.extend(posts)
                logger.info(f"Fetched {len(posts)} posts (total: {len(all_posts)})")
                
                offset += batch_size
                
            except Exception as e:
                logger.error(f"Error fetching posts: {e}")
                break
        
        return all_posts
    
    async def _download_media(self, posts: List, output_dir: Path):
        """Download media with error handling."""
        total_media = sum(len(p.media) for p in posts if p.media)
        logger.info(f"Downloading {total_media} media items...")
        
        downloaded = 0
        
        for post in posts:
            if not post.media:
                continue
            
            for media in post.media:
                try:
                    await self.rate_limiter.acquire()
                    
                    content = await media.download()
                    
                    filename = f"post_{post.id}_{media.id}.{media.extension}"
                    filepath = output_dir / filename
                    
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    downloaded += 1
                    logger.info(f"✓ Downloaded: {filename} ({downloaded}/{total_media})")
                    
                except Exception as e:
                    logger.error(f"✗ Error downloading {media.id}: {e}")
        
        logger.info(f"Download complete: {downloaded}/{total_media} successful")

# Usage
async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "...",
        "user_agent": "...",
        "x-bc": "..."
    }
    
    downloader = ContentDownloader(config)
    await downloader.download_user_content(
        api=api,
        auth_json=auth_json,
        username="someuser",
        output_dir=Path("downloads/someuser")
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

Now that you understand how to work with the APIs, explore related topics:

- 🔄 [Session Management](session-management.md) - Manage sessions and Redis caching
- 🌐 [Proxy Support](proxy-support.md) - Configure proxies for privacy
- 📚 [API Reference](../api-reference/onlyfans.md) - Detailed API documentation
- 🔐 [Authentication](authentication.md) - Authentication best practices
