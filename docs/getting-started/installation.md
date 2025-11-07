# Installation

This guide will walk you through installing UltimaScraperAPI and its dependencies.

## Requirements

- **Python 3.10 or higher** (but less than 4.0)
- **pip** or **uv** package manager (uv recommended for faster installation)
- Minimum of 4GB RAM recommended for optimal performance
- Internet connection for API access

!!! note "Supported Python Versions"
    UltimaScraperAPI officially supports Python 3.10, 3.11, 3.12, 3.13, and 3.14.

## Installation Methods

### Using pip (Simple)

The simplest way to install UltimaScraperAPI is using pip:

```bash
pip install ultima-scraper-api
```

To install a specific version:

```bash
pip install ultima-scraper-api==2.2.46
```

### Using uv (Recommended)

For faster dependency resolution and installation, use [uv](https://github.com/astral-sh/uv):

```bash
# Install uv if you haven't already
pip install uv

# Install the package
uv pip install ultima-scraper-api
```

!!! tip "Why uv?"
    uv is significantly faster than pip for dependency resolution and installation, especially for projects with many dependencies like UltimaScraperAPI.

### From Source (Development)

If you want to install from source or contribute to development:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/UltimaHoarder/UltimaScraperAPI.git
   cd UltimaScraperAPI
   ```

2. **Install in editable mode:**
   
   Using pip:
   ```bash
   pip install -e .
   ```
   
   Using uv:
   ```bash
   uv pip install -e .
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```
   
   Or with uv:
   ```bash
   uv pip install -e ".[dev]"
   ```

!!! warning "Development Installation"
    Installing from source gives you the latest development version, which may be unstable. For production use, install from PyPI.

## Key Dependencies

UltimaScraperAPI includes the following core dependencies (automatically installed):

### Core Libraries
- **aiohttp** (≥3.8.4) - Async HTTP client/server framework
- **httpx** (≥0.28) - Modern HTTP client with HTTP/2 support
- **requests** (≥2.28) - HTTP library with SOCKS proxy support
- **pydantic** (≥2.0) - Data validation using Python type annotations

### Networking & Proxies
- **websockets** (≥15.0.1, <16.0.0) - WebSocket client and server
- **aiohttp-socks** (≥0.9.0) - SOCKS proxy support for aiohttp
- **python-socks[asyncio]** (≥2.2.0) - Python SOCKS client

### Data Processing
- **beautifulsoup4** (≥4.11.1) - HTML/XML parsing
- **lxml** (≥4.9.1) - Fast XML/HTML processing
- **xmltodict** (≥0.13.0) - XML to dict conversion
- **orjson** (≥3.8.3) - Fast JSON serialization

### Storage & Caching
- **redis[hiredis]** (≥6.2.0, <7.0.0) - Redis client with hiredis for performance

### Other
- **pywidevine** - Widevine CDM implementation (from custom repository)
- **user-agent** (≥0.1.10) - User agent generation
- **python-dateutil** (≥2.8.2) - Date/time utilities
- **inflection** (≥0.5.1) - String transformations
- **alive-progress** (≥3.1.5) - Progress bars
- **aiofiles** (≥22.1.0) - Async file operations
- **dill** (≥0.3.6) - Object serialization
- **mergedeep** (≥1.3.4) - Deep dictionary merging

All dependencies are automatically installed when you install UltimaScraperAPI.

## Optional Dependencies

Development dependencies (testing, documentation, etc.) can be installed with:

```bash
pip install ultima-scraper-api[dev]
```

This includes:
- **pytest** & **pytest-asyncio** - Testing framework
- **pytest-cov** - Coverage reporting
- **black** - Code formatting
- **mkdocs-material** - Documentation site generator
- **nox** - Task automation

## Verify Installation

After installation, verify that UltimaScraperAPI is correctly installed:

=== "Python REPL"
    ```python
    import ultima_scraper_api
    print(f"Version: {ultima_scraper_api.__version__}")
    ```

=== "Command Line"
    ```bash
    python -c "import ultima_scraper_api; print(ultima_scraper_api.__version__)"
    ```

Expected output: `2.2.46` (or your installed version)

## Troubleshooting

### Import Errors

If you encounter import errors after installation:

```bash
# Reinstall the package
pip uninstall ultima-scraper-api
pip install ultima-scraper-api

# Or clear pip cache and reinstall
pip cache purge
pip install --no-cache-dir ultima-scraper-api
```

### Dependency Conflicts

If you experience dependency conflicts:

```bash
# Use uv which handles dependencies better
pip install uv
uv pip install --reinstall ultima-scraper-api
```

### Platform-Specific Issues

#### Windows
- The `win32-setctime` package is automatically installed on Windows for file timestamp handling
- Ensure you have Visual C++ Build Tools installed if compilation issues occur

#### Linux
- Some dependencies may require build tools: `sudo apt-get install build-essential python3-dev`
- For lxml: `sudo apt-get install libxml2-dev libxslt1-dev`

#### macOS
- Xcode Command Line Tools may be required: `xcode-select --install`
- Use Homebrew to install system dependencies if needed

## Virtual Environments

It's recommended to use a virtual environment to avoid dependency conflicts:

=== "venv"
    ```bash
    # Create virtual environment
    python -m venv venv
    
    # Activate it
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows
    
    # Install UltimaScraperAPI
    pip install ultima-scraper-api
    ```

=== "conda"
    ```bash
    # Create conda environment
    conda create -n ultimascraper python=3.11
    
    # Activate it
    conda activate ultimascraper
    
    # Install UltimaScraperAPI
    pip install ultima-scraper-api
    ```

## Next Steps

Now that you have UltimaScraperAPI installed, proceed to the [Quick Start](quick-start.md) guide to learn how to use it.

For configuration options, see the [Configuration](configuration.md) guide.
