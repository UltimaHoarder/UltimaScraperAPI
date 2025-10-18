# API Helpers & Utilities

Comprehensive reference for internal helper classes, utilities, and streamliner components used throughout UltimaScraperAPI. These modules provide common functionality, manage pooling, handle authentication flows, and support user operations across all platforms.

---

## Table of Contents

1. [Overview](#overview)
2. [API Helper Module](#api-helper-module)
3. [API Streamliner](#api-streamliner)
4. [Auth Streamliner](#auth-streamliner)
5. [User Streamliner](#user-streamliner)
6. [Helper Utilities](#helper-utilities)
7. [Complete Examples](#complete-examples)
8. [See Also](#see-also)

---

## Overview

The helper and streamliner modules provide reusable components that:

- **Manage thread pools** for concurrent operations
- **Streamline API operations** with common patterns
- **Handle authentication sessions** with caching
- **Manage user operations** with job tracking
- **Provide utility functions** for common tasks

### Module Structure

```
ultima_scraper_api/
├── apis/
│   ├── api_helper.py          # Threading, pooling, utility functions
│   ├── api_streamliner.py     # API operation streamlining
│   ├── auth_streamliner.py    # Authentication management
│   └── user_streamliner.py    # User operations & job tracking
└── helpers/
    ├── identifier_helper.py   # ID parsing and validation
    └── main_helper.py         # General utilities
```

---

## API Helper Module

**Location**: `ultima_scraper_api/apis/api_helper.py`

Provides core utilities for thread pool management, URL manipulation, error handling, and data processing.

### CustomPool

Context manager for thread pool operations with automatic resource cleanup.

```python
from ultima_scraper_api.apis.api_helper import CustomPool

# Use as context manager (recommended)
with CustomPool(max_threads=10) as pool:
    results = pool.map(process_function, items)
    # Pool automatically cleaned up on exit
```

**Parameters:**

- `max_threads` (int | None): Maximum threads. If `None`, auto-calculates based on CPU count.

**Methods:**

- `__enter__()`: Creates and returns thread pool
- `__exit__()`: Closes thread pool

**Example:**

```python
def process_item(item):
    # Process individual item
    return item.upper()

items = ["one", "two", "three"]

with CustomPool(max_threads=4) as pool:
    results = pool.map(process_item, items)
    print(list(results))  # ['ONE', 'TWO', 'THREE']
```

### multiprocessing

Create a thread pool for parallel operations.

```python
from ultima_scraper_api.apis.api_helper import multiprocessing

pool = multiprocessing(max_threads=10)
results = pool.map(function, iterable)
pool.close()
```

**Parameters:**

- `max_threads` (int | None): Maximum threads. If `None` or `-1`, uses CPU count.

**Returns:**

- `ThreadPool`: Multiprocessing thread pool

**Example:**

```python
def download_file(url):
    # Download logic
    return f"Downloaded {url}"

urls = ["url1", "url2", "url3"]
pool = multiprocessing(max_threads=5)
results = pool.map(download_file, urls)
pool.close()
```

### calculate_max_threads

Calculate optimal thread count based on CPU cores.

```python
from ultima_scraper_api.apis.api_helper import calculate_max_threads

max_threads = calculate_max_threads(10)  # Returns min(10, cpu_count())
auto_threads = calculate_max_threads()   # Returns cpu_count()
```

**Parameters:**

- `max_threads` (int | None): Desired thread count. If `None`, `-1`, or exceeds CPU count, returns CPU count.

**Returns:**

- `int`: Calculated thread count

**Logic:**

```python
# If max_threads is None or -1, use all CPU cores
# If max_threads > cpu_count, use cpu_count
# Otherwise, use max_threads
```

### calculate_the_unpredictable

Generate paginated URLs with offset calculation (used for API pagination).

```python
from ultima_scraper_api.apis.api_helper import calculate_the_unpredictable

links, final_offset = calculate_the_unpredictable(
    link="https://api.example.com/posts?offset=0&limit=50",
    offset=0,
    limit=50,
    multiplier=5,
    depth=1
)
```

**Parameters:**

- `link` (str): Base URL with offset parameter
- `offset` (int): Starting offset
- `limit` (int): Items per page
- `multiplier` (int): Number of pages to generate
- `depth` (int): Pagination depth

**Returns:**

- `tuple[list[str], int]`: (List of paginated URLs, final offset value)

**Example:**

```python
base_url = "https://api.example.com/posts?offset=0&limit=50"
links, final_offset = calculate_the_unpredictable(
    link=base_url,
    offset=0,
    limit=50,
    multiplier=3,  # Generate 3 URLs
    depth=1
)

# Returns:
# links = [
#     "https://api.example.com/posts?offset=0&limit=50",
#     "https://api.example.com/posts?offset=50&limit=50",
#     "https://api.example.com/posts?offset=100&limit=50"
# ]
# final_offset = 100
```

### parse_config_inputs

Parse comma-separated configuration strings into lists.

```python
from ultima_scraper_api.apis.api_helper import parse_config_inputs

# Parse string
result = parse_config_inputs("user1,user2,user3")
# Returns: ['user1', 'user2', 'user3']

# Pass through list
result = parse_config_inputs(["user1", "user2"])
# Returns: ['user1', 'user2']
```

**Parameters:**

- `custom_input` (Any): String (comma-separated) or list

**Returns:**

- `list[str]`: Parsed list

### handle_error_details

Process error responses and optionally filter them out.

```python
from ultima_scraper_api.apis.api_helper import handle_error_details

results = await handle_error_details(
    item=api_responses,
    remove_errors_status=True,
    api_type=authed
)
```

**Parameters:**

- `item` (error_types | dict | list): API responses
- `remove_errors_status` (bool): Whether to filter errors. Default: `False`
- `api_type` (auth_types | None): Authentication object

**Returns:**

- `list`: Processed results (errors removed if `remove_errors_status=True`)

### get_function_name

Get calling function name (useful for debugging and logging).

```python
from ultima_scraper_api.apis.api_helper import get_function_name

async def my_function():
    name = await get_function_name()  # Returns "my_function"
    api_name = await get_function_name(convert_to_api_type=True)  # Returns capitalized
```

**Parameters:**

- `function_that_called` (str): Override function name
- `convert_to_api_type` (bool): Convert to API type format (capitalize last part after underscore)

**Returns:**

- `str`: Function name

### merge_dictionaries

Merge multiple dictionaries with additive strategy (arrays are combined, not replaced).

```python
from ultima_scraper_api.apis.api_helper import merge_dictionaries

dict1 = {"users": ["user1"], "count": 1}
dict2 = {"users": ["user2"], "count": 2}
dict3 = {"users": ["user3"], "tags": ["tag1"]}

merged = merge_dictionaries([dict1, dict2, dict3])
# Returns: {
#     "users": ["user1", "user2", "user3"],
#     "count": 2,  # Last value wins for non-list fields
#     "tags": ["tag1"]
# }
```

**Parameters:**

- `items` (list[dict]): List of dictionaries to merge

**Returns:**

- `dict`: Merged dictionary

### remove_errors

Filter out error objects from API response lists.

```python
from ultima_scraper_api.apis.api_helper import remove_errors

responses = [
    {"id": 1, "name": "User1"},
    {"error": "Not found"},
    {"id": 2, "name": "User2"},
    ErrorObject()
]

cleaned = await remove_errors(responses)
# Returns: [{"id": 1, "name": "User1"}, {"id": 2, "name": "User2"}]
```

**Parameters:**

- `results` (Any): Single item or list of items

**Returns:**

- `Any`: Filtered results (error objects removed)

### extract_list

Extract "list" field from API response dictionary.

```python
from ultima_scraper_api.apis.api_helper import extract_list

response = {"list": [1, 2, 3], "hasMore": True}
items = await extract_list(response)
# Returns: [1, 2, 3]
```

**Parameters:**

- `result` (dict): API response with "list" field

**Returns:**

- `Any`: Extracted list

---

## API Streamliner

**Location**: `ultima_scraper_api/apis/api_streamliner.py`

Streamlines API operations by providing platform-agnostic wrappers and common functionality across OnlyFans, Fansly, and LoyalFans.

### Packages

Platform-specific package loader for dynamic imports.

```python
from ultima_scraper_api.apis.api_streamliner import Packages

# Load OnlyFans packages
packages = Packages("onlyfans")
AuthDetails = packages.AuthDetails
CreateAuth = packages.CreateAuth

# Load Fansly packages
packages = Packages("fansly")
auth = packages.CreateAuth(...)
```

**Supported Platforms:**

- `"onlyfans"`: OnlyFans packages
- `"fansly"`: Fansly packages
- `"loyalfans"`: LoyalFans packages

**Attributes:**

- `AuthDetails`: Authentication details class
- `CreateAuth`: Authentication model class (OnlyFansAuthModel, FanslyAuthModel, or LoyalFansAuthModel)

### StreamlinedAPI

Main streamliner class providing unified API operations across platforms.

```python
from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI

streamliner = StreamlinedAPI(api=onlyfans_api, config=config)
```

**Attributes:**

- `api` (api_types): Platform API instance
- `config` (UltimaScraperAPIConfig): Configuration object
- `lists` (Any | None): Custom lists storage
- `pool` (CustomPool): Thread pool manager
- `job_manager` (JobManager): Job management system
- `session_manager` (SessionManager): HTTP session manager
- `packages` (Packages): Platform-specific packages

**Methods:**

#### add_auth

Add an authenticated session to the API.

```python
authed = await api.login(auth_json)
streamliner.add_auth(authed)
```

**Parameters:**

- `auth` (auth_types): Authenticated session

**Returns:**

- `auth_types`: The added auth object

#### has_active_auths

Check if any authenticated sessions are active.

```python
if streamliner.has_active_auths():
    print("Active sessions available")
else:
    print("No active sessions")
```

**Returns:**

- `bool`: `True` if active sessions exist

#### get_site_settings

Get site-specific settings from configuration.

```python
site_settings = streamliner.get_site_settings()
print(site_settings.browser)
print(site_settings.webhooks)
```

**Returns:**

- Site settings object

#### get_global_settings

Get global API settings.

```python
global_settings = streamliner.get_global_settings()
print(global_settings.network.proxies)
print(global_settings.requests.max_retries)
```

**Returns:**

- Global settings object

#### close_pools

Close all session pools and cleanup resources.

```python
await streamliner.close_pools()
```

**Example:**

```python
from ultima_scraper_api import UltimaScraperAPI, UltimaScraperAPIConfig

# Initialize
api = UltimaScraperAPI()
onlyfans = api.get_site_api("onlyfans")
config = UltimaScraperAPIConfig()

# Create streamliner
streamliner = StreamlinedAPI(api=onlyfans, config=config)

# Login
auth_json = {...}
async with onlyfans.login_context(auth_json) as authed:
    streamliner.add_auth(authed)
    
    # Check for active sessions
    if streamliner.has_active_auths():
        # Perform operations
        pass

# Cleanup
await streamliner.close_pools()
```

---

## Auth Streamliner

**Location**: `ultima_scraper_api/apis/auth_streamliner.py`

Manages authenticated sessions with caching, session management, and webhook integration.

### CacheStats

Tracks cache timing for API responses with automatic expiration.

```python
from ultima_scraper_api.apis.auth_streamliner import CacheStats

cache = CacheStats(delay_in_seconds=3600)  # 1 hour cache
```

**Parameters:**

- `delay_in_seconds` (int): Cache duration in seconds. Default: `3600` (1 hour)

**Attributes:**

- `processed_at` (datetime | None): When cache was activated
- `delay_in_seconds` (int): Cache duration
- `released_at` (datetime | None): When cache expires

**Methods:**

#### activate

Activate the cache with current timestamp.

```python
cache.activate()
```

#### deactivate

Deactivate and clear the cache.

```python
cache.deactivate()
```

#### is_released

Check if cache has expired.

```python
if cache.is_released():
    # Cache expired, fetch fresh data
    await fetch_data()
else:
    # Use cached data
    pass
```

**Returns:**

- `bool`: `True` if cache expired or not set

### Cache

Centralized cache management for authenticated sessions.

```python
from ultima_scraper_api.apis.auth_streamliner import Cache

cache = Cache()
```

**Attributes:**

- `chats` (CacheStats): Chat cache (1 hour)
- `paid_content` (CacheStats): Paid content cache (1 hour)
- `mass_message_stats` (CacheStats): Mass message stats cache (1 hour)
- `mass_messages` (CacheStats): Mass messages cache (1 hour)
- `subscriptions` (CacheStats): Subscriptions cache (1 hour)
- `data` (dict): User-specific cache data

**Methods:**

#### users

Get or create cache stats for a specific user (5-minute cache).

```python
user_cache = cache.users(user_id=12345)
if user_cache.is_released():
    # Refresh user data
    pass
```

**Parameters:**

- `user_id` (int | str): User identifier

**Returns:**

- `CacheStats`: User-specific cache stats (300 seconds = 5 minutes)

### StreamlinedAuth

Generic authenticated session wrapper with caching and session management.

```python
from ultima_scraper_api.apis.auth_streamliner import StreamlinedAuth

# Automatically created during login
# authed is StreamlinedAuth instance
async with api.login_context(auth_json) as authed:
    if authed.is_authed():
        # Use authenticated session
        pass
```

**Type Parameters:**

- `T`: Authenticator type
- `TAPI`: API type
- `TAuthDetails`: Auth details type

**Attributes:**

- `authenticator` (T): Platform authenticator
- `auth_session` (AuthedSession): HTTP session
- `cache` (Cache): Cache manager
- `issues` (dict | None): Session issues

**Methods:**

#### is_authed

Check if session is authenticated.

```python
if authed.is_authed():
    print("Authenticated")
else:
    print("Not authenticated")
```

**Returns:**

- `bool`: Authentication status

#### get_auth_details

Get authentication details.

```python
auth_details = authed.get_auth_details()
print(auth_details.cookie)
print(auth_details.user_agent)
```

**Returns:**

- `TAuthDetails`: Authentication details object

#### get_api

Get the associated API instance.

```python
api = authed.get_api()
print(api.site_name)
```

**Returns:**

- `TAPI`: API instance

#### get_requester

Get HTTP session requester.

```python
session = authed.get_requester()
response = await session.get("https://api.example.com/endpoint")
```

**Returns:**

- `AuthedSession`: HTTP session

**Example:**

```python
from ultima_scraper_api import UltimaScraperAPI

api = UltimaScraperAPI()
onlyfans = api.get_site_api("onlyfans")

auth_json = {
    "cookie": "your_cookie",
    "user_agent": "your_user_agent"
}

async with onlyfans.login_context(auth_json) as authed:
    if authed and authed.is_authed():
        # Check cache before fetching
        if authed.cache.subscriptions.is_released():
            subs = await authed.get_subscriptions()
            authed.cache.subscriptions.activate()
        
        # Get API instance
        api = authed.get_api()
        print(f"Using {api.site_name} API")
        
        # Use requester for custom requests
        session = authed.get_requester()
        response = await session.get("/api/endpoint")
```

---

## User Streamliner

**Location**: `ultima_scraper_api/apis/user_streamliner.py`

Manages user operations, job tracking, and content processing workflows.

### JobTask

Represents a sub-task within a job with progress tracking.

```python
from ultima_scraper_api.apis.user_streamliner import JobTask

task = JobTask(title="Download Images")
task.max = 100  # Total items
task.advance(10)  # Processed 10 items
```

**Attributes:**

- `title` (str): Task title
- `child_tasks` (list[JobTask]): Nested sub-tasks
- `min` (int): Completed items
- `max` (int): Total items
- `done` (bool): Task completion status

**Methods:**

#### advance

Advance task progress.

```python
task.advance(length=5)  # Increment by 5
```

**Parameters:**

- `length` (int): Amount to increment

### Job

Represents a scraping job with multiple tasks.

```python
from ultima_scraper_api.apis.user_streamliner import Job

job = Job(title="Scrape User Content")
task1 = job.create_task("Download Posts")
task2 = job.create_task("Download Messages")
```

**Attributes:**

- `title` (str): Job title
- `done` (bool): Job completion status
- `added` (bool): Whether job is added to queue
- `tasks` (list[JobTask]): Job tasks

**Methods:**

#### create_task

Create a new task.

```python
task = job.create_task("Download Videos")
```

**Parameters:**

- `title` (str): Task title

**Returns:**

- `JobTask`: Created task

#### create_tasks

Create multiple tasks from list.

```python
job.create_tasks(["Task 1", "Task 2", "Task 3"])
```

**Parameters:**

- `data` (list[str]): Task titles

#### get_current_task

Get the first incomplete task.

```python
current_task = job.get_current_task()
if current_task:
    print(f"Working on: {current_task.title}")
```

**Returns:**

- `JobTask | None`: Current task or None

### Cache

User-specific cache for posts and messages.

```python
from ultima_scraper_api.apis.user_streamliner import Cache

cache = Cache()
```

**Attributes:**

- `posts` (CacheStats): Posts cache
- `messages` (CacheStats): Messages cache

**Methods:**

#### flush

Clear all caches.

```python
cache.flush()
```

### StreamlinedUser

Generic user wrapper with job tracking, caching, and session management.

```python
from ultima_scraper_api.apis.user_streamliner import StreamlinedUser

# Typically created internally by platform APIs
# user is StreamlinedUser instance
user = await authed.get_user("username")
```

**Type Parameters:**

- `T`: Authed session type
- `TAPI`: API type

**Attributes:**

- `username` (str): Username
- `cache` (Cache): User cache
- `jobs` (list[CustomJob]): Active jobs
- `job_whitelist` (list[int | str]): Allowed job types
- `scrape_whitelist` (list[int | str]): Allowed scrape types
- `active` (bool): User active status
- `aliases` (list[str]): Username aliases

**Methods:**

#### get_authed

Get authenticated session.

```python
authed = user.get_authed()
```

**Returns:**

- `T`: Authenticated session

#### get_job

Get job by title.

```python
job = user.get_job("Download Content")
```

**Parameters:**

- `value` (str): Job title

**Returns:**

- `CustomJob | None`: Job if found

#### get_complete_jobs

Get all completed jobs.

```python
completed = user.get_complete_jobs()
print(f"Completed {len(completed)} jobs")
```

**Returns:**

- `list[CustomJob]`: Completed jobs

#### get_incomplete_jobs

Get all incomplete jobs.

```python
pending = user.get_incomplete_jobs()
print(f"{len(pending)} jobs remaining")
```

**Returns:**

- `list[CustomJob]`: Incomplete jobs

#### get_current_job

Get first incomplete job.

```python
current = user.get_current_job()
if current:
    print(f"Working on: {current.title}")
```

**Returns:**

- `CustomJob | None`: Current job or None

#### get_requester

Get HTTP session.

```python
session = user.get_requester()
```

**Returns:**

- `AuthedSession`: HTTP session

#### get_session_manager

Get session manager.

```python
manager = user.get_session_manager()
```

**Returns:**

- `SessionManager`: Session manager

#### get_api

Get API instance.

```python
api = user.get_api()
```

**Returns:**

- `TAPI`: API instance

#### is_active

Check if user is active.

```python
if user.is_active():
    print("User is active")
```

**Returns:**

- `bool`: Active status

#### get_usernames

Get all usernames including aliases (excluding ID-based usernames).

```python
usernames = user.get_usernames(ignore_id=True)
print(f"Known as: {', '.join(usernames)}")
```

**Parameters:**

- `ignore_id` (bool): Exclude ID-based usernames like "u12345". Default: `True`

**Returns:**

- `list[str]`: All usernames

#### get_aliases

Get username aliases.

```python
aliases = user.get_aliases(ignore_id=True)
```

**Parameters:**

- `ignore_id` (bool): Exclude ID-based aliases. Default: `True`

**Returns:**

- `list[str]`: Aliases

#### add_aliases

Add new aliases.

```python
user.add_aliases(["old_username", "nickname"])
```

**Parameters:**

- `aliases` (list[str]): Aliases to add

**Example:**

```python
from ultima_scraper_api import UltimaScraperAPI

api = UltimaScraperAPI()
onlyfans = api.get_site_api("onlyfans")

async with onlyfans.login_context(auth_json) as authed:
    user = await authed.get_user("example_user")
    
    # Create job
    job = Job(title="Download Content")
    job.create_tasks(["Download Posts", "Download Messages", "Download Stories"])
    user.jobs.append(job)
    
    # Process job
    while current_job := user.get_current_job():
        current_task = current_job.get_current_task()
        if current_task:
            print(f"Processing: {current_task.title}")
            # Process task...
            current_task.done = True
        else:
            current_job.done = True
    
    # Get all usernames
    usernames = user.get_usernames()
    print(f"User known as: {', '.join(usernames)}")
```

---

## Helper Utilities

### Identifier Helper

**Location**: `ultima_scraper_api/helpers/identifier_helper.py`

Provides ID parsing, validation, and manipulation utilities (implementation details in source).

### Main Helper

**Location**: `ultima_scraper_api/helpers/main_helper.py`

General utility functions for common operations (implementation details in source).

---

## Complete Examples

### Example 1: Thread Pool Operations

```python
from ultima_scraper_api.apis.api_helper import CustomPool

def process_media(media_item):
    # Simulate processing
    return f"Processed {media_item['id']}"

media_items = [
    {"id": 1, "url": "https://..."},
    {"id": 2, "url": "https://..."},
    {"id": 3, "url": "https://..."}
]

# Use context manager for automatic cleanup
with CustomPool(max_threads=5) as pool:
    results = pool.map(process_media, media_items)
    for result in results:
        print(result)
```

### Example 2: Pagination with URL Generation

```python
from ultima_scraper_api.apis.api_helper import calculate_the_unpredictable

base_url = "https://api.onlyfans.com/api2/v2/posts?offset=0&limit=50"

# Generate 10 paginated URLs
urls, final_offset = calculate_the_unpredictable(
    link=base_url,
    offset=0,
    limit=50,
    multiplier=10,
    depth=1
)

print(f"Generated {len(urls)} URLs")
print(f"Final offset: {final_offset}")

# urls = [
#     "...?offset=0&limit=50",
#     "...?offset=50&limit=50",
#     "...?offset=100&limit=50",
#     ...
# ]
```

### Example 3: Cache Management

```python
from ultima_scraper_api import UltimaScraperAPI

api = UltimaScraperAPI()
onlyfans = api.get_site_api("onlyfans")

async with onlyfans.login_context(auth_json) as authed:
    # Check subscription cache
    if authed.cache.subscriptions.is_released():
        print("Fetching fresh subscriptions...")
        subs = await authed.get_subscriptions()
        authed.cache.subscriptions.activate()
    else:
        print("Using cached subscriptions")
    
    # Check user-specific cache
    user = await authed.get_user("username")
    user_cache = authed.cache.users(user.id)
    
    if user_cache.is_released():
        print("Fetching fresh user data...")
        # Fetch data
        user_cache.activate()
    else:
        print("Using cached user data")
```

### Example 4: Job Tracking

```python
from ultima_scraper_api import UltimaScraperAPI
from ultima_scraper_api.apis.user_streamliner import Job

api = UltimaScraperAPI()
onlyfans = api.get_site_api("onlyfans")

async with onlyfans.login_context(auth_json) as authed:
    user = await authed.get_user("username")
    
    # Create scraping job
    job = Job(title="Full User Scrape")
    job.create_tasks([
        "Download Timeline Posts",
        "Download Archived Posts",
        "Download Messages",
        "Download Stories"
    ])
    user.jobs.append(job)
    
    # Process job with progress tracking
    while current_job := user.get_current_job():
        current_task = current_job.get_current_task()
        
        if current_task:
            print(f"Working on: {current_task.title}")
            
            if "Posts" in current_task.title:
                posts = await user.get_posts()
                current_task.max = len(posts)
                for i, post in enumerate(posts):
                    # Process post
                    current_task.advance(1)
                    print(f"Progress: {current_task.min}/{current_task.max}")
            
            current_task.done = True
        else:
            current_job.done = True
    
    print("All jobs complete!")
```

### Example 5: Error Handling and Filtering

```python
from ultima_scraper_api.apis.api_helper import remove_errors, handle_error_details

# Fetch data that may contain errors
api_responses = [
    {"id": 1, "name": "User1"},
    {"error": {"message": "Not found"}},
    {"id": 2, "name": "User2"},
    {"error": {"message": "Forbidden"}}
]

# Filter out errors
cleaned = await remove_errors(api_responses)
print(f"Got {len(cleaned)} valid responses")
# Output: Got 2 valid responses

# Advanced error handling
results = await handle_error_details(
    item=api_responses,
    remove_errors_status=True,
    api_type=authed
)
```

### Example 6: Multi-Platform Streamlining

```python
from ultima_scraper_api import UltimaScraperAPI, UltimaScraperAPIConfig
from ultima_scraper_api.apis.api_streamliner import StreamlinedAPI

api = UltimaScraperAPI()
config = UltimaScraperAPIConfig()

# OnlyFans streamliner
onlyfans = api.get_site_api("onlyfans")
of_streamliner = StreamlinedAPI(api=onlyfans, config=config)

async with onlyfans.login_context(of_auth) as of_authed:
    of_streamliner.add_auth(of_authed)
    
    if of_streamliner.has_active_auths():
        print("OnlyFans: Active")
        site_settings = of_streamliner.get_site_settings()
        print(f"Browser: {site_settings.browser}")

# Fansly streamliner
fansly = api.get_site_api("fansly")
fn_streamliner = StreamlinedAPI(api=fansly, config=config)

async with fansly.login_context(fn_auth) as fn_authed:
    fn_streamliner.add_auth(fn_authed)
    
    if fn_streamliner.has_active_auths():
        print("Fansly: Active")

# Cleanup all
await of_streamliner.close_pools()
await fn_streamliner.close_pools()
```

---

## See Also

### Internal Documentation

- **[OnlyFans API Reference](onlyfans.md)** - Complete OnlyFans API
- **[Fansly API Reference](fansly.md)** - Fansly API (WIP)
- **[LoyalFans API Reference](loyalfans.md)** - LoyalFans API (early development)
- **[Working with APIs](../user-guide/working-with-apis.md)** - API usage patterns
- **[Session Management](../user-guide/session-management.md)** - Session handling
- **[Architecture](../development/architecture.md)** - System architecture

### External Resources

- **[Python Multiprocessing](https://docs.python.org/3/library/multiprocessing.html)** - Thread pool documentation
- **[aiohttp](https://docs.aiohttp.org/)** - Async HTTP client
- **[mergedeep](https://github.com/clarketm/mergedeep)** - Dictionary merging

---

**Last Updated**: October 2024 | **Version**: 2.2.46
