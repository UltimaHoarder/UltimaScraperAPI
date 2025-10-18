"""Abstract protocol for site-specific WebSocket implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WebSocketProtocol(ABC):
    """Abstract base class for site-specific WebSocket implementations.

    Each site (OnlyFans, Fansly, LoyalFans) implements this protocol
    to handle their specific WebSocket connection details, authentication,
    and message formatting.
    """

    def __init__(self, auth: Any) -> None:
        """Initialize WebSocket protocol with auth model.

        Args:
            auth: Site-specific auth model (OnlyFansAuthModel, FanslyAuthModel, etc.)
        """
        self.auth = auth
        self._websocket: Any = None  # WebSocket connection instance

    @abstractmethod
    async def connect(self) -> None:
        """Establish WebSocket connection to the site.

        Should set self._websocket to the connected websocket instance.
        Handles site-specific connection URL, headers, authentication, etc.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        pass

    @abstractmethod
    async def send(self, data: dict[str, Any]) -> None:
        """Send data through WebSocket.

        Args:
            data: Data to send (will be site-specifically formatted)
        """
        pass

    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        """Receive and parse message from WebSocket.

        Returns:
            Parsed message dict (site-specific format)
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected.

        Returns:
            True if connected, False otherwise
        """
        pass

    @property
    @abstractmethod
    def connection_url(self) -> str:
        """Get the WebSocket connection URL for this site.

        Returns:
            WebSocket URL (e.g., wss://...)
        """
        pass
