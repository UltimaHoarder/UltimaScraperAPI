# Changelog

All notable changes to UltimaScraperAPI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Enhanced Fansly API support (currently WIP)
- Enhanced LoyalFans API support (currently WIP)
- Two-factor authentication (2FA) support
- Advanced rate limiting strategies
- GraphQL API support for platforms
- Webhook support for real-time notifications
- Enhanced media processing pipeline
- Batch operation improvements

---

## [2.2.46] - 2025-10-18

### Added
- **Comprehensive MkDocs Material documentation** with 10,000+ lines covering:
  - Complete installation guide with multiple methods (uv, pip, source)
  - Quick start tutorial with credential extraction
  - Full configuration reference with all options
  - Authentication guide for all platforms
  - Working with APIs guide (2000+ lines)
  - Complete OnlyFans API reference (850+ lines)
  - Proxy support documentation (900+ lines)
  - Session management guide with Redis integration (1000+ lines)
  - Comprehensive troubleshooting guide (1200+ lines)
- Enhanced README.md with detailed feature list and examples
- Documentation site deployment setup
- Code examples throughout documentation (150+ examples)
- Best practices and patterns for async operations
- Production-ready session management examples
- Redis caching and session storage patterns
- Proxy rotation strategies (HTTP, HTTPS, SOCKS4, SOCKS5)
- DRM decryption documentation
- WebSocket integration patterns

### Changed
- Updated project structure for better organization
- Improved documentation navigation and user experience
- Enhanced error handling documentation
- Refined API method signatures documentation
- Updated dependency documentation with version constraints

### Documentation
- Created comprehensive user guides for all major features
- Added 75+ troubleshooting scenarios with solutions
- Documented all configuration options with examples
- Added platform-specific guides and limitations
- Created development documentation structure

---

## [2.2.43] - 2024-08-20

### Added
- **WebSocket support** for real-time connections
- Message sending functionality to `OnlyFansAuthModel`
- Enhanced `endpoint_links` management
- cURL string parsing for OnlyFans login
- Improved authentication flow with cURL compatibility

### Changed
- Enhanced OnlyFans login methods to support multiple input formats
- Improved session management across all platforms
- Updated authentication context handling

### Fixed
- Login context issues with session persistence
- WebSocket connection stability improvements

---

## [2.2.42] - 2024-05-15

### Changed
- Refactored auth model docstring formatting for better readability
- Enhanced request method typing with proper type hints
- Improved code documentation across API modules
- Updated session handling for LoyalFans platform

### Added
- Better type safety with enhanced typing annotations
- Improved IDE autocomplete support

---

## [2.2.41] - 2024-05-10

### Changed
- Improved `OnlyFansAPI` login context handling
- Enhanced session lifecycle management
- Better context manager cleanup

### Fixed
- Session cleanup issues in login context
- Memory leaks in long-running sessions

---

## [2.2.40] - 2024-04-25

### Changed
- Updated `httpx` dependency to version 0.28+
- Refactored user model structure
- Enhanced cache handling mechanisms
- Improved request/response caching

### Added
- Better cache invalidation strategies
- Enhanced user model with additional fields

### Fixed
- Cache-related memory issues
- User model initialization bugs

---

## [2.2.37] - 2024-04-15

### Changed
- Restructured dependencies in `pyproject.toml`
- Updated dependency version constraints
- Improved package metadata

### Added
- Better dependency resolution
- Enhanced optional dependency groups

---

## [2.2.36] - 2024-04-10

### Changed
- Renamed user model references from `create_user` to `UserModel`
- Updated related class names for consistency
- Standardized model naming conventions

### Refactored
- User model creation patterns
- Authentication model structure
- Improved code organization

---

## [2.2.35] - 2024-03-20

### Fixed
- Updated price type to `int | None` in message and post models
- Improved auth iteration handling
- Better null value handling in models

### Changed
- Enhanced model field definitions
- Improved type safety in pricing fields

---

## [2.2.34] - 2024-01-15

### Added
- Enhanced file decryption with temporary output path support
- Improved DRM handling capabilities
- Better file timestamp handling

### Changed
- Enhanced API data structures
- Improved payment handling in message and post models
- Updated file processing pipeline

---

## [2.2.33] - 2023-12-01

### Fixed
- OnlyFans API login issue handling
- Error recovery in authentication flow
- Session persistence bugs

### Changed
- Improved error messages and logging
- Enhanced authentication retry logic

---

## [2.2.32] - 2023-11-15

### Changed
- Updated `httpx` dependency to version 0.27.2
- Enhanced request error handling in `OnlyFansAPI`
- Improved error recovery mechanisms

### Fixed
- Connection timeout issues
- Request retry logic improvements

---

## [2.2.31] - 2023-11-01

### Added
- `get_transactions` method to `OnlyFansAuthModel`
- PATCH method support in `session_manager.py`
- Transaction history retrieval

### Changed
- Enhanced financial data handling
- Improved HTTP method support

---

## [2.2.30] - 2023-10-15

### Changed
- Updated dependencies with security fixes
- Fixed proxy handling in `session_manager.py`
- Improved error handling in `job_manager.py`

### Fixed
- Proxy authentication issues
- Connection pooling stability
- Job manager error recovery

---

## [2.2.28] - 2023-06-20

### Changed
- Removed unused `get_subscription` method
- Updated `pywidevine.device` import structure
- Code cleanup and optimization

### Removed
- Deprecated subscription methods
- Unused imports and dependencies

---

## [2.2.25-2.2.27] - 2023-05-10

### Changed
- Fixed cache types in `config.py`
- Handled duplicate aliases in user management
- Updated datetime usage in `CacheStats`
- Modified aliases handling in `StreamlinedUser`

### Fixed
- Cache type mismatches
- Duplicate data handling
- Timestamp timezone issues

---

## [2.0.0 - 2.2.24] - 2022-2023

### Major Features Released
- Initial stable release with OnlyFans support
- Async/await architecture with `aiohttp`
- Pydantic v2 integration for data validation
- Redis support for caching and session management
- Proxy support (HTTP, HTTPS, SOCKS4, SOCKS5)
- DRM decryption capabilities with Widevine
- Content downloading with progress tracking
- Rate limiting and retry mechanisms
- Comprehensive error handling
- Multi-platform authentication framework
- Session management and connection pooling
- Media processing pipeline
- Pagination support for large datasets

### Platforms Supported
- ✅ **OnlyFans** - Stable, production-ready
- ⚠️ **Fansly** - Work in progress
- ⚠️ **LoyalFans** - Work in progress

---

## Version Support

### Python Versions
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13
- ✅ Python 3.14

### Maintained Versions
- **2.2.x** - Current stable branch (Active development)
- **2.1.x** - Maintenance mode
- **2.0.x** - Security fixes only

---

## Migration Guides

### Migrating to 2.2.x

#### Breaking Changes from 2.1.x
- Pydantic v2 required (was v1)
- `create_user` renamed to `UserModel`
- Enhanced type hints may require code adjustments
- WebSocket support changes session initialization

#### Required Updates
```python
# Old (2.1.x)
from ultima_scraper_api.apis.onlyfans import create_user
user = create_user(data)

# New (2.2.x)
from ultima_scraper_api.models import UserModel
user = UserModel(**data)
```

#### Pydantic v2 Migration
```python
# Old (Pydantic v1)
class Config:
    orm_mode = True

# New (Pydantic v2)
model_config = ConfigDict(from_attributes=True)
```

---

## Deprecation Notices

### Deprecated in 2.2.x (Will be removed in 3.0.0)
- `get_subscription()` method - Use `auth.subscriptions` property
- Legacy cache configuration - Use Redis configuration
- Synchronous API methods - Use async equivalents

### Removed in 2.2.x
- Python 3.8 and 3.9 support
- Pydantic v1 compatibility
- Legacy authentication methods
- Deprecated session managers

---

## Security Advisories

### 2.2.46
- No known security vulnerabilities
- All dependencies up-to-date with security patches

### Best Practices
- Always use latest version for security updates
- Rotate credentials regularly
- Use environment variables for sensitive data
- Enable SSL certificate verification
- Use HTTPS proxies when possible
- Implement rate limiting
- Monitor authentication token expiration

---

## Legend

| Type | Description |
|------|-------------|
| 🆕 **Added** | New features and capabilities |
| 🔄 **Changed** | Changes in existing functionality |
| 🗑️ **Deprecated** | Features marked for future removal |
| ❌ **Removed** | Features removed in this version |
| 🐛 **Fixed** | Bug fixes and corrections |
| 🔒 **Security** | Security vulnerability fixes |
| 📚 **Documentation** | Documentation improvements |
| ♻️ **Refactored** | Code improvements without behavior changes |

---

## Contributing

We welcome contributions! See our [Contributing Guide](../development/contributing.md) for details on:
- How to report bugs
- How to suggest features
- Development workflow
- Code style guidelines
- Testing requirements

---

## Support

- 📖 **Documentation:** [https://ultimahoarder.github.io/UltimaScraperAPI/](https://ultimahoarder.github.io/UltimaScraperAPI/)
- 🐛 **Issues:** [GitHub Issues](https://github.com/UltimaHoarder/UltimaScraperAPI/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/UltimaHoarder/UltimaScraperAPI/discussions)
- 📦 **Releases:** [GitHub Releases](https://github.com/UltimaHoarder/UltimaScraperAPI/releases)

---

**Last Updated:** October 18, 2025  
**Current Version:** 2.2.46
