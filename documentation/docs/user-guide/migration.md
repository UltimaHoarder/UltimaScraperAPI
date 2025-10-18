# API Migration Guide

Comprehensive guide for upgrading UltimaScraperAPI between major and minor versions. This guide covers breaking changes, deprecated features, and migration strategies to help you smoothly transition your codebase.

---

## Table of Contents

1. [Overview](#overview)
2. [Version Support Policy](#version-support-policy)
3. [Migration Paths](#migration-paths)
4. [Breaking Changes by Version](#breaking-changes-by-version)
5. [Step-by-Step Migrations](#step-by-step-migrations)
6. [Common Migration Issues](#common-migration-issues)
7. [Testing Your Migration](#testing-your-migration)
8. [Getting Help](#getting-help)

---

## Overview

UltimaScraperAPI follows [Semantic Versioning](https://semver.org/):

- **Major versions** (3.0.0): Breaking changes, major API redesigns
- **Minor versions** (2.3.0): New features, backward-compatible
- **Patch versions** (2.2.47): Bug fixes, security patches

### Current Version

**Latest Stable:** 2.2.46 (October 18, 2025)

### Supported Versions

| Version | Status | Support Level | End of Life |
|---------|--------|--------------|-------------|
| **2.2.x** | ✅ Active | Full support | TBD |
| **2.1.x** | 🟡 Maintenance | Security fixes only | 2026-01-01 |
| **2.0.x** | ⚠️ Legacy | Critical security only | 2025-12-31 |
| **1.x** | ❌ Unsupported | None | 2024-01-01 |

---

## Version Support Policy

### Active Development (2.2.x)
- New features and improvements
- Regular bug fixes
- Security updates
- Documentation updates
- Community support

### Maintenance Mode (2.1.x)
- Security patches only
- Critical bug fixes
- No new features
- Limited support

### Legacy (2.0.x)
- Critical security fixes only
- No bug fixes
- No new features
- Deprecated

---

## Migration Paths

### Recommended Migration Strategy

```
1.x → 2.0.x → 2.1.x → 2.2.x (Current)
                ↓
              2.3.x (Future)
                ↓
              3.0.x (Future)
```

!!! warning "Skip Version Migration"
    Skipping major versions (e.g., 1.x → 2.2.x) is **not recommended**. Migrate incrementally to identify and resolve breaking changes systematically.

### Quick Migration Path

For production systems, follow this approach:

1. **Read changelog** for target version
2. **Set up testing environment** with new version
3. **Run automated tests** to identify issues
4. **Fix breaking changes** systematically
5. **Deploy to staging** environment
6. **Monitor for issues** before production
7. **Deploy to production** with rollback plan

---

## Breaking Changes by Version

### 2.2.x (Current) - Breaking Changes from 2.1.x

#### 1. Pydantic v2 Required

**Impact:** 🔴 High - Affects all model usage

```python
# ❌ OLD (2.1.x with Pydantic v1)
from pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# ✅ NEW (2.2.x with Pydantic v2)
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    name: str
```

**Migration Steps:**

1. Update `pydantic` to v2.0+
2. Replace `Config` class with `model_config`
3. Rename configuration options:
   - `orm_mode` → `from_attributes`
   - `allow_population_by_field_name` → `populate_by_name`
   - `allow_mutation` → `frozen` (inverted)

#### 2. Model Creation Changes

**Impact:** 🟡 Medium - Affects user model creation

```python
# ❌ OLD (2.1.x)
from ultima_scraper_api.apis.onlyfans import create_user

user_data = {"id": 123, "username": "example"}
user = create_user(user_data)

# ✅ NEW (2.2.x)
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel

user_data = {"id": 123, "username": "example"}
user = UserModel(**user_data)
```

**Migration Steps:**

1. Replace `create_user()` with `UserModel(**data)`
2. Update imports to use specific model classes
3. Ensure data is unpacked with `**` operator

#### 3. httpx Dependency Update

**Impact:** 🟢 Low - Mostly internal

```python
# Version requirement changed
# OLD: httpx>=0.25
# NEW: httpx>=0.28

# Most code remains compatible, but check:
# - Custom HTTP clients
# - Advanced timeout configurations
# - Proxy handling code
```

#### 4. WebSocket Session Changes

**Impact:** 🟡 Medium - Affects WebSocket users

```python
# ❌ OLD (2.1.x)
async def connect_websocket():
    ws = await api.websocket_connect()
    # Old WebSocket handling

# ✅ NEW (2.2.x)
async def connect_websocket():
    async with api.websocket_context() as ws:
        # Context manager ensures cleanup
        await ws.send(message)
```

**Migration Steps:**

1. Replace direct `websocket_connect()` with `websocket_context()`
2. Use async context manager pattern
3. Update cleanup logic (now automatic)

#### 5. Type Hint Enhancements

**Impact:** 🟢 Low - Improves code quality

```python
# ❌ OLD (2.1.x) - Less specific types
def get_user(identifier) -> Optional[dict]:
    pass

# ✅ NEW (2.2.x) - Enhanced type hints
def get_user(identifier: int | str) -> UserModel | None:
    pass
```

**Migration Steps:**

1. Update type hints to match new signatures
2. Enable strict type checking in IDE
3. Fix any type errors discovered

### 2.1.x - Breaking Changes from 2.0.x

#### 1. Python Version Requirements

**Impact:** 🔴 High

```python
# OLD: Python 3.8+ supported
# NEW: Python 3.10+ required

# Migration: Upgrade Python to 3.10+
pyenv install 3.10.0
pyenv global 3.10.0
```

#### 2. Authentication Context Changes

**Impact:** 🟡 Medium

```python
# ❌ OLD (2.0.x)
authed = await api.login(auth_json)
try:
    # Use authed
    pass
finally:
    await api.remove_auth(authed)

# ✅ NEW (2.1.x+)
async with api.login_context(auth_json) as authed:
    # Use authed - automatic cleanup
    pass
```

#### 3. Session Manager Refactor

**Impact:** 🟡 Medium

```python
# ❌ OLD (2.0.x)
from ultima_scraper_api.managers.session_manager import create_session

session = create_session(headers)

# ✅ NEW (2.1.x+)
from ultima_scraper_api.managers.session_manager import SessionManager

manager = SessionManager(api, proxies=proxies)
session = manager.create_session()
```

### 2.0.x - Initial Stable Release

Breaking changes from pre-release versions (1.x):

- Complete API redesign
- Async/await architecture
- Multi-platform support structure
- Pydantic integration
- Redis caching system
- Proxy support framework

---

## Step-by-Step Migrations

### Migrating from 2.1.x to 2.2.x

#### Prerequisites

```bash
# Check current version
uv pip show ultima-scraper-api

# Backup current environment
uv pip freeze > requirements-old.txt

# Create test branch
git checkout -b migration-2.2.x
```

#### Step 1: Update Dependencies

```bash
# Update to latest 2.2.x
uv pip install --upgrade "ultima-scraper-api>=2.2.46"

# Update Pydantic to v2
uv pip install --upgrade "pydantic>=2.0"

# Update httpx
uv pip install --upgrade "httpx>=0.28"
```

#### Step 2: Update Pydantic Models

**Find all Pydantic models:**

```bash
grep -r "class Config:" --include="*.py" .
```

**Update each model:**

```python
# Before
class MyModel(BaseModel):
    field: str
    
    class Config:
        orm_mode = True

# After
class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    field: str
```

#### Step 3: Update Model Creation

**Find all `create_user` calls:**

```bash
grep -r "create_user" --include="*.py" .
```

**Replace with direct instantiation:**

```python
# Before
user = create_user(data)

# After
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel
user = UserModel(**data)
```

#### Step 4: Update WebSocket Code

```python
# Before
ws = await api.websocket_connect()
try:
    await ws.send(msg)
finally:
    await ws.close()

# After
async with api.websocket_context() as ws:
    await ws.send(msg)
    # Automatic cleanup
```

#### Step 5: Run Tests

```bash
# Run your test suite
pytest tests/

# Check for deprecation warnings
pytest tests/ -W error::DeprecationWarning

# Run type checking
mypy src/
```

#### Step 6: Verify Functionality

```python
# Test authentication
async with api.login_context(auth_json) as authed:
    assert authed.is_authed()
    print("✅ Authentication works")

# Test user fetching
user = await authed.get_user("username")
assert isinstance(user, UserModel)
print("✅ User fetching works")

# Test content fetching
posts = await user.get_posts(limit=10)
assert len(posts) > 0
print("✅ Content fetching works")
```

### Migrating from 2.0.x to 2.1.x

#### Step 1: Update Python

```bash
# Check Python version
python --version

# Must be 3.10+
# If not, upgrade:
pyenv install 3.10.0
pyenv local 3.10.0
```

#### Step 2: Update to 2.1.x

```bash
uv pip install --upgrade "ultima-scraper-api>=2.1.0,<2.2.0"
```

#### Step 3: Migrate to Context Managers

**Authentication:**

```python
# Before
authed = await api.login(auth_json)
try:
    user = await authed.get_user("username")
finally:
    await api.remove_auth(authed)

# After
async with api.login_context(auth_json) as authed:
    user = await authed.get_user("username")
```

**Sessions:**

```python
# Before
session = create_session()
try:
    response = await session.get(url)
finally:
    await session.close()

# After
manager = SessionManager(api, proxies=proxies)
async with manager.session_context() as session:
    response = await session.get(url)
```

#### Step 4: Test Thoroughly

```bash
pytest tests/ -v
```

---

## Common Migration Issues

### Issue 1: Pydantic v2 Field Validation Errors

**Symptom:**

```python
ValidationError: 1 validation error for UserModel
  Field required [type=missing, input_value=...]
```

**Solution:**

```python
# Pydantic v2 is stricter about required fields
# Option 1: Provide all required fields
user = UserModel(id=123, username="user", name="User")

# Option 2: Make fields optional
from typing import Optional

class UserModel(BaseModel):
    id: int
    username: str
    name: Optional[str] = None  # Now optional with default
```

### Issue 2: Config Class Not Found

**Symptom:**

```python
AttributeError: type object 'MyModel' has no attribute 'Config'
```

**Solution:**

```python
# Replace class Config with model_config
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

### Issue 3: create_user ImportError

**Symptom:**

```python
ImportError: cannot import name 'create_user' from 'ultima_scraper_api.apis.onlyfans'
```

**Solution:**

```python
# Use direct model instantiation
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel

# Replace:
# user = create_user(data)
# With:
user = UserModel(**data)
```

### Issue 4: WebSocket Connection Errors

**Symptom:**

```python
RuntimeError: WebSocket connection not properly closed
```

**Solution:**

```python
# Use context manager for automatic cleanup
async with api.websocket_context() as ws:
    await ws.send(message)
    response = await ws.receive()
# Automatically closed here
```

### Issue 5: Type Hint Compatibility

**Symptom:**

```python
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

**Solution:**

```python
# Python 3.10+ supports | for union types
# But for older type checkers:
from typing import Union, Optional

# Instead of:
def func() -> str | None:
    pass

# Use:
def func() -> Optional[str]:
    pass
```

### Issue 6: httpx Timeout Changes

**Symptom:**

```python
TypeError: Timeout.__init__() got an unexpected keyword argument
```

**Solution:**

```python
# httpx 0.28+ changed timeout API
# Before:
timeout = httpx.Timeout(5.0)

# After:
timeout = httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=5.0,
    pool=None
)
```

---

## Testing Your Migration

### Automated Testing Checklist

```python
import pytest
from ultima_scraper_api import UltimaScraperAPI

@pytest.mark.asyncio
async def test_authentication():
    """Test authentication still works"""
    api = UltimaScraperAPI()
    onlyfans = api.get_site_api("onlyfans")
    
    async with onlyfans.login_context(auth_json) as authed:
        assert authed is not None
        assert authed.is_authed()

@pytest.mark.asyncio
async def test_user_fetching():
    """Test user fetching with new models"""
    api = UltimaScraperAPI()
    onlyfans = api.get_site_api("onlyfans")
    
    async with onlyfans.login_context(auth_json) as authed:
        user = await authed.get_user("username")
        assert user is not None
        assert hasattr(user, 'id')
        assert hasattr(user, 'username')

@pytest.mark.asyncio
async def test_content_fetching():
    """Test content fetching still works"""
    api = UltimaScraperAPI()
    onlyfans = api.get_site_api("onlyfans")
    
    async with onlyfans.login_context(auth_json) as authed:
        user = await authed.get_user("username")
        posts = await user.get_posts(limit=10)
        assert isinstance(posts, list)

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling unchanged"""
    api = UltimaScraperAPI()
    onlyfans = api.get_site_api("onlyfans")
    
    async with onlyfans.login_context(invalid_auth) as authed:
        assert authed is None  # Should fail gracefully
```

### Manual Testing Checklist

- [ ] **Authentication** - Login with valid credentials
- [ ] **User Fetching** - Get user profiles
- [ ] **Content Access** - Fetch posts, messages, stories
- [ ] **Media Download** - Download images and videos
- [ ] **Proxy Support** - Test with configured proxies
- [ ] **Caching** - Verify Redis caching works
- [ ] **Session Management** - Multiple accounts
- [ ] **Error Handling** - Invalid credentials, network errors
- [ ] **WebSocket** - Real-time connections (if used)
- [ ] **Performance** - Compare response times

### Regression Testing

```bash
# Run full test suite
pytest tests/ -v

# Check test coverage
pytest --cov=ultima_scraper_api tests/

# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Check for memory leaks
pytest tests/ --memprof
```

---

## Getting Help

### Resources

- **[Changelog](../about/changelog.md)** - Detailed version history
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues
- **[API Reference](../api-reference/onlyfans.md)** - Current API documentation
- **[GitHub Issues](https://github.com/DIGITALCRIMINAL/UltimaScraperAPI/issues)** - Report problems

### Community Support

- **GitHub Discussions** - Ask migration questions
- **Discord** - Real-time help (link in README)
- **Stack Overflow** - Tag: `ultima-scraper-api`

### Professional Support

For commercial users needing migration assistance:

- Priority support available
- Custom migration plans
- Code review services
- Training sessions

Contact: support@ultimascraper.dev

---

## Migration Checklist Template

Use this checklist for your migration:

```markdown
## Migration from X.X.X to Y.Y.Y

### Pre-Migration
- [ ] Read changelog for target version
- [ ] Backup current codebase
- [ ] Create migration branch
- [ ] Document current functionality
- [ ] Set up test environment

### Dependencies
- [ ] Update Python version (if required)
- [ ] Update ultima-scraper-api
- [ ] Update pydantic (if required)
- [ ] Update httpx (if required)
- [ ] Update other dependencies
- [ ] Verify no conflicts

### Code Changes
- [ ] Update Pydantic models
- [ ] Update model creation code
- [ ] Update authentication code
- [ ] Update WebSocket code (if applicable)
- [ ] Update type hints
- [ ] Fix deprecation warnings

### Testing
- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Manual testing
- [ ] Performance testing
- [ ] Security review

### Deployment
- [ ] Deploy to staging
- [ ] Monitor for issues
- [ ] Create rollback plan
- [ ] Deploy to production
- [ ] Monitor production
- [ ] Document changes

### Post-Migration
- [ ] Update documentation
- [ ] Train team members
- [ ] Monitor error logs
- [ ] Performance monitoring
- [ ] Gather feedback
```

---

## Deprecation Timeline

### Deprecated in 2.2.x (Removal in 3.0.0)

| Feature | Replacement | Removal Date |
|---------|------------|--------------|
| `create_user()` | `UserModel(**data)` | 3.0.0 (2026+) |
| `get_subscription()` | `auth.subscriptions` | 3.0.0 |
| Legacy cache config | Redis configuration | 3.0.0 |
| Sync API methods | Async equivalents | 3.0.0 |

### Planning for 3.0.0

Expected breaking changes in 3.0.0 (future):

- Complete removal of deprecated features
- Potential authentication flow redesign
- Enhanced type safety requirements
- Minimum Python 3.11+
- New configuration system
- Improved error handling architecture

**Recommendation:** Start planning 3.0.0 migration once 2.3.x is stable.

---

## Best Practices

### 1. Test Before Upgrading

```bash
# Create isolated test environment
python -m venv test_env
source test_env/bin/activate
pip install ultima-scraper-api==<new_version>
# Run tests
```

### 2. Gradual Migration

```python
# Support both old and new APIs temporarily
try:
    from ultima_scraper_api.apis.onlyfans import create_user
    user = create_user(data)
except ImportError:
    from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel
    user = UserModel(**data)
```

### 3. Feature Flags

```python
# Use feature flags for gradual rollout
USE_NEW_API = os.getenv("USE_NEW_API", "false").lower() == "true"

if USE_NEW_API:
    # New implementation
    pass
else:
    # Legacy implementation
    pass
```

### 4. Monitoring

```python
import logging

logger = logging.getLogger(__name__)

# Log migration progress
logger.info("Using UltimaScraperAPI v%s", api.__version__)

# Track errors
try:
    user = UserModel(**data)
except ValidationError as e:
    logger.error("Pydantic validation error: %s", e)
    # Handle gracefully
```

---

## Version History Summary

| Version | Release Date | Major Features | Breaking Changes |
|---------|--------------|----------------|------------------|
| **2.2.46** | 2024-10-18 | Documentation overhaul | None |
| **2.2.43** | 2024-08-20 | WebSocket support | WebSocket API changes |
| **2.2.40** | 2024-04-25 | httpx 0.28+ | HTTP client changes |
| **2.2.36** | 2024-04-10 | Model naming | `create_user` → `UserModel` |
| **2.0.0** | 2022-06-01 | Initial stable release | Complete rewrite |

---

**Last Updated:** October 18, 2025  
**Guide Version:** 2.2.46

For the most up-to-date information, always check the [Changelog](../about/changelog.md) and [GitHub Releases](https://github.com/DIGITALCRIMINAL/UltimaScraperAPI/releases).
