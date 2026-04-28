# Quick Reference

Quick reference guide for common UltimaScraperAPI operations.

## Installation

```bash
pip install ultima-scraper-api
```

## Basic Setup

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()
api = OnlyFansAPI(config)

auth_json = {
    "id": 123456,
    "cookie": "your_cookie",
    "user_agent": "your_user_agent",
    "x-bc": "your_x-bc"
}
```

## Authentication

### Login
```python
async with api.login_context(auth_json) as authed:
    # Your code here
    pass
```

### Check Auth Status
```python
if authed and authed.is_authed():
    print("Authenticated!")
```

## User Operations

### Get Current User
```python
me = await authed.get_authed_user()
```

### Get User by Username
```python
user = await authed.get_user("username")
```

### Get User Posts
```python
posts = await user.get_posts(limit=50)
```

### Get User Stories
```python
stories = await user.get_stories()
```

### Get User Messages
```python
messages = await user.get_messages(limit=100)
```

### Search Chats
```python
chats = await authed.search_chats("query", limit=50)
```

## Post Operations

### Iterate Posts
```python
for post in posts:
    print(f"ID: {post.id}")
    print(f"Text: {post.text}")
    print(f"Created: {post.created_at}")
```

### Download Media
```python
from ultima_scraper_api.apis.onlyfans import url_picker

for post in posts:
    if post.media:
        for media in post.media:
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
                    with open(f"{media.id}.{media.type}", "wb") as f:
                        f.write(content)
```

### Diagnose CDN URL
```python
from ultima_scraper_api.helpers import diagnose_url

media_url = post.url_picker(media)
if media_url:
    print(diagnose_url(media_url.geturl()).get_diagnosis())
```

## Subscriptions

### Get Subscriptions
```python
subscriptions = await authed.get_subscriptions()

for sub in subscriptions:
    print(f"{sub.user.username} - Expires: {sub.expires_at}")
```

## Error Handling

```python
try:
    async with api.login_context(auth_json) as authed:
        if not authed or not authed.is_authed():
            raise RuntimeError("Authentication failed")
        user = await authed.get_user("username")
except Exception as e:
    print(f"API error: {e}")
```

## Configuration

### With Proxy
```python
from ultima_scraper_api.config import Proxy

config = UltimaScraperAPIConfig()
config.settings.network.proxies.append(Proxy(url="http://proxy:8080"))
```

### From Environment
```python
import os

auth_json = {
    "id": int(os.getenv("ONLYFANS_AUTH_ID", "0")),
    "cookie": os.getenv("COOKIE"),
    "user_agent": os.getenv("USER_AGENT"),
    "x-bc": os.getenv("XBC")
}
```

## Complete Example

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "id": 123456,
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc"
    }
    
    async with api.login_context(auth_json) as authed:
        if not authed or not authed.is_authed():
            print("Authentication failed")
            return
        
        # Get user
        user = await authed.get_user("username")
        if not user:
            print("User not found")
            return
        
        print(f"User: {user.username}")
        
        # Get posts
        posts = await user.get_posts(limit=10)
        print(f"Posts: {len(posts)}")
        
        # Download media
        from ultima_scraper_api.apis.onlyfans import url_picker
        
        for post in posts:
            if post.media:
                for media in post.media:
                    print(f"Downloading: {media.id}")
                    
                    media_url = url_picker(post.get_author(), media)
                    if media_url:
                        response = await authed.auth_session.request(
                            media_url.geturl(),
                            premade_settings=""
                        )
                        if response:
                            content = await response.read()
                            # Save file...
                            with open(f"{media.id}.{media.type}", "wb") as f:
                                f.write(content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Patterns

### Pagination
```python
async def fetch_all_posts(user):
    async def on_progress(done_pages, total_pages, items_so_far):
        print(f"Fetched page {done_pages}/{total_pages}: {items_so_far} posts")

    return await user.get_posts(on_progress=on_progress)
```

### Batch Processing
```python
async def process_users(usernames):
    tasks = [authed.get_user(name) for name in usernames]
    users = await asyncio.gather(*tasks)
    return users
```

### Rate Limiting
```python
import asyncio

async def rate_limited_fetch(items, delay=1.0):
    results = []
    for item in items:
        result = await fetch_item(item)
        results.append(result)
        await asyncio.sleep(delay)
    return results
```

## MkDocs Commands

Install the repo's documentation dependencies first:

```bash
uv sync --group dev
```

### Serve Documentation
```bash
uv run mkdocs serve
```

### Build Documentation
```bash
uv run mkdocs build
```

### Deploy to GitHub Pages
```bash
uv run mkdocs gh-deploy
```

## Useful Links

- [Full Documentation](https://ultimahoarder.github.io/UltimaScraperAPI/)
- [GitHub Repository](https://github.com/UltimaHoarder/UltimaScraperAPI)
- [Issue Tracker](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)
