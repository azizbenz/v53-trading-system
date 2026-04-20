from __future__ import annotations

from data_backbone import compute_spread_dynamics as compute_spread_dynamics_from_data_backbone
from data_backbone.microstructure import (
    DEFAULT_SPREAD_DYNAMICS_HORIZON_SECONDS,
    SPREAD_DYNAMICS_METHOD_VERSION_HASH,
    SpreadDynamicsObservation,
    SpreadDynamicsRecord,
    compute_spread_dynamics,
)
from data_backbone.microstructure.realized_effective_spread import (
    DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS,
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
    LiveSpreadObservation,
    RealizedEffectiveSpreadRecord,
    compute_realized_effective_spread,
)
from interface_contracts.domain_types import Side


def test_spread_dynamics_is_a_backward_compatible_alias_surface() -> None:
    assert DEFAULT_SPREAD_DYNAMICS_HORIZON_SECONDS == DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS
    assert SPREAD_DYNAMICS_METHOD_VERSION_HASH == REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH
    assert SpreadDynamicsObservation is LiveSpreadObservation
    assert SpreadDynamicsRecord is RealizedEffectiveSpreadRecord
    assert compute_spread_dynamics_from_data_backbone is compute_spread_dynamics


def test_spread_dynamics_matches_realized_effective_spread_output() -> None:
    observation = SpreadDynamicsObservation(
        timestamp_ns=1_000_000_000,
        bid_price=99.0,
        ask_price=101.0,
        execution_price=100.25,
        side=Side.BUY,
        future_mid_price=100.75,
    )

    canonical = compute_spread_dynamics(observation, pair="btcusdt")
    legacy = compute_realized_effective_spread(observation, pair="btcusdt")

    assert canonical == legacy
