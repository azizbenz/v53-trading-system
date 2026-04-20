"""
V5.3 - SPREAD DYNAMICS
Canonical doc23 landing seam for live quoted / effective / realized spread diagnostics.
"""

from __future__ import annotations

from data_backbone.microstructure.realized_effective_spread import (
    DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS,
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION,
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
    LiveSpreadObservation,
    RealizedEffectiveSpreadRecord,
    compute_realized_effective_spread,
)


SPREAD_DYNAMICS_METHOD_VERSION = REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION
SPREAD_DYNAMICS_METHOD_VERSION_HASH = REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH
DEFAULT_SPREAD_DYNAMICS_HORIZON_SECONDS = DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS
SpreadDynamicsObservation = LiveSpreadObservation
SpreadDynamicsRecord = RealizedEffectiveSpreadRecord


def compute_spread_dynamics(
    observation: SpreadDynamicsObservation,
    *,
    pair: str,
    realized_horizon_seconds: float = DEFAULT_SPREAD_DYNAMICS_HORIZON_SECONDS,
    computed_at_ns: int | None = None,
) -> SpreadDynamicsRecord:
    """Canonical wrapper that preserves the existing live spread implementation."""

    return compute_realized_effective_spread(
        observation,
        pair=pair,
        realized_horizon_seconds=realized_horizon_seconds,
        computed_at_ns=computed_at_ns,
    )


__all__ = [
    "SPREAD_DYNAMICS_METHOD_VERSION",
    "SPREAD_DYNAMICS_METHOD_VERSION_HASH",
    "DEFAULT_SPREAD_DYNAMICS_HORIZON_SECONDS",
    "SpreadDynamicsObservation",
    "SpreadDynamicsRecord",
    "compute_spread_dynamics",
]
