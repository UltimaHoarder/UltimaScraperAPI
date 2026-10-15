from __future__ import annotations

import asyncio
import logging
import math
import os
import ssl
import time
import weakref
from contextlib import AsyncExitStack, aclosing
from email.utils import parsedate_to_datetime
from itertools import repeat
from contextvars import ContextVar
from random import randint, random
from typing import TYPE_CHECKING, Any, Literal

import aiohttp
import python_socks
import requests
from aiohttp import ClientResponse, ClientSession, RequestInfo
from aiohttp.client_exceptions import (
    ClientOSError,
    ClientPayloadError,
    ClientResponseError,
    ContentTypeError,
    ServerDisconnectedError,
    ServerTimeoutError,
)
from aiohttp_socks import ProxyConnectionError, ProxyConnector, ProxyInfo
from aiohttp_socks import ProxyError as SocksProxyError
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

import ultima_scraper_api
import ultima_scraper_api.apis.api_helper as api_helper
from ultima_scraper_api.config import Proxy
from ultima_scraper_api.helpers.concurrency import map_unordered

logger = logging.getLogger(__name__)

DEFAULT_GUEST_CONNECT_TIMEOUT = 1.5
DEFAULT_GUEST_SOCK_CONNECT_TIMEOUT = 3.0
DEFAULT_GUEST_SOCK_READ_TIMEOUT = 5.0
DEFAULT_GUEST_TOTAL_TIMEOUT = 6.0

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


_JSON_UNSET = object()


# A malformed or hostile Retry-After (an HTTP date months away) must not bench
# a route indefinitely; longer upstream delays are re-probed after this bound.
MAX_RETRY_AFTER_SECONDS = 3600.0


def _retry_after_seconds(value: str | None) -> float:
    """Interpret upstream delay without reducing it to our polling interval."""
    if value is None:
        return 0.0
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            return 0.0
    return min(max(0.0, delay), MAX_RETRY_AFTER_SECONDS) if math.isfinite(delay) else 0.0


async def consume_response_json(response: ClientResponse) -> Any:
    """Transfer JSON already validated by request(), or decode an external response.

    The response owns this value only until its consumer takes it. No process-wide
    cache or altered ClientResponse.json contract is involved.
    """
    value = vars(response).pop("_ultima_validated_json", _JSON_UNSET)
    return await response.json() if value is _JSON_UNSET else value


# OnlyFans accepts about 38 guest requests per second per IP and answers the
# excess with HTTP 429 and Retry-After: 0 (measured 2026-10-11). Workers pace
# every guest request per route below that cap; a 429 that still slips through
# is retried on the same route after a short backoff rather than benching the
# session. GUEST_429_RETRIES bounds those retries per request.
GUEST_429_RETRIES = 2
GUEST_429_BACKOFF_SECONDS = 0.2


# Each worker's bucket holds half a second of its share, so requests that
# arrive in clumps after a quiet moment are not spaced out below the average.
GUEST_ROUTE_BURST_SECONDS = 0.5


class _RouteRateLimiter:
    """Token bucket for one route in this process."""

    def __init__(self, rate: float) -> None:
        self.rate = rate
        self.capacity = max(1.0, rate * GUEST_ROUTE_BURST_SECONDS)
        self.tokens = self.capacity
        self.updated: float | None = None
        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        if self.updated is not None:
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    async def acquire(self) -> None:
        # The lock keeps waiters in arrival order; a cancelled waiter takes nothing.
        async with self._lock:
            loop = asyncio.get_running_loop()
            self._refill(loop.time())
            if self.tokens < 1.0:
                await asyncio.sleep((1.0 - self.tokens) / self.rate)
                self._refill(loop.time())
            self.tokens -= 1.0


_GUEST_ROUTE_RATE: float | None = None
# Limiters own an asyncio.Lock, which binds to one event loop. Keep a set per
# loop so a second loop in the same process gets its own instead of failing.
_ROUTE_LIMITERS: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[str, _RouteRateLimiter]
] = weakref.WeakKeyDictionary()
# A lookup may take its route token before its timeout starts; the next guest
# request on that route in the same context then uses it instead of waiting.
_PREPAID_ROUTE: ContextVar[list[str] | None] = ContextVar("prepaid_guest_route", default=None)


def configure_guest_route_rate(rate_per_second: float | None) -> None:
    """Set this process's guest request rate per route; None or <= 0 disables."""
    global _GUEST_ROUTE_RATE
    _GUEST_ROUTE_RATE = rate_per_second if rate_per_second and rate_per_second > 0 else None
    _ROUTE_LIMITERS.clear()


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

    def create_connection(self, proxy: ProxyInfo, ssl: ssl.SSLContext, **kwargs: Any):
        return ProxyConnector(**proxy._asdict(), ssl=ssl, **kwargs)  # type: ignore

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
        *,
        proxy: ProxyInfo | None = None,
        guest_session_key: str | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.semaphore = session_manager.semaphore
        self.auth = auth
        self.headers = headers
        self.guest_session_key = guest_session_key
        self.request_waiters = 0
        self._guest_request_semaphore = (
            asyncio.Semaphore(1) if guest_session_key is not None else None
        )
        self.current_proxy: ProxyInfo | None = None
        self.active_session = self.create_client_session(proxy=proxy)

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

    def get_current_proxy_info(self) -> ProxyInfo | None:
        if self.current_proxy is not None:
            return self.current_proxy
        raw_proxy_url = getattr(
            getattr(self.auth, "auth_details", None), "proxy_url", None
        )
        if raw_proxy_url:
            try:
                self.current_proxy = ProxyInfo(
                    *python_socks.parse_proxy_url(str(raw_proxy_url).strip())
                )
                return self.current_proxy
            except Exception:
                return None
        return None

    def get_route_key(self) -> str:
        proxy_info = self.get_current_proxy_info()
        if proxy_info is not None:
            auth_part = (
                f"{proxy_info.username}:{proxy_info.password}@"
                if getattr(proxy_info, "username", None)
                else ""
            )
            proto = "http"
            if hasattr(proxy_info, "proxy_type"):
                ptype = str(proxy_info.proxy_type).lower()
                if "socks5" in ptype:
                    proto = "socks5"
                elif "socks4" in ptype:
                    proto = "socks4"
                elif "https" in ptype:
                    proto = "https"
            return f"{proto}://{auth_part}{proxy_info.host}:{proxy_info.port}"
        raw_proxy_url = getattr(
            getattr(self.auth, "auth_details", None), "proxy_url", None
        )
        if raw_proxy_url:
            return str(raw_proxy_url).strip()
        return "__direct__"

    def get_rate_limit_key(self) -> str:
        """Keep each bounded visitor's cooldown on its own cookie context."""
        return self.guest_session_key or self.get_route_key()

    def create_client_session(
        self, test_proxies: bool = False, proxy: ProxyInfo | None = None
    ) -> ClientSession:
        limit = 1 if self.guest_session_key is not None else 0
        session_manager = self.get_session_manager()
        proxy_manager = self.get_proxy_manager()
        raw_proxies = session_manager.get_enabled_proxies()
        if test_proxies and raw_proxies:
            proxies = proxy_manager.test_proxies(raw_proxies)
            if not proxies:
                raise Exception("Unable to create session due to invalid proxies")
            proxy_manager.add_proxies(proxies)
            proxy = proxy_manager.get_current_proxy()
        self.current_proxy = proxy
        ssl_context = session_manager.get_ssl_context()
        connector = (
            self.session_manager.proxy_manager.create_connection(
                proxy, ssl=ssl_context,
                **({"limit": limit} if limit else {}),
            )
            if proxy
            else aiohttp.TCPConnector(limit=limit, ssl=ssl_context)
        )
        final_cookies = self.get_cookies()
        is_guest = getattr(self.auth, "guest", False)
        if is_guest:
            timeout = aiohttp.ClientTimeout(
                total=float(
                    os.environ.get(
                        "ULTIMA_GUEST_TOTAL_TIMEOUT", DEFAULT_GUEST_TOTAL_TIMEOUT
                    )
                ),
                connect=float(
                    os.environ.get(
                        "ULTIMA_GUEST_CONNECT_TIMEOUT", DEFAULT_GUEST_CONNECT_TIMEOUT
                    )
                ),
                sock_connect=float(
                    os.environ.get(
                        "ULTIMA_GUEST_SOCK_CONNECT_TIMEOUT",
                        DEFAULT_GUEST_SOCK_CONNECT_TIMEOUT,
                    )
                ),
                sock_read=float(
                    os.environ.get(
                        "ULTIMA_GUEST_SOCK_READ_TIMEOUT", DEFAULT_GUEST_SOCK_READ_TIMEOUT
                    )
                ),
            )
        else:
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

    def create_json_request_headers(self, url: str) -> dict[str, Any]:
        return self.auth.create_request_headers(
            url,
            extra_headers={
                "accept": "application/json, text/plain, */*",
                "Connection": "keep-alive",
            },
        )

    async def acquire_route_rate(self) -> None:
        """Wait for this route's request budget (guest sessions only)."""
        if _GUEST_ROUTE_RATE is None or not getattr(self.auth, "guest", False):
            return
        key = self.get_route_key()
        limiters = _ROUTE_LIMITERS.setdefault(asyncio.get_running_loop(), {})
        limiter = limiters.get(key)
        if limiter is None:
            limiter = limiters[key] = _RouteRateLimiter(_GUEST_ROUTE_RATE)
        await limiter.acquire()

    async def prepay_route_rate(self) -> Any:
        """Take the next request's route token now; reset the result when done."""
        await self.acquire_route_rate()
        return _PREPAID_ROUTE.set([self.get_route_key()])

    def release_prepaid_route_rate(self, token: Any) -> None:
        _PREPAID_ROUTE.reset(token)

    def _take_prepaid_route_rate(self) -> bool:
        held = _PREPAID_ROUTE.get()
        if held and held[0] == self.get_route_key():
            held.clear()  # Shared with the lookup's child task: use it once.
            return True
        return False

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
        args = (url, method, data, json, premade_settings, custom_cookies,
                custom_headers, range_header)
        semaphore = self._guest_request_semaphore
        if semaphore is None:
            return await self._request(*args)
        self.request_waiters += 1
        try:
            async with semaphore:
                return await self._request(*args)
        finally:
            self.request_waiters -= 1

    async def _request(
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
        route_key = self.get_route_key()
        rate_limit_key = self.get_rate_limit_key()
        retries = 0
        is_guest = getattr(self.auth, "guest", False)
        if is_guest:
            env_guest_attempts = os.environ.get("ULTIMA_GUEST_MAX_ATTEMPTS")
            if env_guest_attempts and env_guest_attempts.strip().isdigit():
                max_attempts = int(env_guest_attempts)
            else:
                max_attempts = min(1, int(getattr(session_manager, "max_attempts", 10) or 1))
        else:
            max_attempts = max(1, int(getattr(session_manager, "max_attempts", 10) or 1))
        backoff_seconds = 1.0
        max_backoff_seconds = 30.0
        guest_429_retries = 0
        while True:
            if not self._take_prepaid_route_rate():
                await self.acquire_route_rate()
            is_limited = (
                session_manager.is_route_rate_limited(rate_limit_key)
                if hasattr(session_manager, "is_route_rate_limited")
                else getattr(session_manager, "rate_limit_check", False)
            )
            if is_limited:
                if is_guest:
                    logger.debug(
                        "Route %s is currently rate-limited; failing fast for guest request: %s %s",
                        route_key,
                        method,
                        url,
                    )
                    raise ClientResponseError(
                        request_info=RequestInfo(
                            url=URL(url),
                            method=method,
                            headers=CIMultiDictProxy(CIMultiDict()),
                            real_url=URL(url),
                        ),
                        history=(),
                        status=429,
                        message=f"Route {route_key} is rate-limited",
                    )
                if retries == 0:
                    logger.debug(
                        "Request paused by rate limiter on route %s: %s %s",
                        route_key,
                        method,
                        url,
                    )
                await asyncio.sleep(5)
                continue
            headers = {}
            if premade_settings == "json":
                headers = self.create_json_request_headers(url)
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
            returning_response = False
            try:
                assert result
                if (
                    result.content
                    and result.content_type
                    and "application/json" in result.content_type
                ):
                    vars(result)["_ultima_validated_json"] = await result.json()
                result.raise_for_status()
                returning_response = True
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
                        returning_response = True
                        return result
                    case 416:
                        return None
                    case 429:
                        logger.warning(
                            "HTTP 429 rate-limited on route %s: %s %s",
                            route_key,
                            method,
                            url,
                        )
                        if is_guest:
                            # Retry-After is 0: back off briefly on the same route
                            # instead of benching this session and probing it.
                            if guest_429_retries < GUEST_429_RETRIES:
                                guest_429_retries += 1
                                await asyncio.sleep(
                                    GUEST_429_BACKOFF_SECONDS * (1 + random())
                                )
                                continue
                            raise
                        if hasattr(session_manager, "mark_route_rate_limited"):
                            session_manager.mark_route_rate_limited(
                                rate_limit_key,
                                proxy=self.get_current_proxy_info(),
                                requester=self,
                                probe_url=url if method.upper() == "GET" else None,
                                retry_after=(
                                    _e.headers.get("Retry-After") if _e.headers else None
                                ),
                            )
                        elif getattr(session_manager, "is_rate_limited", None) is None:
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

            finally:
                if not returning_response and result is not None:
                    # Failed/retried requests must release their connection even
                    # when validation, a timeout or cancellation interrupts them.
                    vars(result).pop("_ultima_validated_json", None)
                    result.release()

    async def bulk_requests(self, urls: list[str]) -> list[ClientResponse | None]:
        # This compatibility method returns a complete ordered list; only its
        # admitted requests, not the required result list, can be bounded.
        results: list[ClientResponse | None] = [None] * len(urls)

        async def request_indexed(item):
            index, url = item
            return index, await self.request(url)

        async with aclosing(
            map_unordered(
                request_indexed, enumerate(urls), limit=self.session_manager.max_threads
            )
        ) as completed:
            async for index, response in completed:
                results[index] = response
        return results

    async def json_request(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET",
        payload: dict[str, Any] = {},
    ) -> dict[str, Any]:
        try:
            response = await self.request(url, method, data=payload)
        except Exception as exc:
            error = {
                "code": exc.status if isinstance(exc, ClientResponseError) else 0,
                "message": _format_exception_message(exc),
            }
            if isinstance(exc, (python_socks.ProxyError, SocksProxyError)) and isinstance(
                exc.error_code, int
            ):
                error["proxy_code"] = exc.error_code
            return {"error": error}
        if not response:
            return {}

        if response.status == 200:
            try:
                return await consume_response_json(response)
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
        count = min(len(urls), len(payloads)) if payloads else len(urls)
        results: list[Any] = [None] * count

        async def request_indexed(item):
            index, (url, payload) = item
            return index, await self.json_request(url, payload=payload, method=method)

        arguments = enumerate(zip(urls, payloads if payloads else repeat({})))
        async with aclosing(
            map_unordered(
                request_indexed, arguments, limit=self.session_manager.max_threads
            )
        ) as completed:
            async for index, value in completed:
                results[index] = value
        return results


class SessionManager:
    def __init__(
        self,
        api: ultima_scraper_api.api_types,
        proxies: list[Proxy] = [],
        max_threads: int = -1,
        use_cookies: bool = True,
    ) -> None:
        max_threads = api_helper.calculate_max_threads(max_threads)
        self.semaphore = asyncio.BoundedSemaphore(max_threads)
        self.max_threads = max_threads
        self.max_attempts = 10
        self.kill = False
        self.authed_sessions: list[AuthedSession] = []
        self.proxy_manager = ProxyManager()

        self.api = api
        self.use_cookies: bool = use_cookies
        self.request_count = 0
        self.proxies = proxies
        self.lock = asyncio.Lock()
        self._route_rate_limited: dict[str, bool] = {}
        self._route_rate_limit_tasks: dict[str, asyncio.Task[None]] = {}
        self._route_proxies: dict[str, ProxyInfo | None] = {}
        self._route_rate_limit_until: dict[str, float] = {}
        self._route_rate_limit_probes: dict[str, tuple[AuthedSession, str]] = {}
        self.time2sleep = 5
        self.rate_limit_checker_active = False
        self._rate_limit_task: asyncio.Task[None] | None = None
        self._ssl_context: ssl.SSLContext | None = None

    def get_ssl_context(self) -> ssl.SSLContext:
        """Reuse verified TLS policy across this manager's clients and probes.

        Loading the platform certificate store is synchronous. Repeating it for
        short-lived rate-limit probes blocks every request on the same loop.
        Configure the context once, before any connector starts using it.
        """
        context = self._ssl_context
        if context is None:
            context = ssl.create_default_context()
            context.post_handshake_auth = True
            self._ssl_context = context
        return context

    @property
    def rate_limit_check(self) -> bool:
        return any(self._route_rate_limited.values())

    @rate_limit_check.setter
    def rate_limit_check(self, value: bool) -> None:
        if value:
            self.mark_route_rate_limited("__direct__")
        else:
            for route_key in list(self._route_rate_limited.keys()):
                self._route_rate_limited[route_key] = False

    @property
    def is_rate_limited(self) -> bool | None:
        if any(self._route_rate_limited.values()):
            return True
        return None

    @is_rate_limited.setter
    def is_rate_limited(self, value: bool | None) -> None:
        if value is True:
            self.mark_route_rate_limited("__direct__")
        elif value is None or value is False:
            for route_key in list(self._route_rate_limited.keys()):
                self._route_rate_limited[route_key] = False

    def is_route_rate_limited(self, route_key: str) -> bool:
        return bool(self._route_rate_limited.get(route_key, False))

    def mark_route_rate_limited(
        self,
        route_key: str,
        proxy: ProxyInfo | None = None,
        *,
        requester: AuthedSession | None = None,
        probe_url: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        self._route_rate_limited[route_key] = True
        delay = max(float(self.time2sleep or 5), 5.0, _retry_after_seconds(retry_after))
        self._route_rate_limit_until[route_key] = max(
            self._route_rate_limit_until.get(route_key, 0.0), time.monotonic() + delay
        )
        if requester is not None and probe_url is not None:
            self._route_rate_limit_probes[route_key] = (requester, probe_url)
        if proxy is not None:
            self._route_proxies[route_key] = proxy
        self.start_route_rate_limit_checker(route_key, proxy=proxy)

    def created_authed_session(
        self, authenticator: ultima_scraper_api.authenticator_types
    ):
        return AuthedSession(authenticator, self)

    async def wait_for_route_recovery(self, route_key: str) -> None:
        """Share the checker while leaving cancellation local to each caller."""
        while self.is_route_rate_limited(route_key) and not self.kill:
            task = self.start_route_rate_limit_checker(route_key)
            await asyncio.shield(task)
        if self.kill:
            raise RuntimeError("Session manager is closing")

    def get_proxy(self):
        proxies = self.get_enabled_proxies()
        proxy = proxies[randint(0, len(proxies) - 1)] if proxies else ""
        return proxy

    def get_enabled_proxies(self) -> list[Proxy]:
        return [proxy for proxy in self.proxies if proxy.enabled]

    def start_route_rate_limit_checker(
        self, route_key: str = "__direct__", proxy: ProxyInfo | None = None
    ) -> asyncio.Task[None]:
        task = self._route_rate_limit_tasks.get(route_key)
        if task is None or task.done():
            resolved_proxy = proxy or self._route_proxies.get(route_key)
            task = asyncio.create_task(
                self.check_route_rate_limit(route_key, proxy=resolved_proxy)
            )
            self._route_rate_limit_tasks[route_key] = task
        return task

    def start_rate_limit_checker(self) -> asyncio.Task[None]:
        if self._rate_limit_task is None or self._rate_limit_task.done():
            self._rate_limit_task = asyncio.create_task(self.check_rate_limit())
        return self._rate_limit_task

    async def stop_rate_limit_checker(self) -> None:
        task = self._rate_limit_task
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._rate_limit_task = None
        route_tasks = [
            t
            for t in self._route_rate_limit_tasks.values()
            if t is not None and not t.done() and t is not asyncio.current_task()
        ]
        for t in route_tasks:
            t.cancel()
        if route_tasks:
            await asyncio.gather(*route_tasks, return_exceptions=True)
        self._route_rate_limit_tasks.clear()
        self._route_rate_limit_probes.clear()
        self._route_rate_limit_until.clear()

    async def check_route_rate_limit(
        self, route_key: str = "__direct__", proxy: ProxyInfo | None = None
    ) -> None:
        logger.info("Rate limit checker started for route %s", route_key)
        timeout = aiohttp.ClientTimeout(
            total=None, connect=10, sock_connect=10, sock_read=60
        )
        ssl_context = self.get_ssl_context()

        resolved_proxy = proxy or self._route_proxies.get(route_key)
        if resolved_proxy is None and route_key != "__direct__":
            try:
                resolved_proxy = ProxyInfo(*python_socks.parse_proxy_url(route_key))
            except Exception:
                resolved_proxy = None

        sleep_interval = max(int(getattr(self, "time2sleep", 5) or 5), 5)
        rate_limit_count = 0
        fallback_probe: ClientSession | None = None
        try:
            async with AsyncExitStack() as stack:
                while self.is_route_rate_limited(route_key) and not self.kill:
                    deadline = self._route_rate_limit_until.get(route_key, 0.0)
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                        if self.kill or not self.is_route_rate_limited(route_key):
                            break
                        if self._route_rate_limit_until.get(route_key, 0.0) > deadline:
                            continue
                    rate_limit_count += 1
                    try:
                        target = self._route_rate_limit_probes.get(route_key)
                        probe_url = (
                            target[1] if target else "https://onlyfans.com/api2/v2/init"
                        )
                        headers = (
                            target[0].create_json_request_headers(probe_url)
                            if target else {}
                        )
                        if target is not None:
                            # A fresh anonymous cookie jar can pass while the
                            # requester's existing visitor/session is still
                            # limited. Probe its exact client context, borrowing
                            # ownership so checker cancellation cannot close it.
                            probe = getattr(target[0], "active_session", None)
                            if probe is None or getattr(probe, "closed", False):
                                raise RuntimeError("Rate-limit requester is closed")
                        else:
                            if fallback_probe is None:
                                connector = (
                                    self.proxy_manager.create_connection(
                                        resolved_proxy, ssl=ssl_context
                                    )
                                    if resolved_proxy
                                    else aiohttp.TCPConnector(ssl=ssl_context)
                                )
                                fallback_probe = await stack.enter_async_context(
                                    ClientSession(connector=connector, timeout=timeout)
                                )
                            probe = fallback_probe
                        async with probe.get(probe_url, headers=headers) as response:
                            status = response.status
                            retry_after = (
                                response.headers.get("Retry-After")
                                if hasattr(response, "headers") else None
                            )
                        if 200 <= status < 300 or (target is not None and status == 404):
                            logger.info(
                                "Rate limit check passed for route %s (status=%d, after %d checks) — resuming requests",
                                route_key,
                                status,
                                rate_limit_count,
                            )
                            self._route_rate_limited[route_key] = False
                            break
                        logger.warning(
                            "Rate limit checker for route %s: inconclusive response (%d), check %d, sleeping %ds",
                            route_key,
                            status,
                            rate_limit_count,
                            sleep_interval,
                        )
                        self._route_rate_limit_until[route_key] = max(
                            self._route_rate_limit_until.get(route_key, 0.0),
                            time.monotonic()
                            + max(sleep_interval, _retry_after_seconds(retry_after)),
                        )
                    except Exception as exc:
                        logger.warning(
                            "Rate limit checker error for route %s (check %d): %s",
                            route_key,
                            rate_limit_count,
                            _format_exception_message(exc),
                        )
                    await asyncio.sleep(sleep_interval)
        finally:
            self._route_rate_limit_tasks.pop(route_key, None)
            self._route_rate_limit_probes.pop(route_key, None)
            self._route_rate_limit_until.pop(route_key, None)

    async def check_rate_limit(self):
        if self.rate_limit_checker_active:
            return
        self.rate_limit_checker_active = True
        owner = asyncio.current_task()
        self._rate_limit_task = owner
        logger.info("Rate limit checker started")
        try:
            while not self.kill:
                if self._route_rate_limited.get("__direct__", False):
                    task = self.start_route_rate_limit_checker("__direct__")
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        pass
                await asyncio.sleep(5)
        finally:
            self.rate_limit_checker_active = False
            if self._rate_limit_task is owner:
                self._rate_limit_task = None
