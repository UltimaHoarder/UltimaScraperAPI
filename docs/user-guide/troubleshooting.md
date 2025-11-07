# Troubleshooting Guide

This comprehensive guide covers common issues you may encounter when using UltimaScraperAPI and their solutions. Issues are organized by category for easy navigation.

!!! tip "Quick Debugging Tips"
    - Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
    - Check your Python version: `python --version` (requires 3.10+)
    - Verify package installation: `pip show ultima-scraper-api`
    - Review configuration: Ensure all required credentials are present

## 📑 Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Problems](#authentication-problems)
- [Connection & Network Errors](#connection-network-errors)
- [Proxy Issues](#proxy-issues)
- [Session Management Problems](#session-management-problems)
- [API Rate Limiting](#api-rate-limiting)
- [Data Scraping Issues](#data-scraping-issues)
- [Redis Integration Problems](#redis-integration-problems)
- [Performance Issues](#performance-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### ❌ Problem: Package Installation Fails

**Symptoms:**
```bash
ERROR: Could not find a version that satisfies the requirement ultima-scraper-api
ERROR: No matching distribution found for ultima-scraper-api
```

**Solutions:**

1. **Check Python Version:**
```bash
python --version
# Should be 3.10, 3.11, 3.12, 3.13, or 3.14
```

2. **Update pip:**
```bash
pip install --upgrade pip setuptools wheel
```

3. **Use uv (Recommended):**
```bash
pip install uv
uv pip install ultima-scraper-api
```

4. **Install from source:**
```bash
git clone https://github.com/UltimaHoarder/UltimaScraperAPI.git
cd UltimaScraperAPI
pip install -e .
```

---

### ❌ Problem: Dependency Conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
ERROR: Incompatible library versions
```

**Solutions:**

1. **Use fresh virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

pip install ultima-scraper-api
```

2. **Check dependency tree:**
```bash
pip install pipdeptree
pipdeptree -p ultima-scraper-api
```

3. **Install with constraints:**
```bash
pip install ultima-scraper-api --use-feature=fast-deps
```

---

### ❌ Problem: Import Errors After Installation

**Symptoms:**
```python
ImportError: No module named 'ultima_scraper_api'
ModuleNotFoundError: No module named 'ultima_scraper_api.apis'
```

**Solutions:**

1. **Verify installation:**
```bash
pip show ultima-scraper-api
pip list | grep ultima
```

2. **Check Python environment:**
```python
import sys
print(sys.executable)  # Should match your virtual environment
print(sys.path)        # Should include site-packages with the package
```

3. **Reinstall package:**
```bash
pip uninstall ultima-scraper-api -y
pip install ultima-scraper-api
```

---

## Authentication Problems

### ❌ Problem: Authentication Fails with "Unauthorized"

**Symptoms:**
```python
AuthenticationError: Failed to authenticate
HTTPStatusError: 401 Unauthorized
```

**Solutions:**

1. **Verify credentials are current:**
   - Cookies expire frequently (24-48 hours)
   - Extract fresh credentials from browser
   - Ensure User-Agent matches browser

2. **Check cookie format:**
```python
# ✅ Correct format
auth_cookie = "auth_id=123456; sess=abc..."

# ❌ Wrong - missing values
auth_cookie = "auth_id=; sess="

# ❌ Wrong - URL encoded
auth_cookie = "auth_id%3D123456%3B%20sess%3Dabc"
```

3. **Validate User-Agent:**
```python
# ✅ Use exact browser User-Agent
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."

# ❌ Generic or missing User-Agent
user_agent = "Python/3.10"
```

4. **Test authentication:**
```python
import asyncio
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

async def test_auth():
    api = OnlyFansAPI()
    auth_details = {
        "cookie": "your_cookie_here",
        "user-agent": "your_user_agent_here",
        "x-bc": "your_x_bc_token_here"
    }
    
    authenticator = api.get_authenticator()
    auth = await authenticator.login(auth_details)
    
    if auth.active:
        print("✅ Authentication successful!")
        print(f"User ID: {auth.id}")
        print(f"Username: {auth.username}")
    else:
        print("❌ Authentication failed")
        print(f"Error: {auth.error_details}")

asyncio.run(test_auth())
```

---

### ❌ Problem: x-bc Token Invalid or Missing

**Symptoms:**
```
AuthenticationError: Missing x-bc token
403 Forbidden: Invalid security token
```

**Solutions:**

1. **Extract x-bc from browser:**
   - Open DevTools (F12) → Network tab
   - Look for API requests to `onlyfans.com/api2/v2/`
   - Copy `x-bc` from request headers

2. **Verify token format:**
```python
# ✅ Correct format (long alphanumeric string)
x_bc = "aB3dEf7gH9jK1mN4pQ6rS8tU0vW2xY4zA6bC8dE0fG2hI4jK6"

# ❌ Wrong - too short or malformed
x_bc = "abc123"
```

3. **Check token expiration:**
   - x-bc tokens can expire
   - Re-extract if authentication fails
   - Consider implementing automatic token refresh

---

### ❌ Problem: Two-Factor Authentication (2FA) Required

**Symptoms:**
```
AuthenticationError: Two-factor authentication required
TwoFactorAuthenticationRequired: Please verify your account
```

**Solutions:**

1. **Disable 2FA temporarily** (if possible) for scraping sessions

2. **Use account without 2FA** for API access

3. **Manual 2FA verification:**
   - Complete 2FA in browser
   - Extract cookies **after** verification
   - Use fresh cookies in API

4. **Future support:**
   - 2FA automation is planned but not currently supported
   - Monitor project updates for 2FA support

---

## Connection & Network Errors

### ❌ Problem: Connection Timeout

**Symptoms:**
```python
TimeoutError: Connection timeout after 30 seconds
asyncio.exceptions.TimeoutError
aiohttp.ClientError: Server disconnected
```

**Solutions:**

1. **Increase timeout:**
```python
from ultima_scraper_api.config import UltimaScraperAPIConfig, Network

config = UltimaScraperAPIConfig()
config.network = Network(
    timeout=60,  # Increase from default 30
    max_read_timeout=120
)
```

2. **Check internet connection:**
```bash
ping onlyfans.com
curl -I https://onlyfans.com
```

3. **Test with retry logic:**
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(api, url):
    return await api.session.get(url)
```

4. **Use connection pooling:**
```python
import aiohttp

connector = aiohttp.TCPConnector(
    limit=100,
    limit_per_host=30,
    ttl_dns_cache=300,
    keepalive_timeout=60
)

# Pass to API session
```

---

### ❌ Problem: SSL Certificate Verification Fails

**Symptoms:**
```python
aiohttp.ClientSSLError: SSL certificate verification failed
ssl.SSLCertVerificationError: certificate verify failed
```

**Solutions:**

1. **Update certificates:**
```bash
# Linux
sudo update-ca-certificates

# macOS
brew install openssl
```

2. **Check system time:**
   - SSL certificates are time-sensitive
   - Ensure system clock is correct

3. **Temporary workaround (NOT recommended for production):**
```python
import ssl
import aiohttp

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

connector = aiohttp.TCPConnector(ssl=ssl_context)
```

!!! danger "Security Warning"
    Disabling SSL verification exposes you to man-in-the-middle attacks. Only use for debugging.

---

### ❌ Problem: DNS Resolution Errors

**Symptoms:**
```python
aiohttp.ClientConnectorError: Cannot connect to host
socket.gaierror: Name or service not known
```

**Solutions:**

1. **Check DNS settings:**
```bash
nslookup onlyfans.com
dig onlyfans.com
```

2. **Use custom DNS:**
```python
import aiohttp

resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
connector = aiohttp.TCPConnector(resolver=resolver)
```

3. **Test with hosts file:**
```bash
# Add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
# Get IP first
nslookup onlyfans.com
# Then add entry
# 104.16.xx.xx onlyfans.com
```

---

## Proxy Issues

### ❌ Problem: Proxy Connection Failed

**Symptoms:**
```python
ProxyConnectionError: Cannot connect to proxy server
aiohttp_socks.ProxyConnectionError
TimeoutError: Proxy connection timeout
```

**Solutions:**

1. **Verify proxy credentials:**
```python
from ultima_scraper_api.config import Proxy

# ✅ Correct format
proxy = Proxy(
    protocol="http",
    host="proxy.example.com",
    port=8080,
    username="user",
    password="pass123"
)

# Test proxy
import aiohttp
from aiohttp_socks import ProxyConnector

connector = ProxyConnector.from_url(
    f"http://user:pass123@proxy.example.com:8080"
)

async with aiohttp.ClientSession(connector=connector) as session:
    async with session.get("http://httpbin.org/ip") as resp:
        print(await resp.json())
```

2. **Check proxy server status:**
```bash
# Test HTTP proxy
curl -x http://proxy.example.com:8080 http://httpbin.org/ip

# Test SOCKS5 proxy
curl --socks5 proxy.example.com:1080 http://httpbin.org/ip
```

3. **Try different proxy protocol:**
```python
# If HTTP fails, try SOCKS5
proxy = Proxy(
    protocol="socks5",  # or "socks5h" for DNS through proxy
    host="proxy.example.com",
    port=1080
)
```

---

### ❌ Problem: Proxy Authentication Fails

**Symptoms:**
```
ProxyAuthenticationRequired: 407 Proxy Authentication Required
aiohttp_socks.ProxyError: Authentication failed
```

**Solutions:**

1. **URL-encode special characters:**
```python
from urllib.parse import quote

username = quote("user@email.com")
password = quote("p@ss:w0rd!")

proxy = Proxy(
    protocol="http",
    host="proxy.example.com",
    port=8080,
    username=username,
    password=password
)
```

2. **Verify credentials:**
```bash
# Test with curl
curl -x http://user:password@proxy.example.com:8080 http://httpbin.org/ip
```

3. **Check proxy authentication method:**
   - Some proxies require specific auth methods
   - Consult your proxy provider's documentation

---

### ❌ Problem: SOCKS5 Proxy Not Working

**Symptoms:**
```python
SOCKSError: SOCKS5 connection failed
python_socks._errors.ProxyError
```

**Solutions:**

1. **Install required dependencies:**
```bash
pip install python-socks[asyncio] aiohttp-socks
```

2. **Use SOCKS5H for DNS:**
```python
# SOCKS5H resolves DNS through proxy
proxy = Proxy(
    protocol="socks5h",  # Note the 'h'
    host="proxy.example.com",
    port=1080
)
```

3. **Test SOCKS5 connection:**
```python
from python_socks.async_.asyncio import Proxy as PythonSocksProxy
import asyncio

async def test_socks5():
    proxy = PythonSocksProxy.from_url("socks5://proxy.example.com:1080")
    sock = await proxy.connect(dest_host="onlyfans.com", dest_port=443)
    print("✅ SOCKS5 connection successful")

asyncio.run(test_socks5())
```

---

## Session Management Problems

### ❌ Problem: Memory Leak with Sessions

**Symptoms:**
```
MemoryError: Out of memory
Program memory usage keeps increasing
ResourceWarning: unclosed sessions
```

**Solutions:**

1. **Always use context managers:**
```python
# ✅ Correct - auto cleanup
async with OnlyFansAPI() as api:
    async with api.login_context(auth_details) as auth:
        # Do work
        pass
# Sessions closed automatically

# ❌ Wrong - manual management
api = OnlyFansAPI()
auth = await api.login(auth_details)
# Sessions remain open
```

2. **Explicitly close sessions:**
```python
api = OnlyFansAPI()
try:
    auth = await api.login(auth_details)
    # Do work
finally:
    await api.close()  # Clean up
```

3. **Monitor with warnings:**
```python
import warnings
warnings.simplefilter('always', ResourceWarning)
```

---

### ❌ Problem: Session Limit Exceeded

**Symptoms:**
```
aiohttp.ClientError: Too many open connections
RuntimeError: Session is closed
```

**Solutions:**

1. **Configure connection limits:**
```python
import aiohttp

connector = aiohttp.TCPConnector(
    limit=100,              # Total connections
    limit_per_host=30,      # Per host
    force_close=False,      # Keep-alive
    enable_cleanup_closed=True
)
```

2. **Reuse sessions:**
```python
# ✅ Reuse single session
api = OnlyFansAPI()
async with api.login_context(auth_details) as auth:
    # Multiple operations with same session
    users = await auth.get_users()
    for user in users:
        posts = await user.get_posts()  # Reuses session

# ❌ Creating new sessions each time
for user in users:
    api = OnlyFansAPI()  # Don't do this
    auth = await api.login(auth_details)
```

3. **Implement connection pooling:**
```python
from ultima_scraper_api.managers.session_manager import SessionManager

session_manager = SessionManager(
    max_connections=100,
    connection_timeout=60,
    keepalive_timeout=30
)
```

---

### ❌ Problem: Redis Connection Issues

**Symptoms:**
```python
redis.exceptions.ConnectionError: Connection refused
redis.exceptions.TimeoutError: Timeout waiting for Redis
```

**Solutions:**

1. **Verify Redis is running:**
```bash
# Check Redis status
redis-cli ping
# Should return: PONG

# Start Redis
sudo systemctl start redis
# or
redis-server
```

2. **Check Redis configuration:**
```python
from ultima_scraper_api.config import Redis

# ✅ Correct configuration
redis_config = Redis(
    host="localhost",
    port=6379,
    db=0,
    password=None  # If no password
)

# Test connection
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())  # Should print True
```

3. **Use connection pooling:**
```python
import redis

pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5
)

r = redis.Redis(connection_pool=pool)
```

See [Redis Integration Problems](#redis-integration-problems) for more Redis-specific issues.

---

## API Rate Limiting

### ❌ Problem: Rate Limit Exceeded (429 Error)

**Symptoms:**
```python
HTTPStatusError: 429 Too Many Requests
RateLimitExceeded: API rate limit exceeded
```

**Solutions:**

1. **Implement exponential backoff:**
```python
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from httpx import HTTPStatusError

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(HTTPStatusError)
)
async def fetch_with_retry(api, endpoint):
    return await api.get(endpoint)

# Usage
try:
    result = await fetch_with_retry(api, "/users/me")
except Exception as e:
    print(f"Failed after retries: {e}")
```

2. **Add delays between requests:**
```python
import asyncio

async def fetch_multiple(api, endpoints):
    results = []
    for endpoint in endpoints:
        result = await api.get(endpoint)
        results.append(result)
        await asyncio.sleep(1)  # 1 second delay
    return results
```

3. **Use request throttling:**
```python
import asyncio
from asyncio import Semaphore

async def throttled_fetch(api, endpoints, max_concurrent=5, delay=0.5):
    semaphore = Semaphore(max_concurrent)
    
    async def fetch_one(endpoint):
        async with semaphore:
            result = await api.get(endpoint)
            await asyncio.sleep(delay)
            return result
    
    tasks = [fetch_one(ep) for ep in endpoints]
    return await asyncio.gather(*tasks)
```

4. **Monitor rate limits:**
```python
async def fetch_with_monitoring(api, endpoint):
    response = await api.get(endpoint)
    
    # Check rate limit headers
    remaining = response.headers.get('X-RateLimit-Remaining')
    reset_time = response.headers.get('X-RateLimit-Reset')
    
    if remaining and int(remaining) < 10:
        print(f"⚠️ Rate limit low: {remaining} requests remaining")
        print(f"Resets at: {reset_time}")
    
    return response
```

---

### ❌ Problem: Concurrent Request Limits

**Symptoms:**
```
Too many concurrent requests
Server returns 503 Service Unavailable
Connection pool exhausted
```

**Solutions:**

1. **Limit concurrency with semaphore:**
```python
import asyncio

async def controlled_concurrency(tasks, max_concurrent=10):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[run_with_semaphore(t) for t in tasks])

# Usage
user_tasks = [api.get_user(uid) for uid in user_ids]
users = await controlled_concurrency(user_tasks, max_concurrent=5)
```

2. **Batch requests:**
```python
async def fetch_in_batches(api, items, batch_size=10):
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(*[api.get_item(item) for item in batch])
        results.extend(batch_results)
        await asyncio.sleep(1)  # Delay between batches
    return results
```

3. **Use queue-based processing:**
```python
import asyncio

async def queue_processor(api, queue, max_workers=5):
    async def worker():
        while True:
            item = await queue.get()
            if item is None:  # Poison pill
                break
            try:
                result = await api.process(item)
                print(f"Processed: {item}")
            except Exception as e:
                print(f"Error processing {item}: {e}")
            finally:
                queue.task_done()
    
    workers = [asyncio.create_task(worker()) for _ in range(max_workers)]
    await queue.join()
    
    # Stop workers
    for _ in workers:
        await queue.put(None)
    await asyncio.gather(*workers)
```

---

## Data Scraping Issues

### ❌ Problem: Missing or Incomplete Data

**Symptoms:**
```python
AttributeError: 'NoneType' object has no attribute
KeyError: Expected field missing from response
Empty lists or null values
```

**Solutions:**

1. **Validate data before access:**
```python
# ✅ Safe access with validation
user = await auth.get_user("username")
if user and hasattr(user, "posts_count"):
    print(f"Posts: {user.posts_count}")
else:
    print("User or posts_count not available")

# Use getattr with defaults
posts_count = getattr(user, "posts_count", 0)
```

2. **Check API response status:**
```python
async def fetch_user_safe(api, username):
    try:
        user = await api.get_user(username)
        if not user:
            print(f"User {username} not found")
            return None
        return user
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"User {username} does not exist")
        elif e.response.status_code == 403:
            print(f"Access denied for user {username}")
        else:
            print(f"Error fetching user: {e}")
        return None
```

3. **Handle pagination properly:**
```python
async def get_all_posts(user):
    all_posts = []
    offset = 0
    limit = 100
    
    while True:
        posts = await user.get_posts(offset=offset, limit=limit)
        if not posts:  # No more posts
            break
        all_posts.extend(posts)
        offset += limit
        
        # Safety check
        if offset > 10000:  # Reasonable limit
            print("⚠️ Reached maximum offset")
            break
    
    return all_posts
```

---

### ❌ Problem: Media Download Failures

**Symptoms:**
```python
DownloadError: Failed to download media
ChunkedEncodingError: Connection broken
FileNotFoundError: Media URL expired
```

**Solutions:**

1. **Implement retry logic for downloads:**
```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def download_with_retry(session, url, save_path):
    async with session.get(url) as response:
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            async for chunk in response.content.iter_chunked(8192):
                f.write(chunk)
    return save_path
```

2. **Validate media URLs:**
```python
async def download_media(api, media_item):
    if not media_item.url:
        print(f"⚠️ No URL for media {media_item.id}")
        return None
    
    # Check URL expiration
    if hasattr(media_item, "expires_at"):
        from datetime import datetime
        if datetime.now() > media_item.expires_at:
            print(f"⚠️ Media URL expired, refreshing...")
            media_item = await api.refresh_media(media_item.id)
    
    return await api.download(media_item.url)
```

3. **Handle DRM-protected content:**
```python
from ultima_scraper_api.config import DRM

# Configure DRM settings
config = UltimaScraperAPIConfig()
config.drm = DRM(
    enabled=True,
    # Add Widevine configuration if needed
)

# Check if content is DRM-protected
if media.is_drm_protected:
    print("⚠️ DRM-protected content detected")
    # Handle DRM decryption
```

---

### ❌ Problem: Scraping Performance Issues

**Symptoms:**
```
Slow scraping speeds
High memory usage
Script hanging or freezing
```

**Solutions:**

1. **Use async patterns efficiently:**
```python
# ✅ Good - concurrent fetching
users = await asyncio.gather(*[
    api.get_user(uid) for uid in user_ids
])

# ❌ Bad - sequential fetching
users = []
for uid in user_ids:
    user = await api.get_user(uid)  # Slow!
    users.append(user)
```

2. **Stream large responses:**
```python
async def download_large_file(session, url, save_path):
    async with session.get(url) as response:
        with open(save_path, 'wb') as f:
            async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                f.write(chunk)
```

3. **Use caching:**
```python
from functools import lru_cache
from ultima_scraper_api.config import Redis

# In-memory caching
@lru_cache(maxsize=1000)
async def get_user_cached(api, user_id):
    return await api.get_user(user_id)

# Redis caching
redis_config = Redis(host="localhost", port=6379)
# API will automatically use Redis for caching
```

4. **Limit data collection:**
```python
# Only fetch what you need
user = await api.get_user(user_id, fields=["id", "username", "avatar"])

# Limit pagination
posts = await user.get_posts(limit=100)  # Don't fetch thousands
```

---

## Redis Integration Problems

### ❌ Problem: Redis Key Errors

**Symptoms:**
```python
KeyError: 'session:user_123'
redis.exceptions.ResponseError: WRONGTYPE Operation against a key
```

**Solutions:**

1. **Verify key format:**
```python
# ✅ Consistent key naming
session_key = f"session:{user_id}:{platform}"
cache_key = f"cache:{endpoint}:{params_hash}"

# Set with expiration
await redis.setex(session_key, 3600, session_data)
```

2. **Check key type:**
```python
import redis

r = redis.Redis()

# Check key type before operations
key_type = r.type("session:user_123")
if key_type == b"string":
    value = r.get("session:user_123")
elif key_type == b"hash":
    value = r.hgetall("session:user_123")
```

3. **Handle missing keys:**
```python
async def get_cached_data(redis_client, key, default=None):
    try:
        data = await redis_client.get(key)
        if data is None:
            return default
        return json.loads(data)
    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return default
```

---

### ❌ Problem: Redis Memory Issues

**Symptoms:**
```
Redis OOM (Out of Memory)
redis.exceptions.ResponseError: OOM command not allowed
```

**Solutions:**

1. **Set expiration on keys:**
```python
# Always set TTL
await redis.setex("key", 3600, value)  # 1 hour

# Or use EXPIRE
await redis.set("key", value)
await redis.expire("key", 3600)
```

2. **Configure Redis memory policy:**
```bash
# In redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used
```

3. **Monitor memory usage:**
```python
import redis

r = redis.Redis()
info = r.info('memory')
print(f"Used memory: {info['used_memory_human']}")
print(f"Peak memory: {info['used_memory_peak_human']}")

# Check key count
key_count = r.dbsize()
print(f"Total keys: {key_count}")
```

4. **Implement key cleanup:**
```python
async def cleanup_expired_keys(redis_client, pattern="session:*"):
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=pattern,
            count=100
        )
        
        for key in keys:
            ttl = await redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                await redis_client.expire(key, 3600)
        
        if cursor == 0:
            break
```

---

### ❌ Problem: Redis Serialization Errors

**Symptoms:**
```python
TypeError: Object of type datetime is not JSON serializable
pickle.PicklingError: Can't pickle object
```

**Solutions:**

1. **Use proper serialization:**
```python
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Serialize
data = {"timestamp": datetime.now(), "value": 123}
serialized = json.dumps(data, cls=DateTimeEncoder)
await redis.set("key", serialized)

# Deserialize
cached = await redis.get("key")
data = json.loads(cached)
```

2. **Use dill for complex objects:**
```python
import dill

# Serialize with dill
obj = SomeComplexObject()
serialized = dill.dumps(obj)
await redis.set("key", serialized)

# Deserialize
cached = await redis.get("key")
obj = dill.loads(cached)
```

3. **Implement custom serializer:**
```python
from ultima_scraper_api.models import UserModel

def serialize_user(user: UserModel) -> str:
    return json.dumps({
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        # Only serialize what you need
    })

def deserialize_user(data: str) -> dict:
    return json.loads(data)
```

---

## Performance Issues

### ❌ Problem: Slow API Response Times

**Symptoms:**
```
Operations taking multiple seconds
High latency
Timeouts under load
```

**Solutions:**

1. **Enable HTTP/2:**
```python
import httpx

client = httpx.AsyncClient(http2=True)
```

2. **Use connection keepalive:**
```python
import aiohttp

connector = aiohttp.TCPConnector(
    keepalive_timeout=60,
    force_close=False,  # Reuse connections
    enable_cleanup_closed=True
)
```

3. **Implement caching:**
```python
from functools import lru_cache
import hashlib
import json

# Memory cache
@lru_cache(maxsize=1000)
def cache_key(endpoint, params):
    key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key.encode()).hexdigest()

# Redis cache with TTL
async def cached_api_call(redis_client, api, endpoint, params, ttl=300):
    key = cache_key(endpoint, params)
    
    # Check cache
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    # Fetch fresh data
    data = await api.get(endpoint, params=params)
    
    # Cache result
    await redis_client.setex(key, ttl, json.dumps(data))
    
    return data
```

4. **Profile your code:**
```python
import cProfile
import pstats

def profile_scraping():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your scraping code
    asyncio.run(main())
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

profile_scraping()
```

---

### ❌ Problem: High Memory Consumption

**Symptoms:**
```
MemoryError: Unable to allocate memory
Program grows to multiple GB
System becomes unresponsive
```

**Solutions:**

1. **Process data in chunks:**
```python
async def process_posts_chunked(user, chunk_size=100):
    offset = 0
    while True:
        posts = await user.get_posts(offset=offset, limit=chunk_size)
        if not posts:
            break
        
        # Process chunk
        for post in posts:
            await process_post(post)
        
        # Clear processed data
        posts.clear()
        offset += chunk_size
```

2. **Use generators:**
```python
async def post_generator(user):
    offset = 0
    limit = 100
    
    while True:
        posts = await user.get_posts(offset=offset, limit=limit)
        if not posts:
            break
        
        for post in posts:
            yield post
        
        offset += limit

# Usage
async for post in post_generator(user):
    await process_post(post)
```

3. **Monitor memory:**
```python
import psutil
import os

def log_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"Memory: {mem_info.rss / 1024 / 1024:.2f} MB")

# Call periodically
log_memory()
```

4. **Explicit garbage collection:**
```python
import gc

async def process_large_dataset(data):
    for chunk in chunks(data, 1000):
        await process_chunk(chunk)
        gc.collect()  # Force garbage collection
```

---

## Platform-Specific Issues

### OnlyFans Issues

#### ❌ Problem: "User Not Found" for Valid Usernames

**Symptoms:**
```python
UserNotFoundError: User 'username' not found
404 Not Found
```

**Solutions:**

1. **Use user ID instead:**
```python
# ✅ More reliable
user = await api.get_user_by_id(12345678)

# ❌ Username can change or be unavailable
user = await api.get_user("username")
```

2. **Search for user:**
```python
results = await api.search_users("username")
if results:
    user = results[0]
```

---

#### ❌ Problem: Paid Content Access Issues

**Symptoms:**
```
PaymentRequiredError: Content requires purchase
403 Forbidden: Insufficient access
```

**Solutions:**

1. **Check subscription status:**
```python
user = await api.get_user(user_id)
if not user.is_subscribed:
    print("⚠️ Subscription required")
    # Handle subscription
```

2. **Verify content access:**
```python
post = await api.get_post(post_id)
if post.is_locked:
    print(f"⚠️ Post requires purchase: ${post.price}")
    if post.can_purchase:
        # Handle purchase flow
        pass
```

---

### Fansly Issues (WIP)

!!! warning "Work in Progress"
    Fansly API integration is currently under development. Some features may be limited or unstable.

#### ❌ Problem: Limited API Coverage

**Current Status:**
- ✅ Authentication
- ✅ Basic user profiles
- ⚠️ Content fetching (limited)
- ❌ Messaging (not yet implemented)
- ❌ Live streams (not yet implemented)

**Solutions:**

Monitor the project's GitHub for updates and feature additions.

---

### LoyalFans Issues (WIP)

!!! warning "Work in Progress"
    LoyalFans API integration is currently under development.

**Current Status:**
- ✅ Authentication
- ⚠️ User profiles (basic)
- ❌ Most features not yet implemented

---

## General Debugging Tips

### Enable Debug Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Specific loggers
logging.getLogger('ultima_scraper_api').setLevel(logging.DEBUG)
logging.getLogger('aiohttp').setLevel(logging.INFO)
```

### Capture Network Traffic

```python
import aiohttp
import logging

# Enable aiohttp debug logging
aiohttp_logger = logging.getLogger('aiohttp')
aiohttp_logger.setLevel(logging.DEBUG)

# Log all requests
async def log_requests(session, ctx, params):
    print(f"Request: {params.method} {params.url}")
    print(f"Headers: {params.headers}")

trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(log_requests)

# Use with session
connector = aiohttp.TCPConnector()
session = aiohttp.ClientSession(
    connector=connector,
    trace_configs=[trace_config]
)
```

### Test Individual Components

```python
import asyncio
from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

async def test_component():
    # Test authentication
    print("Testing authentication...")
    api = OnlyFansAPI()
    auth_details = {...}
    
    try:
        auth = await api.login(auth_details)
        print(f"✅ Auth successful: {auth.username}")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        return
    
    # Test user fetching
    print("Testing user fetch...")
    try:
        user = await auth.get_user("username")
        print(f"✅ User fetch successful: {user.id}")
    except Exception as e:
        print(f"❌ User fetch failed: {e}")
    
    # Cleanup
    await api.close()

asyncio.run(test_component())
```

---

## Getting Help

If you're still experiencing issues:

1. **Check the documentation:**
   - [Installation Guide](../getting-started/installation.md)
   - [API Reference](../api-reference/onlyfans.md)
   - [Configuration](../getting-started/configuration.md)

2. **Search existing issues:**
   - [GitHub Issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)

3. **Create a detailed bug report:**
   Include:
   - Python version (`python --version`)
   - Package version (`pip show ultima-scraper-api`)
   - Full error traceback
   - Minimal reproducible example
   - Configuration (redact sensitive data)

4. **Enable debug logging** and include relevant logs:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Related Documentation

- [Authentication Guide](authentication.md) - Detailed authentication setup
- [Proxy Support](proxy-support.md) - Comprehensive proxy configuration
- [Session Management](session-management.md) - Session and Redis setup
- [Working with APIs](working-with-apis.md) - API usage patterns and best practices

---

**Last Updated:** 2025-01-24  
**Version:** 2.2.46
