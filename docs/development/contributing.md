# Contributing to UltimaScraperAPI

Thank you for your interest in contributing to UltimaScraperAPI! We welcome contributions from the community, whether it's bug reports, feature requests, documentation improvements, or code contributions.

This guide will help you get started with contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Guidelines](#code-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Adding New Platforms](#adding-new-platforms)
- [Release Process](#release-process)

---

## Code of Conduct

By participating in this project, you agree to maintain a **respectful** and **collaborative** environment for all contributors.

### Expected Behavior

- ✅ Be respectful and inclusive
- ✅ Welcome newcomers and help them get started
- ✅ Accept constructive criticism gracefully
- ✅ Focus on what's best for the community and project
- ✅ Show empathy toward others

### Unacceptable Behavior

- ❌ Harassment, discrimination, or hate speech
- ❌ Trolling, insulting comments, or personal attacks
- ❌ Publishing others' private information
- ❌ Spam or off-topic discussions

**Violations** may result in temporary or permanent ban from the project.

---

## Getting Started

### Ways to Contribute

There are many ways to contribute to UltimaScraperAPI:

| Contribution Type | Description | Difficulty |
|-------------------|-------------|------------|
| 🐛 **Bug Reports** | Report issues you encounter | Beginner |
| 💡 **Feature Requests** | Suggest new features or improvements | Beginner |
| 📚 **Documentation** | Improve docs, fix typos, add examples | Beginner |
| 🧪 **Testing** | Write tests, improve coverage | Intermediate |
| 🔧 **Bug Fixes** | Fix reported bugs | Intermediate |
| ✨ **New Features** | Implement new functionality | Advanced |
| 🌐 **New Platforms** | Add support for new platforms | Advanced |

### Reporting Bugs

If you find a bug, please [create an issue](https://github.com/UltimaHoarder/UltimaScraperAPI/issues/new) with the following information:

#### Bug Report Template

```markdown
**Bug Description**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Initialize API with '...'
2. Call method '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Code Sample**
```python
# Minimal reproducible example
import asyncio
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI

async def reproduce_bug():
    api = OnlyFansAPI()
    # Your code here
    pass

asyncio.run(reproduce_bug())
```

**Environment**
- OS: [e.g., Ubuntu 22.04, Windows 11, macOS 14]
- Python Version: [e.g., 3.11.5]
- Package Version: [e.g., 2.2.46]
- Installation Method: [pip, uv, source]

**Error Message/Traceback**
```
Paste full error message and traceback here
```

**Additional Context**
Any other relevant information.
```

#### Before Submitting

- ✅ Search [existing issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues) to avoid duplicates
- ✅ Verify the bug exists in the latest version
- ✅ Include a minimal reproducible example
- ✅ Redact sensitive information (credentials, personal data)

---

### Suggesting Features

Feature requests help us improve the project! 

#### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Describe why this feature would be valuable and how it would be used.

**Proposed Solution**
How you envision this feature working.

**Alternatives Considered**
Any alternative solutions you've thought about.

**Examples**
```python
# Example of how the feature would be used
user = await api.get_user("username")
await user.new_feature_method()
```

**Additional Context**
Screenshots, mockups, or references to similar features.

#### Before Submitting

- ✅ Check if feature already exists or is planned
- ✅ Search existing feature requests
- ✅ Consider if it fits the project scope
- ✅ Think about backward compatibility

---

### Asking Questions

Have a question? Here's how to get help:

1. **Check Documentation:** Browse the [full documentation](https://ultimahoarder.github.io/UltimaScraperAPI/)
2. **Search Issues:** Look through [existing issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)
3. **Ask Question:** Open an issue with the `question` label

!!! tip "Quick Response"
    Include context, what you've tried, and specific questions for faster responses.

---

## Development Setup

### Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10 - 3.14 | Required |
| **Git** | Latest | Required |
| **uv** | Latest | Recommended package manager |
| **Redis** | 6.2.0+ | Optional (for caching features) |
| **Make** | Any | Optional (for Makefile commands) |

### Quick Start

```bash
# 1. Fork the repository on GitHub
# 2. Clone YOUR fork
git clone https://github.com/YOUR_USERNAME/UltimaScraperAPI.git
cd UltimaScraperAPI

# 3. Add upstream remote
git remote add upstream https://github.com/UltimaHoarder/UltimaScraperAPI.git

# 4. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# 5. Install dependencies with uv (recommended)
pip install uv
uv pip install -e ".[dev]"

# 6. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 7. Verify installation
python -c "import ultima_scraper_api; print(ultima_scraper_api.__version__)"
```

### Detailed Setup

#### 1. Fork and Clone

1. **Fork the repository** on GitHub (click "Fork" button)
2. **Clone your fork:**

```bash
git clone https://github.com/YOUR_USERNAME/UltimaScraperAPI.git
cd UltimaScraperAPI
```

3. **Configure remotes:**

```bash
# Add upstream (original repo)
git remote add upstream https://github.com/UltimaHoarder/UltimaScraperAPI.git

# Verify remotes
git remote -v
# Should show:
# origin    https://github.com/YOUR_USERNAME/UltimaScraperAPI.git (fetch)
# origin    https://github.com/YOUR_USERNAME/UltimaScraperAPI.git (push)
# upstream  https://github.com/UltimaHoarder/UltimaScraperAPI.git (fetch)
# upstream  https://github.com/UltimaHoarder/UltimaScraperAPI.git (push)
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Linux/Mac
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Verify activation
which python  # Should point to .venv/bin/python
python --version  # Should be 3.10+
```

#### 3. Install Dependencies

**Option A: Using uv (Recommended)**

```bash
# Install uv if not already installed
pip install uv

# Install package in editable mode with dev dependencies
uv pip install -e ".[dev]"

# Verify installation
uv pip list | grep ultima-scraper-api
```

**Option B: Using pip**

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
pip list | grep ultima-scraper-api
```

**Development Dependencies Include:**

- `black` - Code formatting
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `mkdocs-material` - Documentation
- `nox` - Test automation
- `python-semantic-release` - Version management

#### 4. Configure Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Test hooks (optional)
pre-commit run --all-files
```

Pre-commit hooks will:
- Format code with Black
- Check for trailing whitespace
- Validate YAML/JSON files
- Check for merge conflicts

#### 5. Setup Redis (Optional)

If you want to work on Redis-related features:

```bash
# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
# Or use WSL/Docker

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### 6. Configure IDE

**VS Code Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**PyCharm Settings:**

1. Go to Settings → Project → Python Interpreter
2. Add `.venv` as interpreter
3. Enable Black for formatting
4. Configure pytest as test runner

---

## Development Workflow

### Creating a Feature Branch

```bash
# Make sure you're on main and up to date
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description

# Or for documentation
git checkout -b docs/doc-improvement
```

### Branch Naming Conventions

| Type | Prefix | Example |
|------|--------|---------|
| New Feature | `feature/` | `feature/add-story-highlights` |
| Bug Fix | `fix/` | `fix/authentication-timeout` |
| Documentation | `docs/` | `docs/improve-api-reference` |
| Refactoring | `refactor/` | `refactor/session-manager` |
| Performance | `perf/` | `perf/optimize-downloads` |
| Tests | `test/` | `test/add-integration-tests` |

### Making Changes

1. **Make your changes** in your feature branch
2. **Format code:**

```bash
# Format all Python files
black ultima_scraper_api/

# Check formatting (won't modify files)
black --check ultima_scraper_api/
```

3. **Run tests:**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_onlyfans.py

# Run with coverage
pytest --cov=ultima_scraper_api --cov-report=html
```

4. **Update documentation** if needed

5. **Commit your changes** (see [Commit Guidelines](#commit-guidelines))

### Keeping Your Branch Updated

```bash
# Fetch latest changes from upstream
git fetch upstream

# Rebase your branch on upstream/main
git rebase upstream/main

# If conflicts, resolve them and continue
git add .
git rebase --continue

# Force push to your fork (rebase rewrites history)
git push origin feature/your-feature-name --force-with-lease
```

---

## Code Guidelines

### Code Style

We follow **PEP 8** and use **Black** for automatic formatting.

#### Black Configuration

Black is configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py310', 'py311', 'py312']
include = '\.pyi?$'
```

#### Formatting Commands

```bash
# Format entire project
black ultima_scraper_api/ tests/

# Format specific file
black ultima_scraper_api/apis/onlyfans/onlyfans.py

# Check without modifying
black --check ultima_scraper_api/

# Show diff of what would change
black --diff ultima_scraper_api/
```

#### Style Guidelines

**✅ DO:**
- Use Black for formatting
- Follow PEP 8 naming conventions
- Keep lines under 88 characters (Black default)
- Use meaningful variable names
- Add blank lines between logical sections

**❌ DON'T:**
- Mix tabs and spaces
- Use single-letter variables (except loops)
- Create overly complex expressions
- Ignore linter warnings without reason

### Type Hints

**All functions and methods MUST have type hints.**

#### Basic Type Hints

```python
from typing import Optional, List, Dict, Any

# Function with return type
async def get_user(username: str) -> Optional[UserModel]:
    """Get user by username."""
    pass

# Function with multiple parameters
async def get_posts(
    user_id: int,
    offset: int = 0,
    limit: int = 50,
    include_pinned: bool = False
) -> List[PostModel]:
    """Get user posts with pagination."""
    pass

# Function with dict parameter
async def update_settings(
    settings: Dict[str, Any]
) -> bool:
    """Update user settings."""
    pass
```

#### Modern Type Hints (Python 3.10+)

```python
# Use | instead of Union
def process_id(user_id: int | str) -> int:
    """Process user ID (int or string)."""
    if isinstance(user_id, str):
        return int(user_id)
    return user_id

# Use list[] instead of List[]
async def get_multiple_users(
    user_ids: list[int]
) -> list[UserModel]:
    """Get multiple users by IDs."""
    pass

# Use dict[] instead of Dict[]
def parse_response(
    data: dict[str, Any]
) -> UserModel:
    """Parse API response into model."""
    pass

# Optional with None default
async def find_user(
    username: str,
    cache: dict[str, UserModel] | None = None
) -> UserModel | None:
    """Find user with optional cache."""
    pass
```

#### Pydantic Models

```python
from pydantic import BaseModel, Field, ConfigDict

class UserModel(BaseModel):
    """User data model with validation."""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True
    )
    
    id: int = Field(..., description="User ID")
    username: str = Field(..., min_length=3, max_length=50)
    email: str | None = Field(None, description="User email")
    posts_count: int = Field(0, ge=0, description="Number of posts")
    
    def display_name(self) -> str:
        """Get display name."""
        return f"@{self.username}"
```

### Async/Await Patterns

#### Correct Async Usage

```python
import asyncio

# ✅ DO: Use async/await for I/O operations
async def fetch_user_data(user_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/users/{user_id}") as response:
            return await response.json()

# ✅ DO: Use asyncio.gather for concurrent operations
async def fetch_multiple_users(user_ids: list[int]) -> list[dict]:
    tasks = [fetch_user_data(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)

# ✅ DO: Use context managers
async def download_media(url: str, save_path: str):
    async with OnlyFansAPI() as api:
        async with api.login_context(auth) as authed:
            await authed.download(url, save_path)

# ❌ DON'T: Mix sync and async without proper handling
def bad_function():
    result = await fetch_data()  # ❌ SyntaxError: await outside async

# ❌ DON'T: Block event loop
async def bad_async():
    time.sleep(10)  # ❌ Blocks event loop
    # Use: await asyncio.sleep(10)
```

### Documentation Standards

#### Docstring Format (Google Style)

```python
async def fetch_user_posts(
    user_id: int,
    offset: int = 0,
    limit: int = 100,
    include_archived: bool = False
) -> list[PostModel]:
    """Fetch posts from a user's profile.
    
    This method retrieves posts with pagination support. Posts are returned
    in reverse chronological order by default.
    
    Args:
        user_id: The unique identifier of the user
        offset: Number of posts to skip (for pagination)
        limit: Maximum number of posts to return (1-100)
        include_archived: Whether to include archived posts
    
    Returns:
        List of PostModel objects. Empty list if no posts found.
    
    Raises:
        AuthenticationError: If not authenticated or session expired
        ValueError: If limit is outside valid range (1-100)
        APIError: If API request fails
        RateLimitError: If rate limit exceeded
    
    Example:
        ```python
        async with api.login_context(auth_details) as auth:
            posts = await auth.fetch_user_posts(
                user_id=12345,
                limit=50,
                include_archived=True
            )
            for post in posts:
                print(post.text)
        ```
    
    Note:
        This method requires an authenticated session. Archived posts
        may require additional permissions.
    
    See Also:
        - get_user(): Fetch user profile information
        - get_stories(): Fetch user stories
    """
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    
    # Implementation
    pass
```

#### Class Documentation

```python
class OnlyFansAPI:
    """OnlyFans API client for accessing platform features.
    
    This class provides methods for authenticating with OnlyFans and
    accessing various platform features including user profiles, posts,
    messages, and media content.
    
    Attributes:
        config: Configuration object with API settings
        session: aiohttp ClientSession for HTTP requests
        is_authenticated: Whether currently authenticated
    
    Example:
        ```python
        from ultima_scraper_api.apis.onlyfans import OnlyFansAPI
        
        # Basic usage
        api = OnlyFansAPI()
        async with api.login_context(credentials) as auth:
            user = await auth.get_user("username")
            print(user.name)
        
        # With configuration
        from ultima_scraper_api.config import UltimaScraperAPIConfig
        
        config = UltimaScraperAPIConfig()
        api = OnlyFansAPI(config)
        ```
    
    Note:
        This class should be used as an async context manager to ensure
        proper cleanup of resources.
    """
    
    def __init__(self, config: UltimaScraperAPIConfig | None = None):
        """Initialize OnlyFans API client.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        pass
```

### Error Handling

#### Custom Exceptions

```python
# Define in ultima_scraper_api/exceptions.py
class UltimaScraperAPIError(Exception):
    """Base exception for all API errors."""
    pass

class AuthenticationError(UltimaScraperAPIError):
    """Raised when authentication fails."""
    pass

class RateLimitError(UltimaScraperAPIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after
```

#### Exception Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

# ✅ DO: Handle specific exceptions
async def safe_fetch_user(user_id: int) -> UserModel | None:
    try:
        return await fetch_user(user_id)
    except AuthenticationError:
        logger.error("Authentication failed")
        raise
    except RateLimitError as e:
        logger.warning(f"Rate limited, retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after or 60)
        return await fetch_user(user_id)
    except APIError as e:
        logger.error(f"API error: {e}")
        return None

# ✅ DO: Use retry decorators for transient failures
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(url: str) -> dict:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()

# ❌ DON'T: Catch all exceptions silently
async def bad_error_handling():
    try:
        result = await some_operation()
    except:  # ❌ Too broad, hides errors
        pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# ✅ DO: Use appropriate log levels
logger.debug("Fetching user data for ID: %d", user_id)
logger.info("Successfully authenticated user: %s", username)
logger.warning("Rate limit approaching: %d requests remaining", remaining)
logger.error("Failed to fetch user: %s", error_message)
logger.critical("Database connection lost")

# ✅ DO: Use lazy formatting
logger.info("User %s has %d posts", username, post_count)  # ✅
logger.info(f"User {username} has {post_count} posts")    # ❌ Eager

# ❌ DON'T: Log sensitive information
logger.info(f"Credentials: {password}")  # ❌ NEVER!
logger.debug(f"Auth cookie: {cookie}")   # ❌ NEVER!
```

---

## Testing Guidelines

### Test Requirements

**All contributions MUST include tests:**

- ✅ New features require tests
- ✅ Bug fixes require regression tests  
- ✅ Maintain or improve code coverage
- ✅ All tests must pass before merging

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_onlyfans.py

# Run specific test
pytest tests/test_onlyfans.py::test_authentication

# Run tests matching pattern
pytest -k "test_user"

# Run with coverage
pytest --cov=ultima_scraper_api --cov-report=html

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x

# Run in parallel (faster)
pytest -n auto
```

### Writing Tests

#### Test Structure

```python
# tests/test_onlyfans.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI
from ultima_scraper_api.apis.onlyfans.classes import UserModel

class TestOnlyFansAPI:
    """Tests for OnlyFans API client."""
    
    @pytest.fixture
    def api(self):
        """Create API instance for testing."""
        return OnlyFansAPI()
    
    @pytest.fixture
    def mock_session(self):
        """Create mock HTTP session."""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={"id": 1, "username": "test"})
        session.get.return_value.__aenter__.return_value = response
        return session
    
    @pytest.mark.asyncio
    async def test_get_user_success(self, api, mock_session):
        """Test successful user retrieval."""
        api.session = mock_session
        
        user = await api.get_user("testuser")
        
        assert user is not None
        assert user.username == "test"
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, api, mock_session):
        """Test user not found scenario."""
        mock_session.get.return_value.__aenter__.return_value.status = 404
        api.session = mock_session
        
        user = await api.get_user("nonexistent")
        
        assert user is None
```

#### Testing Async Functions

```python
import pytest
import asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result == expected

# Test concurrent operations
@pytest.mark.asyncio
async def test_concurrent_fetches():
    """Test fetching multiple items concurrently."""
    tasks = [fetch_item(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
```

#### Mocking HTTP Requests

```python
from unittest.mock import AsyncMock, patch
import aiohttp

@pytest.mark.asyncio
async def test_api_request():
    """Test API request with mocked response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = OnlyFansAPI()
        result = await api.fetch_data()
        
        assert result["success"] is True
```

#### Testing Pydantic Models

```python
import pytest
from pydantic import ValidationError

def test_user_model_valid():
    """Test valid user model creation."""
    user = UserModel(
        id=123,
        username="testuser",
        name="Test User"
    )
    assert user.id == 123
    assert user.username == "testuser"

def test_user_model_invalid():
    """Test invalid user model raises error."""
    with pytest.raises(ValidationError):
        UserModel(id="invalid", username="test")  # id should be int
```

#### Testing Error Handling

```python
import pytest
from ultima_scraper_api.exceptions import AuthenticationError

@pytest.mark.asyncio
async def test_authentication_error():
    """Test authentication error is raised."""
    api = OnlyFansAPI()
    
    with pytest.raises(AuthenticationError):
        await api.login(invalid_credentials)

@pytest.mark.asyncio
async def test_error_recovery():
    """Test error recovery mechanism."""
    api = OnlyFansAPI()
    
    # Should retry and succeed
    result = await api.fetch_with_retry(url)
    assert result is not None
```

#### Fixtures for Common Setup

```python
# conftest.py
import pytest
from ultima_scraper_api.apis.onlyfans import OnlyFansAPI
from ultima_scraper_api.config import UltimaScraperAPIConfig

@pytest.fixture
def config():
    """Create test configuration."""
    return UltimaScraperAPIConfig()

@pytest.fixture
def api(config):
    """Create API instance."""
    return OnlyFansAPI(config)

@pytest.fixture
async def authenticated_api(api):
    """Create authenticated API instance."""
    # Mock authentication
    await api.login(test_credentials)
    yield api
    await api.close()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 12345,
        "username": "testuser",
        "name": "Test User",
        "avatar": "https://example.com/avatar.jpg"
    }
```

### Coverage Requirements

- **Minimum coverage:** 80% for new code
- **Target coverage:** 90%+
- **Critical paths:** 100% coverage required

```bash
# Generate coverage report
pytest --cov=ultima_scraper_api --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

See [Testing Documentation](testing.md) for more details.

---

## Adding New Platforms

One of the most valuable contributions is adding support for new content platforms!

### Platform Requirements

Before starting, ensure the platform:

- ✅ Has a documented or reverse-engineered API
- ✅ Allows programmatic access (check ToS)
- ✅ Fits the project scope (premium content platforms)
- ✅ Has enough demand from users

### Step-by-Step Guide

#### 1. Research the Platform

```bash
# Document your findings
docs/research/newplatform.md:
- API endpoints
- Authentication method
- Available features
- Rate limits
- Known limitations
```

#### 2. Create Directory Structure

```bash
mkdir -p ultima_scraper_api/apis/newplatform/classes
touch ultima_scraper_api/apis/newplatform/__init__.py
touch ultima_scraper_api/apis/newplatform/newplatform.py
touch ultima_scraper_api/apis/newplatform/authenticator.py
mkdir -p ultima_scraper_api/apis/newplatform/classes
```

#### 3. Implement API Class

```python
# ultima_scraper_api/apis/newplatform/newplatform.py
from typing import Any
from ultima_scraper_api.apis.api_helper import APIHelper
from ultima_scraper_api.config import UltimaScraperAPIConfig
from .authenticator import NewPlatformAuthenticator
from .classes.auth_model import NewPlatformAuthModel

class NewPlatformAPI:
    """NewPlatform API client.
    
    Provides methods for authenticating and interacting with NewPlatform's API.
    
    Example:
        ```python
        api = NewPlatformAPI()
        async with api.login_context(auth_details) as auth:
            user = await auth.get_user("username")
        ```
    """
    
    def __init__(self, config: UltimaScraperAPIConfig | None = None):
        """Initialize NewPlatform API client.
        
        Args:
            config: Configuration object. Uses default if None.
        """
        self.config = config or UltimaScraperAPIConfig()
        self.api_helper = APIHelper()
        self.base_url = "https://api.newplatform.com"
    
    def get_authenticator(self) -> NewPlatformAuthenticator:
        """Get authenticator instance.
        
        Returns:
            NewPlatformAuthenticator instance
        """
        return NewPlatformAuthenticator(self)
    
    async def login_context(self, auth_details: dict):
        """Async context manager for authenticated session.
        
        Args:
            auth_details: Authentication credentials
        
        Yields:
            Authenticated session model
        
        Example:
            ```python
            async with api.login_context(credentials) as auth:
                user = await auth.get_user("username")
            ```
        """
        authenticator = self.get_authenticator()
        auth = await authenticator.login(auth_details)
        try:
            yield auth
        finally:
            await auth.close()
```

#### 4. Implement Authenticator

```python
# ultima_scraper_api/apis/newplatform/authenticator.py
from ultima_scraper_api.apis.auth_streamliner import AuthStreamliner
from .classes.auth_model import NewPlatformAuthModel

class NewPlatformAuthenticator:
    """Handles NewPlatform authentication."""
    
    def __init__(self, api):
        self.api = api
        self.auth_streamliner = AuthStreamliner()
    
    async def login(self, auth_details: dict) -> NewPlatformAuthModel:
        """Authenticate with NewPlatform.
        
        Args:
            auth_details: Dictionary containing:
                - token: API token
                - user_agent: Browser user agent
        
        Returns:
            Authenticated user model
        
        Raises:
            AuthenticationError: If authentication fails
        """
        # Validate credentials
        if not auth_details.get("token"):
            raise ValueError("Token required")
        
        # Create session
        session = await self._create_session(auth_details)
        
        # Fetch user data
        user_data = await self._fetch_user_data(session)
        
        # Create auth model
        auth = NewPlatformAuthModel(**user_data, session=session)
        
        return auth
```

#### 5. Create Data Models

```python
# ultima_scraper_api/apis/newplatform/classes/auth_model.py
from pydantic import BaseModel, ConfigDict
from .user_model import UserModel

class NewPlatformAuthModel(BaseModel):
    """Authenticated user model for NewPlatform.
    
    Provides methods for interacting with the API as an authenticated user.
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    
    id: int
    username: str
    email: str | None = None
    session: Any  # aiohttp session
    
    async def get_user(self, username: str) -> UserModel | None:
        """Get user by username.
        
        Args:
            username: Username to fetch
        
        Returns:
            UserModel if found, None otherwise
        """
        endpoint = f"/users/{username}"
        data = await self._make_request("GET", endpoint)
        return UserModel(**data) if data else None
    
    async def close(self):
        """Close session and cleanup resources."""
        if self.session:
            await self.session.close()
```

```python
# ultima_scraper_api/apis/newplatform/classes/user_model.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserModel(BaseModel):
    """NewPlatform user model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    name: str
    avatar: str | None = None
    bio: str | None = None
    followers_count: int = 0
    created_at: datetime | None = None
```

#### 6. Write Tests

```python
# tests/test_newplatform.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from ultima_scraper_api.apis.newplatform import NewPlatformAPI
from ultima_scraper_api.apis.newplatform.classes import UserModel

class TestNewPlatformAPI:
    """Tests for NewPlatform API."""
    
    @pytest.fixture
    def api(self):
        """Create API instance."""
        return NewPlatformAPI()
    
    @pytest.fixture
    def auth_details(self):
        """Sample auth details."""
        return {
            "token": "test_token_123",
            "user_agent": "Mozilla/5.0 ..."
        }
    
    @pytest.mark.asyncio
    async def test_authentication(self, api, auth_details):
        """Test authentication process."""
        authenticator = api.get_authenticator()
        
        # Mock the session creation
        with mock_session():
            auth = await authenticator.login(auth_details)
            
            assert auth.username is not None
            assert auth.session is not None
    
    @pytest.mark.asyncio
    async def test_get_user(self, api):
        """Test getting user by username."""
        # Test implementation
        pass
```

#### 7. Add Documentation

```markdown
# documentation/docs/api-reference/newplatform.md

# NewPlatform API Reference

Complete API reference for NewPlatform integration.

## Installation

NewPlatform support is included in the standard installation.

## Authentication

### Requirements

- API Token
- User Agent

### Getting Credentials

1. Log into NewPlatform
2. Go to Settings → API
3. Generate API token
4. Copy token

### Example

```python
from ultima_scraper_api.apis.newplatform import NewPlatformAPI

auth_details = {
    "token": "your_api_token",
    "user_agent": "Mozilla/5.0 ..."
}

api = NewPlatformAPI()
async with api.login_context(auth_details) as auth:
    user = await auth.get_user("username")
    print(user.name)
```

## API Classes

### NewPlatformAPI

Main API client...

[Continue with full API documentation]
```

#### 8. Update Main Documentation

- Add NewPlatform to README.md
- Update platform comparison table
- Add to mkdocs.yml navigation

#### 9. Create Pull Request

```markdown
feat(newplatform): add NewPlatform API support

This PR adds complete support for NewPlatform including:

- Authentication
- User profiles
- Content fetching
- Media downloads

Closes #XXX

## Testing
- [ ] Authentication works
- [ ] Can fetch user profiles
- [ ] Can download content
- [ ] All tests pass
- [ ] Documentation complete

## Status
- ✅ Core functionality
- ✅ Tests
- ✅ Documentation
- ⚠️ Known limitations: ...
```

### Platform Integration Checklist

- [ ] API client class
- [ ] Authenticator
- [ ] Auth model with API methods
- [ ] User model
- [ ] Post/Content models
- [ ] Media model
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] API reference documentation
- [ ] Usage examples
- [ ] Authentication guide
- [ ] Troubleshooting section
- [ ] Update main README
- [ ] Update mkdocs.yml

---

## Documentation Guidelines

### When to Update Documentation

Update documentation when you:

- ✅ Add new features
- ✅ Change existing behavior
- ✅ Fix bugs that affect usage
- ✅ Add/modify configuration options
- ✅ Find errors or unclear sections

### Documentation Structure

```
documentation/docs/
├── index.md                    # Home page
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   └── configuration.md
├── user-guide/
│   ├── authentication.md
│   ├── working-with-apis.md
│   ├── session-management.md
│   ├── proxy-support.md
│   └── troubleshooting.md
├── api-reference/
│   ├── onlyfans.md
│   ├── fansly.md
│   ├── loyalfans.md
│   └── helpers.md
├── development/
│   ├── architecture.md
│   ├── contributing.md
│   └── testing.md
└── about/
    ├── changelog.md
    └── license.md
```

### Writing Documentation

#### Markdown Best Practices

```markdown
# Use Headers Hierarchically

## Main Section

### Subsection

#### Detail Level

## Code Examples

Use code blocks with language specification:

```python
from ultima_scraper_api import OnlyFansAPI

async def example():
    api = OnlyFansAPI()
    user = await api.get_user("username")
```

## Admonitions (MkDocs Material)

!!! note
    This is an informational note.

!!! tip "Pro Tip"
    This is a helpful tip for users.

!!! warning
    This is a warning about potential issues.

!!! danger "Critical"
    This is critical information to prevent errors.

## Tables

| Feature | Status | Notes |
|---------|--------|-------|
| OnlyFans | ✅ Stable | Production ready |
| Fansly | ⚠️ WIP | In development |

## Links

[Internal Link](../user-guide/authentication.md)
[External Link](https://github.com/UltimaHoarder/UltimaScraperAPI)
```

### Building Documentation Locally

```bash
# Install documentation dependencies
pip install mkdocs-material

# Serve documentation locally
mkdocs serve

# Open in browser: http://localhost:8000

# Build static site
mkdocs build

# Deploy to GitHub Pages (maintainers only)
mkdocs gh-deploy
```

---

## Commit Guidelines

We follow **Conventional Commits** for clear, structured commit history.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(onlyfans): add story highlights` |
| `fix` | Bug fix | `fix(auth): handle expired tokens` |
| `docs` | Documentation | `docs(api): update OnlyFans reference` |
| `style` | Code style | `style: format with black` |
| `refactor` | Code refactoring | `refactor(session): improve connection pool` |
| `perf` | Performance improvement | `perf(download): optimize chunk size` |
| `test` | Tests | `test(onlyfans): add user model tests` |
| `chore` | Maintenance | `chore: update dependencies` |
| `ci` | CI/CD changes | `ci: add GitHub Actions workflow` |

### Commit Scope

Common scopes:
- `onlyfans` - OnlyFans API
- `fansly` - Fansly API
- `loyalfans` - LoyalFans API
- `auth` - Authentication
- `session` - Session management
- `config` - Configuration
- `docs` - Documentation
- `tests` - Testing
- `api` - General API

### Commit Subject

- Use imperative mood ("add" not "added")
- Don't capitalize first letter
- No period at the end
- Keep under 50 characters

### Commit Body (Optional)

- Explain **why** the change was made
- Describe **what** changed at a high level
- Wrap at 72 characters

### Commit Footer (Optional)

Reference issues and PRs:

```
Closes #123
Fixes #456
Relates to #789
Breaking Change: Description of breaking change
```

### Examples

#### Good Commits

```
feat(onlyfans): add story highlights support

Added methods to fetch and download story highlights from OnlyFans
profiles. Includes pagination and filtering options.

Closes #123
```

```
fix(auth): handle expired session tokens

Session tokens now automatically refresh when expired. Added retry
logic with exponential backoff for authentication failures.

Fixes #456
```

```
docs(api): improve OnlyFans API reference

- Added examples for all methods
- Documented return types
- Added troubleshooting section

Closes #789
```

```
refactor(session): optimize connection pooling

Reduced default connection pool size from 200 to 100 and improved
connection reuse. Speeds up requests by 15% in benchmarks.

Breaking Change: SessionManager constructor signature changed.
See migration guide for details.
```

#### Bad Commits

```
❌ Fixed stuff
❌ Update code
❌ WIP
❌ asdfasdf
❌ Fixed bug (which bug?)
❌ Added feature (which feature?)
```

### Amending Commits

```bash
# Amend last commit message
git commit --amend

# Amend without changing message
git commit --amend --no-edit

# Add forgotten files to last commit
git add forgotten_file.py
git commit --amend --no-edit
```

---

## Pull Request Process

### Before Submitting

**Checklist:**

- [ ] Code follows style guidelines (Black formatting)
- [ ] All tests pass (`pytest`)
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with `main`
- [ ] No merge conflicts
- [ ] Reviewed your own changes

### Creating Pull Request

1. **Push your branch:**

```bash
git push origin feature/your-feature-name
```

2. **Open Pull Request** on GitHub

3. **Fill out PR template:**

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to break)
- [ ] Documentation update

## Related Issues
Closes #123
Relates to #456

## Changes Made
- Added feature X
- Fixed bug Y
- Updated documentation for Z

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] All tests pass
- [ ] Tested manually

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented if present)

## Additional Notes
Any additional information reviewers should know.
```

### PR Review Process

1. **Automated Checks:**
   - CI/CD pipeline runs tests
   - Code coverage check
   - Linting and formatting

2. **Code Review:**
   - Maintainer reviews code
   - May request changes
   - Discussion in PR comments

3. **Address Feedback:**

```bash
# Make requested changes
# Commit changes
git add .
git commit -m "fix: address review feedback"

# Push updates
git push origin feature/your-feature-name
```

4. **Approval:**
   - At least one maintainer approval required
   - All checks must pass

5. **Merge:**
   - Maintainer merges PR
   - Branch may be deleted

### PR Best Practices

**✅ DO:**
- Keep PRs focused and small
- Write clear PR descriptions
- Respond to feedback promptly
- Be open to suggestions
- Keep PR updated with main branch

**❌ DON'T:**
- Mix multiple unrelated changes
- Force push after review starts
- Add unrelated commits
- Leave PRs stale for weeks
- Take feedback personally

### Draft Pull Requests

For work-in-progress:

```markdown
# Mark as draft PR
[WIP] feat(onlyfans): adding story highlights

This PR is a work in progress. Not ready for review yet.

TODO:
- [ ] Add tests
- [ ] Update docs
- [ ] Handle edge cases
```

---

## Release Process

Releases are managed by project maintainers following **Semantic Versioning** (SemVer).

### Versioning Scheme

```
MAJOR.MINOR.PATCH

Example: 2.2.46
         │ │ │
         │ │ └─ Patch: Bug fixes, no breaking changes
         │ └─── Minor: New features, backward compatible
         └───── Major: Breaking changes
```

### Version Types

| Version | When to Use | Example |
|---------|-------------|---------|
| **Major** (X.0.0) | Breaking API changes | Pydantic v1 → v2 |
| **Minor** (x.X.0) | New features, backward compatible | Add WebSocket support |
| **Patch** (x.x.X) | Bug fixes, improvements | Fix authentication timeout |

### Release Workflow (Maintainers)

1. **Update Changelog**
   - Document all changes since last release
   - Follow Keep a Changelog format

2. **Version Bump**
   ```bash
   # Bump version
   uv version --bump patch  # or minor/major
   ```

3. **Create Release**
   ```bash
   # Tag release
   git tag -a v2.2.47 -m "Release v2.2.47"
   git push origin v2.2.47
   ```

4. **Build and Publish**
   ```bash
   # Build distribution
   python -m build
   
   # Publish to PyPI
   python -m twine upload dist/*
   ```

5. **GitHub Release**
   - Create release on GitHub
   - Add changelog
   - Attach artifacts

### Pre-release Versions

For testing:

```bash
# Alpha release
2.3.0a1, 2.3.0a2

# Beta release
2.3.0b1, 2.3.0b2

# Release candidate
2.3.0rc1, 2.3.0rc2
```

---

## Community Guidelines

### Being a Good Contributor

**Respect the Community:**
- Be patient with reviewers
- Accept feedback gracefully
- Help other contributors
- Share knowledge

**Quality Over Quantity:**
- Well-tested, focused contributions
- Clear documentation
- Follow established patterns

**Communication:**
- Ask questions when unclear
- Provide context in discussions
- Update issues/PRs with progress
- Be responsive to feedback

### Getting Recognition

Contributors are recognized through:

- 📝 Changelog mentions
- 👥 GitHub contributors page
- 🌟 Special acknowledgment for major contributions
- 🎖️ Maintainer status for consistent contributors

---

## Resources

### Documentation

- [Full Documentation](https://ultimahoarder.github.io/UltimaScraperAPI/)
- [Architecture Guide](architecture.md)
- [Testing Guide](testing.md)
- [API Reference](../api-reference/onlyfans.md)

### External Resources

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [pytest documentation](https://docs.pytest.org/)
- [aiohttp documentation](https://docs.aiohttp.org/)
- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)

### Tools

- [Black formatter](https://black.readthedocs.io/)
- [uv package manager](https://github.com/astral-sh/uv)
- [pre-commit hooks](https://pre-commit.com/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

---

## FAQ

### How do I get started contributing?

1. Start with documentation improvements or bug fixes
2. Look for issues labeled `good first issue`
3. Read this guide thoroughly
4. Ask questions if unsure

### What should my first contribution be?

Good first contributions:
- Fix typos in documentation
- Add examples to docs
- Write tests for existing code
- Fix small bugs labeled `good first issue`

### How long does PR review take?

- Simple changes: 1-3 days
- Complex features: 1-2 weeks
- Depends on maintainer availability

### My PR was rejected. What now?

- Don't take it personally
- Read feedback carefully
- Ask for clarification
- Consider alternative approaches
- Try again with improvements

### Can I work on multiple PRs simultaneously?

Yes, but:
- Keep them independent
- Don't let any become stale
- Focus on quality over quantity

### How do I become a maintainer?

Maintainer status is earned through:
- Consistent, quality contributions
- Helping other contributors
- Active participation in discussions
- Demonstrating technical expertise
- 6+ months of regular contributions

---

## Questions or Issues?

**Need Help?**

1. **Check Documentation:** Browse the [full documentation](https://ultimahoarder.github.io/UltimaScraperAPI/)
2. **Search Issues:** Look through [existing issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)
3. **Ask Questions:** Open an issue with the `question` label
4. **Join Discussions:** Participate in [GitHub Discussions](https://github.com/UltimaHoarder/UltimaScraperAPI/discussions)

**Report Problems:**

- 🐛 [Report a bug](https://github.com/UltimaHoarder/UltimaScraperAPI/issues/new?labels=bug)
- 💡 [Request a feature](https://github.com/UltimaHoarder/UltimaScraperAPI/issues/new?labels=enhancement)
- 📚 [Improve documentation](https://github.com/UltimaHoarder/UltimaScraperAPI/issues/new?labels=documentation)

---

## License

By contributing to UltimaScraperAPI, you agree that your contributions will be licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### What This Means

- ✅ You retain copyright of your contributions
- ✅ Your code can be used, modified, and distributed
- ✅ Any derivative work must also be open source (AGPL-3.0)
- ✅ Network use = distribution (AGPL requirement)

See [LICENSE](../about/license.md) for full details.

---

## Acknowledgments

Thank you to all contributors who help make UltimaScraperAPI better! 🎉

Your contributions, whether code, documentation, bug reports, or ideas, are invaluable to the project.

### Special Thanks

- All contributors listed in [GitHub Contributors](https://github.com/UltimaHoarder/UltimaScraperAPI/graphs/contributors)
- Community members who report bugs and suggest features
- Users who provide feedback and testing

---

## Final Notes

**Remember:**

- 💻 Code quality matters
- 📚 Documentation is crucial
- 🧪 Tests prevent bugs
- 🤝 Collaboration makes us stronger
- 🎯 Focus on user value

**Happy Contributing!** 🚀

---

**Last Updated:** October 18, 2025  
**Version:** 2.2.46
