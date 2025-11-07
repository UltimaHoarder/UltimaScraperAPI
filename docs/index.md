# Welcome to UltimaScraperAPI

UltimaScraperAPI is a modular Python scraping framework designed to interact with premium content platforms such as OnlyFans, LoyalFans, and Fansly. It provides a unified API for authentication, user data, posts, messages, and media downloads.

!!! note "Platform Support Status"
    - **OnlyFans**: Stable and fully supported
    - **LoyalFans**: Work in Progress (WIP) - Limited functionality
    - **Fansly**: Work in Progress (WIP) - Limited functionality

## Features

### 🌐 Multi-Site Support
Support for multiple premium content platforms with a unified interface:

- OnlyFans (Stable)
- LoyalFans (WIP)
- Fansly (WIP)

### ⚡ Async API
Built with `asyncio` and `aiohttp` for high-performance asynchronous operations.

### 🔐 Authentication
Flexible authentication system supporting:

- Cookie/session-based login
- Token-based authentication
- Guest API access

### 📦 Unified Data Models
Consistent data models across platforms for:

- Users
- Posts
- Messages
- Media content

### 🔧 Extensible Architecture
Easily extend functionality:

- Add new sites
- Customize existing integrations
- Plugin-based architecture

### 🌍 Session & Proxy Management
Robust handling of:

- Session persistence
- Proxy configuration
- Connection pooling

## Quick Example

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()
api = OnlyFansAPI(config)

auth_json = {
    "cookie": "your_cookie_here",
    "user_agent": "your_user_agent_here",
    "x-bc": "your_x-bc_here"
}

async def main():
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            user = await authed.get_user("onlyfans")
            if user:
                posts = await user.get_posts()
                print(f"Found {len(posts)} posts")

# Use asyncio.run(main()) in your script entry point
```

## Getting Started

Ready to start using UltimaScraperAPI? Check out the [Installation](getting-started/installation.md) guide to get up and running, then follow the [Quick Start](getting-started/quick-start.md) tutorial.

## License

This project is licensed under the GNU Affero General Public License v3.0. See the [License](about/license.md) page for details.
