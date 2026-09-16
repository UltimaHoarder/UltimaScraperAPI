from __future__ import annotations

import asyncio
import logging
import ssl
from contextlib import aclosing
from itertools import repeat
from random import randint
from typing import TYPE_CHECKING, Any, Literal

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
from ultima_scraper_core.concurrency import map_unordered

logger = logging.getLogger(__name__)

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


async def consume_response_json(response: ClientResponse) -> Any:
    """Transfer JSON already validated by request(), or decode an external response.

    The response owns this value only until its consumer takes it. No process-wide
    cache or altered ClientResponse.json contract is involved.
    """
    value = vars(response).pop("_ultima_validated_json", _JSON_UNSET)
    return await response.json() if value is _JSON_UNSET else value


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
        self.current_proxy: ProxyInfo | None = None
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

    def create_client_session(
        self, test_proxies: bool = False, proxy: ProxyInfo | None = None
    ) -> ClientSession:
        limit = 0
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
        route_key = self.get_route_key()
        retries = 0
        max_attempts = max(1, int(getattr(session_manager, "max_attempts", 10) or 1))
        backoff_seconds = 1.0
        max_backoff_seconds = 30.0
        while True:
            is_limited = (
                session_manager.is_route_rate_limited(route_key)
                if hasattr(session_manager, "is_route_rate_limited")
                else getattr(session_manager, "rate_limit_check", False)
            )
            if is_limited:
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
                        if hasattr(session_manager, "mark_route_rate_limited"):
                            session_manager.mark_route_rate_limited(
                                route_key, proxy=self.get_current_proxy_info()
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
        self.time2sleep = 5
        self.rate_limit_checker_active = False
        self._rate_limit_task: asyncio.Task[None] | None = None

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
        self, route_key: str, proxy: ProxyInfo | None = None
    ) -> None:
        self._route_rate_limited[route_key] = True
        if proxy is not None:
            self._route_proxies[route_key] = proxy
        self.start_route_rate_limit_checker(route_key, proxy=proxy)

    def created_authed_session(
        self, authenticator: ultima_scraper_api.authenticator_types
    ):
        return AuthedSession(authenticator, self)

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

    async def check_route_rate_limit(
        self, route_key: str = "__direct__", proxy: ProxyInfo | None = None
    ) -> None:
        logger.info("Rate limit checker started for route %s", route_key)
        timeout = aiohttp.ClientTimeout(
            total=None, connect=10, sock_connect=10, sock_read=60
        )
        ssl_context = ssl.create_default_context()
        ssl_context.post_handshake_auth = True

        resolved_proxy = proxy or self._route_proxies.get(route_key)
        if resolved_proxy is None and route_key != "__direct__":
            try:
                resolved_proxy = ProxyInfo(*python_socks.parse_proxy_url(route_key))
            except Exception:
                resolved_proxy = None

        connector = (
            self.proxy_manager.create_connection(resolved_proxy, ssl=ssl_context)
            if resolved_proxy
            else aiohttp.TCPConnector(ssl=ssl_context)
        )
        sleep_interval = max(int(getattr(self, "time2sleep", 5) or 5), 5)
        rate_limit_count = 0
        try:
            async with ClientSession(connector=connector, timeout=timeout) as probe:
                while self.is_route_rate_limited(route_key) and not self.kill:
                    rate_limit_count += 1
                    try:
                        async with probe.get(
                            "https://onlyfans.com/api2/v2/init"
                        ) as response:
                            status = response.status
                        if status != 429:
                            logger.info(
                                "Rate limit check passed for route %s (status=%d, after %d checks) — resuming requests",
                                route_key,
                                status,
                                rate_limit_count,
                            )
                            self._route_rate_limited[route_key] = False
                            break
                        logger.warning(
                            "Rate limit checker for route %s: still rate-limited (429), check %d, sleeping %ds",
                            route_key,
                            rate_limit_count,
                            sleep_interval,
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
