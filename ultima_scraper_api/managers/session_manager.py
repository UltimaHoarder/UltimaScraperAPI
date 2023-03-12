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
        self.kill = False
        self.headers = headers
        self.proxies: list[str] = proxies
        global_settings = auth.get_api().get_global_settings()
        dynamic_rules_link = (
            global_settings.dynamic_rules_link if global_settings else ""
        )
        dr_link = dynamic_rules_link
        dynamic_rules = requests.get(dr_link).json()  # type: ignore
        self.dynamic_rules = dynamic_rules
        self.auth = auth
        self.use_cookies: bool = use_cookies
        self.active_session = self.create_client_session()

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
            read_timeout=None,
        )
        return client_session

    def get_proxy(self) -> str:
        proxies = self.proxies
        proxy = self.proxies[randint(0, len(proxies) - 1)] if proxies else ""
        return proxy

    async def request(self, link: str, premade_settings: str = "json"):

        while True:
            try:
                headers = {}
                if premade_settings == "json":
                    headers = await self.session_rules(link)
                    headers["accept"] = "application/json, text/plain, */*"
                    headers["Connection"] = "keep-alive"
                result = await self.active_session.get(link, headers=headers)
                return result
            except (
                ClientPayloadError,
                ContentTypeError,
                ClientOSError,
                ServerDisconnectedError,
                ProxyConnectionError,
                ConnectionResetError,
            ) as _exception:
                continue

    async def bulk_requests(self, links: list[str]) -> list[ClientResponse | None]:
        return await asyncio.gather(*[self.request(link) for link in links])

    async def json_request(
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
            self.auth.auth_details, onlyfans_classes.extras.auth_details
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
        elif "https://apiv3.fansly.com" in link and isinstance(
            self.auth.auth_details, fansly_classes.extras.auth_details
        ):
            headers["authorization"] = self.auth.auth_details.authorization
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
