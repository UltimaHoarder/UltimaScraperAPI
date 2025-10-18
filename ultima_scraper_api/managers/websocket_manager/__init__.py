"""WebSocket management package for UltimaScraperAPI.

Provides site-agnostic WebSocket connection management with dependency injection
for site-specific implementations.
"""

from .connection import WebSocketConnection
from .manager import WebSocketManager
from .protocol import WebSocketProtocol

__all__ = [
    "WebSocketManager",
    "WebSocketConnection",
    "WebSocketProtocol",
]
