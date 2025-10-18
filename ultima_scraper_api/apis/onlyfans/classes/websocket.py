"""OnlyFans-specific WebSocket implementation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

import websockets

from ultima_scraper_api.managers.websocket_manager.protocol import WebSocketProtocol

if TYPE_CHECKING:
    from ultima_scraper_api.apis.onlyfans.classes.auth_model import OnlyFansAuthModel

logger = logging.getLogger(__name__)


class OnlyFansWebSocket(WebSocketProtocol):
    """OnlyFans-specific WebSocket implementation.

    Handles OnlyFans WebSocket connection details including:
    - Connection URL from user profile
    - OnlyFans-specific authentication headers and tokens
    - Automatic heartbeat/ping messages
    - OnlyFans message format parsing
    """

    def __init__(self, auth: OnlyFansAuthModel) -> None:
        """Initialize OnlyFans WebSocket.

        Args:
            auth: OnlyFans auth model
        """
        super().__init__(auth)
        self._heartbeat_task: asyncio.Task[None] | None = None

    @property
    def connection_url(self) -> str:
        """Get OnlyFans WebSocket URL from user profile.

        Returns:
            WebSocket URL
        """
        url = self.auth.user.ws_url
        if not url:
            raise ValueError("WebSocket URL not available on user profile")
        return url

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise
        """
        if self._websocket is None:
            return False
        # Check if the websocket has a state attribute (websockets 11+)
        if hasattr(self._websocket, "state"):
            from websockets.protocol import State

            return self._websocket.state == State.OPEN
        # Fallback: check if closed attribute exists (older versions)
        if hasattr(self._websocket, "closed"):
            return not self._websocket.closed
        # Last resort: assume it's connected if it exists
        return True

    async def connect(self) -> None:
        """Establish OnlyFans WebSocket connection with auth headers."""
        url = self.connection_url
        logger.info(f"Connecting to OnlyFans WebSocket: {url}")

        # Get auth details for headers
        auth_details = self.auth.get_auth_details()
        user_agent = auth_details.user_agent
        cookie_header: str = auth_details.cookie.convert()

        # Prepare headers for websockets 15.x
        additional_headers: list[tuple[str, str]] = [
            ("Cookie", cookie_header),
        ]

        # Connect to WebSocket
        self._websocket = await websockets.connect(
            url,
            user_agent_header=user_agent,
            additional_headers=additional_headers,
            compression="deflate",
        )

        logger.info("OnlyFans WebSocket connected")

        # Send initial connect frame with auth token if available
        token = self.auth.user.ws_auth_token
        if token:
            try:
                await self._websocket.send(
                    json.dumps({"act": "connect", "token": token})
                )
                logger.debug("Sent connect frame with auth token")
            except Exception as e:
                logger.warning(f"Failed to send connect frame: {e}")

        # Start heartbeat
        self._start_heartbeat()

    async def disconnect(self) -> None:
        """Close OnlyFans WebSocket connection."""
        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Close websocket
        if self._websocket:
            try:
                await self._websocket.close()
                logger.info("OnlyFans WebSocket disconnected")
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")
            finally:
                self._websocket = None

    async def send(self, data: dict[str, Any]) -> None:
        """Send data through OnlyFans WebSocket.

        Args:
            data: Data dict to send (will be JSON encoded)
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")

        try:
            await self._websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise

    async def receive(self) -> dict[str, Any]:
        """Receive and parse message from OnlyFans WebSocket.

        Returns:
            Parsed message dict
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")

        try:
            msg = await self._websocket.recv()

            # OnlyFans sends JSON messages, parse them
            try:
                parsed = json.loads(msg)
                return parsed
            except json.JSONDecodeError:
                # If not JSON, return raw message
                return {"type": "raw", "data": msg}

        except websockets.ConnectionClosed as e:
            logger.warning(
                f"OnlyFans WebSocket closed: code={e.code}, reason={e.reason}"
            )
            raise
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {e}")
            raise

    def _start_heartbeat(self) -> None:
        """Start automatic heartbeat/ping task."""
        if self._heartbeat_task:
            return

        async def _heartbeat_loop():
            """Send periodic ping messages (every 25 seconds, matching browser behavior)."""
            try:
                while self.is_connected:
                    await asyncio.sleep(25)
                    if self.is_connected:
                        try:
                            await self._websocket.send(json.dumps({"act": "ping"}))
                            logger.debug("Sent heartbeat ping")
                        except Exception as e:
                            logger.debug(f"Heartbeat send failed: {e}")
                            break
            except asyncio.CancelledError:
                logger.debug("Heartbeat cancelled")
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())
