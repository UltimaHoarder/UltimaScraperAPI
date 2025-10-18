# Authentication

This comprehensive guide covers authentication for all supported platforms in UltimaScraperAPI.

## Overview

UltimaScraperAPI uses cookie-based authentication to interact with platform APIs. This mimics how your browser communicates with these platforms, allowing full API access.

### Authentication Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **Cookie-based** | Primary authentication method using browser session cookies | Production use, full API access |
| **Guest mode** | Limited access without authentication | Testing, public data only |

!!! info "Why Cookie-Based?"
    Platform APIs authenticate using session cookies from logged-in browser sessions. This is the most reliable method and provides full API access.

## Prerequisites

Before authenticating, you need:

- ✅ Active account on the target platform (OnlyFans, Fansly, etc.)
- ✅ Modern web browser (Chrome, Firefox, Edge)
- ✅ Basic knowledge of browser developer tools

## Obtaining Authentication Credentials

### Step-by-Step Guide

#### For OnlyFans

1. **Open your browser** and navigate to [onlyfans.com](https://onlyfans.com)
2. **Log in** to your account
3. **Open Developer Tools**:
   - Windows/Linux: Press `F12` or `Ctrl+Shift+I`
   - macOS: Press `Cmd+Option+I`
4. **Go to the Network tab**
5. **Refresh the page** or navigate to trigger API requests
6. **Find an API request**:
   - Look for requests to `onlyfans.com/api/`
   - Click on any request to view details
7. **Extract credentials**:

=== "Cookie"
    In the **Request Headers** section, find the `Cookie` header.
    
    Copy the **entire cookie string**, which looks like:
    ```
    auth_id=123456; sess=abcdef1234567890...; auth_hash=xyz...
    ```
    
    !!! tip "Cookie Format"
        The cookie string contains multiple key-value pairs separated by semicolons. Copy everything.

=== "User-Agent"
    Find the `User-Agent` header in the Request Headers.
    
    Example:
    ```
    Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
    ```
    
    !!! warning "Important"
        Use your actual browser's User-Agent, not a generic one. Mismatched User-Agents can trigger security measures.

=== "x-bc"
    Find the `x-bc` header in the Request Headers. This is an OnlyFans-specific authentication token.
    
    Example:
    ```
    a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    ```
    
    !!! note "x-bc Token"
        The `x-bc` token is dynamically generated and required for OnlyFans API requests. It's typically found in requests to `/api2/v2/` endpoints.

#### For Fansly (WIP)

1. **Navigate to** [fansly.com](https://fansly.com)
2. **Log in** to your account
3. **Open Developer Tools** (F12)
4. **Go to Network tab**
5. **Find API requests** to `apiv2.fansly.com`
6. **Extract credentials**:
   - Cookie header
   - User-Agent
   - Fansly-specific authorization tokens

!!! warning "Fansly Status"
    Fansly support is under active development. Authentication structure may change.

#### For LoyalFans (WIP)

1. **Navigate to** [loyalfans.com](https://loyalfans.com)
2. **Log in** to your account
3. **Open Developer Tools** (F12)
4. **Go to Network tab**
5. **Find API requests**
6. **Extract credentials**:
   - Cookie header
   - User-Agent

!!! warning "LoyalFans Status"
    LoyalFans support is under active development. Authentication structure may change.

### Video Tutorial: Finding Credentials

<div style="position: relative; padding-bottom: 56.25%; height: 0;">
  <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
    src="about:blank" frameborder="0" allowfullscreen>
  </iframe>
</div>

*Note: Replace with actual tutorial video when available*

## Authentication Implementation

### Basic Authentication Example

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def authenticate_onlyfans():
    """Basic authentication example for OnlyFans."""
    
    # Initialize configuration
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Authentication credentials
    auth_json = {
        "cookie": "auth_id=123456; sess=abcdef...; auth_hash=xyz...",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        "x-bc": "a1b2c3d4e5f6g7h8i9j0..."
    }
    
    # Authenticate and use API
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ Successfully authenticated!")
            
            # Get authenticated user info
            me = await authed.get_authed_user()
            print(f"Logged in as: {me.name} (@{me.username})")
            print(f"User ID: {me.id}")
            
            return authed
        else:
            print("✗ Authentication failed")
            return None

# Run authentication
if __name__ == "__main__":
    asyncio.run(authenticate_onlyfans())
```

### Secure Authentication Pattern

Using environment variables to keep credentials secure:

```python
import asyncio
import os
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def secure_authenticate():
    """Secure authentication using environment variables."""
    
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Load credentials from environment
    auth_json = {
        "cookie": os.getenv("ONLYFANS_COOKIE"),
        "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
        "x-bc": os.getenv("ONLYFANS_XBC")
    }
    
    # Validate credentials are present
    if not all(auth_json.values()):
        print("✗ Missing authentication credentials in environment!")
        print("Required: ONLYFANS_COOKIE, ONLYFANS_USER_AGENT, ONLYFANS_XBC")
        return None
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ Authenticated successfully")
            return authed
        else:
            print("✗ Authentication failed")
            return None

if __name__ == "__main__":
    asyncio.run(secure_authenticate())
```

### Guest Mode (Limited Access)

For testing or accessing public data without authentication:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def guest_mode_example():
    """Connect in guest mode - very limited functionality."""
    
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # No credentials needed for guest mode
    async with api.login_context(guest=True) as authed:
        if authed:
            print("✓ Connected in guest mode")
            # Very limited operations available
            # Most features require full authentication
        else:
            print("✗ Failed to connect")

if __name__ == "__main__":
    asyncio.run(guest_mode_example())
```

!!! warning "Guest Mode Limitations"
    Guest mode provides **very limited** functionality:
    
    - ❌ Cannot access private content
    - ❌ Cannot view subscribed users
    - ❌ Cannot access messages
    - ❌ Cannot download restricted media
    - ✅ May access some public/free content (platform-dependent)
    
    **For production use, full authentication is required.**

## Platform-Specific Authentication

### OnlyFans (Stable) ✅

OnlyFans requires three authentication components:

| Field | Required | Description |
|-------|----------|-------------|
| `cookie` | ✅ Yes | Full cookie string from authenticated session |
| `user_agent` | ✅ Yes | Browser User-Agent string |
| `x-bc` | ✅ Yes | OnlyFans dynamic authentication token |

**Complete Example:**

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def onlyfans_auth_example():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # OnlyFans authentication
    auth_json = {
        "cookie": "auth_id=123456; sess=abcdef1234567890; auth_hash=xyz789; ...",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-bc": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    }
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ OnlyFans authentication successful")
            
            # Get subscriptions
            subscriptions = await authed.get_subscriptions()
            print(f"You have {len(subscriptions)} active subscriptions")
            
            # Get your own profile
            me = await authed.get_authed_user()
            print(f"Account: {me.name} (@{me.username})")
        else:
            print("✗ OnlyFans authentication failed")

asyncio.run(onlyfans_auth_example())
```

**Common OnlyFans Cookie Components:**

- `auth_id` - Your user authentication ID
- `sess` - Session token
- `auth_hash` - Authentication hash
- `auth_uid_` - User ID related token
- `fp` - Fingerprint token

### Fansly (Work in Progress) ⚠️ {#fansly}

Fansly authentication is under development. Current structure:

| Field | Required | Description |
|-------|----------|-------------|
| `cookie` | ✅ Yes | Session cookie from Fansly |
| `user_agent` | ✅ Yes | Browser User-Agent |
| `authorization` | ⚠️ Maybe | Authorization token (if required) |

**Example (Subject to Change):**

```python
import asyncio
from ultima_scraper_api import FanslyAPI, UltimaScraperAPIConfig

async def fansly_auth_example():
    config = UltimaScraperAPIConfig()
    api = FanslyAPI(config)
    
    # Fansly authentication (structure may change)
    auth_json = {
        "cookie": "session_id=...; other_cookies=...",
        "user_agent": "Mozilla/5.0...",
        # Additional fields as needed
    }
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ Fansly authentication successful")
            # Limited operations available
        else:
            print("✗ Fansly authentication failed")

# Note: Fansly support is WIP
asyncio.run(fansly_auth_example())
```

!!! warning "Fansly Development Status"
    Fansly API integration is actively being developed. Authentication methods and available features may change in future versions.

### LoyalFans (Work in Progress) ⚠️ {#loyalfans}

LoyalFans authentication is under development:

| Field | Required | Description |
|-------|----------|-------------|
| `cookie` | ✅ Yes | Session cookie from LoyalFans |
| `user_agent` | ✅ Yes | Browser User-Agent |

**Example (Subject to Change):**

```python
import asyncio
from ultima_scraper_api import LoyalFansAPI, UltimaScraperAPIConfig

async def loyalfans_auth_example():
    config = UltimaScraperAPIConfig()
    api = LoyalFansAPI(config)
    
    # LoyalFans authentication (structure may change)
    auth_json = {
        "cookie": "PHPSESSID=...; other_cookies=...",
        "user_agent": "Mozilla/5.0...",
    }
    
    async with api.login_context(auth_json) as authed:
        if authed and authed.is_authed():
            print("✓ LoyalFans authentication successful")
            # Limited operations available
        else:
            print("✗ LoyalFans authentication failed")

# Note: LoyalFans support is WIP
asyncio.run(loyalfans_auth_example())
```

!!! warning "LoyalFans Development Status"
    LoyalFans API integration is actively being developed. Authentication methods and available features may change in future versions.

### Multi-Platform Authentication

Working with multiple platforms simultaneously:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, FanslyAPI, UltimaScraperAPIConfig

async def multi_platform_auth():
    config = UltimaScraperAPIConfig()
    
    # OnlyFans credentials
    of_auth = {
        "cookie": "...",
        "user_agent": "...",
        "x-bc": "..."
    }
    
    # Fansly credentials
    fansly_auth = {
        "cookie": "...",
        "user_agent": "..."
    }
    
    # Authenticate to both platforms
    of_api = OnlyFansAPI(config)
    fansly_api = FanslyAPI(config)
    
    async with of_api.login_context(of_auth) as of_authed:
        async with fansly_api.login_context(fansly_auth) as fansly_authed:
            if of_authed and of_authed.is_authed():
                print("✓ OnlyFans authenticated")
            
            if fansly_authed and fansly_authed.is_authed():
                print("✓ Fansly authenticated")
            
            # Work with both platforms
            # ...

asyncio.run(multi_platform_auth())
```

## Authentication Management

### Verifying Authentication Status

Always verify authentication before making API calls:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def verify_auth():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "...",
        "user_agent": "...",
        "x-bc": "..."
    }
    
    async with api.login_context(auth_json) as authed:
        # Check if authentication succeeded
        if authed and authed.is_authed():
            print("✓ Authentication successful")
            
            # Get authenticated user details
            me = await authed.get_authed_user()
            print(f"Logged in as: {me.name} (@{me.username})")
            print(f"User ID: {me.id}")
            print(f"Email: {me.email if hasattr(me, 'email') else 'N/A'}")
            
            return True
        else:
            print("✗ Authentication failed")
            return False

asyncio.run(verify_auth())
```

### Session Persistence with Redis

UltimaScraperAPI can persist sessions using Redis for better performance:

```python
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

# Enable Redis for session caching
config = UltimaScraperAPIConfig()
config.settings.redis.enabled = True
config.settings.redis.host = "localhost"
config.settings.redis.port = 6379

api = OnlyFansAPI(config)

# Sessions will be automatically cached in Redis
async with api.login_context(auth_json) as authed:
    # Session is cached - subsequent runs will be faster
    pass
```

**Benefits of Redis caching:**

- 🚀 Faster authentication on subsequent runs
- 💾 Persistent session storage
- 🔄 Shared sessions across multiple processes
- ⚡ Reduced API calls

See [Session Management](session-management.md) for more details.

### Handling Authentication Errors

Implement robust error handling:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def robust_auth():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    auth_json = {
        "cookie": "...",
        "user_agent": "...",
        "x-bc": "..."
    }
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with api.login_context(auth_json) as authed:
                if authed and authed.is_authed():
                    print(f"✓ Authenticated successfully")
                    return authed
                else:
                    print(f"✗ Authentication failed (attempt {retry_count + 1}/{max_retries})")
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        # Wait before retrying
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    
        except ConnectionError as e:
            print(f"✗ Connection error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
                
        except Exception as e:
            print(f"✗ Unexpected error: {type(e).__name__}: {e}")
            break
    
    print("✗ Authentication failed after all retries")
    return None

asyncio.run(robust_auth())
```

### Re-authentication on Expiry

Automatically re-authenticate when sessions expire:

```python
import asyncio
from datetime import datetime, timedelta
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

class AuthManager:
    def __init__(self, api, auth_json):
        self.api = api
        self.auth_json = auth_json
        self.authed = None
        self.last_auth_time = None
        self.auth_ttl = timedelta(hours=24)  # Re-auth after 24 hours
    
    async def get_authenticated_session(self):
        """Get authenticated session, re-authenticating if needed."""
        current_time = datetime.now()
        
        # Check if we need to re-authenticate
        if (self.authed is None or 
            self.last_auth_time is None or
            current_time - self.last_auth_time > self.auth_ttl):
            
            print("Authenticating...")
            async with self.api.login_context(self.auth_json) as authed:
                if authed and authed.is_authed():
                    self.authed = authed
                    self.last_auth_time = current_time
                    print("✓ Authentication successful")
                else:
                    print("✗ Authentication failed")
                    return None
        
        return self.authed

# Usage
async def main():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    auth_json = {...}  # Your credentials
    
    auth_manager = AuthManager(api, auth_json)
    
    # Get authenticated session
    authed = await auth_manager.get_authenticated_session()
    if authed:
        # Use authenticated session
        pass

asyncio.run(main())
```

## Security Best Practices

### 1. Never Hardcode Credentials ⚠️

Hardcoding credentials is a major security risk.

❌ **Bad - Never do this:**
```python
# DON'T DO THIS!
auth_json = {
    "cookie": "auth_id=12345; sess=abcdef123456",  # Exposed in source code!
    "user_agent": "Mozilla/5.0 ...",
    "x-bc": "my_secret_token"  # Will be committed to git!
}
```

✅ **Good - Use environment variables:**
```python
import os

auth_json = {
    "cookie": os.getenv("ONLYFANS_COOKIE"),
    "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
    "x-bc": os.getenv("ONLYFANS_XBC"),
}

# Validate credentials are present
if not all(auth_json.values()):
    raise ValueError("Missing required authentication credentials in environment")
```

### 2. Use Environment Variables

**Create a `.env` file** (add to `.gitignore`!):

```bash
# .env - NEVER commit this file!
ONLYFANS_COOKIE="auth_id=123456; sess=abcdef1234567890; auth_hash=xyz789"
ONLYFANS_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ONLYFANS_XBC="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

**Load with python-dotenv:**

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
import os
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

# Load environment variables from .env file
load_dotenv()

async def secure_auth():
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    # Load from environment
    auth_json = {
        "cookie": os.getenv("ONLYFANS_COOKIE"),
        "user_agent": os.getenv("ONLYFANS_USER_AGENT"),
        "x-bc": os.getenv("ONLYFANS_XBC"),
    }
    
    async with api.login_context(auth_json) as authed:
        # Secure authentication
        pass
```

**Add to `.gitignore`:**

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Credential files
**/credentials.json
**/auth.json
**/cookies.txt
```

### 3. Encrypt Sensitive Data

For storing credentials in files or databases:

```python
from cryptography.fernet import Fernet
import json
from pathlib import Path

class CredentialManager:
    """Securely manage encrypted credentials."""
    
    def __init__(self, key_file: str = "secret.key"):
        self.key_file = Path(key_file)
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one."""
        if self.key_file.exists():
            return self.key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Read/write for owner only
            return key
    
    def encrypt_credentials(self, auth_json: dict) -> bytes:
        """Encrypt authentication credentials."""
        json_str = json.dumps(auth_json)
        return self.cipher.encrypt(json_str.encode())
    
    def decrypt_credentials(self, encrypted_data: bytes) -> dict:
        """Decrypt authentication credentials."""
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def save_credentials(self, auth_json: dict, filename: str = "credentials.enc"):
        """Save encrypted credentials to file."""
        encrypted = self.encrypt_credentials(auth_json)
        Path(filename).write_bytes(encrypted)
        Path(filename).chmod(0o600)
    
    def load_credentials(self, filename: str = "credentials.enc") -> dict:
        """Load encrypted credentials from file."""
        encrypted = Path(filename).read_bytes()
        return self.decrypt_credentials(encrypted)

# Usage
manager = CredentialManager()

# Save credentials (one time)
auth_json = {
    "cookie": "...",
    "user_agent": "...",
    "x-bc": "..."
}
manager.save_credentials(auth_json)

# Load credentials later
auth_json = manager.load_credentials()
```

### 4. Secure File Permissions

When storing credentials in files, set appropriate permissions:

```python
from pathlib import Path
import os

# Create credentials file with restricted permissions
credentials_file = Path("credentials.json")
credentials_file.touch(mode=0o600)  # rw------- (owner only)

# Write credentials
credentials_file.write_text(json.dumps(auth_json))

# Verify permissions
stat_info = credentials_file.stat()
print(f"File permissions: {oct(stat_info.st_mode)[-3:]}")  # Should be 600
```

### 5. Use Keyring for System Integration

Store credentials in system keyring:

```bash
pip install keyring
```

```python
import keyring
import json

# Store credentials in system keyring
def store_credentials(service: str, username: str, auth_json: dict):
    """Store credentials in system keyring."""
    credentials_json = json.dumps(auth_json)
    keyring.set_password(service, username, credentials_json)

# Retrieve credentials
def get_credentials(service: str, username: str) -> dict:
    """Retrieve credentials from system keyring."""
    credentials_json = keyring.get_password(service, username)
    if credentials_json:
        return json.loads(credentials_json)
    return None

# Usage
store_credentials("UltimaScraperAPI", "onlyfans_main", auth_json)
auth_json = get_credentials("UltimaScraperAPI", "onlyfans_main")
```

### 6. Rotate Credentials Regularly

```python
from datetime import datetime, timedelta
import json

class CredentialRotation:
    """Track and enforce credential rotation."""
    
    def __init__(self, rotation_days: int = 30):
        self.rotation_days = rotation_days
        self.metadata_file = "credentials_metadata.json"
    
    def should_rotate(self) -> bool:
        """Check if credentials should be rotated."""
        try:
            metadata = json.loads(Path(self.metadata_file).read_text())
            last_rotation = datetime.fromisoformat(metadata["last_rotation"])
            return datetime.now() - last_rotation > timedelta(days=self.rotation_days)
        except (FileNotFoundError, KeyError, ValueError):
            return True
    
    def mark_rotated(self):
        """Mark credentials as rotated."""
        metadata = {
            "last_rotation": datetime.now().isoformat(),
            "rotation_count": self._get_rotation_count() + 1
        }
        Path(self.metadata_file).write_text(json.dumps(metadata))
    
    def _get_rotation_count(self) -> int:
        try:
            metadata = json.loads(Path(self.metadata_file).read_text())
            return metadata.get("rotation_count", 0)
        except (FileNotFoundError, KeyError, ValueError):
            return 0

# Usage
rotation = CredentialRotation(rotation_days=30)
if rotation.should_rotate():
    print("⚠️  Credentials should be rotated!")
    print("   Please update your authentication credentials.")
```

## Troubleshooting Authentication Issues

### Common Problems and Solutions

#### ❌ Authentication Failed

**Symptoms:**
- `authed.is_authed()` returns `False`
- Connection errors or timeouts
- "Invalid credentials" messages

**Possible Causes & Solutions:**

=== "Expired Cookies"
    **Problem:** Cookies expire after a certain time period.
    
    **Solution:**
    1. Open your browser
    2. Log out and log back into the platform
    3. Extract fresh cookies using Developer Tools
    4. Update your credentials
    
    ```python
    # Always check authentication status
    if not authed or not authed.is_authed():
        print("Credentials may be expired - please refresh")
    ```

=== "Incorrect Headers"
    **Problem:** Missing or malformed authentication headers.
    
    **Solution:**
    1. Verify all required fields are present:
       - `cookie` (complete string)
       - `user_agent` (from your browser)
       - `x-bc` (for OnlyFans)
    2. Check for typos or truncated values
    3. Ensure no extra spaces or newlines
    
    ```python
    # Validate credentials
    required_fields = ["cookie", "user_agent", "x-bc"]
    missing = [f for f in required_fields if not auth_json.get(f)]
    if missing:
        print(f"Missing fields: {missing}")
    ```

=== "Platform API Changes"
    **Problem:** Platform updated their API authentication.
    
    **Solution:**
    1. Check for UltimaScraperAPI updates
    2. Review the changelog
    3. Update to the latest version
    
    ```bash
    pip install --upgrade ultima-scraper-api
    ```

=== "IP/Location Restrictions"
    **Problem:** Platform blocking requests from your IP.
    
    **Solution:**
    1. Use a proxy from a different location
    2. Configure residential proxies if available
    3. Reduce request frequency
    
    ```python
    from ultima_scraper_api.config import Proxy
    
    config = UltimaScraperAPIConfig()
    proxy = Proxy(url="socks5://proxy.example.com:1080")
    config.settings.network.proxies.append(proxy)
    ```

#### ❌ User-Agent Mismatch

**Symptoms:**
- Authentication fails with valid cookies
- "Suspicious activity" warnings

**Solution:**
Use your **actual browser's** User-Agent string, not a generic one.

```python
# ✗ Bad - Generic User-Agent
"user_agent": "Python/3.11"

# ✓ Good - Real browser User-Agent
"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
```

**Find your browser's User-Agent:**
1. Visit: https://www.whatismybrowser.com/detect/what-is-my-user-agent
2. Copy the displayed User-Agent string
3. Use it in your `auth_json`

#### ❌ Rate Limiting / Too Many Requests

**Symptoms:**
- HTTP 429 errors
- Temporary authentication failures
- Slow or blocked responses

**Solutions:**

```python
import asyncio

async def rate_limited_requests():
    """Implement rate limiting to avoid blocks."""
    
    # Add delays between requests
    await asyncio.sleep(1)  # Wait 1 second
    
    # Use exponential backoff for retries
    for retry in range(3):
        try:
            async with api.login_context(auth_json) as authed:
                if authed and authed.is_authed():
                    return authed
        except Exception:
            wait_time = 2 ** retry
            await asyncio.sleep(wait_time)
```

#### ❌ x-bc Token Not Found (OnlyFans)

**Symptoms:**
- Can't find `x-bc` header in Network tab
- Authentication fails even with valid cookies

**Solution:**
1. In Developer Tools Network tab, click "Clear" to remove old requests
2. Refresh the OnlyFans page
3. Look for requests to `/api2/v2/` endpoints
4. Click on any such request
5. Find `x-bc` in Request Headers
6. The token may change periodically - extract a fresh one

**Alternative locations for x-bc:**
- Requests to `/api2/v2/users/me`
- Requests to `/api2/v2/subscriptions`
- Any authenticated API requests

#### ❌ Cookie String Truncated

**Symptoms:**
- Authentication fails
- Cookie appears incomplete

**Solution:**
Ensure you copy the **entire** cookie string:

```python
# Cookie should contain multiple components
# ✓ Complete cookie (multiple key-value pairs)
cookie = "auth_id=123456; sess=abc...; auth_hash=xyz...; fp=fingerprint..."

# ✗ Truncated cookie (missing components)
cookie = "auth_id=123456"  # TOO SHORT!
```

#### ❌ Redis Connection Failed

**Symptoms:**
- Error: "Connection refused" or "Redis not available"
- Authentication works but throws connection errors

**Solution:**

```python
# Option 1: Disable Redis
config = UltimaScraperAPIConfig()
config.settings.redis.enabled = False

# Option 2: Start Redis server
# Linux/macOS: sudo systemctl start redis
# or: redis-server

# Option 3: Use Docker
# docker run -d -p 6379:6379 redis
```

### Debug Mode

Enable verbose logging to troubleshoot issues:

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now authentication attempts will be logged
async with api.login_context(auth_json) as authed:
    pass
```

### Testing Credentials

Quick script to test if credentials are valid:

```python
import asyncio
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

async def test_credentials(auth_json: dict):
    """Test if authentication credentials are valid."""
    config = UltimaScraperAPIConfig()
    api = OnlyFansAPI(config)
    
    print("Testing authentication...")
    print(f"Cookie length: {len(auth_json.get('cookie', ''))}")
    print(f"User-Agent length: {len(auth_json.get('user_agent', ''))}")
    print(f"x-bc length: {len(auth_json.get('x-bc', ''))}")
    
    try:
        async with api.login_context(auth_json) as authed:
            if authed and authed.is_authed():
                print("\n✓ Authentication successful!")
                me = await authed.get_authed_user()
                print(f"  User: {me.name} (@{me.username})")
                print(f"  ID: {me.id}")
                return True
            else:
                print("\n✗ Authentication failed")
                print("  Please check your credentials")
                return False
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        return False

# Usage
auth_json = {
    "cookie": "your_cookie",
    "user_agent": "your_user_agent",
    "x-bc": "your_x_bc"
}

asyncio.run(test_credentials(auth_json))
```

## FAQ

??? question "How long do cookies stay valid?"
    Cookie validity varies by platform:
    
    - **OnlyFans**: Typically 1-7 days, depending on account activity
    - **Fansly**: Varies (WIP - exact duration unclear)
    - **LoyalFans**: Varies (WIP - exact duration unclear)
    
    Monitor for authentication failures and refresh as needed.

??? question "Can I use the same credentials on multiple machines?"
    Yes, but be cautious:
    
    - ✅ Same cookies work on different machines
    - ⚠️ Simultaneous use from different IPs may trigger security alerts
    - ✅ Consider using proxies from consistent locations
    - ⚠️ Platforms may limit concurrent sessions

??? question "Do I need a premium account?"
    No, authentication works with any account type:
    
    - ✅ Free accounts can authenticate
    - ✅ Premium/creator accounts work the same way
    - ℹ️ API access depends on account permissions
    - ℹ️ Some content requires subscriptions (per platform rules)

??? question "Is this against platform Terms of Service?"
    ⚠️ **Important Legal Notice:**
    
    Using third-party APIs may violate platform Terms of Service. This tool is for:
    
    - Educational purposes
    - Personal data management
    - Backup of owned content
    
    Users are responsible for compliance with platform ToS and local laws.

## Next Steps

Now that you understand authentication, explore:

- 📖 [Working with APIs](working-with-apis.md) - Learn API operations
- 🌐 [Proxy Support](proxy-support.md) - Configure proxies for better privacy
- 🔄 [Session Management](session-management.md) - Manage sessions efficiently
- 📚 [API Reference](../api-reference/onlyfans.md) - Detailed API documentation
