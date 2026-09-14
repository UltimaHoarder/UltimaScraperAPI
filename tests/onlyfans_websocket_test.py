from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ultima_scraper_api.apis.onlyfans.classes.extras import AuthDetails
from ultima_scraper_api.apis.onlyfans.classes.websocket import websocket as websocket_module
from ultima_scraper_api.apis.onlyfans.classes.websocket.websocket import (
    OnlyFansWebSocket,
)


def _auth(*, token: str = "old-token", url: str = "wss://example.test/ws"):
    return SimpleNamespace(
        user=SimpleNamespace(ws_auth_token=token, ws_url=url),
        auth_session=SimpleNamespace(json_request=AsyncMock()),
        get_auth_details=lambda: AuthDetails(
            cookie="auth_id=1; sess=session",
            user_agent="pytest-agent",
        ),
    )


@pytest.mark.asyncio
async def test_connect_uses_type_only_auth_without_runtime_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = _auth()
    socket = SimpleNamespace(send=AsyncMock())
    connect = AsyncMock(return_value=socket)
    websocket = OnlyFansWebSocket(auth)

    monkeypatch.setattr(websocket_module.websockets, "connect", connect)
    monkeypatch.setattr(websocket, "_refresh_ws_credentials", AsyncMock())
    monkeypatch.setattr(websocket, "_start_heartbeat", lambda: None)

    await websocket.connect()

    connect.assert_awaited_once_with(
        "wss://example.test/ws",
        user_agent_header="pytest-agent",
        additional_headers=[
            (
                "Cookie",
                "auth_id=1; sess=session; auth_hash=; auth_uniq_1=; "
                "auth_uid_1=; aws-waf-token=;",
            )
        ],
        compression="deflate",
    )
    socket.send.assert_awaited_once_with(
        json.dumps({"act": "connect", "token": "old-token"})
    )


@pytest.mark.asyncio
async def test_refresh_ws_credentials_updates_auth_model() -> None:
    auth = _auth()
    auth.auth_session.json_request.return_value = {
        "wsAuthToken": "fresh-token",
        "wsUrl": "wss://example.test/fresh",
    }
    websocket = OnlyFansWebSocket(auth)

    await websocket._refresh_ws_credentials()

    auth.auth_session.json_request.assert_awaited_once()
    assert auth.user.ws_auth_token == "fresh-token"
    assert auth.user.ws_url == "wss://example.test/fresh"
