"""
4.5 - WebSocket Gateway: connexion fiable, observable et reconnectable.
"""

from .runtime_gateway import (
    AdapterMessage,
    GatewayPollResult,
    WebSocketGatewayAdapter,
    WebSocketGatewayRuntime,
)

__all__ = [
    "AdapterMessage",
    "GatewayPollResult",
    "WebSocketGatewayAdapter",
    "WebSocketGatewayRuntime",
]
