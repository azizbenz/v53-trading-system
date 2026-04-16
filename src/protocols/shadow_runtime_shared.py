"""Shared constants for the governed Shadow runtime."""

from __future__ import annotations


_REQUIRED_SHADOW_ENGINES = frozenset(
    {"engine_a", "engine_b", "engine_c", "engine_d"}
)
_REQUIRED_BUILD14_COMPONENTS = frozenset(
    {
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    }
)
_RUNTIME_EVIDENCE_ACCEPTED_SOURCES = frozenset({"live_websocket", "recorded_replay"})


__all__ = [
    "_REQUIRED_SHADOW_ENGINES",
    "_REQUIRED_BUILD14_COMPONENTS",
    "_RUNTIME_EVIDENCE_ACCEPTED_SOURCES",
]
