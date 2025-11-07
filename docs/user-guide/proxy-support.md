# Proxy Support

Comprehensive guide to configuring and using proxies with UltimaScraperAPI for privacy, geo-restriction bypass, and rate limit management.

## Overview

UltimaScraperAPI provides full proxy support through `python-socks` and `aiohttp-socks`, enabling you to:

- ✅ Route traffic through HTTP/HTTPS proxies
- ✅ Use SOCKS4/SOCKS5 proxies for enhanced privacy
- ✅ Configure proxy authentication with username/password
- ✅ Implement proxy rotation for load distribution
- ✅ Bypass rate limiting and geo-restrictions
- ✅ Chain multiple proxies for added security
- ✅ Test and monitor proxy health automatically

!!! tip "When to Use Proxies"
    - **Privacy**: Hide your real IP address
    - **Geo-restrictions**: Access content from different regions
    - **Rate limiting**: Distribute requests across multiple IPs
    - **Testing**: Test region-specific functionality
    - **Compliance**: Adhere to usage policies

## Supported Proxy Types

| Type | Protocol | Authentication | Speed | Security | Recommended |
|------|----------|----------------|-------|----------|-------------|
| **HTTP** | HTTP | Yes | Fast | Low | Basic use |
| **HTTPS** | HTTPS | Yes | Fast | Medium | Encrypted traffic |
| **SOCKS4** | SOCKS v4 | No | Medium | Low | Legacy systems |
| **SOCKS5** | SOCKS v5 | Yes | Fast | High | ✅ **Best choice** |

!!! success "Recommendation"
    **Use SOCKS5 proxies** for the best balance of speed, security, and authentication support.

## Quick Start

### Basic HTTP Proxy

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig
from ultima_scraper_api.config import Network, Proxy

# Configure HTTP proxy
config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(
            http="http://proxy.example.com:8080",
            https="http://proxy.example.com:8080"
        )
    )
)

api = OnlyFansAPI(config)

# Use API with proxy
auth_json = {"cookie": "...", "user_agent": "...", "x-bc": "..."}
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    print(f"Connected via proxy: {user.username}")
```

### SOCKS5 Proxy (Recommended)

```python
# SOCKS5 proxy configuration (best for privacy)
config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(
            http="socks5://proxy.example.com:1080",
            https="socks5://proxy.example.com:1080"
        )
    )
)

api = OnlyFansAPI(config)
```

### Alternative Dictionary Format

You can also use the simpler dictionary format:

```python
# Using dictionary for proxy configuration
proxy_dict = {
    "http": "http://proxy.example.com:8080",
    "https": "http://proxy.example.com:8080",
}

config = UltimaScraperAPIConfig(proxy=proxy_dict)
api = OnlyFansAPI(config)
```

## Proxy Authentication

### HTTP/HTTPS with Authentication

```python
# Proxy with username and password
proxy_url = "http://username:password@proxy.example.com:8080"

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(
            http=proxy_url,
            https=proxy_url
        )
    )
)

api = OnlyFansAPI(config)
```

### SOCKS5 with Authentication

```python
# SOCKS5 with authentication (most secure)
proxy_url = "socks5://username:password@proxy.example.com:1080"

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(
            http=proxy_url,
            https=proxy_url
        )
    )
)

api = OnlyFansAPI(config)
```

### Special Characters in Credentials

If your username or password contains special characters, URL-encode them:

```python
from urllib.parse import quote

username = quote("user@example.com")
password = quote("p@ssw0rd!#$%")

proxy_url = f"socks5://{username}:{password}@proxy.example.com:1080"

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)
```

### Environment Variables (Secure)

Store credentials securely in environment variables:

```bash
# Set environment variables
export PROXY_HOST="proxy.example.com"
export PROXY_PORT="1080"
export PROXY_USERNAME="myuser"
export PROXY_PASSWORD="mypassword"
```

```python
import os

# Load from environment
proxy_host = os.getenv("PROXY_HOST")
proxy_port = os.getenv("PROXY_PORT")
proxy_user = os.getenv("PROXY_USERNAME")
proxy_pass = os.getenv("PROXY_PASSWORD")

proxy_url = f"socks5://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)
```

## Advanced Proxy Configuration

### Using aiohttp-socks

```python
from aiohttp_socks import ProxyConnector
import aiohttp

# Create SOCKS proxy connector
connector = ProxyConnector.from_url('socks5://proxy.example.com:1080')

# Custom session with proxy
async with aiohttp.ClientSession(connector=connector) as session:
    # Use session for API requests
    pass
```

### Proxy Chain

Chain multiple proxies for added privacy:

```python
from python_socks.async_.asyncio import Proxy

# Configure proxy chain
proxies = [
    Proxy.from_url("socks5://first-proxy.com:1080"),
    Proxy.from_url("socks5://second-proxy.com:1080"),
]

# Use with your requests
# Note: Implementation depends on API structure
```

## Proxy Rotation

### Simple Proxy Rotation

```python
import itertools

class ProxyRotator:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.proxy_pool = itertools.cycle(proxy_list)
    
    def get_next_proxy(self):
        return next(self.proxy_pool)

# Usage
proxies = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]

rotator = ProxyRotator(proxies)

# Get proxy for each request
proxy_url = rotator.get_next_proxy()
config = UltimaScraperAPIConfig(proxy={"http": proxy_url, "https": proxy_url})
```

### Smart Proxy Rotation

Rotate proxies based on success/failure:

```python
import random
from collections import defaultdict

class SmartProxyRotator:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.stats = defaultdict(lambda: {"success": 0, "failure": 0})
    
    def get_best_proxy(self):
        # Calculate success rate for each proxy
        proxy_scores = {}
        for proxy in self.proxy_list:
            stats = self.stats[proxy]
            total = stats["success"] + stats["failure"]
            if total == 0:
                proxy_scores[proxy] = 1.0  # New proxy, give it a chance
            else:
                proxy_scores[proxy] = stats["success"] / total
        
        # Weight selection by success rate
        proxies = list(proxy_scores.keys())
        weights = list(proxy_scores.values())
        return random.choices(proxies, weights=weights, k=1)[0]
    
    def record_success(self, proxy):
        self.stats[proxy]["success"] += 1
    
    def record_failure(self, proxy):
        self.stats[proxy]["failure"] += 1

# Usage
rotator = SmartProxyRotator(proxies)

async def fetch_with_proxy_rotation(authed, username):
    max_retries = 3
    
    for attempt in range(max_retries):
        proxy = rotator.get_best_proxy()
        
        try:
            # Configure with selected proxy
            config = UltimaScraperAPIConfig(proxy={"http": proxy, "https": proxy})
            
            # Make request
            user = await authed.get_user(username)
            
            # Record success
            rotator.record_success(proxy)
            return user
            
        except Exception as e:
            print(f"Proxy {proxy} failed: {e}")
            rotator.record_failure(proxy)
            
            if attempt == max_retries - 1:
                raise
```

## Proxy Testing

### Test Proxy Connectivity

```python
import aiohttp
from aiohttp_socks import ProxyConnector

async def test_proxy(proxy_url, test_url="https://httpbin.org/ip"):
    """Test if a proxy is working"""
    try:
        connector = ProxyConnector.from_url(proxy_url)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(test_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Proxy {proxy_url} is working. IP: {data.get('origin')}")
                    return True
                else:
                    print(f"Proxy {proxy_url} returned status {response.status}")
                    return False
                    
    except Exception as e:
        print(f"Proxy {proxy_url} failed: {e}")
        return False

# Test multiple proxies
proxies = [
    "http://proxy1.example.com:8080",
    "socks5://proxy2.example.com:1080",
]

async def test_all_proxies():
    results = []
    for proxy in proxies:
        result = await test_proxy(proxy)
        results.append((proxy, result))
    return results
```

### Measure Proxy Performance

```python
import time

async def measure_proxy_speed(proxy_url, test_url="https://httpbin.org/ip"):
    """Measure proxy response time"""
    try:
        start_time = time.time()
        
        connector = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(test_url, timeout=30) as response:
                await response.read()
                
        elapsed = time.time() - start_time
        print(f"Proxy {proxy_url}: {elapsed:.2f}s")
        return elapsed
        
    except Exception as e:
        print(f"Proxy {proxy_url} failed: {e}")
        return float('inf')

# Find fastest proxy
async def find_fastest_proxy(proxy_list):
    speeds = {}
    
    for proxy in proxy_list:
        speed = await measure_proxy_speed(proxy)
        speeds[proxy] = speed
    
    fastest = min(speeds.items(), key=lambda x: x[1])
    print(f"Fastest proxy: {fastest[0]} ({fastest[1]:.2f}s)")
    return fastest[0]
```

## Environment-Based Configuration

### Load Proxies from Environment

```python
import os

# Set proxy via environment variable
# export HTTP_PROXY=http://proxy.example.com:8080
# export HTTPS_PROXY=https://proxy.example.com:8080

proxy_config = {
    "http": os.getenv("HTTP_PROXY"),
    "https": os.getenv("HTTPS_PROXY"),
}

if proxy_config["http"] and proxy_config["https"]:
    config = UltimaScraperAPIConfig(proxy=proxy_config)
else:
    config = UltimaScraperAPIConfig()  # No proxy
```

### Load from Configuration File

```python
import json

# Load proxies from JSON file
def load_proxies_from_file(filepath):
    with open(filepath) as f:
        data = json.load(f)
        return data.get("proxies", [])

# proxies.json:
# {
#   "proxies": [
#     "http://proxy1.example.com:8080",
#     "http://proxy2.example.com:8080"
#   ]
# }

proxies = load_proxies_from_file("proxies.json")
rotator = ProxyRotator(proxies)
```

## Proxy for Specific Platforms

### OnlyFans with Proxy

```python
from ultima_scraper_api import OnlyFansAPI

proxy_config = {
    "http": "socks5://proxy.example.com:1080",
    "https": "socks5://proxy.example.com:1080",
}

config = UltimaScraperAPIConfig(proxy=proxy_config)
api = OnlyFansAPI(config)

async with api.login_context(auth_json) as authed:
    # All requests will use the proxy
    user = await authed.get_user("username")
```

## Real-World Examples

### Complete Proxy Setup with Error Handling

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig
from ultima_scraper_api.config import Network, Proxy

async def main():
    # Configure proxy
    proxy_url = "socks5://user:pass@proxy.example.com:1080"
    
    config = UltimaScraperAPIConfig(
        network=Network(
            proxy=Proxy(http=proxy_url, https=proxy_url)
        )
    )
    
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "your_cookie",
        "user_agent": "your_user_agent",
        "x-bc": "your_x-bc"
    }
    
    try:
        async with api.login_context(auth_json) as authed:
            if authed and authed.is_authed():
                # Verify proxy is working
                me = await authed.get_me()
                print(f"✓ Connected via proxy as: {me.username}")
                
                # Fetch data through proxy
                user = await authed.get_user("username")
                posts = await user.get_posts(limit=10)
                print(f"✓ Fetched {len(posts)} posts via proxy")
                
            else:
                print("✗ Authentication failed")
                
    except Exception as e:
        print(f"✗ Error with proxy: {e}")
        print("Try testing proxy connectivity first")

if __name__ == "__main__":
    asyncio.run(main())
```

### Proxy with Multiple Platforms

```python
# Use same proxy for all platforms
proxy_url = "socks5://proxy.example.com:1080"

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)

# OnlyFans
from ultima_scraper_api import OnlyFansAPI
of_api = OnlyFansAPI(config)

# Fansly
from ultima_scraper_api import FanslyAPI
fansly_api = FanslyAPI(config)

# All platforms will use the same proxy
```

### Dynamic Proxy Configuration

```python
import os
from pathlib import Path
import json

def load_proxy_config():
    """Load proxy configuration from file or environment"""
    
    # Try environment variables first
    if os.getenv("PROXY_URL"):
        return os.getenv("PROXY_URL")
    
    # Try config file
    config_file = Path("proxy_config.json")
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
            return data.get("proxy_url")
    
    # No proxy configured
    return None

# Usage
proxy_url = load_proxy_config()

if proxy_url:
    print(f"Using proxy: {proxy_url}")
    config = UltimaScraperAPIConfig(
        network=Network(
            proxy=Proxy(http=proxy_url, https=proxy_url)
        )
    )
else:
    print("No proxy configured - using direct connection")
    config = UltimaScraperAPIConfig()

api = OnlyFansAPI(config)
```

---

## Troubleshooting

### Proxy Connection Fails

!!! error "Common Error"
    ```
    aiohttp.client_exceptions.ClientProxyConnectionError: 
    Cannot connect to host proxy.example.com:1080
    ```

**Possible Causes:**

- ❌ Incorrect proxy URL or format
- ❌ Proxy server is down or unreachable
- ❌ Authentication credentials are wrong
- ❌ Firewall blocking proxy connection
- ❌ Wrong protocol (HTTP instead of SOCKS5)

**Solutions:**

1. **Verify proxy URL format:**
   ```python
   # Correct formats:
   "http://proxy.com:8080"
   "socks5://proxy.com:1080"
   "socks5://user:pass@proxy.com:1080"
   
   # Incorrect formats:
   "proxy.com:1080"  # Missing protocol
   "socks5//proxy.com:1080"  # Missing colon
   ```

2. **Test proxy independently:**
   ```bash
   # Test with curl
   curl --proxy socks5://proxy.example.com:1080 https://httpbin.org/ip
   ```

3. **Check credentials:**
   ```python
   # URL-encode special characters
   from urllib.parse import quote
   username = quote("user@domain.com")
   password = quote("p@$$w0rd")
   ```

4. **Try different proxy:**
   ```python
   # Fallback to direct connection if proxy fails
   try:
       config = UltimaScraperAPIConfig(
           network=Network(
               proxy=Proxy(http=proxy_url, https=proxy_url)
           )
       )
   except Exception:
       print("Proxy failed, using direct connection")
       config = UltimaScraperAPIConfig()
   ```

### Slow Performance

!!! warning "Symptom"
    Requests taking significantly longer than normal

**Possible Causes:**

- 🐌 Geographically distant proxy server
- 🐌 Overloaded proxy with many users
- 🐌 Multiple proxy hops (proxy chain)
- 🐌 Bandwidth throttling

**Solutions:**

1. **Use geographically closer proxies:**
   ```python
   # Choose proxies near your target service
   # For US-based service, use US proxy
   us_proxy = "socks5://us-proxy.example.com:1080"
   ```

2. **Test and compare proxy speeds:**
   ```python
   import time
   
   async def benchmark_proxy(proxy_url):
       start = time.time()
       # Make test request
       config = UltimaScraperAPIConfig(
           network=Network(
               proxy=Proxy(http=proxy_url, https=proxy_url)
           )
       )
       # ... make request ...
       elapsed = time.time() - start
       print(f"{proxy_url}: {elapsed:.2f}s")
       return elapsed
   ```

3. **Implement timeout settings:**
   ```python
   # Add timeout to prevent hanging
   config = UltimaScraperAPIConfig(
       network=Network(
           proxy=Proxy(http=proxy_url, https=proxy_url),
           timeout=30  # 30 second timeout
       )
   )
   ```

### Authentication Errors

!!! error "Common Error"
    ```
    ProxyError: Proxy authentication failed
    ```

**Solutions:**

1. **Verify credentials format:**
   ```python
   # Correct format
   proxy_url = "socks5://username:password@proxy.com:1080"
   
   # Common mistakes:
   # - Wrong order: "socks5://password:username@..."
   # - Missing @ symbol
   # - Unencoded special characters
   ```

2. **URL-encode special characters:**
   ```python
   from urllib.parse import quote
   
   # If username/password contains @, :, /, etc.
   username = quote("user@company.com", safe="")
   password = quote("p@$$w0rd!#$", safe="")
   
   proxy_url = f"socks5://{username}:{password}@proxy.com:1080"
   ```

3. **Test credentials separately:**
   ```bash
   # Test SOCKS5 auth with curl
   curl --proxy socks5://username:password@proxy.com:1080 \
        https://httpbin.org/ip
   ```

### SSL/TLS Certificate Errors

!!! error "Common Error"
    ```
    ssl.SSLError: certificate verify failed
    ```

**Solutions:**

```python
# For testing only - disable SSL verification
# WARNING: Only use in development!
config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url),
        verify_ssl=False  # Disable SSL verification
    )
)

# Better: Use proper certificates
# Install required CA certificates on your system
```

### Rate Limiting Through Proxy

Even with proxies, you may encounter rate limits:

```python
import asyncio

async def fetch_with_rate_limit(authed, username):
    """Fetch with built-in rate limiting"""
    try:
        user = await authed.get_user(username)
        
        # Add delay between requests
        await asyncio.sleep(1.0)
        
        return user
    except Exception as e:
        if "rate limit" in str(e).lower():
            print("Rate limited - waiting...")
            await asyncio.sleep(60)  # Wait 1 minute
            return await fetch_with_rate_limit(authed, username)
        raise
```

---

## Best Practices

### 1. Choose the Right Proxy Type

```python
# ✅ Best: SOCKS5 for privacy and performance
proxy_url = "socks5://proxy.com:1080"

# ✅ Good: HTTPS for encrypted traffic
proxy_url = "https://proxy.com:8080"

# ⚠️ OK: HTTP for basic needs
proxy_url = "http://proxy.com:8080"

# ❌ Avoid: SOCKS4 (no authentication, less secure)
proxy_url = "socks4://proxy.com:1080"
```

### 2. Implement Proxy Rotation

```python
# Rotate proxies to distribute load
proxy_list = [
    "socks5://proxy1.com:1080",
    "socks5://proxy2.com:1080",
    "socks5://proxy3.com:1080",
]

import random

def get_random_proxy():
    return random.choice(proxy_list)

# Use different proxy for each session
proxy_url = get_random_proxy()
config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)
```

### 3. Test Proxies Before Use

```python
async def validate_proxy(proxy_url):
    """Test if proxy is working before using it"""
    try:
        import aiohttp
        from aiohttp_socks import ProxyConnector
        
        connector = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://httpbin.org/ip", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Proxy working - IP: {data['origin']}")
                    return True
    except Exception as e:
        print(f"✗ Proxy failed: {e}")
        return False

# Validate before using
if await validate_proxy(proxy_url):
    config = UltimaScraperAPIConfig(
        network=Network(
            proxy=Proxy(http=proxy_url, https=proxy_url)
        )
    )
```

### 4. Monitor Proxy Health

```python
from collections import defaultdict
import time

class ProxyMonitor:
    def __init__(self):
        self.stats = defaultdict(lambda: {
            "requests": 0,
            "failures": 0,
            "total_time": 0,
            "last_used": None
        })
    
    def record_request(self, proxy_url, success, elapsed_time):
        stats = self.stats[proxy_url]
        stats["requests"] += 1
        if not success:
            stats["failures"] += 1
        stats["total_time"] += elapsed_time
        stats["last_used"] = time.time()
    
    def get_success_rate(self, proxy_url):
        stats = self.stats[proxy_url]
        if stats["requests"] == 0:
            return 0
        return (stats["requests"] - stats["failures"]) / stats["requests"]
    
    def get_avg_response_time(self, proxy_url):
        stats = self.stats[proxy_url]
        if stats["requests"] == 0:
            return 0
        return stats["total_time"] / stats["requests"]
```

### 5. Secure Credential Storage

```python
# ❌ BAD: Hardcoded credentials
proxy_url = "socks5://myuser:mypassword@proxy.com:1080"

# ✅ GOOD: Environment variables
import os
proxy_user = os.getenv("PROXY_USER")
proxy_pass = os.getenv("PROXY_PASS")
proxy_url = f"socks5://{proxy_user}:{proxy_pass}@proxy.com:1080"

# ✅ BETTER: Use keyring
import keyring
proxy_pass = keyring.get_password("proxy", "myuser")
proxy_url = f"socks5://myuser:{proxy_pass}@proxy.com:1080"
```

### 6. Implement Fallback Strategy

```python
async def fetch_with_fallback(authed, username):
    """Try proxy first, fallback to direct connection"""
    proxies = [
        "socks5://proxy1.com:1080",
        "socks5://proxy2.com:1080",
        None,  # Direct connection as last resort
    ]
    
    for proxy_url in proxies:
        try:
            if proxy_url:
                config = UltimaScraperAPIConfig(
                    network=Network(
                        proxy=Proxy(http=proxy_url, https=proxy_url)
                    )
                )
                print(f"Trying proxy: {proxy_url}")
            else:
                config = UltimaScraperAPIConfig()
                print("Trying direct connection")
            
            api = OnlyFansAPI(config)
            async with api.login_context(auth_json) as authed:
                user = await authed.get_user(username)
                return user
                
        except Exception as e:
            print(f"Failed: {e}")
            continue
    
    raise Exception("All connection methods failed")
```

### 7. Log Proxy Usage

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log proxy configuration
proxy_url = "socks5://proxy.com:1080"
logger.info(f"Configuring proxy: {proxy_url}")

config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)

# Log requests
logger.info("Making request through proxy")
# ... make request ...
logger.info("Request completed successfully")
```

### 8. Use Residential Proxies for Better Success

```python
# Datacenter proxy (may be detected)
datacenter_proxy = "socks5://datacenter-proxy.com:1080"

# Residential proxy (better success rate, more expensive)
residential_proxy = "socks5://residential-proxy.com:1080"

# Choose based on your needs
proxy_url = residential_proxy  # For production
config = UltimaScraperAPIConfig(
    network=Network(
        proxy=Proxy(http=proxy_url, https=proxy_url)
    )
)
```

---

## Related Documentation

- **[Configuration Guide](../getting-started/configuration.md)** - Complete configuration options
- **[Authentication](authentication.md)** - Authentication with proxies
- **[Working with APIs](working-with-apis.md)** - API usage patterns
- **[Session Management](session-management.md)** - Session handling with proxies
- **[OnlyFans API Reference](../api-reference/onlyfans.md)** - API documentation

---

## External Resources

- **[python-socks Documentation](https://github.com/romis2012/python-socks)** - SOCKS proxy library
- **[aiohttp-socks Documentation](https://github.com/romis2012/aiohttp-socks)** - Async SOCKS support
- **[SOCKS Protocol](https://en.wikipedia.org/wiki/SOCKS)** - Understanding SOCKS
- **[Proxy Best Practices](https://www.whatismyip.com/proxy-vs-vpn/)** - Proxy vs VPN comparison
