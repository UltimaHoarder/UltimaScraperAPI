# UltimaScraperAPI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.2.46-green.svg)](https://github.com/UltimaHoarder/UltimaScraperAPI/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

UltimaScraperAPI is a modular Python scraping framework designed to interact with premium content platforms such as OnlyFans, Fansly, and LoyalFans. It provides a unified, async-first API for authentication, user data retrieval, posts, messages, and media downloads with comprehensive session management and caching capabilities.

> **Platform Status:** 
> - ✅ **OnlyFans**: Fully supported and stable
> - 🚧 **Fansly**: Work in progress with limited functionality
> - 🚧 **LoyalFans**: Work in progress with limited functionality

## 📚 Documentation

**[Read the full documentation →](https://ultimahoarder.github.io/UltimaScraperAPI/)**

### Getting Started
- [Installation Guide](https://ultimahoarder.github.io/UltimaScraperAPI/getting-started/installation/) - Installation methods and requirements
- [Quick Start Tutorial](https://ultimahoarder.github.io/UltimaScraperAPI/getting-started/quick-start/) - Get up and running in minutes
- [Configuration](https://ultimahoarder.github.io/UltimaScraperAPI/getting-started/configuration/) - Complete configuration reference

### User Guides
- [Authentication](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/authentication/) - How to authenticate with platforms
- [Working with APIs](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/working-with-apis/) - Common operations and patterns
- [Proxy Support](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/proxy-support/) - Configure proxies and VPNs
- [Session Management](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/session-management/) - Redis integration and caching

### API Reference
- [OnlyFans API](https://ultimahoarder.github.io/UltimaScraperAPI/api-reference/onlyfans/) - Complete OnlyFans API reference
- [Fansly API](https://ultimahoarder.github.io/UltimaScraperAPI/api-reference/fansly/) - Fansly API reference (WIP)
- [LoyalFans API](https://ultimahoarder.github.io/UltimaScraperAPI/api-reference/loyalfans/) - LoyalFans API reference (WIP)
- [Helpers](https://ultimahoarder.github.io/UltimaScraperAPI/api-reference/helpers/) - Utility functions and helpers

### Development
- [Architecture](https://ultimahoarder.github.io/UltimaScraperAPI/development/architecture/) - System design and architecture
- [Contributing Guide](https://ultimahoarder.github.io/UltimaScraperAPI/development/contributing/) - How to contribute
- [Testing](https://ultimahoarder.github.io/UltimaScraperAPI/development/testing/) - Running and writing tests

## ✨ Features

- 🌐 **Multi-Platform Support**: OnlyFans (stable), Fansly (WIP), and LoyalFans (WIP)
- ⚡ **Async-First Design**: Built with `asyncio` and `aiohttp` for high performance
- 🔐 **Flexible Authentication**: Cookie-based and guest authentication flows
- 📦 **Unified Data Models**: Consistent Pydantic models for users, posts, messages, and media
- 🔧 **Highly Extensible**: Modular architecture makes adding new platforms easy
- 🌍 **Advanced Networking**: Session management, connection pooling, proxy support (HTTP/HTTPS/SOCKS)
- 🔄 **WebSocket Support**: Real-time updates and live notifications
- 💾 **Redis Integration**: Optional caching, session persistence, and rate limiting
- 📊 **Type Safety**: Comprehensive type hints and validation with Pydantic v2
- 🔒 **DRM Support**: Widevine CDM integration for encrypted content
- 🎯 **Rate Limiting**: Built-in rate limiting and exponential backoff
- 🛡️ **Error Handling**: Comprehensive error handling with retry mechanisms
- 📝 **Comprehensive Logging**: Detailed logging for debugging and monitoring

## 📋 Requirements

- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14 (but less than 4.0)
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (recommended) or pip
- **Optional**: Redis 6.2+ for caching and session management

## 🚀 Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install uv if you haven't already
pip install uv

# Install UltimaScraperAPI
uv pip install ultima-scraper-api
```

### Using pip

```bash
pip install ultima-scraper-api
```

### From Source

For development or the latest features:

```bash
# Clone the repository
git clone https://github.com/UltimaHoarder/UltimaScraperAPI.git
cd UltimaScraperAPI

# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

### Virtual Environment (Recommended)

Always use a virtual environment to avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install the package
uv pip install ultima-scraper-api
```


## 💡 Quick Start

### Basic Usage

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    # Initialize configuration
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Authentication credentials
    # Obtain these from your browser's Network tab (F12)
    # See: https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/authentication/
    auth_json = {
        "cookie": "your_cookie_value",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc_token"
    }
    
    # Use context manager for automatic cleanup
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Get authenticated user info
            me = await authed.get_me()
            print(f"Logged in as: {me.username}")
            
            # Get user profile
            user = await authed.get_user("username")
            if user:
                print(f"User: {user.username} ({user.name})")
                
                # Fetch user's posts
                posts = await user.get_posts(limit=10)
                print(f"Found {len(posts)} posts")
                
                # Download media from posts
                for post in posts:
                    if post.media:
                        for media in post.media:
                            print(f"Downloading: {media.filename}")
                            content = await media.download()
                            # Save content to file...

if __name__ == "__main__":
    asyncio.run(main())
```

### Credential Extraction

You need three pieces of information from your browser:

1. **Cookie**: Your session cookie
2. **User-Agent**: Your browser's user agent string
3. **x-bc** (OnlyFans only): Dynamic authorization token

**Quick Steps:**

1. Open your browser and navigate to the platform
2. Open Developer Tools (F12)
3. Go to the Network tab
4. Look for API requests and copy the required headers

For detailed instructions with screenshots, see the [Authentication Guide](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/authentication/).

### Guest Mode (Limited Access)

Some platforms support guest access for public content:

```python
async with api.login_context(guest=True) as authed:
    # Limited operations available (public profiles, posts, etc.)
    user = await authed.get_user("public_username")
    if user:
        print(f"Public profile: {user.username}")
```

## 🔧 Configuration

### Basic Configuration

```python
from ultima_scraper_api import UltimaScraperAPIConfig

# Load from JSON file
config = UltimaScraperAPIConfig.from_json_file("config.json")

# Or create programmatically
config = UltimaScraperAPIConfig()
```

### Environment Variables

```bash
# Set up your credentials
export ONLYFANS_COOKIE="your_cookie_value"
export ONLYFANS_USER_AGENT="Mozilla/5.0 ..."
export ONLYFANS_XBC="your_x-bc_token"
```

Then load them in your code:

```python
import os

auth_json = {
    "cookie": os.getenv("ONLYFANS_COOKIE"),
    "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
    "x-bc": os.getenv("ONLYFANS_XBC")
}
```

### Proxy Configuration

Configure HTTP, HTTPS, or SOCKS proxies:

```python
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Network, Proxy

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(
            http="http://proxy.example.com:8080",
            https="https://proxy.example.com:8080",
            # Or SOCKS proxy
            # http="socks5://proxy.example.com:1080"
        )
    )
)
```

### Redis Configuration

Enable Redis for caching and session management:

```python
from ultima_scraper_api.config import Redis

config = UltimaScraperAPIConfig(
    redis=Redis(
        host="localhost",
        port=6379,
        db=0,
        password="your_password"  # Optional
    )
)
```

For complete configuration options, see the [Configuration Guide](https://ultimahoarder.github.io/UltimaScraperAPI/getting-started/configuration/).

## 📖 Usage Examples

### Fetching Subscriptions

```python
async with api.login_context(auth_json) as authed:
    # Get all active subscriptions
    subscriptions = await authed.get_subscriptions()
    
    for sub in subscriptions:
        user = sub.user
        print(f"{user.username} - Subscribed: {sub.subscribed_at}")
        print(f"  Expires: {sub.expires_at}")
        print(f"  Price: ${sub.price}")
```

### Getting Messages

```python
async with api.login_context(auth_json) as authed:
    # Get a specific user
    user = await authed.get_user("username")
    
    # Fetch message conversation
    messages = await user.get_messages(limit=50)
    
    for msg in messages:
        print(f"[{msg.created_at}] {msg.from_user.username}: {msg.text}")
        
        # Check for media attachments
        if msg.media:
            print(f"  Attachments: {len(msg.media)} media files")
```

### Downloading Stories

```python
import aiofiles

async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    
    # Get active stories
    stories = await user.get_stories()
    
    for story in stories:
        if story.media:
            for media in story.media:
                # Download media content
                content = await media.download()
                
                # Save to file
                filename = f"stories/{media.filename}"
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(content)
                    
                print(f"Downloaded: {filename}")
```

### Pagination and Batch Processing

```python
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    
    # Fetch all posts with pagination
    all_posts = []
    offset = 0
    limit = 50
    
    while True:
        posts = await user.get_posts(limit=limit, offset=offset)
        if not posts:
            break
            
        all_posts.extend(posts)
        offset += limit
        
        print(f"Fetched {len(all_posts)} posts so far...")
    
    print(f"Total posts: {len(all_posts)}")
```

### Concurrent Operations

```python
import asyncio

async with api.login_context(auth_json) as authed:
    # Get multiple users concurrently
    usernames = ["user1", "user2", "user3"]
    
    tasks = [authed.get_user(username) for username in usernames]
    users = await asyncio.gather(*tasks, return_exceptions=True)
    
    for username, user in zip(usernames, users):
        if isinstance(user, Exception):
            print(f"Error fetching {username}: {user}")
        else:
            print(f"Fetched: {user.username} - {user.posts_count} posts")
```

For more examples and patterns, see the [Working with APIs Guide](https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/working-with-apis/).

## 🛠️ Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/UltimaHoarder/UltimaScraperAPI.git
cd UltimaScraperAPI

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install in development mode with dev dependencies
uv pip install -e ".[dev]"
# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=ultima_scraper_api --cov-report=html

# Run specific test file
pytest tests/test_onlyfans.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code with Black
black ultima_scraper_api/ tests/

# Check formatting without changing files
black --check ultima_scraper_api/

# Type checking (if using mypy)
mypy ultima_scraper_api/
```

### Building Documentation

```bash
# Serve documentation locally with live reload
uv run mkdocs serve -a localhost:8001
# Open http://localhost:8001 in your browser

# Build static documentation site
uv run mkdocs build --clean

# Deploy to GitHub Pages
uv run mkdocs gh-deploy
```

### Using Nox for Automation

```bash
# Run all sessions (tests, linting, docs)
nox

# Run specific session
nox -s tests
nox -s lint
nox -s docs
```

For detailed contribution guidelines, see the [Contributing Guide](https://ultimahoarder.github.io/UltimaScraperAPI/development/contributing/).

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](https://ultimahoarder.github.io/UltimaScraperAPI/development/contributing/) for details on:

- Code of conduct
- Development setup
- Submitting pull requests
- Writing tests
- Documentation standards

## 📦 Project Structure

```
UltimaScraperAPI/
├── ultima_scraper_api/       # Main package
│   ├── apis/                 # Platform-specific APIs
│   │   ├── onlyfans/        # OnlyFans implementation
│   │   ├── fansly/          # Fansly implementation (WIP)
│   │   └── loyalfans/       # LoyalFans implementation (WIP)
│   ├── classes/             # Utility classes
│   ├── helpers/             # Helper functions
│   ├── managers/            # Session/scrape managers
│   └── models/              # Data models
├── documentation/           # MkDocs documentation
├── tests/                   # Test files
├── typings/                 # Type stubs
└── pyproject.toml          # Project configuration
```

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** - see the [LICENSE](./LICENSE) file for details.

### What This Means

- ✅ You can use this commercially
- ✅ You can modify the code
- ✅ You can distribute it
- ⚠️ You must disclose source code when distributing
- ⚠️ You must use the same license for derivatives
- ⚠️ Network use requires source code disclosure

## ⚠️ Disclaimer

This software is provided for **educational and research purposes**. Users are responsible for complying with the terms of service of any platforms they interact with using this software.

## 🙏 Acknowledgments

Built with industry-leading open source libraries:

- **[aiohttp](https://github.com/aio-libs/aiohttp)** - Async HTTP client/server framework
- **[Pydantic](https://github.com/pydantic/pydantic)** - Data validation using Python type hints
- **[httpx](https://github.com/encode/httpx)** - Modern HTTP client
- **[Redis](https://redis.io/)** - In-memory data structure store for caching
- **[websockets](https://github.com/python-websockets/websockets)** - WebSocket client and server
- **[MkDocs Material](https://squidfunk.github.io/mkdocs-material/)** - Beautiful documentation site generator
- **[pytest](https://pytest.org/)** - Testing framework
- **[Black](https://github.com/psf/black)** - Code formatter

Special thanks to all contributors and the open source community!

## 📞 Support & Community

- 📖 **[Documentation](https://ultimahoarder.github.io/UltimaScraperAPI/)** - Comprehensive guides and API reference
- 🐛 **[Issue Tracker](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)** - Report bugs or request features
- 💬 **[Discussions](https://github.com/UltimaHoarder/UltimaScraperAPI/discussions)** - Ask questions and share ideas
- 📦 **[Releases](https://github.com/UltimaHoarder/UltimaScraperAPI/releases)** - Version history and changelogs

### Getting Help

If you encounter issues:

1. Check the [documentation](https://ultimahoarder.github.io/UltimaScraperAPI/) first
2. Search [existing issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues) for similar problems
3. Create a new issue with a detailed description and minimal reproduction example
4. Join the [discussions](https://github.com/UltimaHoarder/UltimaScraperAPI/discussions) for community support

---

**Made with ❤️ by UltimaHoarder**
