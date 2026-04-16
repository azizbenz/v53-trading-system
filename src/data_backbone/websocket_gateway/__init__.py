"""
4.5 - WebSocket Gateway: connexion fiable, observable et reconnectable.
"""

from __future__ import annotations

from .runtime_gateway import (
    AdapterMessage,
    GatewayPollResult,
    WebSocketGatewayAdapter,
    WebSocketGatewayRuntime,
)
from .injected_stream_loader import InjectedWebSocketFrame, load_injected_websocket_frames

__all__ = [
    "AdapterMessage",
    "GatewayPollResult",
    "WebSocketGatewayAdapter",
    "WebSocketGatewayRuntime",
    "InjectedWebSocketFrame",
    "load_injected_websocket_frames",
]
