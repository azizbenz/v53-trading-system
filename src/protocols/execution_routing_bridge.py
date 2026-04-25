"""Protocol-layer re-export for the Build-3 routing bridge."""

from __future__ import annotations

from execution_backbone.execution_routing_bridge import (
    ExecutionRoutingBridge,
    ExecutionRoutingBridgeConfig,
)

__all__ = [
    "ExecutionRoutingBridge",
    "ExecutionRoutingBridgeConfig",
]
