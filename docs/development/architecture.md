# Architecture

Understanding the architecture and design of UltimaScraperAPI.

## Overview

UltimaScraperAPI is designed with **modularity**, **extensibility**, and **maintainability** in mind. The architecture follows a layered approach with clear separation of concerns, enabling support for multiple content platforms while maintaining code reusability.

### Design Principles

1. **Modular Design** - Each platform is independent with shared core services
2. **Async-First** - All I/O operations use async/await patterns
3. **Type Safety** - Pydantic v2 for runtime validation and type hints
4. **Separation of Concerns** - Clear boundaries between layers
5. **Extensibility** - Easy to add new platforms or features
6. **Resource Management** - Context managers for automatic cleanup

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│        (User Scripts, CLI Tools, External Integrations)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ OnlyFans    │  │   Fansly    │  │ LoyalFans   │         │
│  │ API (Stable)│  │  API (WIP)  │  │  API (WIP)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Core Services                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Stream  │  │ API Stream   │  │ User Stream  │      │
│  │              │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Scrape Mgr   │  │ Session Mgr  │  │   Job Mgr    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ HTTP Client  │  │   Redis      │  │  WebSocket   │      │
│  │  (aiohttp)   │  │   Cache      │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Helpers     │  │   Models     │  │    Config    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

### Complete Directory Layout

```
ultima_scraper_api/
├── __init__.py                      # Package initialization
├── __main__.py                      # CLI entry point
├── config.py                        # Configuration classes
├── py.typed                         # Type hints marker
│
├── apis/                            # Platform-specific APIs
│   ├── __init__.py
│   ├── api_helper.py                # HTTP request utilities
│   ├── api_streamliner.py           # API optimization layer
│   ├── auth_streamliner.py          # Authentication streamlining
│   ├── user_streamliner.py          # User operation streamlining
│   ├── background_tasks.py          # Async background tasks
│   │
│   ├── onlyfans/                    # OnlyFans implementation
│   │   ├── __init__.py
│   │   ├── onlyfans.py              # Main OnlyFans API class
│   │   ├── authenticator.py         # OnlyFans authentication
│   │   ├── classes/                 # OnlyFans data models
│   │   │   ├── auth_model.py        # Authenticated user model
│   │   │   ├── user_model.py        # User data model
│   │   │   ├── post_model.py        # Post data model
│   │   │   ├── message_model.py     # Message data model
│   │   │   ├── story_model.py       # Story data model
│   │   │   ├── media_model.py       # Media data model
│   │   │   └── extras.py            # Additional models
│   │   └── content_downloader.py    # Content download handler
│   │
│   ├── fansly/                      # Fansly implementation (WIP)
│   │   └── ...
│   │
│   └── loyalfans/                   # LoyalFans implementation (WIP)
│       └── ...
│
├── managers/                        # Service managers
│   ├── __init__.py
│   ├── session_manager.py           # HTTP session management
│   ├── scrape_manager.py            # Scraping orchestration
│   ├── job_manager/                 # Background job processing
│   │   ├── __init__.py
│   │   └── ...
│   ├── redis/                       # Redis integration
│   │   ├── __init__.py
│   │   └── ...
│   └── websocket_manager/           # WebSocket connections
│       ├── __init__.py
│       └── ...
│
├── models/                          # Shared data models
│   ├── __init__.py
│   └── subscription_model.py        # Subscription model
│
├── helpers/                         # Utility functions
│   ├── __init__.py
│   ├── identifier_helper.py         # ID parsing/validation
│   └── main_helper.py               # General utilities
│
└── classes/                         # Base classes
    ├── __init__.py
    ├── make_settings.py             # Settings factory
    └── prepare_webhooks.py          # Webhook configuration
```

---

## Core Components

### 1. API Layer

Each platform has its own independent API implementation following a common interface pattern.

#### OnlyFans API (`apis/onlyfans/`)

**Status:** ✅ Stable, Production-Ready

**Key Components:**

```python
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI

# Main API class
api = OnlyFansAPI(config)

# Authentication
authenticator = api.get_authenticator()
auth = await authenticator.login(credentials)

# Data models
from ultima_scraper_api.apis.onlyfans.classes import (
    OnlyFansAuthModel,    # Authenticated user with API methods
    UserModel,            # User profile data
    PostModel,            # Post content
    MessageModel,         # Direct messages
    StoryModel,           # Stories/highlights
    MediaModel            # Media files (images, videos)
)
```

**Responsibilities:**
- Platform-specific API endpoint management
- Request/response handling with proper headers
- Data transformation from API responses to models
- Error handling and retry logic
- Rate limiting compliance

**Key Features:**
- Full CRUD operations for content
- Subscription management
- Payment/transaction handling
- Media download with DRM support
- WebSocket for real-time updates

#### Fansly API (`apis/fansly/`)

**Status:** ⚠️ Work in Progress

**Available:**
- Basic authentication
- User profile retrieval
- Limited content access

**Planned:**
- Full content downloading
- Messaging support
- Transaction history

#### LoyalFans API (`apis/loyalfans/`)

**Status:** ⚠️ Work in Progress

**Available:**
- Basic authentication
- User profile retrieval (basic)

**Planned:**
- Content downloading
- Full API coverage

---

### 2. Authentication System

Multi-layer authentication system with platform-specific implementations.

#### Authentication Flow

```
User Credentials
        ↓
┌──────────────────────┐
│  AuthStreamliner     │  ← Generic authentication interface
│  - Validates format  │
│  - Prepares data     │
│  - Session init      │
└──────────────────────┘
        ↓
┌──────────────────────┐
│  Platform Authenticator │  ← Platform-specific logic
│  - API handshake      │
│  - Token exchange     │
│  - Cookie management  │
└──────────────────────┘
        ↓
┌──────────────────────┐
│  AuthModel           │  ← Authenticated session
│  - User data         │
│  - API methods       │
│  - Session state     │
└──────────────────────┘
```

#### Implementation Example

```python
# Generic interface (auth_streamliner.py)
class AuthStreamliner:
    """Base authentication streamliner"""
    
    async def authenticate(self, credentials: dict):
        """Generic authentication"""
        pass

# Platform-specific (onlyfans/authenticator.py)
class OnlyFansAuthenticator:
    """OnlyFans-specific authentication"""
    
    async def login(self, auth_details: dict) -> OnlyFansAuthModel:
        """
        Authenticate with OnlyFans API
        
        Args:
            auth_details: {
                "cookie": "auth_id=...",
                "user-agent": "Mozilla/5.0...",
                "x-bc": "token123..."
            }
        
        Returns:
            OnlyFansAuthModel with authenticated session
        """
        # Validate credentials
        # Create session
        # Exchange tokens
        # Return authenticated model
```

#### Credential Management

**Required Credentials:**

| Platform | Cookie | User-Agent | Token | Notes |
|----------|--------|------------|-------|-------|
| OnlyFans | ✅ `auth_id` | ✅ Required | ✅ `x-bc` | All required |
| Fansly | ✅ Auth token | ✅ Required | ❌ Optional | Cookie-based |
| LoyalFans | ✅ Session | ✅ Required | ❌ Optional | Session-based |

**Security Features:**
- Credentials never logged
- Secure session storage (Redis encryption optional)
- Automatic token refresh
- Session expiration handling

---

### 3. Session Management (`managers/session_manager.py`)

Centralized HTTP session management with connection pooling and optional Redis integration.

#### Architecture

```
┌─────────────────────────────────────────┐
│         SessionManager                   │
│  ┌───────────────────────────────────┐  │
│  │  Connection Pool                  │  │
│  │  - aiohttp.TCPConnector          │  │
│  │  - Keep-alive                    │  │
│  │  - DNS caching                   │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Request Handler                  │  │
│  │  - Timeout management            │  │
│  │  - Retry logic                   │  │
│  │  - Error handling                │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Proxy Support                    │  │
│  │  - HTTP/HTTPS/SOCKS4/SOCKS5      │  │
│  │  - Proxy rotation                │  │
│  │  - Auth handling                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Redis Cache (Optional)              │
│  ┌───────────────────────────────────┐  │
│  │  Session Storage                  │  │
│  │  - Session state                 │  │
│  │  - Authentication tokens         │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Response Cache                   │  │
│  │  - API responses                 │  │
│  │  - User data                     │  │
│  │  - TTL management                │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

#### Key Features

**1. Connection Pooling**
```python
import aiohttp

connector = aiohttp.TCPConnector(
    limit=100,              # Max total connections
    limit_per_host=30,      # Max per host
    ttl_dns_cache=300,      # DNS cache TTL (seconds)
    keepalive_timeout=60,   # Keep-alive timeout
    force_close=False,      # Reuse connections
    enable_cleanup_closed=True
)

session = aiohttp.ClientSession(connector=connector)
```

**2. Timeout Management**
```python
from ultima_scraper_api.config import Network

network_config = Network(
    timeout=30,              # Default timeout
    max_read_timeout=120,    # Max read timeout
    max_connect_timeout=10   # Max connect timeout
)
```

**3. Proxy Support**
```python
from ultima_scraper_api.config import Proxy

proxy = Proxy(
    protocol="socks5",
    host="proxy.example.com",
    port=1080,
    username="user",
    password="pass"
)
```

**4. Redis Integration**
```python
from ultima_scraper_api.config import Redis

redis_config = Redis(
    host="localhost",
    port=6379,
    db=0,
    password=None
)
```

See the [Session Management Guide](../user-guide/session-management.md) for detailed usage.

---

### 4. Data Models (`apis/*/classes/`)

Pydantic v2 models for type-safe data validation and transformation.

#### Model Hierarchy

```
BaseModel (Pydantic)
    ↓
┌─────────────────────────────────────┐
│     OnlyFans Models                  │
├─────────────────────────────────────┤
│  OnlyFansAuthModel                  │  ← Authenticated user
│    - id, username, email            │
│    - get_user(), get_users()        │
│    - get_posts(), get_messages()    │
│    - send_message()                 │
│    - get_transactions()             │
│                                     │
│  UserModel                          │  ← User profile
│    - id, username, name             │
│    - avatar, header, bio            │
│    - posts_count, photos_count      │
│    - get_posts(), get_stories()     │
│    - subscribe(), unsubscribe()     │
│                                     │
│  PostModel                          │  ← Post content
│    - id, text, price                │
│    - media: list[MediaModel]        │
│    - is_opened, is_archived         │
│    - buy(), favorite()              │
│                                     │
│  MessageModel                       │  ← Direct message
│    - id, text, price                │
│    - from_user: UserModel           │
│    - media: list[MediaModel]        │
│    - is_opened, created_at          │
│                                     │
│  StoryModel                         │  ← Story/highlight
│    - id, created_at                 │
│    - media: list[MediaModel]        │
│    - is_ready, is_opened            │
│                                     │
│  MediaModel                         │  ← Media file
│    - id, type (photo/video)         │
│    - source: dict (URLs, qualities) │
│    - preview, thumb                 │
│    - download()                     │
└─────────────────────────────────────┘
```

#### Example Model Definition

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UserModel(BaseModel):
    """OnlyFans user profile model"""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )
    
    # Required fields
    id: int | str
    username: str
    name: str
    
    # Optional fields with defaults
    avatar: str | None = None
    header: str | None = None
    bio: str | None = None
    location: str | None = None
    website: str | None = None
    
    # Statistics
    posts_count: int = 0
    photos_count: int = 0
    videos_count: int = 0
    audios_count: int = 0
    subscribers_count: int = 0
    
    # Timestamps
    created_at: datetime | None = None
    joined_at: datetime | None = None
    
    # Status flags
    is_verified: bool = False
    is_subscribed: bool = False
    can_dm: bool = True
    
    # Methods
    async def get_posts(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> list["PostModel"]:
        """Fetch user's posts"""
        pass
    
    async def get_stories(self) -> list["StoryModel"]:
        """Fetch user's stories"""
        pass
```

#### Model Benefits

| Feature | Benefit |
|---------|---------|
| **Type Hints** | IDE autocomplete, static analysis |
| **Validation** | Runtime data validation |
| **Serialization** | JSON/dict conversion |
| **Immutability** | Optional frozen models |
| **Custom Validators** | Business logic validation |
| **Computed Fields** | Derived properties |

#### Example Usage

```python
# Create from API response
user_data = {
    "id": 12345,
    "username": "example",
    "name": "Example User",
    "posts_count": 150
}
user = UserModel(**user_data)

# Type-safe access
print(user.username)  # ✅ IDE knows this is str
print(user.posts_count)  # ✅ IDE knows this is int

# Validation
try:
    invalid_user = UserModel(id="invalid")  # ❌ Will fail
except ValidationError as e:
    print(e)

# Serialization
user_dict = user.model_dump()
user_json = user.model_dump_json()

# Updating
user.posts_count += 1  # Validates new value
```

---

### 5. Helper System

Utility modules providing reusable functionality across the framework.

#### Helper Modules

```python
ultima_scraper_api/
├── helpers/
│   ├── identifier_helper.py  # ID parsing/validation
│   └── main_helper.py        # General utilities
├── apis/
│   ├── api_helper.py         # HTTP utilities
│   ├── api_streamliner.py    # API optimization
│   ├── auth_streamliner.py   # Auth streamlining
│   └── user_streamliner.py   # User operations
```

#### API Helper (`apis/api_helper.py`)

HTTP request utilities and response handling.

```python
from ultima_scraper_api.apis.api_helper import APIHelper

class APIHelper:
    """HTTP request utilities"""
    
    async def make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None
    ):
        """Make HTTP request with retry logic"""
        pass
    
    def prepare_headers(self, auth_token: str) -> dict:
        """Prepare request headers"""
        pass
    
    def handle_response(self, response):
        """Process API response"""
        pass
```

#### API Streamliner (`apis/api_streamliner.py`)

Optimizes API calls with caching, batching, and request deduplication.

```python
from ultima_scraper_api.apis.api_streamliner import APIStreamliner

class APIStreamliner:
    """API call optimization"""
    
    async def batch_requests(self, requests: list):
        """Batch multiple requests"""
        pass
    
    async def cache_response(self, key: str, data: dict):
        """Cache API response"""
        pass
    
    async def deduplicate_requests(self, requests: list):
        """Remove duplicate requests"""
        pass
```

#### User Streamliner (`apis/user_streamliner.py`)

Streamlines user-related operations with efficient data fetching.

```python
from ultima_scraper_api.apis.user_streamliner import UserStreamliner

class UserStreamliner:
    """User operation optimization"""
    
    async def get_users_batch(self, user_ids: list[int]):
        """Fetch multiple users efficiently"""
        pass
    
    async def refresh_user_data(self, user_id: int):
        """Refresh cached user data"""
        pass
```

#### Identifier Helper (`helpers/identifier_helper.py`)

ID parsing, validation, and normalization.

```python
from ultima_scraper_api.helpers.identifier_helper import parse_user_id

def parse_user_id(identifier: str | int) -> int:
    """Parse and validate user ID"""
    pass

def extract_username(url: str) -> str:
    """Extract username from URL"""
    pass

def validate_identifier(identifier: str) -> bool:
    """Validate identifier format"""
    pass
```

#### Main Helper (`helpers/main_helper.py`)

General utility functions.

```python
from ultima_scraper_api.helpers.main_helper import (
    format_timestamp,
    calculate_hash,
    sanitize_filename
)

def format_timestamp(dt: datetime) -> str:
    """Format datetime for display"""
    pass

def calculate_hash(data: bytes) -> str:
    """Calculate data hash"""
    pass

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem"""
    pass
```

---

### 6. Manager System

Service managers for orchestrating complex operations.

#### Scrape Manager (`managers/scrape_manager.py`)

Coordinates scraping operations across platforms.

```python
from ultima_scraper_api.managers.scrape_manager import ScrapeManager

class ScrapeManager:
    """Scraping orchestration"""
    
    async def scrape_user(self, user_id: int):
        """Scrape all user content"""
        pass
    
    async def scrape_posts(self, post_ids: list[int]):
        """Scrape specific posts"""
        pass
    
    async def monitor_updates(self, user_ids: list[int]):
        """Monitor for new content"""
        pass
```

#### Job Manager (`managers/job_manager/`)

Background job processing with queue management.

```python
from ultima_scraper_api.managers.job_manager import JobManager

class JobManager:
    """Background job processing"""
    
    async def enqueue_job(self, job_type: str, payload: dict):
        """Add job to queue"""
        pass
    
    async def process_jobs(self):
        """Process queued jobs"""
        pass
    
    def get_job_status(self, job_id: str) -> dict:
        """Get job status"""
        pass
```

#### WebSocket Manager (`managers/websocket_manager/`)

Real-time WebSocket connection management.

```python
from ultima_scraper_api.managers.websocket_manager import WebSocketManager

class WebSocketManager:
    """WebSocket connection management"""
    
    async def connect(self, endpoint: str):
        """Establish WebSocket connection"""
        pass
    
    async def send_message(self, message: dict):
        """Send message through WebSocket"""
        pass
    
    async def listen(self, callback):
        """Listen for incoming messages"""
        pass
```

## Design Patterns

### 1. Context Manager Pattern

Used for session management:

```python
async with api.login_context(auth_json) as authed:
    # Session automatically managed
    user = await authed.get_user("username")
# Session automatically closed
```

**Benefits:**
- Automatic resource cleanup
- Exception safety
- Clear scope

### 2. Factory Pattern

API creation:

```python
def create_api(platform: str, config: Config):
    apis = {
        "onlyfans": OnlyFansAPI,
        "fansly": FanslyAPI,
        "loyalfans": LoyalFansAPI,
    }
    return apis[platform](config)
```

### 3. Strategy Pattern

Different authentication strategies:

```python
class AuthStrategy:
    async def authenticate(self, credentials): pass

class CookieAuth(AuthStrategy):
    async def authenticate(self, credentials):
        # Cookie-based auth
        pass

class TokenAuth(AuthStrategy):
    async def authenticate(self, credentials):
        # Token-based auth
        pass
```

### 4. Repository Pattern

Data access abstraction:

```python
class UserRepository:
    async def get_by_id(self, user_id: int) -> User:
        pass
    
    async def get_by_username(self, username: str) -> User:
        pass
    
    async def save(self, user: User) -> None:
        pass
```

## Async Architecture

### Event Loop Management

```python
import asyncio

# Single event loop for all operations
loop = asyncio.get_event_loop()

# Concurrent operations
async def fetch_multiple_users(usernames):
    tasks = [fetch_user(name) for name in usernames]
    return await asyncio.gather(*tasks)
```

### Concurrency Control

```python
import asyncio

class RateLimiter:
    def __init__(self, rate: int):
        self.semaphore = asyncio.Semaphore(rate)
    
    async def acquire(self):
        await self.semaphore.acquire()
    
    def release(self):
        self.semaphore.release()
```

---

## Data Flow

### Complete Request Flow

```
┌──────────────────────────────────────────────────────────────┐
│                      User Application                         │
│  user = await auth.get_user("username")                      │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│               OnlyFansAuthModel.get_user()                   │
│  - Validates input                                           │
│  - Checks cache                                              │
│  - Prepares request                                          │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    API Helper Layer                          │
│  - Constructs endpoint URL                                   │
│  - Adds authentication headers                               │
│  - Applies rate limiting                                     │
│  - Adds retry logic                                          │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                   Session Manager                            │
│  - Gets connection from pool                                 │
│  - Applies proxy if configured                               │
│  - Sets timeouts                                             │
│  - Manages keep-alive                                        │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│               HTTP Client (aiohttp)                          │
│  - Makes actual HTTP request                                 │
│  - Handles SSL/TLS                                           │
│  - Manages TCP connection                                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                  Platform API Server                         │
│  GET /api2/v2/users/{username}                              │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    Response Handling                         │
│  - Status code validation                                    │
│  - Error handling                                            │
│  - JSON parsing                                              │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                 Pydantic Model Creation                      │
│  user = UserModel(**response_data)                           │
│  - Type validation                                           │
│  - Field transformation                                      │
│  - Custom validators                                         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    Caching Layer                             │
│  - Store in Redis (if enabled)                               │
│  - Set TTL                                                   │
│  - Update local cache                                        │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                   Return to User                             │
│  user: UserModel                                             │
└──────────────────────────────────────────────────────────────┘
```

### Authentication Flow Detailed

```
┌──────────────────────────────────────────────────────────────┐
│                  User Provides Credentials                    │
│  credentials = {                                             │
│      "cookie": "auth_id=123...",                            │
│      "user-agent": "Mozilla/5.0...",                        │
│      "x-bc": "token123..."                                  │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              OnlyFansAuthenticator.login()                   │
│  Step 1: Validate Credentials                                │
│  - Check cookie format                                       │
│  - Validate User-Agent                                       │
│  - Verify x-bc token                                         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│  Step 2: Create HTTP Session                                │
│  - Initialize aiohttp.ClientSession                          │
│  - Configure headers (User-Agent, Cookie)                    │
│  - Set up connection pool                                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│  Step 3: API Handshake                                       │
│  GET /api2/v2/users/me                                       │
│  - Validates session                                         │
│  - Retrieves user data                                       │
│  - Confirms authentication                                   │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│  Step 4: Create Auth Model                                   │
│  auth = OnlyFansAuthModel(                                   │
│      id=user_data["id"],                                     │
│      username=user_data["username"],                         │
│      session=session,                                        │
│      ...                                                     │
│  )                                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│  Step 5: Store Session (Optional)                           │
│  if redis_enabled:                                           │
│      redis.set(                                              │
│          f"session:{user_id}",                              │
│          session_data,                                       │
│          ex=3600                                             │
│      )                                                       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│             Return Authenticated Model                        │
│  return auth  # OnlyFansAuthModel with API methods          │
└──────────────────────────────────────────────────────────────┘
```

### Content Download Flow

```
┌──────────────────────────────────────────────────────────────┐
│          User Requests Content Download                       │
│  await media.download(save_path="./downloads")               │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              Check if DRM Protected                          │
│  if media.is_drm_protected:                                  │
│      # Special handling for DRM                              │
│  else:                                                       │
│      # Direct download                                       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│            Get Download URL (may refresh if expired)         │
│  url = media.source["url"]                                   │
│  if url_expired:                                             │
│      url = await refresh_media_url(media.id)                │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                 Stream Download with Progress                │
│  async with session.get(url) as response:                    │
│      with open(save_path, 'wb') as f:                        │
│          async for chunk in response.content.iter_chunked(): │
│              f.write(chunk)                                  │
│              progress_bar.update(len(chunk))                 │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              DRM Decryption (if needed)                      │
│  if is_drm_protected:                                        │
│      decrypted = await drm_handler.decrypt(                  │
│          encrypted_file=save_path,                           │
│          license_url=media.drm_license_url                   │
│      )                                                       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                   Verify Download                            │
│  - Check file size                                           │
│  - Verify checksum (if available)                            │
│  - Update metadata                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                Return Downloaded File Path                    │
│  return save_path                                            │
└──────────────────────────────────────────────────────────────┘
```

### WebSocket Event Flow

```
┌──────────────────────────────────────────────────────────────┐
│             Establish WebSocket Connection                    │
│  ws_manager = WebSocketManager(auth)                         │
│  await ws_manager.connect()                                  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                 Platform Sends Event                         │
│  {                                                           │
│      "type": "new_message",                                  │
│      "data": {...}                                           │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              WebSocket Manager Receives                      │
│  - Parses JSON                                               │
│  - Validates event type                                      │
│  - Routes to handler                                         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                Create Event Model                            │
│  event = MessageEvent(**event_data)                          │
│  message = MessageModel(**event.data)                        │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│               Trigger User Callback                          │
│  await user_callback(event, message)                         │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│            Update Local State/Cache                          │
│  - Add message to cache                                      │
│  - Update Redis if enabled                                   │
│  - Emit internal events                                      │
└──────────────────────────────────────────────────────────────┘
```

## Error Handling

### Exception Hierarchy

```python
class UltimaScraperAPIError(Exception):
    """Base exception"""
    pass

class AuthenticationError(UltimaScraperAPIError):
    """Auth-related errors"""
    pass

class APIError(UltimaScraperAPIError):
    """API request errors"""
    pass

class RateLimitError(APIError):
    """Rate limiting errors"""
    pass

class NotFoundError(APIError):
    """Resource not found"""
    pass
```

### Error Recovery

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()
```

## Extensibility

### Adding New Platforms

1. **Create platform directory**
2. **Implement API interface**
3. **Define data models**
4. **Add authenticator**
5. **Register in factory**

### Plugin System (Future)

```python
class Plugin:
    def on_user_fetched(self, user: User):
        """Hook for user fetch"""
        pass
    
    def on_post_downloaded(self, post: Post):
        """Hook for post download"""
        pass
```

## Performance Considerations

### Connection Pooling

```python
connector = aiohttp.TCPConnector(
    limit=100,           # Total connections
    limit_per_host=30,   # Per host
    ttl_dns_cache=300    # DNS cache
)
```

### Caching Strategy

```python
# Memory cache for frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_user(user_id: int):
    return user_cache.get(user_id)

# Redis for distributed caching
async def get_user_from_cache(user_id: int):
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return User.parse_raw(cached)
    return None
```

## Security

### Credential Storage

- Never log credentials
- Use environment variables
- Support encryption at rest

### Session Security

- Automatic session expiration
- Secure token handling
- HTTPS enforcement

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
@pytest.mark.asyncio
async def test_user_model():
    user = User(id=1, username="test")
    assert user.username == "test"
```

### Integration Tests

Test component interaction:

```python
@pytest.mark.asyncio
async def test_api_login():
    api = OnlyFansAPI(config)
    async with api.login_context(auth) as authed:
        assert authed.is_authed()
```

### Mocking External Services

```python
from unittest.mock import AsyncMock

mock_session = AsyncMock()
mock_session.get.return_value = mock_response
```

## Future Enhancements

- GraphQL API support
- WebSocket real-time updates
- Plugin architecture
- Advanced caching
- Metrics and monitoring
- Distributed tracing

## See Also

- [Contributing Guide](contributing.md)
- [Testing Guide](testing.md)
- [API Reference](../api-reference/onlyfans.md)
