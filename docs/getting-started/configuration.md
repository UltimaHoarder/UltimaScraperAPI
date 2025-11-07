# Configuration

UltimaScraperAPI provides a comprehensive configuration system built on Pydantic models, allowing you to customize network settings, proxies, caching, DRM, and platform-specific options.

## Overview

Configuration is organized into three main layers:

1. **Global Settings** - Network, Redis, Server, DRM
2. **Site-Specific Settings** - OnlyFans, Fansly configurations
3. **Runtime Options** - Media quality, webhooks

## Basic Usage

### Default Configuration

```python
from ultima_scraper_api import UltimaScraperAPIConfig

# Use default configuration
config = UltimaScraperAPIConfig()
```

### Custom Configuration

```python
from ultima_scraper_api import UltimaScraperAPIConfig

# Customize specific settings
config = UltimaScraperAPIConfig()

# Modify network settings
config.settings.network.max_connections = 50

# Enable Redis
config.settings.redis.enabled = True
config.settings.redis.host = "localhost"
config.settings.redis.port = 6379

# Set media quality
config.site_apis.onlyfans.media_quality.video = "720p"
```

## Configuration Structure

### Network Settings

Control connection limits and proxy configuration:

```python
from ultima_scraper_api import UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()

# Network configuration
config.settings.network.max_connections = 100  # Max concurrent connections (-1 = unlimited)
config.settings.network.proxy_fallback = True  # Fallback to direct if proxy fails
```

#### Adding Proxies

```python
from ultima_scraper_api.config import Proxy

# Add a proxy
proxy = Proxy(
    url="socks5://proxy.example.com:1080",
    username="proxy_user",  # Optional
    password="proxy_pass",  # Optional
    max_connections=50      # Per-proxy connection limit (-1 = unlimited)
)

config.settings.network.proxies.append(proxy)
```

!!! tip "Proxy Support"
    UltimaScraperAPI supports HTTP, HTTPS, SOCKS4, and SOCKS5 proxies through `python-socks` and `aiohttp-socks`.

**Proxy URL Formats:**

- HTTP: `http://proxy.example.com:8080`
- HTTPS: `https://proxy.example.com:8443`
- SOCKS4: `socks4://proxy.example.com:1080`
- SOCKS5: `socks5://proxy.example.com:1080`

**Multiple Proxies Example:**

```python
from ultima_scraper_api.config import Proxy

config = UltimaScraperAPIConfig()

# Add multiple proxies
proxies = [
    Proxy(url="socks5://proxy1.example.com:1080", max_connections=25),
    Proxy(url="socks5://proxy2.example.com:1080", max_connections=25),
    Proxy(url="http://proxy3.example.com:8080", username="user", password="pass"),
]

config.settings.network.proxies.extend(proxies)
config.settings.network.proxy_fallback = False  # Don't fall back to direct connection
```

### Redis Configuration

Redis is used for caching and session management:

```python
config = UltimaScraperAPIConfig()

# Redis settings
config.settings.redis.enabled = True
config.settings.redis.host = "localhost"
config.settings.redis.port = 6379
config.settings.redis.db = 0
config.settings.redis.password = "your_redis_password"  # If required
```

**Benefits of Redis:**

- 🚀 Faster subsequent requests through caching
- 💾 Persistent session storage
- 🔄 Shared state across multiple instances
- ⚡ Reduced API calls

!!! warning "Redis Requirement"
    Redis must be installed and running if `enabled=True`. Install with: `sudo apt install redis-server` (Linux) or `brew install redis` (macOS).

### Server Configuration

Built-in server settings (for API server mode):

```python
config = UltimaScraperAPIConfig()

# Server settings
config.settings.server.active = False  # Enable/disable server mode
config.settings.server.host = "0.0.0.0"
config.settings.server.port = 8080
```

### DRM Configuration

Configure Widevine DRM for protected content:

```python
from pathlib import Path

config = UltimaScraperAPIConfig()

# DRM settings
config.settings.drm.device_client_blob_filepath = Path("client_id.blob")
config.settings.drm.device_private_key_filepath = Path("private_key.pem")
config.settings.drm.decrypt_media_path = Path("decrypted_media/")
```

!!! note "DRM Files"
    DRM configuration requires Widevine device files (client ID blob and private key) for decrypting protected content.

## Platform-Specific Configuration

### OnlyFans Configuration

```python
config = UltimaScraperAPIConfig()

# Media quality settings
config.site_apis.onlyfans.media_quality.image = "source"  # source, high, medium, low
config.site_apis.onlyfans.media_quality.video = "source"  # source, 1080p, 720p, 480p, etc.
config.site_apis.onlyfans.media_quality.audio = "source"

# Dynamic rules URL (for rule-based scraping)
config.site_apis.onlyfans.dynamic_rules_url = "https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json"

# Cache settings
config.site_apis.onlyfans.cache.paid_content = 3600  # Cache duration in seconds
```

### Fansly Configuration

```python
config = UltimaScraperAPIConfig()

# Media quality for Fansly
config.site_apis.fansly.media_quality.image = "source"
config.site_apis.fansly.media_quality.video = "source"
config.site_apis.fansly.media_quality.audio = "source"
```

### Webhooks

Configure webhooks for notifications:

```python
config = UltimaScraperAPIConfig()

# Authentication webhook
config.site_apis.onlyfans.webhooks.auth.active = True
config.site_apis.onlyfans.webhooks.auth.url = "https://webhook.site/your-webhook-id"
config.site_apis.onlyfans.webhooks.auth.hide_info = ["password", "cookie"]

# Download webhook
config.site_apis.onlyfans.webhooks.download.active = True
config.site_apis.onlyfans.webhooks.download.url = "https://webhook.site/your-webhook-id"
```

## Configuration from JSON/YAML

### Using JSON

```python
import json
from ultima_scraper_api import UltimaScraperAPIConfig

# JSON configuration file
config_json = """
{
  "settings": {
    "network": {
      "max_connections": 50,
      "proxy_fallback": true,
      "proxies": [
        {
          "url": "socks5://proxy.example.com:1080",
          "max_connections": 25
        }
      ]
    },
    "redis": {
      "enabled": true,
      "host": "localhost",
      "port": 6379,
      "db": 0
    }
  },
  "site_apis": {
    "onlyfans": {
      "media_quality": {
        "video": "720p"
      }
    }
  }
}
"""

# Load configuration
config_dict = json.loads(config_json)
config = UltimaScraperAPIConfig(**config_dict)
```

### Loading from File

```python
import json
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPIConfig

# Load from JSON file
config_file = Path("config.json")
with open(config_file) as f:
    config_dict = json.load(f)

config = UltimaScraperAPIConfig(**config_dict)
```

### Using Pydantic's model_validate

```python
from ultima_scraper_api import UltimaScraperAPIConfig

# Validate and load from dict
config_dict = {
    "settings": {
        "network": {"max_connections": 100},
        "redis": {"enabled": True}
    }
}

config = UltimaScraperAPIConfig.model_validate(config_dict)
```

## Environment Variables

While UltimaScraperAPI doesn't natively load from environment variables, you can easily implement this pattern:

```python
import os
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Proxy

# Load configuration from environment
config = UltimaScraperAPIConfig()

# Network settings from env
if proxy_url := os.getenv("ULTIMA_PROXY_URL"):
    proxy = Proxy(
        url=proxy_url,
        username=os.getenv("ULTIMA_PROXY_USER"),
        password=os.getenv("ULTIMA_PROXY_PASS"),
    )
    config.settings.network.proxies.append(proxy)

if max_conn := os.getenv("ULTIMA_MAX_CONNECTIONS"):
    config.settings.network.max_connections = int(max_conn)

# Redis settings from env
config.settings.redis.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
config.settings.redis.host = os.getenv("REDIS_HOST", "localhost")
config.settings.redis.port = int(os.getenv("REDIS_PORT", "6379"))
config.settings.redis.db = int(os.getenv("REDIS_DB", "0"))

if redis_pass := os.getenv("REDIS_PASSWORD"):
    config.settings.redis.password = redis_pass

# DRM settings from env
if drm_blob := os.getenv("DRM_CLIENT_BLOB"):
    config.settings.drm.device_client_blob_filepath = Path(drm_blob)
if drm_key := os.getenv("DRM_PRIVATE_KEY"):
    config.settings.drm.device_private_key_filepath = Path(drm_key)
```

**.env file example:**

```bash
# Network
ULTIMA_PROXY_URL=socks5://proxy.example.com:1080
ULTIMA_PROXY_USER=username
ULTIMA_PROXY_PASS=password
ULTIMA_MAX_CONNECTIONS=50

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# DRM
DRM_CLIENT_BLOB=/path/to/client_id.blob
DRM_PRIVATE_KEY=/path/to/private_key.pem
```

## Complete Configuration Example

Here's a comprehensive example with all options:

```python
from pathlib import Path
from ultima_scraper_api import UltimaScraperAPIConfig
from ultima_scraper_api.config import Proxy

# Create configuration
config = UltimaScraperAPIConfig()

# === NETWORK SETTINGS ===
config.settings.network.max_connections = 100
config.settings.network.proxy_fallback = True

# Add proxies
config.settings.network.proxies = [
    Proxy(url="socks5://proxy1.example.com:1080", max_connections=50),
    Proxy(url="socks5://proxy2.example.com:1080", max_connections=50),
]

# === REDIS SETTINGS ===
config.settings.redis.enabled = True
config.settings.redis.host = "localhost"
config.settings.redis.port = 6379
config.settings.redis.db = 0
config.settings.redis.password = None

# === SERVER SETTINGS ===
config.settings.server.active = False
config.settings.server.host = "localhost"
config.settings.server.port = 8080

# === DRM SETTINGS ===
config.settings.drm.device_client_blob_filepath = Path("client_id.blob")
config.settings.drm.device_private_key_filepath = Path("private_key.pem")
config.settings.drm.decrypt_media_path = Path("decrypted/")

# === ONLYFANS SETTINGS ===
config.site_apis.onlyfans.media_quality.image = "source"
config.site_apis.onlyfans.media_quality.video = "source"
config.site_apis.onlyfans.media_quality.audio = "source"
config.site_apis.onlyfans.cache.paid_content = 3600

# Webhooks
config.site_apis.onlyfans.webhooks.auth.active = False
config.site_apis.onlyfans.webhooks.download.active = False

# === FANSLY SETTINGS ===
config.site_apis.fansly.media_quality.video = "source"

# Use the configuration
from ultima_scraper_api import OnlyFansAPI

api = OnlyFansAPI(config)
```

## Configuration Best Practices

### 1. Separate Configuration from Code

```python
# ✓ Good: Load from external file
from pathlib import Path
import json
from ultima_scraper_api import UltimaScraperAPIConfig

config_file = Path("config.json")
with open(config_file) as f:
    config = UltimaScraperAPIConfig(**json.load(f))

# ✗ Bad: Hardcode everything
config = UltimaScraperAPIConfig()
config.settings.redis.password = "hardcoded_password"  # Don't do this!
```

### 2. Use Environment Variables for Secrets

```python
import os

# ✓ Good: Credentials from environment
auth_json = {
    "cookie": os.getenv("ONLYFANS_COOKIE"),
    "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
    "x-bc": os.getenv("ONLYFANS_XBC"),
}

# ✗ Bad: Hardcoded credentials
auth_json = {
    "cookie": "auth_id=123456...",  # Don't commit this!
    "user_agent": "Mozilla/5.0...",
    "x-bc": "token123",
}
```

### 3. Enable Redis for Production

```python
# For production use, enable Redis
config.settings.redis.enabled = True
config.settings.redis.host = os.getenv("REDIS_HOST", "localhost")
```

### 4. Configure Proxies for High-Volume Scraping

```python
# Use proxies to avoid rate limiting
from ultima_scraper_api.config import Proxy

proxies = [Proxy(url=url) for url in os.getenv("PROXY_URLS", "").split(",") if url]
config.settings.network.proxies = proxies
```

### 5. Set Appropriate Connection Limits

```python
# Don't overload the server
config.settings.network.max_connections = 50  # Reasonable limit

# Per-proxy limits
for proxy in config.settings.network.proxies:
    proxy.max_connections = 25
```

### 6. Validate Configuration

```python
from ultima_scraper_api import UltimaScraperAPIConfig
from pydantic import ValidationError

try:
    config = UltimaScraperAPIConfig(**config_dict)
except ValidationError as e:
    print(f"Configuration error: {e}")
    # Handle validation errors
```

## Exporting Configuration

You can export your configuration to JSON:

```python
import json
from ultima_scraper_api import UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()

# Configure as needed
config.settings.network.max_connections = 100
config.settings.redis.enabled = True

# Export to JSON
config_json = config.model_dump_json(indent=2)
print(config_json)

# Save to file
with open("config.json", "w") as f:
    f.write(config_json)
```

## Accessing Site-Specific Settings

```python
from ultima_scraper_api import UltimaScraperAPIConfig

config = UltimaScraperAPIConfig()

# Get site-specific configuration
onlyfans_config = config.site_apis.get_settings("OnlyFans")
fansly_config = config.site_apis.get_settings("Fansly")

# Modify and use
onlyfans_config.media_quality.video = "720p"
```

## Summary

| Setting | Purpose | Default |
|---------|---------|---------|
| `settings.network.max_connections` | Max concurrent connections | `-1` (unlimited) |
| `settings.network.proxy_fallback` | Fallback to direct if proxy fails | `False` |
| `settings.redis.enabled` | Enable Redis caching | `True` |
| `settings.redis.host` | Redis server host | `"localhost"` |
| `settings.redis.port` | Redis server port | `6379` |
| `settings.server.active` | Enable server mode | `False` |
| `site_apis.onlyfans.media_quality.video` | Video quality preference | `"source"` |
| `site_apis.onlyfans.cache.paid_content` | Paid content cache duration (sec) | `3600` |

## Next Steps

Now that you understand configuration, explore related topics:

- 🔐 [Authentication](../user-guide/authentication.md) - Set up API authentication
- 🌐 [Proxy Support](../user-guide/proxy-support.md) - Deep dive into proxy configuration
- 🔄 [Session Management](../user-guide/session-management.md) - Learn about Redis and caching
- 📚 [API Reference](../api-reference/onlyfans.md) - Explore the full API
