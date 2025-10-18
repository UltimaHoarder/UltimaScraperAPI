# Testing Guide

Comprehensive guide to testing UltimaScraperAPI with pytest, async patterns, mocking strategies, and best practices.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Async Testing](#async-testing)
- [Fixtures](#fixtures)
- [Mocking Strategies](#mocking-strategies)
- [Parameterized Tests](#parameterized-tests)
- [Testing Exceptions](#testing-exceptions)
- [Integration Tests](#integration-tests)
- [Test Organization](#test-organization)
- [Coverage Requirements](#coverage-requirements)
- [Testing Best Practices](#testing-best-practices)
- [CI/CD Integration](#cicd-integration)
- [Debugging Tests](#debugging-tests)
- [Performance Testing](#performance-testing)
- [Troubleshooting Tests](#troubleshooting-tests)
- [Testing Cheat Sheet](#testing-cheat-sheet)

---

## Overview

UltimaScraperAPI uses **pytest** as the testing framework with extensions for async operations, coverage reporting, and mocking.

### Testing Stack

| Tool | Purpose | Version |
|------|---------|---------|
| **pytest** | Test framework | 7.0+ |
| **pytest-asyncio** | Async test support | 0.21+ |
| **pytest-cov** | Coverage reporting | 4.0+ |
| **unittest.mock** | Mocking framework | Built-in |
| **aioresponses** | HTTP mocking (optional) | Latest |

### Testing Philosophy

- ✅ **Unit tests** for individual components
- ✅ **Integration tests** for component interaction
- ✅ **Mock external dependencies** (APIs, databases)
- ✅ **Test edge cases and error conditions**
- ✅ **Maintain high code coverage** (80%+ target)

---

## Quick Start

### Installation

```bash
# Install test dependencies
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_onlyfans.py

# Run specific test
pytest tests/test_onlyfans.py::test_authentication

# Run tests matching pattern
pytest -k "test_user"

# Stop at first failure
pytest -x

# Show local variables on failure
pytest -l

# Run in parallel (faster)
pytest -n auto
```

### Coverage

```bash
# Run with coverage
pytest --cov=ultima_scraper_api

# Generate HTML report
pytest --cov=ultima_scraper_api --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Show missing lines
pytest --cov=ultima_scraper_api --cov-report=term-missing
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_onlyfans.py

# Run specific test
pytest tests/test_onlyfans.py::test_user_fetch

# Run with verbose output
pytest -v

# Run with output capture disabled
pytest -s
```

### Coverage

```bash
# Run tests with coverage
pytest --cov=ultima_scraper_api

# Generate HTML coverage report
pytest --cov=ultima_scraper_api --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## Test Structure

### Directory Layout

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
│
├── unit/                          # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_models.py             # Pydantic model tests
│   ├── test_config.py             # Configuration tests
│   ├── test_helpers.py            # Helper function tests
│   └── test_validators.py         # Validation logic tests
│
├── integration/                   # Integration tests (slower)
│   ├── __init__.py
│   ├── test_onlyfans_api.py       # OnlyFans API integration
│   ├── test_fansly_api.py         # Fansly API integration
│   ├── test_loyalfans_api.py      # LoyalFans API integration
│   ├── test_session_manager.py    # Session management
│   ├── test_redis_integration.py  # Redis integration
│   └── test_websocket.py          # WebSocket tests
│
├── fixtures/                      # Test data and fixtures
│   ├── __init__.py
│   ├── api_responses.py           # Mock API responses
│   ├── sample_data.py             # Sample data for tests
│   └── credentials.py             # Test credentials
│
└── performance/                   # Performance tests
    ├── __init__.py
    ├── test_concurrency.py        # Concurrent operation tests
    └── test_load.py               # Load testing
```

### Test File Naming

| Pattern | Purpose | Example |
|---------|---------|---------|
| `test_*.py` | Test file | `test_onlyfans.py` |
| `test_<module>_<feature>.py` | Specific feature | `test_auth_login.py` |
| `*_test.py` | Alternative pattern | `onlyfans_test.py` |

### Test Function Naming

```python
# ✅ Good: Clear, descriptive
def test_user_model_validates_required_fields():
    pass

def test_authentication_fails_with_invalid_credentials():
    pass

def test_get_user_returns_none_when_not_found():
    pass

# ❌ Bad: Unclear, generic
def test_user():
    pass

def test_1():
    pass

def test_thing():
    pass
```

---

## Writing Tests

### Test Anatomy

Every test should follow the Arrange-Act-Assert (AAA) pattern:

```python
def test_example():
    # Arrange: Set up test data and dependencies
    user_data = {"id": 123, "username": "test"}
    
    # Act: Execute the code being tested
    user = UserModel(**user_data)
    
    # Assert: Verify the results
    assert user.id == 123
    assert user.username == "test"
```

### Unit Tests

#### Testing Pydantic Models

```python
import pytest
from pydantic import ValidationError
from ultima_scraper_api.apis.onlyfans.classes.user_model import UserModel

class TestUserModel:
    """Test suite for UserModel."""
    
    def test_user_model_creation_with_valid_data(self):
        """Test creating a user model with valid data."""
        # Arrange
        user_data = {
            "id": 12345,
            "name": "Test User",
            "username": "test_user",
            "avatar": "https://example.com/avatar.jpg"
        }
        
        # Act
        user = UserModel(**user_data)
        
        # Assert
        assert user.id == 12345
        assert user.name == "Test User"
        assert user.username == "test_user"
        assert user.avatar == "https://example.com/avatar.jpg"
    
    def test_user_model_requires_id(self):
        """Test that user model requires ID field."""
        # Arrange
        invalid_data = {
            "name": "Test User",
            "username": "test_user"
        }
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserModel(**invalid_data)
        
        # Verify the error message contains "id"
        assert "id" in str(exc_info.value).lower()
    
    def test_user_model_coerces_types(self):
        """Test that model coerces compatible types."""
        # Arrange
        user_data = {
            "id": "12345",  # String instead of int
            "username": "test_user"
        }
        
        # Act
        user = UserModel(**user_data)
        
        # Assert - should be converted to int
        assert isinstance(user.id, int)
        assert user.id == 12345
```

#### Testing API Initialization

```python
import pytest
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

def test_api_creation():
    """Test API instance creation."""
    # Arrange
    config = UltimaScraperAPIConfig()
    
    # Act
    api = OnlyFansAPI(config)
    
    # Assert
    assert api is not None
    assert api.config == config
    assert api.session_manager is not None

def test_api_creation_with_custom_config():
    """Test API creation with custom configuration."""
    # Arrange
    config = UltimaScraperAPIConfig(
        proxy="http://proxy:8080",
        timeout=60
    )
    
    # Act
    api = OnlyFansAPI(config)
    
    # Assert
    assert api.config.proxy == "http://proxy:8080"
    assert api.config.timeout == 60
```

#### Testing Helper Functions

```python
from ultima_scraper_api.helpers.main_helper import parse_url, format_date

def test_parse_url_with_valid_url():
    """Test URL parsing with valid URL."""
    # Arrange
    url = "https://onlyfans.com/user/12345"
    
    # Act
    result = parse_url(url)
    
    # Assert
    assert result["site"] == "onlyfans"
    assert result["user_id"] == "12345"

def test_parse_url_with_invalid_url():
    """Test URL parsing with invalid URL."""
    # Arrange
    url = "not-a-url"
    
    # Act
    result = parse_url(url)
    
    # Assert
    assert result is None

@pytest.mark.parametrize("url,expected_site", [
    ("https://onlyfans.com/user/123", "onlyfans"),
    ("https://fansly.com/user/456", "fansly"),
    ("https://loyalfans.com/user/789", "loyalfans"),
])
def test_parse_url_detects_site(url, expected_site):
    """Test URL parsing detects correct site."""
    result = parse_url(url)
    assert result["site"] == expected_site
```

---

## Async Testing

### Basic Async Tests

Use `pytest.mark.asyncio` for async tests:

```python
import pytest
from ultima_scraper_api import OnlyFansAPI

@pytest.mark.asyncio
async def test_user_fetch():
    """Test fetching a user."""
    # Arrange
    api = OnlyFansAPI()
    
    # Act
    async with api.login_context(test_auth) as authed:
        user = await authed.get_user("testuser")
    
    # Assert
    assert user is not None
    assert user.username == "testuser"

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling concurrent API requests."""
    # Arrange
    api = OnlyFansAPI()
    user_ids = [123, 456, 789]
    
    # Act
    async with api.login_context(test_auth) as authed:
        tasks = [authed.get_user(uid) for uid in user_ids]
        users = await asyncio.gather(*tasks)
    
    # Assert
    assert len(users) == 3
    assert all(user is not None for user in users)
```

### Testing Async Context Managers

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_session_context_manager():
    """Test session context manager lifecycle."""
    # Arrange
    api = OnlyFansAPI()
    auth = {"username": "test", "password": "pass"}
    
    # Act
    async with api.login_context(auth) as session:
        # Assert - inside context
        assert session is not None
        assert session.is_authenticated
    
    # Assert - after context exit
    assert session.is_closed

@pytest.mark.asyncio
async def test_context_manager_error_handling():
    """Test context manager handles errors properly."""
    # Arrange
    api = OnlyFansAPI()
    invalid_auth = {"username": "bad", "password": "bad"}
    
    # Act & Assert
    with pytest.raises(AuthenticationError):
        async with api.login_context(invalid_auth) as session:
            pass
```

### Testing Async Generators

```python
@pytest.mark.asyncio
async def test_async_generator():
    """Test async generator pagination."""
    # Arrange
    api = OnlyFansAPI()
    
    # Act
    posts = []
    async with api.login_context(test_auth) as authed:
        async for post in authed.get_posts_paginated():
            posts.append(post)
            if len(posts) >= 10:
                break
    
    # Assert
    assert len(posts) == 10
    assert all(hasattr(post, "id") for post in posts)
```

### Testing Async Timeouts

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_request_timeout():
    """Test that requests timeout appropriately."""
    # Arrange
    api = OnlyFansAPI(timeout=1)
    
    # Act & Assert
    with pytest.raises(asyncio.TimeoutError):
        async with api.login_context(test_auth) as authed:
            await authed.get_large_resource()

@pytest.mark.asyncio
async def test_timeout_does_not_affect_fast_requests():
    """Test that timeout doesn't affect fast requests."""
    # Arrange
    api = OnlyFansAPI(timeout=10)
    
    # Act
    start = time.time()
    async with api.login_context(test_auth) as authed:
        user = await authed.get_user("testuser")
    duration = time.time() - start
    
    # Assert
    assert duration < 5  # Should be fast
    assert user is not None
```

### Testing Event Loops

```python
@pytest.mark.asyncio
async def test_concurrent_api_clients():
    """Test multiple API clients running concurrently."""
    # Arrange
    api1 = OnlyFansAPI()
    api2 = OnlyFansAPI()
    
    # Act
    async with api1.login_context(test_auth1) as session1, \
               api2.login_context(test_auth2) as session2:
        user1, user2 = await asyncio.gather(
            session1.get_user("user1"),
            session2.get_user("user2")
        )
    
    # Assert
    assert user1.username == "user1"
    assert user2.username == "user2"
```

---

## Fixtures

### Basic Fixtures

Define reusable test fixtures in `conftest.py`:

```python
import pytest
from pathlib import Path
from ultima_scraper_api import OnlyFansAPI, UltimaScraperAPIConfig

@pytest.fixture
def config():
    """Create test configuration."""
    return UltimaScraperAPIConfig(
        supported_sites=["onlyfans"],
        settings={
            "timeout": 30,
            "max_retries": 3
        }
    )

@pytest.fixture
def api(config):
    """Create API instance."""
    return OnlyFansAPI(config)

@pytest.fixture
def test_auth():
    """Test authentication credentials."""
    return {
        "cookie": "auth_id=test_cookie_value",
        "user_agent": "Mozilla/5.0 Test Agent",
        "x-bc": "test_token_value"
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 12345,
        "name": "Test User",
        "username": "testuser",
        "avatar": "https://example.com/avatar.jpg",
        "subscribedByData": {"subscribePrice": 10.0}
    }
```

### Async Fixtures

```python
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def authenticated_session(api, test_auth):
    """Create authenticated session."""
    async with api.login_context(test_auth) as session:
        yield session

@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing."""
    import redis.asyncio as aioredis
    
    client = await aioredis.from_url("redis://localhost:6379/15")
    
    # Clean up before test
    await client.flushdb()
    
    yield client
    
    # Clean up after test
    await client.flushdb()
    await client.close()

@pytest_asyncio.fixture
async def temp_session_file(tmp_path):
    """Create temporary session file."""
    session_file = tmp_path / "test_session.json"
    yield session_file
    
    # Cleanup
    if session_file.exists():
        session_file.unlink()
```

### Fixture Scopes

```python
@pytest.fixture(scope="session")
def shared_config():
    """Session-scoped config (created once per test session)."""
    return UltimaScraperAPIConfig()

@pytest.fixture(scope="module")
def module_api(shared_config):
    """Module-scoped API (created once per module)."""
    return OnlyFansAPI(shared_config)

@pytest.fixture(scope="function")
def function_api():
    """Function-scoped API (created for each test)."""
    return OnlyFansAPI()
```

### Parametrized Fixtures

```python
@pytest.fixture(params=[
    "onlyfans",
    "fansly",
    "loyalfans"
])
def site_name(request):
    """Parametrized site name."""
    return request.param

def test_api_supports_site(site_name):
    """Test runs once for each site."""
    config = UltimaScraperAPIConfig(supported_sites=[site_name])
    assert site_name in config.supported_sites
```

### Using Fixtures

```python
def test_api_with_config(api):
    """Test using fixture."""
    # Fixture automatically injected
    assert api is not None
    assert api.config is not None

@pytest.mark.asyncio
async def test_authenticated_request(authenticated_session):
    """Test using async fixture."""
    user = await authenticated_session.get_user("testuser")
    assert user is not None

def test_multiple_fixtures(api, test_auth, sample_user_data):
    """Test using multiple fixtures."""
    assert api is not None
    assert "cookie" in test_auth
    assert sample_user_data["username"] == "testuser"
```

---

## Mocking Strategies

### Mocking HTTP Requests

#### Basic HTTP Mocking

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import aiohttp

@pytest.mark.asyncio
async def test_user_fetch_with_mocked_response():
    """Test user fetch with mocked HTTP response."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": 12345,
        "username": "testuser",
        "name": "Test User"
    })
    
    # Mock the session.get method
    with patch('aiohttp.ClientSession.get', return_value=mock_response) as mock_get:
        api = OnlyFansAPI()
        
        # Act
        async with api.login_context(test_auth) as authed:
            user = await authed.get_user("testuser")
        
        # Assert
        assert user.username == "testuser"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_api_error_handling():
    """Test handling of API errors."""
    # Arrange
    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.json = AsyncMock(return_value={"error": "Not found"})
    
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        api = OnlyFansAPI()
        
        # Act & Assert
        async with api.login_context(test_auth) as authed:
            with pytest.raises(APIError):
                await authed.get_user("nonexistent")
```

#### Mocking with aioresponses

Using `aioresponses` library for cleaner HTTP mocking:

```python
from aioresponses import aioresponses
import pytest

@pytest.mark.asyncio
async def test_user_fetch_with_aioresponses():
    """Test user fetch using aioresponses."""
    with aioresponses() as m:
        # Arrange
        m.get(
            "https://onlyfans.com/api2/v2/users/testuser",
            payload={
                "id": 12345,
                "username": "testuser",
                "name": "Test User"
            },
            status=200
        )
        
        api = OnlyFansAPI()
        
        # Act
        async with api.login_context(test_auth) as authed:
            user = await authed.get_user("testuser")
        
        # Assert
        assert user.username == "testuser"

@pytest.mark.asyncio
async def test_rate_limiting_with_aioresponses():
    """Test rate limiting behavior."""
    with aioresponses() as m:
        # First request succeeds
        m.get(
            "https://onlyfans.com/api2/v2/posts",
            payload={"posts": []},
            status=200
        )
        
        # Second request is rate limited
        m.get(
            "https://onlyfans.com/api2/v2/posts",
            payload={"error": "Rate limited"},
            status=429
        )
        
        api = OnlyFansAPI()
        async with api.login_context(test_auth) as authed:
            # First request succeeds
            posts1 = await authed.get_posts()
            assert posts1 is not None
            
            # Second request raises rate limit error
            with pytest.raises(RateLimitError):
                await authed.get_posts()
```

### Mocking External Services

#### Redis Mocking

```python
from unittest.mock import MagicMock, AsyncMock
import pytest

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.expire = AsyncMock(return_value=True)
    return redis

@pytest.mark.asyncio
async def test_session_caching_with_redis(mock_redis):
    """Test session caching with mocked Redis."""
    # Arrange
    from ultima_scraper_api.managers.session_manager import SessionManager
    manager = SessionManager(redis_client=mock_redis)
    
    # Act
    await manager.cache_session("user123", {"token": "abc"})
    cached = await manager.get_cached_session("user123")
    
    # Assert
    mock_redis.set.assert_called_once()
    mock_redis.get.assert_called_once_with("session:user123")

```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis

```

#### File System Mocking

```python
from unittest.mock import patch, mock_open
import pytest

def test_config_file_loading():
    """Test loading configuration from file."""
    # Arrange
    mock_config_content = '{"proxy": "http://proxy:8080"}'
    
    with patch("builtins.open", mock_open(read_data=mock_config_content)):
        # Act
        config = Config.from_file("config.json")
        
        # Assert
        assert config.proxy == "http://proxy:8080"

@pytest.mark.asyncio
async def test_download_with_mocked_filesystem(tmp_path):
    """Test file download with temporary directory."""
    # Arrange
    download_path = tmp_path / "downloads"
    download_path.mkdir()
    
    api = OnlyFansAPI()
    
    # Act
    async with api.login_context(test_auth) as authed:
        file_path = await authed.download_content(
            "https://example.com/video.mp4",
            download_path
        )
    
    # Assert
    assert file_path.exists()
    assert file_path.parent == download_path
```

#### WebSocket Mocking

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection handling."""
    # Arrange
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_json = AsyncMock(return_value={"type": "notification"})
    
    with patch('aiohttp.ClientSession.ws_connect', return_value=mock_ws):
        api = OnlyFansAPI()
        
        # Act
        async with api.websocket_context() as ws:
            await ws.send_json({"action": "subscribe"})
            message = await ws.receive_json()
        
        # Assert
        assert message["type"] == "notification"
        mock_ws.send_json.assert_called_once()
```

### Mocking Class Methods

```python
from unittest.mock import patch

def test_authentication_flow():
    """Test authentication flow with mocked methods."""
    # Arrange
    with patch.object(OnlyFansAPI, 'validate_auth', return_value=True), \
         patch.object(OnlyFansAPI, 'get_session_data', return_value={"user_id": 123}):
        
        api = OnlyFansAPI()
        
        # Act
        is_valid = api.validate_auth(test_auth)
        session_data = api.get_session_data()
        
        # Assert
        assert is_valid is True
        assert session_data["user_id"] == 123
```

---

## Parameterized Tests

### Basic Parameterization

Test multiple scenarios with parameters:

```python
import pytest

@pytest.mark.parametrize("username,expected", [
    ("user1", True),
    ("user2", True),
    ("invalid", False),
])
@pytest.mark.asyncio
async def test_user_exists(username, expected):
    """Test user existence check for multiple usernames."""
    api = OnlyFansAPI()
    async with api.login_context(test_auth) as authed:
        exists = await authed.user_exists(username)
        assert exists == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("site,endpoint,expected_url", [
    ("onlyfans", "/users/123", "https://onlyfans.com/api2/v2/users/123"),
    ("fansly", "/account/123", "https://apiv3.fansly.com/api/v1/account/123"),
    ("loyalfans", "/users/123", "https://www.loyalfans.com/api/v1/users/123"),
])
def test_url_construction(site, endpoint, expected_url):
    """Test URL construction for different sites."""
    api = get_api_for_site(site)
    url = api.build_url(endpoint)
    assert url == expected_url
```

### Parametrized IDs for Readability

```python
@pytest.mark.parametrize(
    "user_data,should_validate",
    [
        ({"id": 123, "username": "valid"}, True),
        ({"id": "123", "username": "coerced"}, True),
        ({"username": "missing_id"}, False),
        ({}, False),
    ],
    ids=["valid", "type_coercion", "missing_required", "empty"]
)
def test_user_validation(user_data, should_validate):
    """Test user validation with clear test IDs."""
    if should_validate:
        user = UserModel(**user_data)
        assert user is not None
    else:
        with pytest.raises(ValidationError):
            UserModel(**user_data)
```

### Combining Parametrization with Fixtures

```python
@pytest.fixture(params=["onlyfans", "fansly"])
def api_client(request):
    """Parametrized API client fixture."""
    site = request.param
    return get_api_for_site(site)

@pytest.mark.parametrize("user_id", [123, 456, 789])
@pytest.mark.asyncio
async def test_user_fetch_across_sites(api_client, user_id):
    """Test user fetch for multiple IDs across different sites."""
    async with api_client.login_context(test_auth) as authed:
        user = await authed.get_user(user_id)
        assert user.id == user_id
```

---

## Testing Exceptions

### Basic Exception Testing

```python
import pytest
from ultima_scraper_api.exceptions import AuthenticationError, APIError

@pytest.mark.asyncio
async def test_invalid_auth_raises_exception():
    """Test authentication with invalid credentials."""
    # Arrange
    api = OnlyFansAPI()
    invalid_auth = {
        "cookie": "invalid",
        "user_agent": "test",
        "x-bc": "invalid"
    }
    
    # Act & Assert
    with pytest.raises(AuthenticationError):
        async with api.login_context(invalid_auth) as authed:
            pass

def test_validation_error_on_invalid_model():
    """Test that invalid model data raises ValidationError."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        UserModel(username="missing_id")
    
    # Verify specific field in error
    assert "id" in str(exc_info.value)
```

### Testing Exception Messages

```python
@pytest.mark.asyncio
async def test_api_error_message():
    """Test that API errors contain helpful messages."""
    api = OnlyFansAPI()
    
    with pytest.raises(APIError) as exc_info:
        async with api.login_context(test_auth) as authed:
            await authed.get_user("nonexistent")
    
    # Verify error message
    assert "User not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404

def test_custom_exception_attributes():
    """Test custom exception attributes."""
    error = APIError(
        message="Rate limited",
        status_code=429,
        retry_after=60
    )
    
    assert error.status_code == 429
    assert error.retry_after == 60
    assert "Rate limited" in str(error)
```

### Testing Exception Handling

```python
@pytest.mark.asyncio
async def test_retry_after_rate_limit():
    """Test that rate limit errors are retried."""
    # Arrange
    api = OnlyFansAPI(max_retries=3)
    call_count = 0
    
    async def mock_request():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("Rate limited", retry_after=1)
        return {"data": "success"}
    
    with patch.object(api, 'make_request', side_effect=mock_request):
        # Act
        result = await api.make_request()
        
        # Assert
        assert call_count == 3
        assert result["data"] == "success"

@pytest.mark.asyncio
async def test_exception_cleanup():
    """Test that resources are cleaned up on exception."""
    api = OnlyFansAPI()
    
    try:
        async with api.login_context(test_auth) as authed:
            raise RuntimeError("Unexpected error")
    except RuntimeError:
        pass
    
    # Verify cleanup occurred
    assert api.session is None or api.session.closed
```

### Testing Multiple Exception Types

```python
@pytest.mark.parametrize("error_type,status_code", [
    (AuthenticationError, 401),
    (AuthorizationError, 403),
    (NotFoundError, 404),
    (RateLimitError, 429),
    (ServerError, 500),
])
@pytest.mark.asyncio
async def test_http_error_mapping(error_type, status_code):
    """Test that HTTP status codes map to correct exception types."""
    with aioresponses() as m:
        m.get(
            "https://onlyfans.com/api2/v2/test",
            status=status_code,
            payload={"error": "Test error"}
        )
        
        api = OnlyFansAPI()
        
        with pytest.raises(error_type):
            async with api.login_context(test_auth) as authed:
                await authed.make_request("GET", "/test")
```

---

## Integration Tests

Integration tests verify that multiple components work together correctly. Use these sparingly as they're slower than unit tests.

### Testing Component Integration

```python
import pytest
import os

@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_to_user_fetch_integration():
    """Test full flow from authentication to user fetch."""
    # This uses mocked HTTP but tests real integration
    with aioresponses() as m:
        # Mock auth endpoint
        m.post(
            "https://onlyfans.com/api2/v2/users/auth",
            payload={"token": "test_token"},
            status=200
        )
        
        # Mock user endpoint
        m.get(
            "https://onlyfans.com/api2/v2/users/me",
            payload={"id": 123, "username": "testuser"},
            status=200
        )
        
        # Test full flow
        api = OnlyFansAPI()
        async with api.login_context(test_auth) as authed:
            me = await authed.get_me()
            assert me.username == "testuser"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_manager_with_redis():
    """Test session manager with real Redis."""
    import redis.asyncio as aioredis
    
    # Use test database
    redis_client = await aioredis.from_url("redis://localhost:6379/15")
    
    try:
        # Test session caching
        manager = SessionManager(redis_client=redis_client)
        
        await manager.cache_session("user123", {"token": "abc"})
        cached = await manager.get_cached_session("user123")
        
        assert cached["token"] == "abc"
    finally:
        await redis_client.flushdb()
        await redis_client.close()
```

### Testing with Real APIs (Optional)

For optional real API testing during development:

```python
# Skip if no credentials provided
@pytest.mark.real_api
@pytest.mark.skipif(
    not os.getenv("TEST_COOKIE"),
    reason="No test credentials provided"
)
@pytest.mark.asyncio
async def test_real_api_authentication():
    """Test with real API (requires credentials)."""
    auth = {
        "cookie": os.getenv("TEST_COOKIE"),
        "user_agent": os.getenv("TEST_USER_AGENT"),
        "x-bc": os.getenv("TEST_XBC")
    }
    
    api = OnlyFansAPI()
    async with api.login_context(auth) as authed:
        me = await authed.get_me()
        assert me is not None
        assert me.id > 0

@pytest.mark.real_api
@pytest.mark.skipif(not os.getenv("TEST_COOKIE"), reason="No credentials")
@pytest.mark.asyncio
async def test_real_api_user_fetch():
    """Test fetching real user data."""
    auth = get_test_auth_from_env()
    
    api = OnlyFansAPI()
    async with api.login_context(auth) as authed:
        # Use a known test user
        user = await authed.get_user(os.getenv("TEST_USER_ID"))
        assert user is not None
        assert user.username is not None
```

### Database Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_operations():
    """Test database operations integration."""
    from ultima_scraper_api.managers.database_manager import DatabaseManager
    
    # Use test database
    db = DatabaseManager(database_url="sqlite:///test.db")
    
    try:
        await db.initialize()
        
        # Test CRUD operations
        user_data = {"id": 123, "username": "test"}
        await db.save_user(user_data)
        
        user = await db.get_user(123)
        assert user["username"] == "test"
        
        await db.delete_user(123)
        user = await db.get_user(123)
        assert user is None
    finally:
        await db.cleanup()
        Path("test.db").unlink(missing_ok=True)
```

---

## Test Organization

### Grouping Tests with Classes

```python
class TestUserOperations:
    """Tests for user operations."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, api, test_auth):
        """Setup for all tests in this class."""
        self.api = api
        self.auth = test_auth
    
    @pytest.mark.asyncio
    async def test_get_user(self):
        """Test getting user."""
        async with self.api.login_context(self.auth) as authed:
            user = await authed.get_user("test")
            assert user is not None
    
    @pytest.mark.asyncio
    async def test_get_user_posts(self):
        """Test getting user posts."""
        async with self.api.login_context(self.auth) as authed:
            user = await authed.get_user("test")
            posts = await user.get_posts()
            assert isinstance(posts, list)
    
    @pytest.mark.asyncio
    async def test_get_user_subscriptions(self):
        """Test getting user subscriptions."""
        async with self.api.login_context(self.auth) as authed:
            user = await authed.get_user("test")
            subs = await user.get_subscriptions()
            assert isinstance(subs, list)

class TestAuthenticationFlow:
    """Tests for authentication flows."""
    
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, api, test_auth):
        """Test login with valid credentials."""
        async with api.login_context(test_auth) as authed:
            assert authed.is_authenticated
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, api):
        """Test login with invalid credentials."""
        invalid_auth = {"cookie": "invalid"}
        
        with pytest.raises(AuthenticationError):
            async with api.login_context(invalid_auth) as authed:
                pass
    
    @pytest.mark.asyncio
    async def test_session_persistence(self, api, test_auth):
        """Test session persistence."""
        async with api.login_context(test_auth) as authed:
            token1 = authed.session_token
            
            # Re-login
            async with api.login_context(test_auth) as authed2:
                token2 = authed2.session_token
                assert token1 == token2
```

### Using Test Markers

```python
# Mark tests by category
@pytest.mark.unit
def test_unit_example():
    """Unit test."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_example():
    """Integration test."""
    pass

@pytest.mark.slow
@pytest.mark.asyncio
async def test_slow_operation():
    """Slow test."""
    pass

@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_specific():
    """Unix-specific test."""
    pass
```

Run specific markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Combine markers
pytest -m "unit and not slow"
```

---

## Coverage Requirements

### Minimum Coverage Targets

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| **Overall** | **80%** | - | Target |
| API Layer | 85% | - | Target |
| Models | 90% | - | Target |
| Helpers | 80% | - | Target |
| Managers | 85% | - | Target |

### Measuring Coverage

```bash
# Generate coverage report
pytest --cov=ultima_scraper_api --cov-report=term-missing

# Generate HTML report
pytest --cov=ultima_scraper_api --cov-report=html

# Fail if coverage below threshold
pytest --cov=ultima_scraper_api --cov-fail-under=80
```

### Coverage Report Example

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
ultima_scraper_api/__init__.py             12      0   100%
ultima_scraper_api/apis/onlyfans.py       234     23    90%   45-67
ultima_scraper_api/config.py               45      5    89%   23-27
ultima_scraper_api/helpers/main.py         89      8    91%   112, 145-151
ultima_scraper_api/models/user.py         123     12    90%   67-78
---------------------------------------------------------------------
TOTAL                                     503     48    90%
```

### Excluding Code from Coverage

```python
def debug_function():  # pragma: no cover
    """Debug function not tested."""
    print("Debug info")

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
```

---

## Testing Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
@pytest.fixture(autouse=True)
async def cleanup():
    """Cleanup after each test."""
    yield
    # Cleanup code here
    await cleanup_sessions()
    clear_caches()

# ✅ Good: Independent test
@pytest.mark.asyncio
async def test_create_user():
    user = await create_user({"username": "test"})
    assert user.username == "test"

# ❌ Bad: Depends on previous test
@pytest.mark.asyncio
async def test_get_user():
    user = await get_user("test")  # Assumes test_create_user ran
    assert user is not None
```

### 2. Use Descriptive Names

```python
# ✅ Good: Clear what's being tested
def test_user_model_validates_required_fields():
    """Test that UserModel validates required fields."""
    pass

def test_authentication_fails_with_invalid_cookie():
    """Test authentication failure with invalid cookie."""
    pass

def test_get_posts_returns_empty_list_for_new_user():
    """Test that new users have no posts."""
    pass

# ❌ Bad: Unclear purpose
def test_user():
    pass

def test_1():
    pass

def test_it_works():
    pass
```

### 3. Test Edge Cases

```python
@pytest.mark.parametrize("limit", [
    0,      # Zero
    1,      # Single item
    100,    # Normal batch
    1000,   # Large batch
    -1,     # Negative (should error)
])
@pytest.mark.asyncio
async def test_get_posts_with_various_limits(limit):
    """Test pagination with different limit values."""
    if limit < 0:
        with pytest.raises(ValueError):
            await get_posts(limit=limit)
    else:
        posts = await get_posts(limit=limit)
        assert len(posts) <= limit

@pytest.mark.parametrize("input_data,expected_error", [
    ({}, ValidationError),  # Empty
    ({"id": "not_a_number"}, ValidationError),  # Wrong type
    ({"id": None}, ValidationError),  # None value
    ({"id": -1}, ValidationError),  # Invalid value
])
def test_model_validation_edge_cases(input_data, expected_error):
    """Test model validation with edge cases."""
    with pytest.raises(expected_error):
        UserModel(**input_data)
```

### 4. Mock External Dependencies

Never make real API calls or database connections in unit tests:

```python
# ✅ Good: Mocked external dependency
@pytest.mark.asyncio
async def test_api_call_with_mock():
    """Test API call with mocked response."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_get.return_value = mock_response
        
        result = await fetch_data()
        assert result["data"] == "test"

# ❌ Bad: Makes real API call
@pytest.mark.asyncio
async def test_api_call_real():
    """Don't do this in unit tests!"""
    result = await fetch_data()  # Makes real HTTP request
    assert result is not None
```

### 5. Follow AAA Pattern

Arrange-Act-Assert pattern keeps tests readable:

```python
@pytest.mark.asyncio
async def test_user_creation():
    # Arrange: Set up test data and dependencies
    user_data = {"id": 123, "username": "test"}
    mock_db = AsyncMock()
    
    # Act: Execute the code being tested
    user = await create_user(user_data, db=mock_db)
    
    # Assert: Verify the results
    assert user.id == 123
    assert user.username == "test"
    mock_db.save.assert_called_once()
```

### 6. Test One Thing at a Time

```python
# ✅ Good: Tests one specific behavior
def test_user_model_validates_id_is_required():
    with pytest.raises(ValidationError) as exc:
        UserModel(username="test")
    assert "id" in str(exc.value)

def test_user_model_validates_username_is_required():
    with pytest.raises(ValidationError) as exc:
        UserModel(id=123)
    assert "username" in str(exc.value)

# ❌ Bad: Tests multiple things
def test_user_model_validation():
    # Tests too many things at once
    with pytest.raises(ValidationError):
        UserModel()  # Missing all fields
```

### 7. Use Fixtures for Common Setup

```python
@pytest.fixture
def user_data():
    """Common user data."""
    return {"id": 123, "username": "test"}

@pytest.fixture
def mock_api():
    """Mock API with common configuration."""
    api = Mock()
    api.get_user = AsyncMock(return_value=UserModel(id=123, username="test"))
    return api

def test_with_fixtures(user_data, mock_api):
    """Test using shared fixtures."""
    assert user_data["id"] == 123
    # Use mock_api
```

### 8. Document Test Purpose

```python
def test_session_timeout_triggers_reauthentication():
    """
    Test that expired sessions trigger automatic reauthentication.
    
    Given: An expired session token
    When: Making an API request
    Then: The session should be refreshed automatically
    """
    # Test implementation
    pass
```

---

## CI/CD Integration

### GitHub Actions Configuration

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Lint with ruff
      run: |
        ruff check .
    
    - name: Type check with mypy
      run: |
        mypy ultima_scraper_api
    
    - name: Run tests with coverage
      run: |
        pytest --cov=ultima_scraper_api --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false
    
    - name: Check coverage threshold
      run: |
        pytest --cov=ultima_scraper_api --cov-fail-under=80 --cov-report=term

  integration:
    runs-on: ubuntu-latest
    needs: test
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run integration tests
      run: |
        pytest -m integration
      env:
        REDIS_URL: redis://localhost:6379
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [-m, "not slow"]
```

Install hooks:

```bash
pip install pre-commit
pre-commit install
```

---

## Debugging Tests

### Interactive Debugging with PDB

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --trace

# Drop into debugger on first failure, then stop
pytest -x --pdb
```

Using breakpoints in tests:

```python
@pytest.mark.asyncio
async def test_with_breakpoint():
    """Test with breakpoint."""
    user = await fetch_user("test")
    
    # Execution will stop here
    breakpoint()
    
    assert user is not None
```

### Print Debugging

```python
@pytest.mark.asyncio
async def test_with_debug_output():
    """Test with debug output."""
    user = await fetch_user("test")
    
    # Print debugging (visible with -s flag)
    print(f"User: {user}")
    print(f"User ID: {user.id}")
    print(f"User dict: {user.model_dump()}")
    
    assert user is not None
```

Run with output:

```bash
# Show print statements
pytest -s

# Show print + verbose
pytest -sv

# Show only failed test output
pytest --tb=short
```

### Logging in Tests

```python
import logging

def test_with_logging(caplog):
    """Test with logging capture."""
    with caplog.at_level(logging.INFO):
        logger = logging.getLogger("ultima_scraper_api")
        logger.info("Starting user fetch")
        
        user = fetch_user("test")
        
        logger.info(f"Fetched user: {user.username}")
    
    # Assert log messages
    assert "Starting user fetch" in caplog.text
    assert "Fetched user: test" in caplog.text

def test_log_levels(caplog):
    """Test different log levels."""
    logger = logging.getLogger("test")
    
    with caplog.at_level(logging.WARNING):
        logger.info("This won't be captured")
        logger.warning("This will be captured")
        logger.error("This will too")
    
    assert "won't be captured" not in caplog.text
    assert "will be captured" in caplog.text
```

### Verbose Output

```bash
# Verbose test names
pytest -v

# Very verbose (show test docstrings)
pytest -vv

# Show all variables on failure
pytest -l

# Show full diff on assertion failure
pytest -vv --tb=long
```

### Debugging Async Tests

```python
@pytest.mark.asyncio
async def test_async_with_debug():
    """Debug async test."""
    import asyncio
    
    # Enable asyncio debug mode
    asyncio.get_event_loop().set_debug(True)
    
    # Your async code
    result = await some_async_function()
    
    # Check for unclosed resources
    tasks = [t for t in asyncio.all_tasks() if not t.done()]
    print(f"Pending tasks: {tasks}")
    
    assert result is not None
```

### Using pytest-timeout

```python
import pytest

@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_with_timeout():
    """Test that fails if it takes longer than 5 seconds."""
    result = await some_operation()
    assert result is not None

# Or configure globally in pytest.ini:
# [pytest]
# timeout = 10
```

### Debugging Test Failures

```bash
# Show last failed tests
pytest --lf

# Run last failed, then all
pytest --lf --ff

# Show why tests were skipped
pytest -rs

# Show all test outcomes
pytest -ra
```

---

## Performance Testing

### Basic Performance Tests

```python
import time
import pytest

@pytest.mark.slow
@pytest.mark.asyncio
async def test_fetch_performance():
    """Test that fetch operation completes in reasonable time."""
    # Arrange
    start = time.time()
    
    # Act
    await fetch_many_users(100)
    
    # Assert
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Fetch took {elapsed}s, expected < 5s"

@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_requests_performance():
    """Test concurrent request performance."""
    import asyncio
    
    start = time.time()
    
    # Run 50 concurrent requests
    tasks = [fetch_user(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    # Should be significantly faster than sequential
    assert elapsed < 10.0  # 50 requests in under 10 seconds
    assert len(results) == 50
```

### Memory Usage Testing

```python
import pytest
import tracemalloc

@pytest.mark.slow
@pytest.mark.asyncio
async def test_memory_usage():
    """Test that operation doesn't leak memory."""
    tracemalloc.start()
    
    # Get baseline
    baseline = tracemalloc.get_traced_memory()[0]
    
    # Perform operation multiple times
    for _ in range(100):
        await fetch_user("test")
    
    # Check memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    memory_increase = (current - baseline) / 1024 / 1024  # MB
    assert memory_increase < 50, f"Memory increased by {memory_increase}MB"

@pytest.mark.slow
def test_memory_leak_with_loops():
    """Test for memory leaks in loops."""
    import gc
    import sys
    
    gc.collect()
    
    # Create objects in loop
    initial_objects = len(gc.get_objects())
    
    for _ in range(1000):
        user = UserModel(id=123, username="test")
        # Use user
        _ = user.username
    
    gc.collect()
    final_objects = len(gc.get_objects())
    
    # Should not have grown significantly
    growth = final_objects - initial_objects
    assert growth < 100, f"Object count grew by {growth}"
```

### Load Testing

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_api_under_load():
    """Test API behavior under load."""
    import asyncio
    
    errors = []
    successes = 0
    
    async def make_request(i):
        nonlocal successes
        try:
            result = await fetch_user(f"user{i}")
            if result:
                successes += 1
        except Exception as e:
            errors.append(e)
    
    # Simulate 200 concurrent requests
    tasks = [make_request(i) for i in range(200)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Should handle most requests successfully
    success_rate = successes / 200
    assert success_rate > 0.95, f"Success rate: {success_rate:.2%}"
    assert len(errors) < 10, f"Too many errors: {len(errors)}"
```

### Benchmarking with pytest-benchmark

```python
import pytest

def test_user_model_creation_benchmark(benchmark):
    """Benchmark user model creation."""
    user_data = {"id": 123, "username": "test"}
    
    result = benchmark(lambda: UserModel(**user_data))
    
    assert result.username == "test"

@pytest.mark.asyncio
async def test_async_operation_benchmark(benchmark):
    """Benchmark async operation."""
    
    @benchmark
    async def run():
        return await fetch_user("test")
    
    result = await run
    assert result is not None
```

Run benchmarks:

```bash
# Run benchmark tests
pytest tests/test_benchmarks.py --benchmark-only

# Compare with previous results
pytest --benchmark-compare

# Save baseline
pytest --benchmark-save=baseline
```

### Response Time Testing

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_api_response_times():
    """Test API response times for various endpoints."""
    endpoints = [
        ("/users/me", 1.0),
        ("/users/123", 1.0),
        ("/posts", 2.0),
        ("/messages", 2.0),
    ]
    
    for endpoint, max_time in endpoints:
        start = time.time()
        await api_request(endpoint)
        elapsed = time.time() - start
        
        assert elapsed < max_time, \
            f"{endpoint} took {elapsed:.2f}s, expected < {max_time}s"
```

---

## Troubleshooting Tests

### Common Issues

#### Import Errors

```bash
# Problem: ModuleNotFoundError
ModuleNotFoundError: No module named 'ultima_scraper_api'

# Solution: Install in editable mode
pip install -e .

# Or ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Async Test Failures

```python
# Problem: RuntimeWarning: coroutine was never awaited
RuntimeWarning: coroutine 'test_function' was never awaited

# Solution: Add @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_function():
    await some_async_operation()
```

#### Fixture Not Found

```bash
# Problem: fixture 'api' not found
fixture 'api' not found

# Solution: Ensure conftest.py is in the right location
# and fixtures are properly defined
tests/
├── conftest.py  # ← Fixtures should be here
└── test_api.py
```

#### Redis Connection Errors

```python
# Problem: Connection refused on Redis
ConnectionRefusedError: [Errno 111] Connection refused

# Solution: Mock Redis or ensure Redis is running
@pytest.fixture
def mock_redis():
    redis = Mock()
    redis.get = AsyncMock(return_value=None)
    return redis

# Or start Redis for integration tests
# docker run -d -p 6379:6379 redis:7-alpine
```

#### Slow Tests

```bash
# Problem: Tests taking too long

# Solution 1: Run in parallel
pytest -n auto

# Solution 2: Skip slow tests
pytest -m "not slow"

# Solution 3: Use faster mocks instead of real calls
# Replace real HTTP calls with aioresponses
```

#### Flaky Tests

```python
# Problem: Tests pass/fail randomly

# Solution 1: Add retry for flaky tests
@pytest.mark.flaky(reruns=3)
@pytest.mark.asyncio
async def test_flaky_operation():
    result = await unreliable_operation()
    assert result is not None

# Solution 2: Increase timeouts
@pytest.mark.timeout(10)  # Instead of default 5
async def test_slow_operation():
    pass

# Solution 3: Fix race conditions with proper mocking
```

#### Coverage Not Calculating

```bash
# Problem: Coverage shows 0% or missing files

# Solution 1: Ensure package is installed
pip install -e .

# Solution 2: Specify source explicitly
pytest --cov=ultima_scraper_api --cov-config=.coveragerc

# Solution 3: Check .coveragerc configuration
# [run]
# source = ultima_scraper_api
# omit = */tests/*
```

### Debug Strategies

| Issue | Command | Purpose |
|-------|---------|---------|
| Test not running | `pytest -v test_file.py::test_name` | Run specific test |
| Silent failure | `pytest -s` | Show print statements |
| Unclear failure | `pytest -vv --tb=long` | Verbose traceback |
| Slow test suite | `pytest --durations=10` | Show slowest tests |
| Import issues | `pytest --collect-only` | Check test collection |
| Coverage gaps | `pytest --cov --cov-report=html` | Visual coverage report |

---

## Testing Cheat Sheet

### Essential Commands

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_onlyfans.py

# Run specific test
pytest tests/test_onlyfans.py::test_user_fetch

# Run with coverage
pytest --cov=ultima_scraper_api --cov-report=html

# Run in parallel
pytest -n auto

# Run last failed tests
pytest --lf

# Stop on first failure
pytest -x

# Show verbose output
pytest -vv

# Show print statements
pytest -s

# Run marked tests
pytest -m unit
pytest -m "not slow"

# Debug mode
pytest --pdb

# Show slowest tests
pytest --durations=10
```

### Pytest Markers

```python
@pytest.mark.asyncio           # Async test
@pytest.mark.parametrize       # Parameterized test
@pytest.mark.skip              # Skip test
@pytest.mark.skipif            # Conditional skip
@pytest.mark.xfail             # Expected failure
@pytest.mark.slow              # Mark as slow
@pytest.mark.integration       # Integration test
@pytest.mark.unit              # Unit test
@pytest.mark.timeout(10)       # 10 second timeout
```

### Assertion Helpers

```python
# Basic assertions
assert value
assert value == expected
assert value != unexpected
assert value in collection
assert value is None
assert value is not None

# Type assertions
assert isinstance(value, UserModel)
assert issubclass(MyClass, BaseClass)

# Collection assertions
assert len(collection) == 5
assert all(item > 0 for item in collection)
assert any(item == "test" for item in collection)

# Exception assertions
with pytest.raises(ValueError):
    raise ValueError("error")

with pytest.raises(ValueError, match="specific error"):
    raise ValueError("specific error message")

# Approximate assertions
assert value == pytest.approx(0.333, rel=1e-3)

# Warnings
with pytest.warns(UserWarning):
    warnings.warn("test", UserWarning)
```

---

## See Also

### Internal Documentation
- **[Contributing Guide](contributing.md)** - Contribution workflow and guidelines
- **[Architecture](architecture.md)** - System architecture and design patterns
- **[User Guide](../user-guide/working-with-apis.md)** - API usage examples
- **[Troubleshooting](../user-guide/troubleshooting.md)** - Common issues and solutions

### External Resources
- **[pytest Documentation](https://docs.pytest.org/)** - Official pytest docs
- **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)** - Async test support
- **[pytest-cov](https://pytest-cov.readthedocs.io/)** - Coverage plugin
- **[unittest.mock](https://docs.python.org/3/library/unittest.mock.html)** - Python mocking
- **[aioresponses](https://github.com/pnuckowski/aioresponses)** - Mock aiohttp requests
- **[Pydantic Testing](https://docs.pydantic.dev/latest/concepts/validation/)** - Model validation testing

### Testing Resources
- **[Test-Driven Development](https://testdriven.io/)** - TDD practices
- **[Python Testing Best Practices](https://realpython.com/pytest-python-testing/)** - RealPython guide
- **[Effective Python Testing](https://effectivepython.com/)** - Book resources
