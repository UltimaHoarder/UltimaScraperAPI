from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import ssl
import string
import time
from random import randint
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

import aiohttp
import python_socks
import requests
from aiohttp import ClientResponse, ClientSession
from aiohttp.client_exceptions import (
    ClientOSError,
    ClientPayloadError,
    ClientResponseError,
    ContentTypeError,
    ServerDisconnectedError,
    ServerTimeoutError,
)
from aiohttp_socks import ProxyConnectionError, ProxyConnector, ProxyInfo

import ultima_scraper_api
import ultima_scraper_api.apis.api_helper as api_helper
from ultima_scraper_api.config import Proxy

if TYPE_CHECKING:
    auth_types = ultima_scraper_api.auth_types
EXCEPTION_TEMPLATE = (
    ClientPayloadError,
    ContentTypeError,
    ClientOSError,
    ServerDisconnectedError,
    ProxyConnectionError,
    ConnectionResetError,
    asyncio.TimeoutError,
)


class ProxyManager:
    def __init__(self) -> None:
        self.proxies: list[ProxyInfo] = []
        self.current_proxy_index = 0

    def test_proxies(self, proxies: list[Proxy] = []):
        final_proxies: list[Proxy] = []

        session = requests.Session()
        for proxy in proxies:
            url = "https://checkip.amazonaws.com"
            temp_proxies = {"https": proxy.url}
            try:
                final_proxies.append(proxy)
                return final_proxies
                resp = session.get(url, proxies=temp_proxies)
                ip = resp.text
                ip = ip.strip()
                final_proxies.append(proxy)
            except Exception as _e:
                continue
        return final_proxies

    def create_connection(self, proxy: ProxyInfo, ssl: ssl.SSLContext):
        return ProxyConnector(**proxy._asdict(), ssl=ssl)  # type: ignore

    def get_current_proxy(self):
        return self.proxies[self.current_proxy_index]

    def add_proxies(self, proxies: list[Proxy] = []):
        for proxy in proxies:
            self._add_proxy(proxy)

    def _add_proxy(self, proxy: Proxy):
        self.proxies.append(ProxyInfo(*python_socks.parse_proxy_url(proxy.url)))  # type: ignore


class AuthedSession:
    def __init__(
        self,
        auth: ultima_scraper_api.authenticator_types,
        session_manager: SessionManager,
        headers: dict[str, Any] = {},
    ) -> None:
        self.session_manager = session_manager
        self.semaphore = session_manager.semaphore
        self.auth = auth
        self.headers = headers
        self.active_session = self.create_client_session()

    def get_session_manager(self):
        return self.session_manager

    def get_proxy_manager(self):
        return self.session_manager.proxy_manager

    def get_cookies(self):
        from ultima_scraper_api.apis.fansly.authenticator import FanslyAuthenticator
        from ultima_scraper_api.apis.loyalfans.authenticator import (
            LoyalFansAuthenticator,
        )

        if isinstance(self.auth, FanslyAuthenticator):
            final_cookies: dict[str, Any] = {}
        elif isinstance(self.auth, LoyalFansAuthenticator):
            final_cookies: dict[str, Any] = {}

        else:
            final_cookies = self.auth.auth_details.cookie.format()
        return final_cookies

    def create_client_session(
        self, test_proxies: bool = False, proxy: ProxyInfo | None = None
    ) -> ClientSession:
        limit = 0
        session_manager = self.get_session_manager()
        proxy_manager = self.get_proxy_manager()
        raw_proxies = session_manager.proxies
        if test_proxies and raw_proxies:
            proxies = proxy_manager.test_proxies(raw_proxies)
            if not proxies:
                raise Exception("Unable to create session due to invalid proxies")
            proxy_manager.add_proxies(proxies)
            proxy = proxy_manager.get_current_proxy()
        ssl_context = ssl.create_default_context()
        ssl_context.post_handshake_auth = True
        connector = (
            self.session_manager.proxy_manager.create_connection(proxy, ssl=ssl_context)
            if proxy
            else aiohttp.TCPConnector(limit=limit, ssl=ssl_context)
        )
        final_cookies = self.get_cookies()
        # Had to remove final_cookies and cookies=final_cookies due to it conflicting with headers
        # timeout = aiohttp.ClientTimeout(None)
        timeout = aiohttp.ClientTimeout(
            total=None, connect=10, sock_connect=10, sock_read=60
        )
        client_session = ClientSession(
            connector=connector, cookies=final_cookies, timeout=timeout
        )
        return client_session

    async def proxy_switcher(self):
        proxy_manager = self.get_proxy_manager()
        if proxy_manager.proxies:
            proxy_manager.current_proxy_index = (
                proxy_manager.current_proxy_index + 1
            ) % len(proxy_manager.proxies)
            await self.active_session.close()
            self.active_session = self.create_client_session(
                False, proxy_manager.get_current_proxy()
            )

    async def request(
        self,
        url: str,
        method: Literal["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"] = "GET",
        data: Any = {},
        json: Any = {},
        premade_settings: str = "json",
        custom_cookies: str = "",
        custom_headers: dict[str, Any] = {},
        range_header: dict[str, Any] | None = None,
    ) -> ClientResponse | None:
        """
        Make an HTTP request with automatic retry logic and error handling.

        Performs an HTTP request with support for rate limiting, proxy rotation, and
        comprehensive error recovery. The method will retry indefinitely on transient
        failures and handle rate limiting by pausing subsequent requests.

        Args:
            url: The URL to request.
            method: HTTP method to use. Defaults to "GET".
            data: Form data to send with POST/PATCH requests.
            json: JSON payload to send with POST/PATCH requests.
            premade_settings: Header preset to use ("json" for JSON content type).
                Defaults to "json".
            custom_cookies: Optional custom cookies to include in the request.
            range_header: Optional range header dict for partial content requests.

        Returns:
            ClientResponse if request succeeded, None if Range (416) error occurred.

        Raises:
            Exception: If an unhandled HTTP status code is returned.

        Note:
            - Automatically retries on transient errors (timeouts, connection errors).
            - Rate limit (429) errors trigger backoff for subsequent requests.
            - HTTP errors 400, 401, 403, 404 are returned immediately without retry.
            - Server errors (500, 502, 503, 504) trigger automatic retry.
        """
        # NOTE: Some apis need data= or json= when posting
        session_manager = self.get_session_manager()
        retries = 0
        while True:
            if session_manager.rate_limit_check:
                if retries == 0:
                    logger.debug("Request paused by rate limiter: %s %s", method, url)
                await asyncio.sleep(5)
                continue
            headers = {}
            if premade_settings == "json":
                headers = self.auth.create_request_headers(
                    url,
                    extra_headers={
                        "accept": "application/json, text/plain, */*",
                        "Connection": "keep-alive",
                    },
                )
            if custom_cookies:
                headers = self.auth.create_request_headers(
                    url, custom_cookies=custom_cookies
                )
            if range_header:
                headers.update(range_header)
            if custom_headers:
                headers.update(custom_headers)

            # await self.limit_rate()
            result = None
            try:
                match method.upper():
                    case "HEAD":
                        result = await self.active_session.head(url, headers=headers)
                    case "GET":
                        result = await self.active_session.get(url, headers=headers)
                    case "POST":
                        if data:
                            result = await self.active_session.post(
                                url, headers=headers, data=data
                            )
                        else:
                            result = await self.active_session.post(
                                url, headers=headers, json=json
                            )
                    case "PATCH":
                        if data:
                            result = await self.active_session.patch(
                                url, headers=headers, data=data
                            )
                        else:
                            result = await self.active_session.patch(
                                url, headers=headers, json=json
                            )
                    case "DELETE":
                        result = await self.active_session.delete(url, headers=headers)
                    case "PUT":
                        if data:
                            result = await self.active_session.put(
                                url, headers=headers, data=data
                            )
                        else:
                            result = await self.active_session.put(
                                url, headers=headers, json=json
                            )
                    case _:
                        raise Exception("Method not found")
            except ServerTimeoutError as _e:
                retries += 1
                logger.warning(
                    "Request timeout (attempt %d): %s %s — %s",
                    retries,
                    method,
                    url,
                    _e,
                )
                if session_manager.is_rate_limited is None:
                    logger.info(
                        "Activating rate limit check due to timeout: %s %s",
                        method,
                        url,
                    )
                    session_manager.rate_limit_check = True
                continue
            except EXCEPTION_TEMPLATE as _e:
                retries += 1
                logger.warning(
                    "Transient error (attempt %d): %s %s — %s: %s",
                    retries,
                    method,
                    url,
                    type(_e).__name__,
                    _e,
                )
                continue
            except Exception as _e:
                retries += 1
                logger.warning(
                    "Unexpected error (attempt %d): %s %s — %s: %s",
                    retries,
                    method,
                    url,
                    type(_e).__name__,
                    _e,
                )
                continue
            try:
                assert result
                if (
                    result.content
                    and result.content_type
                    and "application/json" in result.content_type
                ):
                    await result.json()
                result.raise_for_status()
                return result
            except EXCEPTION_TEMPLATE as _e:
                # Can retry
                retries += 1
                logger.warning(
                    "Response processing error (attempt %d): %s %s — %s: %s",
                    retries,
                    method,
                    url,
                    type(_e).__name__,
                    _e,
                )
                continue
            except ClientResponseError as _e:
                match _e.status:
                    case 400 | 401 | 403 | 404:
                        assert result
                        return result
                    case 416:
                        # Range not satisfiable, return None
                        return None
                    case 429:
                        logger.warning(
                            "HTTP 429 rate-limited: %s %s",
                            method,
                            url,
                        )
                        if session_manager.is_rate_limited is None:
                            session_manager.rate_limit_check = True
                        continue
                    case 500 | 502 | 503 | 504:
                        retries += 1
                        logger.warning(
                            "Server error %d (attempt %d): %s %s",
                            _e.status,
                            retries,
                            method,
                            url,
                        )
                        continue
                    case _:
                        raise Exception(
                            f"Infinite Loop Detected for unhandled status error: {_e.status}"
                        )
            except Exception as _e:
                pass

    async def bulk_requests(self, urls: list[str]) -> list[ClientResponse | None]:
        return await asyncio.gather(*[self.request(url) for url in urls])

    async def json_request(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET",
        payload: dict[str, Any] = {},
    ) -> dict[str, Any]:
        response = await self.request(url, method, data=payload)
        if not response:
            return {}

        if response.status == 200:
            try:
                return await response.json()
            except EXCEPTION_TEMPLATE:
                return {}
        return {
            "error": {
                "code": response.status,
                "message": response.reason,
            }
        }

    async def bulk_json_requests(
        self,
        urls: list[str],
        payloads: list[dict[str, Any]] = [],
        method: Literal["GET", "POST", "PATCH", "DELETE"] = "GET",
    ) -> list[dict[Any, Any]]:
        # If no payloads provided, use empty dicts for each URL
        if not payloads:
            payloads = [{} for _ in urls]
        return await asyncio.gather(
            *[
                self.json_request(url, payload=payload, method=method)
                for url, payload in zip(urls, payloads)
            ]
        )


class SessionManager:
    def __init__(
        self,
        api: ultima_scraper_api.api_types,
        proxies: list[Proxy] = [],
        max_threads: int = -1,
        use_cookies: bool = True,
    ) -> None:
        from ultima_scraper_api.apis.onlyfans.onlyfans import OnlyFansAPI

        max_threads = api_helper.calculate_max_threads(max_threads)
        self.semaphore = asyncio.BoundedSemaphore(max_threads)
        self.max_threads = max_threads
        self.max_attempts = 10
        self.kill = False
        self.authed_sessions: list[AuthedSession] = []
        self.proxy_manager = ProxyManager()

        self.use_cookies: bool = use_cookies
        self.request_count = 0
        # self.last_request_time: float | None = None
        # self.rate_limit_wait_minutes = 6
        self.proxies = proxies
        self.lock = self.lock = asyncio.Lock()
        self.rate_limit_check = False
        self.is_rate_limited = None
        self.time2sleep = 0
        self.rate_limit_checker_active = False
        # asyncio.create_task(self.check_rate_limit())

    def created_authed_session(
        self, authenticator: ultima_scraper_api.authenticator_types
    ):
        return AuthedSession(authenticator, self)

    def get_proxy(self):
        proxies = self.proxies
        proxy = self.proxies[randint(0, len(proxies) - 1)] if proxies else ""
        return proxy

    # async def limit_rate(self):
    #     if self.auth.api.site_name == "OnlyFans":
    #         # [OF] 1,000 requests every 5 minutes
    #         # Can batch  =< 5,000 amount of requests, but will get rate limited and throw 429 error
    #         MAX_REQUEST_LIMIT = 900  # 900 instead of 1,000 to be safe
    #         rate_limit_wait_minutes = self.rate_limit_wait_minutes
    #         RATE_LIMIT_WAIT_TIME = 60 * rate_limit_wait_minutes
    #         if self.request_count >= MAX_REQUEST_LIMIT:
    #             # Wait until 5 minutes have elapsed since last request
    #             if self.last_request_time is not None:
    #                 elapsed_time = time.time() - self.last_request_time
    #                 if elapsed_time < RATE_LIMIT_WAIT_TIME:
    #                     time2sleep = RATE_LIMIT_WAIT_TIME - elapsed_time
    #                     print(time2sleep)
    #                     await asyncio.sleep(time2sleep)
    #             # Reset counter and timer
    #             self.request_count = 0
    #             self.last_request_time = None
    #         self.request_count += 1
    #         if self.last_request_time is None:
    #             self.last_request_time = time.time()

    async def check_rate_limit(self):
        if self.rate_limit_checker_active:
            return
        self.rate_limit_checker_active = True
        logger.info("Rate limit checker started")
        while True:
            rate_limit_count = 1
            async with self.lock:
                while self.rate_limit_check:
                    import requests

                    try:
                        url = "https://onlyfans.com/api2/v2/init"
                        # proxy_manager = self.proxy_manager
                        # if proxy_manager.proxies:
                        #     await proxy_manager.proxy_switcher()
                        #     print(proxy_manager.get_current_proxy().host)

                        result = requests.get(url)
                        if result.status_code == 429:
                            result.raise_for_status()
                        logger.info(
                            "Rate limit check passed (status=%d, after %d checks) — resuming requests",
                            result.status_code,
                            rate_limit_count,
                        )
                        self.rate_limit_check = False
                        self.is_rate_limited = None
                        break
                    except EXCEPTION_TEMPLATE as _e:
                        logger.warning(
                            "Rate limit checker transient error (check %d): %s: %s",
                            rate_limit_count,
                            type(_e).__name__,
                            _e,
                        )
                        continue
                    except requests.HTTPError as _e:
                        if _e.response and _e.response.status_code == 429:
                            # Still rate limited, wait 5 seconds and retry
                            self.is_rate_limited = True
                            rate_limit_count += 1
                            logger.warning(
                                "Rate limit checker: still rate-limited (429), check %d, sleeping %ds",
                                rate_limit_count,
                                self.time2sleep,
                            )
                    except Exception as _e:
                        logger.warning(
                            "Rate limit checker unexpected error (check %d): %s: %s",
                            rate_limit_count,
                            type(_e).__name__,
                            _e,
                        )
                    await asyncio.sleep(self.time2sleep)
                await asyncio.sleep(5)
