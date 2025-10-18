# Session Management

Comprehensive guide to session management, Redis integration, connection pooling, and persistence in UltimaScraperAPI.

## Overview

UltimaScraperAPI provides robust session management built on `aiohttp` for asynchronous HTTP requests, with optional Redis integration for distributed caching and persistence.

**Key Features:**

- ✅ Automatic session lifecycle management with context managers
- ✅ Redis integration for distributed sessions and caching
- ✅ Connection pooling for optimal performance
- ✅ Session persistence and restoration
- ✅ Configurable timeouts and retry logic
- ✅ Concurrent session handling
- ✅ Session state monitoring and validation

!!! tip "Why Session Management Matters"
    Proper session management ensures:
    
    - **Performance**: Reuse connections and cache responses
    - **Reliability**: Handle failures gracefully with retry logic
    - **Scalability**: Support multiple concurrent sessions
    - **Persistence**: Maintain state across application restarts
    - **Security**: Secure storage of sensitive session data

## Quick Start

### Basic Session Usage

The recommended way to manage sessions is with the `login_context` context manager:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc"
    }
    
    # Session is automatically created and cleaned up
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            # Session is active here
            user = await authed.get_user("username")
            print(f"Connected: {user.username}")
    # Session is automatically closed here

if __name__ == "__main__":
    asyncio.run(main())
```

### Session Lifecycle

```python
# 1. Session Creation
async with api.login_context(auth_json) as authed:
    # 2. Session is active - make API calls
    me = await authed.get_me()
    posts = await me.get_posts()
    
    # 3. Session validation
    if authed.is_authed():
        print("Session is valid")
    
# 4. Session cleanup (automatic)
# - Connections closed
# - Resources freed
# - Temporary data cleared
```

### Manual Session Management (Advanced)

For complete control over session lifecycle:

```python
from ultima_scraper_api import OnlyFansAPI
from ultima_scraper_api.apis.onlyfans.authenticator import OnlyFansAuthenticator
from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails

async def manual_session():
    api = OnlyFansAPI()
    
    # Create auth details
    auth_details = AuthDetails(
        cookie="your_cookie",
        user_agent="your_user_agent",
        x_bc="your_x-bc"
    )
    
    # Create authenticator
    authenticator = OnlyFansAuthenticator(api, auth_details)
    
    try:
        # Login
        auth_model = await authenticator.login()
        
        # Use session
        user = await auth_model.get_user("username")
        print(f"User: {user.username}")
        
    finally:
        # Always close
        await authenticator.close()
```

## Session Persistence

### Saving Sessions

Save session data for later use:

```python
import json

async with api.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        # Export session data
        session_data = await authed.export_session()
        
        # Save to file
        with open("session.json", "w") as f:
            json.dump(session_data, f)
```

### Loading Sessions

Restore a previously saved session:

```python
import json

# Load session data
with open("session.json") as f:
    session_data = json.load(f)

# Restore session
async with api.login_context(session_data) as authed:
    # Use restored session
    user = await authed.get_user("username")
```

## Connection Pooling

### Why Connection Pooling?

Connection pooling improves performance by:

- **Reusing Connections**: Avoid TCP handshake overhead
- **Limiting Connections**: Prevent resource exhaustion
- **DNS Caching**: Reduce DNS lookup time
- **Keep-Alive**: Maintain persistent connections

### Configure Connection Pool

Optimize performance with `aiohttp` connection pooling:

```python
import aiohttp
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig
from ultima_scraper_api.config import Network

# Create custom connector with optimized settings
connector = aiohttp.TCPConnector(
    limit=100,                     # Total connection limit across all hosts
    limit_per_host=30,             # Per-host connection limit
    ttl_dns_cache=300,             # DNS cache TTL (5 minutes)
    enable_cleanup_closed=True,    # Clean up closed connections
    force_close=False,             # Reuse connections
    keepalive_timeout=30,          # Keep-alive timeout (seconds)
)

# Configure network settings
config = UltimaScraperAPIConfig(
    network=Network(
        timeout=60,                # Request timeout
        max_connections=100,       # Max concurrent connections
    )
)

api = OnlyFansAPI(config)
```

### Connection Pool Monitoring

Monitor connection pool health:

```python
class ConnectionPoolMonitor:
    def __init__(self, connector: aiohttp.TCPConnector):
        self.connector = connector
    
    def get_stats(self) -> dict:
        """Get connection pool statistics"""
        return {
            "total_connections": len(self.connector._conns),
            "acquired": len(self.connector._acquired),
            "acquired_per_host": {
                str(key): len(conns) 
                for key, conns in self.connector._acquired_per_host.items()
            }
        }
    
    def print_stats(self):
        """Print connection pool stats"""
        stats = self.get_stats()
        print(f"Connection Pool Stats:")
        print(f"  Total connections: {stats['total_connections']}")
        print(f"  Acquired: {stats['acquired']}")
        for host, count in stats['acquired_per_host'].items():
            print(f"  {host}: {count} connections")

# Usage
monitor = ConnectionPoolMonitor(connector)
monitor.print_stats()
```

### Connection Pool Best Practices

=== "✅ Do"
    ```python
    # Reuse connections
    connector = aiohttp.TCPConnector(
        limit=100,
        force_close=False,  # Reuse connections
        enable_cleanup_closed=True
    )
    
    # Set appropriate limits
    limit_per_host = 30  # Based on API rate limits
    
    # Enable DNS caching
    ttl_dns_cache = 300  # 5 minutes
    ```

=== "❌ Don't"
    ```python
    # Don't create new connector for each request
    for _ in range(100):
        connector = aiohttp.TCPConnector()  # Bad!
        # ...
    
    # Don't set limits too high
    connector = aiohttp.TCPConnector(
        limit=10000  # Too many connections!
    )
    
    # Don't disable connection reuse
    connector = aiohttp.TCPConnector(
        force_close=True  # Creates new connection each time
    )
    ```

### Concurrent Request Handling

Handle multiple concurrent requests efficiently:

```python
import asyncio

async def fetch_multiple_users(authed, usernames):
    """Fetch multiple users concurrently using connection pool"""
    async def fetch_user(username):
        try:
            user = await authed.get_user(username)
            return {"username": username, "success": True, "data": user}
        except Exception as e:
            return {"username": username, "success": False, "error": str(e)}
    
    # Create tasks
    tasks = [fetch_user(username) for username in usernames]
    
    # Execute concurrently (connection pool manages connections)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    
    print(f"✓ Successful: {len(successful)}")
    print(f"✗ Failed: {len(failed)}")
    
    return results

# Usage
usernames = ["user1", "user2", "user3", "user4", "user5"]
results = await fetch_multiple_users(authed, usernames)
```

## Session Timeout

### Configure Timeouts

Set timeout values for different operations:

```python
import aiohttp

timeout = aiohttp.ClientTimeout(
    total=60,      # Total timeout
    connect=10,    # Connection timeout
    sock_read=30,  # Socket read timeout
    sock_connect=10  # Socket connect timeout
)

# Apply timeout to requests
# Note: Check actual API implementation for usage
```

### Handling Timeouts

```python
from aiohttp import ClientTimeout, ServerTimeoutError
import asyncio

async def fetch_with_timeout(authed, username, timeout=30):
    try:
        user = await asyncio.wait_for(
            authed.get_user(username),
            timeout=timeout
        )
        return user
    except asyncio.TimeoutError:
        print(f"Request timed out after {timeout} seconds")
        return None
```

## Session State Management

### Checking Session State

```python
async with api.login_context(auth_json) as authed:
    # Check if authenticated
    if authed and authed.is_authed():
        print("Session is active")
        
        # Check session validity
        is_valid = await authed.validate_session()
        if is_valid:
            print("Session is valid")
        else:
            print("Session expired or invalid")
```

### Refreshing Sessions

```python
async def ensure_valid_session(api, auth_json):
    async with api.login_context(auth_json) as authed:
        if not authed or not authed.is_authed():
            # Re-authenticate
            async with api.login_context(auth_json, force_refresh=True) as new_authed:
                return new_authed
        return authed
```

## Redis Integration

### Why Use Redis?

Redis provides powerful features for session management:

- **Distributed Sessions**: Share sessions across multiple application instances
- **Caching**: Cache API responses to reduce load and improve speed
- **Persistence**: Survive application restarts
- **TTL Support**: Automatic expiration of old sessions
- **High Performance**: Sub-millisecond response times

### Configuring Redis

Configure Redis in your `UltimaScraperAPIConfig`:

```python
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Redis

config = UltimaScraperAPIConfig(
    redis=Redis(
        host="localhost",
        port=6379,
        db=0,
        password="your_redis_password",  # Optional
        socket_timeout=5,
        socket_connect_timeout=5,
        max_connections=50
    )
)

api = OnlyFansAPI(config)
```

### Environment Variables

Store Redis configuration in environment variables:

```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_secure_password
```

```python
import os
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Redis

# Load from environment
config = UltimaScraperAPIConfig(
    redis=Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD")
    )
)
```

### Session Storage in Redis

Store and retrieve sessions using Redis:

```python
import json
import redis.asyncio as redis
from datetime import timedelta

class RedisSessionManager:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = timedelta(hours=24)  # 24 hour sessions
    
    async def save_session(self, user_id: str, session_data: dict) -> bool:
        """Save session to Redis with TTL"""
        try:
            key = f"session:{user_id}"
            value = json.dumps(session_data)
            await self.redis.setex(key, self.session_ttl, value)
            print(f"✓ Session saved for {user_id}")
            return True
        except Exception as e:
            print(f"✗ Failed to save session: {e}")
            return False
    
    async def get_session(self, user_id: str) -> dict | None:
        """Retrieve session from Redis"""
        try:
            key = f"session:{user_id}"
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"✗ Failed to get session: {e}")
            return None
    
    async def delete_session(self, user_id: str) -> bool:
        """Delete session from Redis"""
        try:
            key = f"session:{user_id}"
            await self.redis.delete(key)
            print(f"✓ Session deleted for {user_id}")
            return True
        except Exception as e:
            print(f"✗ Failed to delete session: {e}")
            return False
    
    async def refresh_session(self, user_id: str) -> bool:
        """Extend session TTL"""
        try:
            key = f"session:{user_id}"
            await self.redis.expire(key, self.session_ttl)
            return True
        except Exception as e:
            print(f"✗ Failed to refresh session: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()

# Usage
async def main():
    manager = RedisSessionManager()
    
    try:
        # Save session
        session_data = {
            "cookie": "auth_cookie",
            "user_agent": "Mozilla/5.0...",
            "x-bc": "token",
            "created_at": "2025-10-18T10:00:00"
        }
        await manager.save_session("user123", session_data)
        
        # Retrieve session
        session = await manager.get_session("user123")
        if session:
            print(f"Session found: {session}")
        
        # Refresh session TTL
        await manager.refresh_session("user123")
        
        # Delete session
        await manager.delete_session("user123")
        
    finally:
        await manager.close()
```

### Response Caching with Redis

Cache API responses to improve performance:

```python
import hashlib
from typing import Any

class RedisCache:
    def __init__(self, redis_client, default_ttl=300):
        self.redis = redis_client
        self.default_ttl = default_ttl  # 5 minutes
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_str = ":".join(key_parts)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    async def get(self, prefix: str, *args) -> Any | None:
        """Get cached value"""
        key = self._make_key(prefix, *args)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(self, prefix: str, value: Any, ttl: int | None = None, *args) -> bool:
        """Set cached value"""
        key = self._make_key(prefix, *args)
        data = json.dumps(value)
        ttl = ttl or self.default_ttl
        await self.redis.setex(key, ttl, data)
        return True
    
    async def delete(self, prefix: str, *args) -> bool:
        """Delete cached value"""
        key = self._make_key(prefix, *args)
        await self.redis.delete(key)
        return True
    
    async def exists(self, prefix: str, *args) -> bool:
        """Check if key exists"""
        key = self._make_key(prefix, *args)
        return await self.redis.exists(key)

# Usage with API calls
async def get_user_cached(authed, username, cache):
    """Get user with caching"""
    # Try cache first
    cached = await cache.get("user", username)
    if cached:
        print(f"✓ Cache hit for {username}")
        return cached
    
    # Cache miss - fetch from API
    print(f"✗ Cache miss for {username} - fetching...")
    user = await authed.get_user(username)
    
    if user:
        # Cache for 10 minutes
        user_data = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "posts_count": user.posts_count
        }
        await cache.set("user", user_data, ttl=600, username)
    
    return user
```

### Redis Connection Pooling

Optimize Redis connections:

```python
import redis.asyncio as redis

# Create connection pool
pool = redis.ConnectionPool(
    host="localhost",
    port=6379,
    db=0,
    max_connections=50,
    decode_responses=True
)

# Create Redis client from pool
redis_client = redis.Redis(connection_pool=pool)

# Use across multiple operations
async def use_redis_pool():
    # Multiple operations share the same connection pool
    await redis_client.set("key1", "value1")
    await redis_client.set("key2", "value2")
    
    # Get values
    val1 = await redis_client.get("key1")
    val2 = await redis_client.get("key2")
    
    return val1, val2

# Close pool when done
await pool.disconnect()
```

## Concurrent Sessions

### Managing Multiple Sessions

```python
async def manage_multiple_sessions(accounts):
    tasks = []
    
    for account in accounts:
        auth_json = account["credentials"]
        api = OnlyFansAPI(config)
        
        async def process_account(api, auth):
            async with api.login_context(auth) as authed:
                if authed and authed.is_authed():
                    user = await authed.get_me()
                    return user
            return None
        
        task = process_account(api, auth_json)
        tasks.append(task)
    
    # Process all accounts concurrently
    results = await asyncio.gather(*tasks)
    return results
```

### Session Isolation

Ensure sessions don't interfere with each other:

```python
class IsolatedSession:
    def __init__(self, api, auth_json):
        self.api = api
        self.auth_json = auth_json
        self.session = None
    
    async def __aenter__(self):
        self.session = await self.api.login_context(self.auth_json).__aenter__()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)

# Usage
async with IsolatedSession(api, auth_json) as session:
    # Isolated session operations
    pass
```

## Session Monitoring

### Track Session Activity

```python
from datetime import datetime

class SessionMonitor:
    def __init__(self):
        self.sessions = {}
    
    def register(self, session_id, username):
        self.sessions[session_id] = {
            "username": username,
            "started": datetime.now(),
            "requests": 0,
            "errors": 0
        }
    
    def track_request(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]["requests"] += 1
    
    def track_error(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]["errors"] += 1
    
    def get_stats(self, session_id):
        return self.sessions.get(session_id)

# Usage
monitor = SessionMonitor()

async with api.login_context(auth_json) as authed:
    session_id = id(authed)
    monitor.register(session_id, "username")
    
    # Track activity
    monitor.track_request(session_id)
```

## Session Security

### Secure Session Storage

```python
from cryptography.fernet import Fernet

class SecureSessionStorage:
    def __init__(self, key):
        self.cipher = Fernet(key)
    
    def encrypt_session(self, session_data):
        json_data = json.dumps(session_data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted
    
    def decrypt_session(self, encrypted_data):
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode())

# Generate key (do once, store securely)
key = Fernet.generate_key()
storage = SecureSessionStorage(key)

# Encrypt session
encrypted = storage.encrypt_session(session_data)

# Decrypt session
decrypted = storage.decrypt_session(encrypted)
```

## Complete Example: Production-Ready Session Manager

Here's a complete implementation combining all best practices:

```python
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import redis.asyncio as redis
from cryptography.fernet import Fernet
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig
from ultima_scraper_api.config import Network, Redis as RedisConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionSessionManager:
    """Production-ready session manager with Redis caching and encryption"""
    
    def __init__(
        self,
        config: UltimaScraperAPIConfig,
        redis_url: str = "redis://localhost:6379",
        encryption_key: Optional[bytes] = None
    ):
        self.config = config
        self.api = OnlyFansAPI(config)
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.cipher = Fernet(encryption_key) if encryption_key else None
        self.session_ttl = timedelta(hours=24)
        self.cache_ttl = 600  # 10 minutes
        
    async def login(self, auth_json: Dict[str, str], user_id: str):
        """Login and cache session"""
        try:
            # Check if session exists in cache
            cached_session = await self._get_cached_session(user_id)
            if cached_session:
                logger.info(f"Using cached session for {user_id}")
                auth_json = cached_session
            
            # Login
            async with self.api.login_context(auth_json) as authed:
                if authed and authed.is_authed():
                    logger.info(f"✓ Authenticated as {user_id}")
                    
                    # Cache session
                    await self._cache_session(user_id, auth_json)
                    
                    return authed
                else:
                    logger.error(f"✗ Authentication failed for {user_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Login error for {user_id}: {e}")
            return None
    
    async def _cache_session(self, user_id: str, auth_json: Dict[str, str]):
        """Cache session data in Redis"""
        try:
            key = f"session:{user_id}"
            data = json.dumps(auth_json)
            
            # Encrypt if cipher available
            if self.cipher:
                data = self.cipher.encrypt(data.encode()).decode()
            
            await self.redis.setex(key, self.session_ttl, data)
            logger.info(f"✓ Session cached for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache session: {e}")
    
    async def _get_cached_session(self, user_id: str) -> Optional[Dict[str, str]]:
        """Retrieve cached session from Redis"""
        try:
            key = f"session:{user_id}"
            data = await self.redis.get(key)
            
            if not data:
                return None
            
            # Decrypt if cipher available
            if self.cipher:
                data = self.cipher.decrypt(data.encode()).decode()
            
            return json.loads(data)
            
        except Exception as e:
            logger.error(f"Failed to get cached session: {e}")
            return None
    
    async def refresh_session(self, user_id: str):
        """Refresh session TTL"""
        try:
            key = f"session:{user_id}"
            await self.redis.expire(key, self.session_ttl)
            logger.info(f"✓ Session refreshed for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
    
    async def invalidate_session(self, user_id: str):
        """Invalidate session"""
        try:
            key = f"session:{user_id}"
            await self.redis.delete(key)
            logger.info(f"✓ Session invalidated for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
    
    async def close(self):
        """Close connections"""
        await self.redis.close()


async def main():
    # Generate encryption key (store securely in production)
    encryption_key = Fernet.generate_key()
    
    # Configure
    config = UltimaScraperAPIConfig(
        network=Network(
            timeout=60,
            max_connections=100
        ),
        redis=RedisConfig(
            host="localhost",
            port=6379,
            db=0
        )
    )
    
    # Create session manager
    manager = ProductionSessionManager(
        config=config,
        redis_url="redis://localhost:6379",
        encryption_key=encryption_key
    )
    
    try:
        # Login
        auth_json = {
            "cookie": "your_cookie",
            "user_agent": "your_user_agent",
            "x-bc": "your_x-bc"
        }
        
        authed = await manager.login(auth_json, user_id="user123")
        
        if authed:
            # Use session
            me = await authed.get_me()
            print(f"Logged in as: {me.username}")
            
            # Refresh session
            await manager.refresh_session("user123")
        
    finally:
        # Cleanup
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Best Practices

### 1. Always Use Context Managers

```python
# ✅ Good: Automatic cleanup
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")

# ❌ Bad: Manual cleanup required
authed = await api.login(auth_json)
user = await authed.get_user("username")
# Easy to forget: await authed.close()
```

### 2. Implement Session Persistence

```python
# Save sessions for long-running applications
async def persistent_session(api, auth_json, user_id):
    session_manager = RedisSessionManager()
    
    # Try to load existing session
    session = await session_manager.get_session(user_id)
    if session:
        auth_json = session
    
    async with api.login_context(auth_json) as authed:
        # Save session
        await session_manager.save_session(user_id, auth_json)
        
        # Use session...
        return authed
```

### 3. Configure Appropriate Timeouts

```python
# Set timeouts to prevent hanging
config = UltimaScraperAPIConfig(
    network=Network(
        timeout=60,          # Total timeout
        connect_timeout=10,  # Connection timeout
    )
)
```

### 4. Monitor Session Health

```python
# Check session validity regularly
async def ensure_valid_session(authed):
    if not authed.is_authed():
        logger.warning("Session invalid - re-authenticating")
        # Re-authenticate logic here
        return False
    return True
```

### 5. Use Connection Pooling

```python
# Reuse connections for better performance
connector = aiohttp.TCPConnector(
    limit=100,
    limit_per_host=30,
    force_close=False,  # Reuse connections
)
```

### 6. Secure Session Data

```python
# Encrypt sensitive session data
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt
encrypted = cipher.encrypt(session_data.encode())

# Decrypt
decrypted = cipher.decrypt(encrypted).decode()
```

### 7. Implement Retry Logic

```python
# Retry on transient failures
async def fetch_with_retry(authed, username, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await authed.get_user(username)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Retry {attempt + 1}/{max_retries}: {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 8. Clean Up Expired Sessions

```python
# Periodic cleanup of expired sessions
async def cleanup_expired_sessions(redis_client):
    """Redis TTL handles this automatically, but you can also do manual cleanup"""
    pattern = "session:*"
    cursor = 0
    
    while True:
        cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
        
        for key in keys:
            ttl = await redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                await redis_client.expire(key, 86400)  # Set 24h expiration
        
        if cursor == 0:
            break
```

### 9. Handle Concurrent Sessions Safely

```python
# Use asyncio locks for concurrent access
import asyncio

session_locks = {}

async def safe_session_access(user_id, operation):
    """Ensure thread-safe session access"""
    if user_id not in session_locks:
        session_locks[user_id] = asyncio.Lock()
    
    async with session_locks[user_id]:
        return await operation()
```

### 10. Log Session Activity

```python
# Comprehensive logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log session events
logger.info(f"Session created for {user_id}")
logger.warning(f"Session expired for {user_id}")
logger.error(f"Session error for {user_id}: {error}")
```

---

## Troubleshooting

### Session Won't Connect

!!! error "Common Error"
    ```
    aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host
    ```

**Possible Causes:**

- ❌ Network connectivity issues
- ❌ Invalid credentials or expired tokens
- ❌ Timeout set too low
- ❌ Proxy configuration problems
- ❌ Firewall blocking connections

**Solutions:**

1. **Test network connectivity:**
   ```bash
   # Test connection to API
   curl -I https://onlyfans.com
   ```

2. **Verify credentials:**
   ```python
   # Check if credentials are still valid
   auth_json = {
       "cookie": "your_cookie",  # Check not expired
       "user_agent": "your_user_agent",
       "x-bc": "your_x-bc"  # OnlyFans specific
   }
   
   # Try authentication
   async with api.login_context(auth_json) as authed:
       if not authed:
           print("Invalid credentials")
   ```

3. **Increase timeout:**
   ```python
   config = UltimaScraperAPIConfig(
       network=Network(
           timeout=120,  # Increase to 2 minutes
       )
   )
   ```

4. **Check proxy configuration:**
   ```python
   # Test without proxy first
   config = UltimaScraperAPIConfig()  # No proxy
   
   # If works, proxy issue
   # If doesn't work, credential/network issue
   ```

### Session Expires Quickly

!!! warning "Symptom"
    Session becomes invalid after short period

**Possible Causes:**

- 🕐 Platform automatically logs out inactive sessions
- 🕐 Cookie expiration
- 🕐 Token refresh required
- 🕐 Multiple sessions from same account

**Solutions:**

1. **Implement automatic session refresh:**
   ```python
   async def keep_alive_session(authed, interval=300):
       """Keep session alive with periodic requests"""
       while True:
           try:
               # Make lightweight request
               await authed.get_me()
               logger.info("✓ Session refreshed")
               await asyncio.sleep(interval)  # 5 minutes
           except Exception as e:
               logger.error(f"Session refresh failed: {e}")
               break
   ```

2. **Save and restore sessions:**
   ```python
   # Save session before closing
   session_manager = RedisSessionManager()
   await session_manager.save_session(user_id, auth_json)
   
   # Restore later
   auth_json = await session_manager.get_session(user_id)
   ```

3. **Monitor session validity:**
   ```python
   async def check_session_health(authed):
       try:
           me = await authed.get_me()
           return True
       except Exception:
           return False
   
   # Check before important operations
   if not await check_session_health(authed):
       logger.warning("Session invalid - re-authenticating")
       # Re-authenticate...
   ```

### Connection Pool Exhausted

!!! error "Common Error"
    ```
    aiohttp.client_exceptions.ServerDisconnectedError: 
    Server disconnected
    ```

**Possible Causes:**

- 🔌 Too many concurrent connections
- 🔌 Connections not being released
- 🔌 Pool size too small
- 🔌 Long-running requests blocking pool

**Solutions:**

1. **Increase pool size:**
   ```python
   connector = aiohttp.TCPConnector(
       limit=200,           # Increase from 100
       limit_per_host=50,   # Increase from 30
   )
   ```

2. **Ensure proper cleanup:**
   ```python
   # ✅ Always use context managers
   async with api.login_context(auth_json) as authed:
       user = await authed.get_user("username")
   # Connection automatically released
   
   # ❌ Don't forget to close
   authed = await api.login(auth_json)
   user = await authed.get_user("username")
   # await authed.close()  # Easy to forget!
   ```

3. **Add delays between requests:**
   ```python
   import asyncio
   
   async def fetch_with_delay(authed, usernames):
       results = []
       for username in usernames:
           user = await authed.get_user(username)
           results.append(user)
           await asyncio.sleep(0.5)  # Small delay
       return results
   ```

4. **Use semaphore for concurrency control:**
   ```python
   async def fetch_with_limit(authed, usernames, max_concurrent=10):
       semaphore = asyncio.Semaphore(max_concurrent)
       
       async def fetch_one(username):
           async with semaphore:
               return await authed.get_user(username)
       
       tasks = [fetch_one(username) for username in usernames]
       return await asyncio.gather(*tasks)
   ```

### Redis Connection Issues

!!! error "Common Error"
    ```
    redis.exceptions.ConnectionError: Error connecting to Redis
    ```

**Solutions:**

1. **Check Redis is running:**
   ```bash
   # Test Redis connection
   redis-cli ping
   # Should return: PONG
   ```

2. **Verify configuration:**
   ```python
   config = UltimaScraperAPIConfig(
       redis=RedisConfig(
           host="localhost",  # Correct host?
           port=6379,         # Correct port?
           db=0,
           password="your_password"  # If required
       )
   )
   ```

3. **Test connection separately:**
   ```python
   import redis.asyncio as redis
   
   async def test_redis():
       try:
           client = redis.from_url("redis://localhost:6379")
           await client.ping()
           print("✓ Redis connected")
       except Exception as e:
           print(f"✗ Redis error: {e}")
   ```

### Memory Leaks with Sessions

**Symptoms:**

- Memory usage increases over time
- Application slows down
- Out of memory errors

**Solutions:**

1. **Always close sessions:**
   ```python
   # Use context managers - automatic cleanup
   async with api.login_context(auth_json) as authed:
       # Operations...
       pass
   # Session closed automatically
   ```

2. **Limit session lifetime:**
   ```python
   # Don't keep sessions open indefinitely
   max_session_lifetime = 3600  # 1 hour
   
   session_start = time.time()
   async with api.login_context(auth_json) as authed:
       while time.time() - session_start < max_session_lifetime:
           # Operations...
           await asyncio.sleep(10)
   # Re-create session after lifetime expires
   ```

3. **Monitor memory usage:**
   ```python
   import psutil
   
   def check_memory():
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024
       print(f"Memory usage: {memory_mb:.2f} MB")
   
   # Check periodically
   check_memory()
   ```

---

## Related Documentation

- **[Authentication Guide](authentication.md)** - Authentication methods and credential management
- **[Proxy Support](proxy-support.md)** - Configure proxies for sessions
- **[Working with APIs](working-with-apis.md)** - API usage patterns and best practices
- **[Configuration Guide](../getting-started/configuration.md)** - Complete configuration options
- **[OnlyFans API Reference](../api-reference/onlyfans.md)** - API documentation

---

## External Resources

- **[aiohttp Documentation](https://docs.aiohttp.org/)** - Async HTTP client/server
- **[Redis Documentation](https://redis.io/docs/)** - Redis database
- **[redis-py Documentation](https://redis-py.readthedocs.io/)** - Redis Python client
- **[Connection Pooling Best Practices](https://www.michaelcho.me/article/using-pythons-asyncio-to-manage-work-in-progress)** - Advanced patterns
