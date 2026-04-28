# UltimaScraperAPI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-3.0.0b4-green.svg)](https://github.com/UltimaHoarder/UltimaScraperAPI/releases)
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
- 📡 **Typed Event Models**: Shared Redis pub/sub schemas for scrape and download progress
- 📈 **Progress Callbacks**: Per-page progress hooks for large post, story, and message scrapes
- 📊 **Type Safety**: Comprehensive type hints and validation with Pydantic v2
- 🔒 **DRM Support**: Widevine CDM integration for encrypted content
- 🧭 **URL Diagnostics**: Decode signed CDN URLs to detect expiry and IP locks
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
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPI
from ultima_scraper_api.config import UltimaScraperAPIConfig

async def main():
    # Initialize configuration
    config = UltimaScraperAPIConfig()
    
    # Initialize UltimaScraperAPI
    api = UltimaScraperAPI(config)
    await api.init()  # Initialize the API
    
    # Get OnlyFans API instance
    onlyfans_api = api.api_instances.OnlyFans
    
    # Authentication credentials
    # Obtain these from your browser's Network tab (F12)
    # See: https://ultimahoarder.github.io/UltimaScraperAPI/user-guide/authentication/
    auth_json = {
        "id": 123456,
        "cookie": "your_cookie_value",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc_token"
    }
    
    # Login with context manager for automatic cleanup
    authed = await onlyfans_api.login(auth_json=auth_json)
    
    if authed and authed.is_authed():
        # Get authenticated user info
        me = await authed.get_authed_user()
        print(f"Logged in as: {me.username}")
        
        # Get user profile
        user = await authed.get_user("username")
        if user:
            print(f"User: {user.username} ({user.name})")
            
            # Fetch user's posts
            posts = await user.get_posts(limit=10)
            print(f"Found {len(posts)} posts")
            
            # Download media from posts
            download_dir = Path("downloads")
            download_dir.mkdir(exist_ok=True)
            
            for post in posts:
                if post.media:
                    for media in post.media:
                        print(f"Downloading: {media.id}")
                        
                        # Get media URL using url_picker
                        from ultima_scraper_api.apis.onlyfans import url_picker
                        media_url = url_picker(post.get_author(), media)
                        
                        if media_url:
                            # Download media content
                            response = await authed.auth_session.request(
                                media_url.geturl(),
                                premade_settings=""
                            )
                            
                            if response:
                                content = await response.read()
                                
                                # Save to file
                                filename = f"{media.id}.{media.type}"
                                filepath = download_dir / filename
                                with open(filepath, 'wb') as f:
                                    f.write(content)
                                print(f"  ✓ Saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Downloading DRM-Protected Content

For DRM-protected content, you need to configure Widevine CDM and follow a multi-step process:

```python
import asyncio
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPI
from ultima_scraper_api.config import UltimaScraperAPIConfig, DRM

async def download_drm_content():
    # Configure DRM settings
    config = UltimaScraperAPIConfig()
    config.settings.drm.device_client_blob_filepath = Path("/path/to/device_client_id_blob")
    config.settings.drm.device_private_key_filepath = Path("/path/to/device_private_key")
    
    # Initialize API
    api = UltimaScraperAPI(config)
    await api.init()
    
    onlyfans_api = api.api_instances.OnlyFans
    auth_json = {
        "id": 123456,
        "cookie": "your_cookie_value",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc_token"
    }
    
    authed = await onlyfans_api.login(auth_json=auth_json)
    
    if authed and authed.is_authed():
        # Get DRM manager
        only_drm = authed.drm
        
        if only_drm:
            user = await authed.get_user("username")
            posts = await user.get_posts(limit=10)
            
            download_dir = Path("downloads")
            download_dir.mkdir(exist_ok=True)
            
            for post in posts:
                if post.media:
                    for media in post.media:
                        # Check if media has DRM protection
                        if media.files and media.files.drm:
                            print(f"Processing DRM-protected media: {media.id}")
                            
                            # Get cookies for DRM requests
                            cookies = media.files.drm.dash.__drm_media__.get_cookies()
                            
                            # Resolve DRM URLs and get decryption key
                            video_url, audio_url, key = await media.files.drm.resolve_drm()
                            
                            # Download encrypted video
                            response = await authed.auth_session.request(
                                video_url,
                                premade_settings="",
                                custom_cookies=cookies
                            )
                            
                            enc_video_filepath = download_dir / f"{video_url.split('/')[-1]}"
                            with open(enc_video_filepath, "wb") as f:
                                f.write(await response.read())
                            print(f"  Downloaded encrypted video: {enc_video_filepath.name}")
                            
                            # Download encrypted audio
                            response = await authed.auth_session.request(
                                audio_url,
                                premade_settings="",
                                custom_cookies=cookies
                            )
                            
                            enc_audio_filepath = download_dir / f"{audio_url.split('/')[-1]}"
                            with open(enc_audio_filepath, "wb") as f:
                                f.write(await response.read())
                            print(f"  Downloaded encrypted audio: {enc_audio_filepath.name}")
                            
                            # Decrypt files
                            decrypted_video = only_drm.decrypt_file(enc_video_filepath, key)
                            decrypted_audio = only_drm.decrypt_file(enc_audio_filepath, key)
                            print(f"  Decrypted video: {decrypted_video.name}")
                            print(f"  Decrypted audio: {decrypted_audio.name}")
                            
                            # Merge video and audio
                            output_filepath = download_dir / f"{media.id}_final.mp4"
                            future = only_drm.enqueue_merge_task(
                                output_filepath,
                                [decrypted_video, decrypted_audio]
                            )
                            
                            # Wait for merge to complete
                            success = await asyncio.wrap_future(future)
                            
                            if success:
                                print(f"  ✓ Merged to: {output_filepath.name}")
                                
                                # Clean up temporary files
                                enc_video_filepath.unlink()
                                enc_audio_filepath.unlink()
                                decrypted_video.unlink()
                                decrypted_audio.unlink()

if __name__ == "__main__":
    asyncio.run(download_drm_content())
```

**DRM Setup Requirements:**

1. **Widevine CDM Files**: You need valid Widevine CDM files:
   - `device_client_id_blob`: Client ID blob file
   - `device_private_key`: Private key file

2. **FFmpeg**: Required for merging video and audio streams
   ```bash
   # Install FFmpeg
   sudo apt install ffmpeg  # Ubuntu/Debian
   brew install ffmpeg      # macOS
   ```

3. **Configure in your config**:
   ```python
   config.settings.drm.device_client_blob_filepath = Path("/path/to/device_client_id_blob")
   config.settings.drm.device_private_key_filepath = Path("/path/to/device_private_key")
   ```

**Note**: DRM content requires proper Widevine CDM setup. Obtaining CDM files is beyond the scope of this documentation and must comply with applicable laws and terms of service.

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
export ONLYFANS_AUTH_ID="123456"
export ONLYFANS_COOKIE="your_cookie_value"
export ONLYFANS_USER_AGENT="Mozilla/5.0 ..."
export ONLYFANS_XBC="your_x-bc_token"
```

Then load them in your code:

```python
import os

auth_json = {
    "id": int(os.getenv("ONLYFANS_AUTH_ID", "0")),
    "cookie": os.getenv("ONLYFANS_COOKIE"),
    "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
    "x-bc": os.getenv("ONLYFANS_XBC")
}
```

### Proxy Configuration

Configure HTTP, HTTPS, or SOCKS proxies:

```python
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Proxy

config = UltimaScraperAPIConfig()
config.settings.network.proxies.append(
    Proxy(url="http://proxy.example.com:8080")
    # Or SOCKS proxy:
    # Proxy(url="socks5://proxy.example.com:1080")
)
```

### Redis Configuration

Enable Redis for caching and session management:

```python
from ultima_scraper_api.config import Redis

config = UltimaScraperAPIConfig()
config.settings.redis = Redis(
    host="localhost",
    port=6379,
    db=0,
    password="your_password"  # Optional
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
                # Resolve and download media content
                media_url = story.url_picker(media)
                if not media_url:
                    continue
                response = await authed.auth_session.request(
                    media_url.geturl(),
                    premade_settings=""
                )
                if not response:
                    continue
                content = await response.read()
                
                # Save to file
                filename = f"stories/{media.id}.{media.type}"
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(content)
                    
                print(f"Downloaded: {filename}")
```

### Pagination and Progress Tracking

`UserModel.get_posts`, `get_stories`, and `get_messages` accept an optional
`on_progress` callback (and `job_id` for Redis event correlation) so you can
stream progress as pages are fetched:

```python
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")

    async def on_progress(done_pages: int, total_pages: int, items_so_far: int):
        print(f"Posts: page {done_pages}/{total_pages} — {items_so_far} fetched")

    # Fetch all posts up to the user's total in one call (paginated internally)
    posts = await user.get_posts(on_progress=on_progress)

    # Or filter by date / label
    archived = await user.get_posts(label="archived")

    from datetime import datetime, timezone
    recent = await user.get_posts(
        after_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    print(f"Total posts: {len(posts)}")
```

### Search Chats (3.0.0b4+)

```python
async with api.login_context(auth_json) as authed:
    chats = await authed.search_chats("happy birthday", limit=50)
    for chat in chats:
        print(chat.user.username)
```

### Diagnosing Signed CDN URLs

```python
from ultima_scraper_api.helpers import diagnose_url

media_url = post.url_picker(media)
diag = diagnose_url(media_url.geturl()) if media_url else None
if diag:
    print(diag.get_diagnosis())  # e.g. "URL valid for ~5.2 hours" or "URL expired ..."
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
├── docs/                    # MkDocs documentation source
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
