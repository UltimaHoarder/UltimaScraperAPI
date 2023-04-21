from __future__ import annotations

import asyncio
import hashlib
import json
import random
import string
import time
from random import randint
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiohttp
import python_socks
import requests
from aiohttp import ClientResponse, ClientSession
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientOSError,
    ClientPayloadError,
    ClientResponseError,
    ContentTypeError,
    ServerDisconnectedError,
)
from aiohttp_socks import (
    ChainProxyConnector,
    ProxyConnectionError,
    ProxyError,
    ProxyInfo,
)

import ultima_scraper_api
import ultima_scraper_api.apis.api_helper as api_helper

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


class SessionManager:
    def __init__(
        self,
        auth: auth_types,
        headers: dict[str, Any] = {},
        proxies: list[str] = [],
        max_threads: int = -1,
        use_cookies: bool = True,
    ) -> None:
        max_threads = api_helper.calculate_max_threads(max_threads)
        self.semaphore = asyncio.BoundedSemaphore(max_threads)
        self.max_threads = max_threads
        self.max_attempts = 10
        self.kill = False
        self.headers = headers
        self.proxies: list[str] = proxies
        global_settings = auth.api.get_global_settings()
        dynamic_rules_link = (
            global_settings.dynamic_rules_link if global_settings else ""
        )
        dr_link = dynamic_rules_link
        dynamic_rules = requests.get(dr_link).json()  # type: ignore
        self.dynamic_rules = dynamic_rules
        self.auth = auth
        self.use_cookies: bool = use_cookies
        self.active_session = self.create_client_session()
        self.request_count = 0
        # self.last_request_time: float | None = None
        # self.rate_limit_wait_minutes = 6
        self.rate_limit_check = False
        self.is_rate_limited = None
        self.time2sleep = 0
        asyncio.create_task(self.check_rate_limit())

    def get_cookies(self):

        import ultima_scraper_api.apis.fansly.classes as fansly_classes

        if isinstance(self.auth, fansly_classes.auth_model.create_auth):
            final_cookies: dict[str, Any] = {}
        else:
            final_cookies = self.auth.auth_details.cookie.format()
        return final_cookies

    def test_proxies(self, proxies: list[str] = []):

        final_proxies: list[str] = []
        proxies = proxies if proxies else self.proxies
        for proxy in proxies:
            url = "https://checkip.amazonaws.com"
            temp_proxies = {"https": proxy}
            try:
                resp = requests.get(url, proxies=temp_proxies)
                ip = resp.text
                ip = ip.strip()
                final_proxies.append(proxy)
            except Exception as _e:
                continue
        return final_proxies

    def create_client_session(self, test_proxies: bool = True):
        limit = 0
        if test_proxies and self.proxies:
            self.proxies = self.test_proxies()
            if not self.proxies:
                raise Exception("Unable to create session due to invalid proxies")
        proxies = [
            ProxyInfo(*python_socks.parse_proxy_url(proxy)) for proxy in self.proxies  # type: ignore
        ]

        connector = (
            ChainProxyConnector(proxies, limit=limit)
            if self.proxies
            else aiohttp.TCPConnector(limit=limit)
        )
        final_cookies = self.get_cookies()
        # Had to remove final_cookies and cookies=final_cookies due to it conflicting with headers
        client_session = ClientSession(
            connector=connector,
            cookies=final_cookies,
        )
        return client_session

    def get_proxy(self) -> str:
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
        lock = asyncio.Lock()
        while True:
            rate_limit_count = 1
            while self.rate_limit_check:
                async with lock:
                    try:
                        url = "https://onlyfans.com/api2/v2/init"
                        headers = await self.session_rules(url)
                        headers["accept"] = "application/json, text/plain, */*"
                        headers["Connection"] = "keep-alive"

                        result = await self.active_session.get(url, headers=headers)
                        result.raise_for_status()
                        self.rate_limit_check = False
                        self.is_rate_limited = None
                        break
                    except ClientResponseError as _e:
                        if _e.status == 429:
                            # Still rate limited, wait 5 seconds and retry
                            self.is_rate_limited = True
                            rate_limit_count += 1
                    except Exception as _e:
                        pass
                await asyncio.sleep(self.time2sleep)
            await asyncio.sleep(5)

    async def request(self, url: str, premade_settings: str = "json"):
        while True:
            if self.rate_limit_check:
                await asyncio.sleep(5)
                continue
            headers = {}
            if premade_settings == "json":
                headers = await self.session_rules(url)
                headers["accept"] = "application/json, text/plain, */*"
                headers["Connection"] = "keep-alive"
            # await self.limit_rate()
            try:
                result = await self.active_session.get(url, headers=headers)
            except EXCEPTION_TEMPLATE as _e:
                continue
            except Exception as _e:
                continue
            try:
                result.raise_for_status()
                return result
            except EXCEPTION_TEMPLATE as _e:
                # Can retry
                continue
            except ClientResponseError as _e:
                match _e.status:
                    case 403 | 404:
                        return result
                    case 429:
                        if self.is_rate_limited is None:
                            self.rate_limit_check = True
                        continue
                    case 500 | 503 | 504:
                        continue
                    case _:
                        raise Exception(
                            f"Infinite Loop Detected for unhandled status error: {_e.status}"
                        )
            except Exception as _e:
                pass

    async def bulk_requests(self, urls: list[str]) -> list[ClientResponse | None]:
        return await asyncio.gather(*[self.request(url) for url in urls])

    async def json_request(self, url: str):
        response = await self.request(url)
        json_resp = await response.json()
        return json_resp

    async def bulk_json_requests(self, urls: list[str]):
        return await asyncio.gather(*[self.json_request(url) for url in urls])

    async def json_request_2(
        self,
        link: str,
        session: ClientSession | None = None,
        method: str = "GET",
        stream: bool = False,
        json_format: bool = True,
        payload: dict[str, str | bool] | str = {},
        _handle_error_details: bool = True,
    ) -> Any:
        import ultima_scraper_api.apis.fansly.classes as fansly_classes
        import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

        async with self.semaphore:
            headers = {}
            custom_session = False
            if not session:
                custom_session = True
                session = self.create_client_session()
            headers = await self.session_rules(link)
            headers["accept"] = "application/json, text/plain, */*"
            headers["Connection"] = "keep-alive"
            if isinstance(payload, str):
                temp_payload = payload.encode()
            else:
                temp_payload = payload.copy()

            request_method = None
            result = None
            if method == "HEAD":
                request_method = session.head
            elif method == "GET":
                request_method = session.get
            elif method == "POST":
                request_method = session.post
                headers["content-type"] = "application/json"
                if isinstance(payload, str):
                    temp_payload = payload.encode()
                else:
                    temp_payload = json.dumps(payload)
            elif method == "DELETE":
                request_method = session.delete
            else:
                return None
            while True:
                try:
                    response = await request_method(
                        link, headers=headers, data=temp_payload
                    )
                    if method == "HEAD":
                        result = response
                    else:
                        if json_format and not stream:
                            # qwsd = list(response.request_info.headers.items())
                            result = await response.json()
                            if "error" in result:

                                extras: dict[str, Any] = {}
                                extras["auth"] = self.auth
                                extras["link"] = link
                                if isinstance(
                                    self.auth, onlyfans_classes.auth_model.create_auth
                                ):
                                    handle_error = onlyfans_classes.extras.ErrorDetails
                                else:
                                    handle_error = fansly_classes.extras.ErrorDetails

                                result = await handle_error(result).format(extras)
                                if _handle_error_details:
                                    await api_helper.handle_error_details(result)
                        elif stream and not json_format:
                            result = response
                        else:
                            result = await response.read()
                    break
                except (ClientConnectorError, ProxyError):
                    break
                except (
                    ClientPayloadError,
                    ContentTypeError,
                    ClientOSError,
                    ServerDisconnectedError,
                    ProxyConnectionError,
                    ConnectionResetError,
                ) as _exception:
                    continue
                except Exception as _exception:
                    pass
            if custom_session:
                await session.close()
            return result

    async def session_rules(
        self, link: str, signed_headers: dict[str, Any] = {}
    ) -> dict[str, Any]:

        import ultima_scraper_api.apis.fansly.classes as fansly_classes
        import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

        headers: dict[str, Any] = {}
        headers |= self.headers
        if "https://onlyfans.com/api2/v2/" in link and isinstance(
            self.auth.auth_details, onlyfans_classes.extras.AuthDetails
        ):
            dynamic_rules = self.dynamic_rules
            final_cookies = self.auth.auth_details.cookie.convert()
            headers["app-token"] = dynamic_rules["app_token"]
            headers["cookie"] = final_cookies
            if self.auth.guest:
                headers["x-bc"] = "".join(
                    random.choice(string.digits + string.ascii_lowercase)
                    for _ in range(40)
                )
            headers2 = self.create_signed_headers(link)
            headers |= headers2
            # t2s does not set for cdn links yet
            self.time2sleep = 5
        elif "https://apiv3.fansly.com" in link and isinstance(
            self.auth.auth_details, fansly_classes.extras.AuthDetails
        ):
            headers["authorization"] = self.auth.auth_details.authorization
            self.is_rate_limited = False
        return headers

    def create_signed_headers(
        self, link: str, auth_id: int = 0, time_: int | None = None
    ):
        # Users: 300000 | Creators: 301000
        headers: dict[str, Any] = {}
        final_time = str(int(round(time.time()))) if not time_ else str(time_)
        path = urlparse(link).path
        query = urlparse(link).query
        if query:
            auth_id = self.auth.id if self.auth.id else auth_id
            headers["user-id"] = str(auth_id)
        path = path if not query else f"{path}?{query}"
        dynamic_rules = self.dynamic_rules
        a = [dynamic_rules["static_param"], final_time, path, str(auth_id)]
        msg = "\n".join(a)
        message = msg.encode("utf-8")
        hash_object = hashlib.sha1(message)
        sha_1_sign = hash_object.hexdigest()
        sha_1_b = sha_1_sign.encode("ascii")
        checksum = (
            sum([sha_1_b[number] for number in dynamic_rules["checksum_indexes"]])
            + dynamic_rules["checksum_constant"]
        )
        headers["sign"] = dynamic_rules["format"].format(sha_1_sign, abs(checksum))
        headers["time"] = final_time
        return headers
