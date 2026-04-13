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


def _format_exception_message(error: BaseException) -> str:
    detail = str(error).strip()
    if detail:
        return f"{type(error).__name__}: {detail}"
    return type(error).__name__


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
        comprehensive error recovery. The method retries transient failures up to
        ``session_manager.max_attempts`` and handles rate limiting by pausing
        subsequent requests.
        """
        session_manager = self.get_session_manager()
        retries = 0
        max_attempts = max(1, int(getattr(session_manager, "max_attempts", 10) or 1))
        backoff_seconds = 1.0
        max_backoff_seconds = 30.0
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
                if retries >= max_attempts:
                    logger.error(
                        "Request timeout after %d/%d attempts: %s %s — %s",
                        retries,
                        max_attempts,
                        method,
                        url,
                        _format_exception_message(_e),
                    )
                    raise
                logger.warning(
                    "Request timeout (attempt %d/%d): %s %s — %s; retrying in %.1fs",
                    retries,
                    max_attempts,
                    method,
                    url,
                    _format_exception_message(_e),
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                continue
            except EXCEPTION_TEMPLATE as _e:
                retries += 1
                if retries >= max_attempts:
                    logger.error(
                        "Transient error after %d/%d attempts: %s %s — %s",
                        retries,
                        max_attempts,
                        method,
                        url,
                        _format_exception_message(_e),
                    )
                    raise
                logger.warning(
                    "Transient error (attempt %d/%d): %s %s — %s; retrying in %.1fs",
                    retries,
                    max_attempts,
                    method,
                    url,
                    _format_exception_message(_e),
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                continue
            except Exception as _e:
                retries += 1
                if retries >= max_attempts:
                    logger.error(
                        "Unexpected error after %d/%d attempts: %s %s — %s",
                        retries,
                        max_attempts,
                        method,
                        url,
                        _format_exception_message(_e),
                    )
                    raise
                logger.warning(
                    "Unexpected error (attempt %d/%d): %s %s — %s; retrying in %.1fs",
                    retries,
                    max_attempts,
                    method,
                    url,
                    _format_exception_message(_e),
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
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
                retries += 1
                if retries >= max_attempts:
                    logger.error(
                        "Response processing error after %d/%d attempts: %s %s — %s",
                        retries,
                        max_attempts,
                        method,
                        url,
                        _format_exception_message(_e),
                    )
                    raise
                logger.warning(
                    "Response processing error (attempt %d/%d): %s %s — %s; retrying in %.1fs",
                    retries,
                    max_attempts,
                    method,
                    url,
                    _format_exception_message(_e),
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                continue
            except ClientResponseError as _e:
                match _e.status:
                    case 400 | 401 | 403 | 404:
                        assert result
                        return result
                    case 416:
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
                        if retries >= max_attempts:
                            logger.error(
                                "Server error %d after %d/%d attempts: %s %s",
                                _e.status,
                                retries,
                                max_attempts,
                                method,
                                url,
                            )
                            raise
                        logger.warning(
                            "Server error %d (attempt %d/%d): %s %s — retrying in %.1fs",
                            _e.status,
                            retries,
                            max_attempts,
                            method,
                            url,
                            backoff_seconds,
                        )
                        await asyncio.sleep(backoff_seconds)
                        backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                        continue
                    case _:
                        raise Exception(
                            f"Infinite Loop Detected for unhandled status error: {_e.status}"
                        )
            except Exception as _e:
                retries += 1
                if retries >= max_attempts:
                    logger.error(
                        "Unhandled response error after %d/%d attempts: %s %s — %s",
                        retries,
                        max_attempts,
                        method,
                        url,
                        _format_exception_message(_e),
                    )
                    raise
                logger.warning(
                    "Unhandled response error (attempt %d/%d): %s %s — %s; retrying in %.1fs",
                    retries,
                    max_attempts,
                    method,
                    url,
                    _format_exception_message(_e),
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
                continue

    async def bulk_requests(self, urls: list[str]) -> list[ClientResponse | None]:
        return await asyncio.gather(*[self.request(url) for url in urls])

    async def json_request(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET",
        payload: dict[str, Any] = {},
    ) -> dict[str, Any]:
        try:
            response = await self.request(url, method, data=payload)
        except Exception as exc:
            return {
                "error": {
                    "code": 0,
                    "message": _format_exception_message(exc),
                }
            }
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
        self.proxies = proxies
        self.lock = self.lock = asyncio.Lock()
        self.rate_limit_check = False
        self.is_rate_limited = None
        self.time2sleep = 0
        self.rate_limit_checker_active = False

    def created_authed_session(
        self, authenticator: ultima_scraper_api.authenticator_types
    ):
        return AuthedSession(authenticator, self)

    def get_proxy(self):
        proxies = self.proxies
        proxy = self.proxies[randint(0, len(proxies) - 1)] if proxies else ""
        return proxy

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
