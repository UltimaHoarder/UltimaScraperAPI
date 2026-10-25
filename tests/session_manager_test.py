from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.client_exceptions import ClientResponseError

from ultima_scraper_api.managers.session_manager import AuthedSession, SessionManager


class DummyAuth:
    def __init__(self, guest: bool = False) -> None:
        self.guest = guest
        self.auth_details = SimpleNamespace(
            cookie=SimpleNamespace(format=lambda: {}),
            proxy_url=None,
        )

    def create_request_headers(
        self,
        url: str,
        custom_cookies: str = "",
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)
        return headers


class DummySessionManager:
    def __init__(self, max_attempts: int = 3) -> None:
        self.semaphore = asyncio.BoundedSemaphore(1)
        self.max_attempts = max_attempts
        self.proxies: list[str] = []
        self.proxy_manager = SimpleNamespace(proxies=[], current_proxy_index=0)
        self.rate_limit_check = False
        self.is_rate_limited = None
        self.time2sleep = 0


class ProxyTimeoutError(Exception):
    pass


def make_authed_session(
    max_attempts: int = 3, guest: bool = False
) -> AuthedSession:
    auth = DummyAuth(guest=guest)
    with patch.object(
        AuthedSession,
        "create_client_session",
        return_value=SimpleNamespace(),
    ):
        session = AuthedSession(auth, DummySessionManager(max_attempts))
    return session


@pytest.mark.asyncio
async def test_request_stops_retrying_after_max_attempts() -> None:
    session = make_authed_session(max_attempts=3)
    session.active_session.get = AsyncMock(
        side_effect=[
            ProxyTimeoutError("Proxy connection timed out: 10"),
            ProxyTimeoutError("Proxy connection timed out: 10"),
            ProxyTimeoutError("Proxy connection timed out: 10"),
        ]
    )
    sleep_mock = AsyncMock()

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=sleep_mock,
        ),
        pytest.raises(ProxyTimeoutError, match="Proxy connection timed out: 10"),
    ):
        await session.request("https://onlyfans.com/api2/v2/users/me")

    assert session.active_session.get.await_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_json_request_returns_error_payload_when_retries_exhausted() -> None:
    session = make_authed_session(max_attempts=2)
    session.active_session.get = AsyncMock(
        side_effect=[
            ProxyTimeoutError("Proxy connection timed out: 10"),
            ProxyTimeoutError("Proxy connection timed out: 10"),
        ]
    )

    with patch(
        "ultima_scraper_api.managers.session_manager.asyncio.sleep",
        new=AsyncMock(),
    ):
        result = await session.json_request("https://onlyfans.com/api2/v2/users/me")

    assert result == {
        "error": {
            "code": 0,
            "message": "ProxyTimeoutError: Proxy connection timed out: 10",
        }
    }


@pytest.mark.asyncio
async def test_per_route_rate_limiting_isolation() -> None:
    sm = SessionManager(api=None)
    sm.check_route_rate_limit = AsyncMock()

    auth_a = DummyAuth()
    auth_b = DummyAuth()

    with patch.object(
        AuthedSession, "create_client_session", return_value=SimpleNamespace()
    ):
        session_a = AuthedSession(auth_a, sm)
        session_b = AuthedSession(auth_b, sm)

    session_a.get_route_key = lambda: "http://proxy-a:8080"
    session_b.get_route_key = lambda: "http://proxy-b:8080"

    resp_success = SimpleNamespace(
        status=200,
        content=b'{"ok": true}',
        content_type="application/json",
        raise_for_status=lambda: None,
        json=AsyncMock(return_value={"ok": True}),
    )
    err_429 = ClientResponseError(
        request_info=None, history=(), status=429, message="Too Many Requests"
    )

    session_a.active_session.get = AsyncMock(side_effect=[err_429, resp_success])
    session_b.active_session.get = AsyncMock(return_value=resp_success)

    # Initial state: neither route is rate limited
    assert not sm.is_route_rate_limited("http://proxy-a:8080")
    assert not sm.is_route_rate_limited("http://proxy-b:8080")

    # Mark route A rate limited directly
    sm.mark_route_rate_limited("http://proxy-a:8080")
    assert sm.is_route_rate_limited("http://proxy-a:8080") is True
    assert sm.is_route_rate_limited("http://proxy-b:8080") is False

    # Route B executes requests immediately despite Route A being rate limited
    result_b = await session_b.request("https://onlyfans.com/api2/v2/users/me")
    assert result_b is resp_success
    assert session_b.active_session.get.await_count == 1

    # Unblock route A and verify it can complete requests
    sm._route_rate_limited["http://proxy-a:8080"] = False
    result_a = await session_a.request("https://onlyfans.com/api2/v2/users/me")
    assert result_a is resp_success


@pytest.mark.asyncio
async def test_session_manager_backward_compatibility() -> None:
    sm = SessionManager(api=None)
    sm.check_route_rate_limit = AsyncMock()

    assert sm.rate_limit_check is False
    assert sm.is_rate_limited is None

    # Setting rate_limit_check to True marks __direct__ as limited
    sm.rate_limit_check = True
    assert sm.rate_limit_check is True
    assert sm.is_rate_limited is True
    assert sm.is_route_rate_limited("__direct__") is True

    # Setting rate_limit_check to False clears all limits
    sm.rate_limit_check = False
    assert sm.rate_limit_check is False
    assert sm.is_rate_limited is None
    assert sm.is_route_rate_limited("__direct__") is False


@pytest.mark.asyncio
async def test_authed_session_429_triggers_route_mark() -> None:
    from aiohttp import RequestInfo
    from yarl import URL

    sm = SessionManager(api=None)
    sm.check_route_rate_limit = AsyncMock()

    auth = DummyAuth()
    with patch.object(
        AuthedSession, "create_client_session", return_value=SimpleNamespace()
    ):
        session = AuthedSession(auth, sm)

    session.get_route_key = lambda: "http://proxy-x:8080"
    session.get_current_proxy_info = lambda: None

    req_info = RequestInfo(
        url=URL("https://onlyfans.com/api2/v2/users/me"),
        method="GET",
        headers={},
        real_url=URL("https://onlyfans.com/api2/v2/users/me"),
    )
    err_429 = ClientResponseError(
        request_info=req_info, history=(), status=429, message="Too Many Requests"
    )

    def raise_429() -> None:
        raise err_429

    resp_429 = SimpleNamespace(
        status=429,
        content=b"{}",
        content_type="application/json",
        raise_for_status=raise_429,
        json=AsyncMock(return_value={}),
        release=lambda: None,
    )
    resp_success = SimpleNamespace(
        status=200,
        content=b"{}",
        content_type="application/json",
        raise_for_status=lambda: None,
        json=AsyncMock(return_value={}),
    )

    async def fake_sleep(seconds: float) -> None:
        sm._route_rate_limited["http://proxy-x:8080"] = False

    session.active_session.get = AsyncMock(side_effect=[resp_429, resp_success])

    with patch(
        "ultima_scraper_api.managers.session_manager.asyncio.sleep",
        side_effect=fake_sleep,
    ):
        res = await session.request("https://onlyfans.com/api2/v2/users/me")

    assert res is resp_success
    assert session.active_session.get.await_count == 2


def test_route_key_generation() -> None:
    import python_socks
    from aiohttp_socks import ProxyInfo

    sm = SessionManager(api=None)
    auth = DummyAuth()
    with patch.object(
        AuthedSession, "create_client_session", return_value=SimpleNamespace()
    ):
        session = AuthedSession(auth, sm)

    # Without proxy, defaults to "__direct__"
    assert session.get_route_key() == "__direct__"

    # With proxy
    proxy_info = ProxyInfo(
        *python_socks.parse_proxy_url("http://user:pass@192.168.1.1:8080")
    )
    session.current_proxy = proxy_info
    assert session.get_route_key() == "http://user:pass@192.168.1.1:8080"


@pytest.mark.asyncio
async def test_check_route_rate_limit_probe_clears_flag() -> None:
    sm = SessionManager(api=None)
    route = "http://user:pass@127.0.0.1:8080"
    sm._route_rate_limited[route] = True

    resp_429 = SimpleNamespace(status=429)
    resp_200 = SimpleNamespace(status=200)

    class MockAsyncContext:
        def __init__(self, response: Any) -> None:
            self.response = response

        async def __aenter__(self) -> Any:
            return self.response

        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

    probe_get = [
        MockAsyncContext(resp_429),
        MockAsyncContext(resp_200),
    ]

    class MockClientSession:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def get(self, url: str, **kwargs: Any) -> MockAsyncContext:
            return probe_get.pop(0)

        async def __aenter__(self) -> MockClientSession:
            return self

        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.ClientSession",
            new=MockClientSession,
        ),
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=AsyncMock(),
        ),
    ):
        await sm.check_route_rate_limit(route)

    assert sm.is_route_rate_limited(route) is False


@pytest.mark.asyncio
async def test_guest_session_uses_fast_failing_socket_timeout() -> None:
    sm = SessionManager(api=None)
    auth = DummyAuth(guest=True)
    with patch("ultima_scraper_api.managers.session_manager.ClientSession") as mock_cs:
        session = AuthedSession(auth, sm)
        mock_cs.assert_called_once()
        timeout = mock_cs.call_args.kwargs.get("timeout")
        assert timeout is not None
        assert timeout.total == 10.0
        assert timeout.connect == 5.0
        assert timeout.sock_connect == 5.0
        assert timeout.sock_read == 10.0


@pytest.mark.asyncio
async def test_guest_session_respects_configured_lookup_timeout() -> None:
    api = SimpleNamespace(
        config=SimpleNamespace(
            settings=SimpleNamespace(
                network=SimpleNamespace(
                    guest_lookup_timeout=15.0,
                    proxies=[],
                )
            )
        )
    )
    sm = SessionManager(api=api)
    auth = DummyAuth(guest=True)
    with patch("ultima_scraper_api.managers.session_manager.ClientSession") as mock_cs:
        session = AuthedSession(auth, sm)
        mock_cs.assert_called_once()
        timeout = mock_cs.call_args.kwargs.get("timeout")
        assert timeout is not None
        assert timeout.total == 15.0
        assert timeout.connect == 15.0
        assert timeout.sock_connect == 15.0
        assert timeout.sock_read == 15.0


@pytest.mark.asyncio
async def test_guest_session_respects_env_var_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ULTIMA_GUEST_TOTAL_TIMEOUT", "4.0")
    monkeypatch.setenv("ULTIMA_GUEST_CONNECT_TIMEOUT", "2.0")
    monkeypatch.setenv("ULTIMA_GUEST_SOCK_CONNECT_TIMEOUT", "2.0")
    monkeypatch.setenv("ULTIMA_GUEST_SOCK_READ_TIMEOUT", "3.0")

    sm = SessionManager(api=None)
    auth = DummyAuth(guest=True)
    with patch("ultima_scraper_api.managers.session_manager.ClientSession") as mock_cs:
        session = AuthedSession(auth, sm)
        mock_cs.assert_called_once()
        timeout = mock_cs.call_args.kwargs.get("timeout")
        assert timeout is not None
        assert timeout.total == 4.0
        assert timeout.connect == 2.0
        assert timeout.sock_connect == 2.0
        assert timeout.sock_read == 3.0


@pytest.mark.asyncio
async def test_non_guest_session_retains_standard_timeout() -> None:
    sm = SessionManager(api=None)
    auth = DummyAuth(guest=False)
    with patch("ultima_scraper_api.managers.session_manager.ClientSession") as mock_cs:
        session = AuthedSession(auth, sm)
        mock_cs.assert_called_once()
        timeout = mock_cs.call_args.kwargs.get("timeout")
        assert timeout is not None
        assert timeout.total is None
        assert timeout.connect == 10.0
        assert timeout.sock_connect == 10.0
        assert timeout.sock_read == 60.0


@pytest.mark.asyncio
async def test_guest_request_fails_fast_on_dead_proxy() -> None:
    session = make_authed_session(max_attempts=10, guest=True)
    session.active_session.get = AsyncMock(
        side_effect=ProxyTimeoutError("Proxy connection timed out: 3")
    )
    sleep_mock = AsyncMock()

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=sleep_mock,
        ),
        pytest.raises(ProxyTimeoutError, match="Proxy connection timed out: 3"),
    ):
        await session.request("https://onlyfans.com/api2/v2/users/me")

    assert session.active_session.get.await_count == 1
    assert sleep_mock.await_count == 0


@pytest.mark.asyncio
async def test_guest_request_honors_env_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ULTIMA_GUEST_MAX_ATTEMPTS", "2")
    session = make_authed_session(max_attempts=10, guest=True)
    session.active_session.get = AsyncMock(
        side_effect=[
            ProxyTimeoutError("Proxy connection timed out: 3"),
            ProxyTimeoutError("Proxy connection timed out: 3"),
        ]
    )
    sleep_mock = AsyncMock()

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=sleep_mock,
        ),
        pytest.raises(ProxyTimeoutError, match="Proxy connection timed out: 3"),
    ):
        await session.request("https://onlyfans.com/api2/v2/users/me")

    assert session.active_session.get.await_count == 2
    assert sleep_mock.await_count == 1


def _guest_429_response() -> AsyncMock:
    response = AsyncMock()
    response.status = 429
    response.content = b"{}"
    response.content_type = "application/json"
    response.json = AsyncMock(return_value={})
    response.raise_for_status = MagicMock(
        side_effect=ClientResponseError(
            request_info=SimpleNamespace(real_url="https://onlyfans.com/api2/v2/users/me"),
            history=(),
            status=429,
            message="Too Many Requests",
        )
    )
    response.release = MagicMock()
    return response


@pytest.mark.asyncio
async def test_guest_429_benches_the_session_without_retrying_it() -> None:
    from ultima_scraper_api.managers.session_manager import GUEST_SESSION_BENCH_SECONDS

    session = make_authed_session(max_attempts=10, guest=True)
    session.guest_session_key = "guest-abc"
    session.session_manager.mark_route_rate_limited = MagicMock()
    session.active_session.get = AsyncMock(return_value=_guest_429_response())
    sleep_mock = AsyncMock()

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=sleep_mock,
        ),
        pytest.raises(ClientResponseError) as exc_info,
    ):
        await session.request("https://onlyfans.com/api2/v2/users/me")

    assert exc_info.value.status == 429
    # OnlyFans limits each visitor session: the same session cannot succeed
    # until its window clears, so it is benched and the caller moves on.
    assert session.active_session.get.await_count == 1
    assert sleep_mock.await_count == 0
    mark = session.session_manager.mark_route_rate_limited
    mark.assert_called_once()
    assert mark.call_args.args == ("guest-abc",)
    assert mark.call_args.kwargs["min_delay"] == GUEST_SESSION_BENCH_SECONDS
    assert mark.call_args.kwargs["requester"] is session
    assert mark.call_args.kwargs["probe_url"] == "https://onlyfans.com/api2/v2/users/me"


def test_bench_delay_honours_the_guest_minimum() -> None:
    manager = SessionManager.__new__(SessionManager)
    manager.time2sleep = 0
    manager._route_rate_limited, manager._route_rate_limit_until = {}, {}
    manager._route_rate_limit_probes, manager._route_proxies = {}, {}
    manager.start_route_rate_limit_checker = MagicMock()
    with patch("ultima_scraper_api.managers.session_manager.time.monotonic", return_value=100.0):
        manager.mark_route_rate_limited("guest-abc", min_delay=20.0)
        manager.mark_route_rate_limited("route-b")
    assert manager._route_rate_limit_until["guest-abc"] == 120.0
    assert manager._route_rate_limit_until["route-b"] == 105.0


def test_route_rate_cuts_on_429s_and_grows_back_while_clean() -> None:
    from ultima_scraper_api.managers import session_manager as sm

    limiter = sm._RouteRateLimiter(10.0)
    limiter.rate_limited(0.0)
    assert limiter.rate == pytest.approx(10.0 * sm.GUEST_RATE_CUT)
    # A burst of 429s within one interval is one cut.
    limiter.rate_limited(0.5)
    assert limiter.rate == pytest.approx(7.0)
    for second in range(1, 20):
        limiter.rate_limited(float(second))
    assert limiter.rate == pytest.approx(10.0 * sm.GUEST_RATE_MIN_FRACTION)
    assert limiter.capacity >= 1.0 and limiter.tokens <= limiter.capacity
    # No growth during the hold after the last cut, then a linear climb.
    last_cut = 19.0
    limiter.succeeded(last_cut + sm.GUEST_RATE_HOLD_SECONDS - 0.1)
    assert limiter.rate == pytest.approx(1.0)
    limiter.succeeded(last_cut + sm.GUEST_RATE_HOLD_SECONDS + 10)
    assert limiter.rate == pytest.approx(1.0 + 10.0 * sm.GUEST_RATE_GROWTH_PER_SECOND * 10)
    limiter.succeeded(last_cut + sm.GUEST_RATE_HOLD_SECONDS + 1000)
    assert limiter.rate == pytest.approx(10.0)
    # A limiter that never saw a 429 stays at the configured rate.
    fresh = sm._RouteRateLimiter(10.0)
    fresh.succeeded(1000.0)
    assert fresh.rate == 10.0


@pytest.mark.asyncio
async def test_guest_responses_steer_the_route_rate() -> None:
    from ultima_scraper_api.managers import session_manager as sm

    session = make_authed_session(max_attempts=10, guest=True)
    session.session_manager.mark_route_rate_limited = MagicMock()
    ok = AsyncMock()
    ok.status, ok.content, ok.content_type = 200, b"", None
    ok.raise_for_status = MagicMock()
    sm.configure_guest_route_rate(10.0)
    try:
        session.active_session.get = AsyncMock(return_value=_guest_429_response())
        with pytest.raises(ClientResponseError):
            await session.request("https://onlyfans.com/api2/v2/users/1")
        limiter = session._route_limiter()
        assert limiter.rate == pytest.approx(10.0 * sm.GUEST_RATE_CUT)
        limiter._last_cut -= sm.GUEST_RATE_HOLD_SECONDS + 10  # the hold has passed
        session.active_session.get = AsyncMock(return_value=ok)
        await session.request("https://onlyfans.com/api2/v2/users/2")
        assert limiter.rate > 10.0 * sm.GUEST_RATE_CUT
    finally:
        sm.configure_guest_route_rate(None)


@pytest.mark.asyncio
async def test_guest_request_fails_fast_when_route_already_rate_limited() -> None:
    session = make_authed_session(max_attempts=10, guest=True)
    # Simulate route already marked rate limited in session manager
    session.session_manager.is_route_rate_limited = MagicMock(return_value=True)
    session.active_session.get = AsyncMock()
    sleep_mock = AsyncMock()

    with (
        patch(
            "ultima_scraper_api.managers.session_manager.asyncio.sleep",
            new=sleep_mock,
        ),
        pytest.raises(ClientResponseError) as exc_info,
    ):
        await session.request("https://onlyfans.com/api2/v2/users/me")

    assert exc_info.value.status == 429
    assert session.active_session.get.await_count == 0
    assert sleep_mock.await_count == 0



def test_retry_after_is_bounded() -> None:
    from email.utils import format_datetime
    from datetime import datetime, timedelta, timezone

    from ultima_scraper_api.managers.session_manager import (
        MAX_RETRY_AFTER_SECONDS,
        _retry_after_seconds,
    )

    assert _retry_after_seconds("120") == 120
    assert _retry_after_seconds("31536000") == MAX_RETRY_AFTER_SECONDS
    far = datetime.now(timezone.utc) + timedelta(days=90)
    assert _retry_after_seconds(format_datetime(far, usegmt=True)) == MAX_RETRY_AFTER_SECONDS


def test_guest_route_pacing_works_on_a_second_event_loop() -> None:
    from ultima_scraper_api.managers import session_manager as sm

    session = make_authed_session(guest=True)

    async def burst() -> None:
        # More acquisitions than the bucket holds, so waiters queue on the
        # limiter's lock and bind it to this loop.
        await asyncio.gather(*(session.acquire_route_rate() for _ in range(13)))

    sm.configure_guest_route_rate(20.0)
    try:
        asyncio.run(burst())
        asyncio.run(burst())  # A fresh loop must not reuse the bound lock.
    finally:
        sm.configure_guest_route_rate(None)


@pytest.mark.asyncio
async def test_guest_sends_hold_the_proxy_permit_only_on_the_wire() -> None:
    from contextlib import asynccontextmanager

    from ultima_scraper_api.managers import session_manager as sm

    events: list[tuple[str, str]] = []

    @asynccontextmanager
    async def permit(proxy_url: str):
        events.append(("acquire", proxy_url))
        try:
            yield
        finally:
            events.append(("release", proxy_url))

    ok = AsyncMock()
    ok.status, ok.content, ok.content_type = 404, b"", None
    ok.raise_for_status = MagicMock()

    async def send(url, headers=None):
        events.append(("send", url))
        return ok

    guest = make_authed_session(guest=True)
    guest.auth.auth_details.proxy_url = "http://user:pw@1.2.3.4:8080"
    guest.session_manager.mark_route_rate_limited = MagicMock()
    guest.active_session.get = send
    authed = make_authed_session(guest=False)
    authed.auth.auth_details.proxy_url = "http://user:pw@1.2.3.4:8080"
    authed.active_session.get = send
    sm.configure_guest_route_permits(permit)
    try:
        await guest.request("https://onlyfans.com/api2/v2/users/1")
        assert events == [
            ("acquire", "http://user:pw@1.2.3.4:8080"),
            ("send", "https://onlyfans.com/api2/v2/users/1"),
            ("release", "http://user:pw@1.2.3.4:8080"),
        ]
        events.clear()
        # A 429 still releases the permit.
        guest.active_session.get = AsyncMock(return_value=_guest_429_response())
        with pytest.raises(ClientResponseError):
            await guest.request("https://onlyfans.com/api2/v2/users/2")
        assert [kind for kind, _ in events] == ["acquire", "release"]
        events.clear()
        # A benched session fails fast without taking a permit.
        guest.session_manager.is_route_rate_limited = MagicMock(return_value=True)
        with pytest.raises(ClientResponseError):
            await guest.request("https://onlyfans.com/api2/v2/users/3")
        assert events == []
        # Authenticated sessions are not guest traffic.
        await authed.request("https://onlyfans.com/api2/v2/users/4")
        assert events == [("send", "https://onlyfans.com/api2/v2/users/4")]
    finally:
        sm.configure_guest_route_permits(None)


def test_route_burst_is_configurable_and_keeps_the_average_rate(monkeypatch) -> None:
    from ultima_scraper_api.managers import session_manager as sm

    monkeypatch.delenv("ULTIMA_GUEST_ROUTE_BURST_SECONDS", raising=False)
    assert sm._guest_route_burst_seconds() == 0.5
    for raw, expected in (("3", 3.0), ("0", 0.5), ("bad", 0.5)):
        monkeypatch.setenv("ULTIMA_GUEST_ROUTE_BURST_SECONDS", raw)
        assert sm._guest_route_burst_seconds() == expected
    monkeypatch.setattr(sm, "GUEST_ROUTE_BURST_SECONDS", 3.0)
    limiter = sm._RouteRateLimiter(4.0)
    assert limiter.capacity == 12.0
    # A full bucket absorbs a clump; refill stays at the configured rate.
    limiter.updated = 0.0
    limiter.tokens = 0.0
    limiter._refill(1.0)
    assert limiter.tokens == pytest.approx(4.0)
    limiter._refill(100.0)
    assert limiter.tokens == limiter.capacity
