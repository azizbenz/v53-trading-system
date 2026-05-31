"""Test engine-specific projection: neutral breakout features → EngineCInput.

Validates that `build_engine_c_input_from_breakout_features` maps the
neutral BreakoutMicrostructureResolution into a 7-float dict that satisfies
EngineCInput.model_validate (when merged with base scalars).
"""

from __future__ import annotations

from data_backbone.microstructure.breakout_microstructure_features import (
    FRESHNESS_FRESH,
    BreakoutMicrostructureInputs,
    resolve_breakout_microstructure_features,
)
from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_c.structure_resolver_c import (
    build_engine_c_input_from_breakout_features,
)


def _make_full_inputs() -> BreakoutMicrostructureInputs:
    return BreakoutMicrostructureInputs(
        breakout_price=100.5,
        entry_price=101.0,
        range_high=100.0,
        range_low=99.0,
        recent_range_width=1.0,
        realized_vol_current=0.001,
        realized_vol_lookback_mean=0.0015,
        realized_vol_lookback_p50=0.0014,
        cumulative_ofi=0.3,
        aggressive_buy_ratio=0.62,
        signed_trade_imbalance=0.25,
        queue_pressure=0.55,
        queue_pressure_stability=0.7,
        microprice_stability=0.8,
        microprice_reversal=0.1,
        distance_to_ask_wall_bps=25.0,
        liquidity_gap_above_bps=30.0,
        depth_thinning_score=0.6,
        expected_slippage_bps=2.0,
        spread_stability=0.85,
        spread_widening_recent=1.05,
        vpin_spike=0.05,
        bid_support_strength=0.7,
        ask_absorption_failure=0.2,
        wick_noise_ratio=0.15,
        inputs_freshness_status=FRESHNESS_FRESH,
    )


def test_build_engine_c_input_from_full_resolution_produces_seven_floats() -> None:
    """Full microstructure → 7 floats ∈ [0, 1] mapped to EngineCInput field names."""
    resolution = resolve_breakout_microstructure_features(_make_full_inputs())

    floats = build_engine_c_input_from_breakout_features(resolution)

    assert set(floats.keys()) == {
        "breakout_strength",
        "range_quality",
        "compression_quality",
        "volume_confirmation",
        "followthrough_room",
        "extension_pct",
        "retrace_risk",
    }
    for k, v in floats.items():
        assert isinstance(v, float)
        assert 0.0 <= v <= 1.0


def test_merged_payload_satisfies_engine_c_input_validation() -> None:
    """floats + base (pair) → EngineCInput.model_validate passes."""
    resolution = resolve_breakout_microstructure_features(_make_full_inputs())
    floats = build_engine_c_input_from_breakout_features(resolution)

    payload = {"pair": "BTCUSDT", **floats}
    engine_c_input = EngineCInput.model_validate(payload)

    assert engine_c_input.pair == "BTCUSDT"
    assert 0.0 <= engine_c_input.breakout_strength <= 1.0
    assert 0.0 <= engine_c_input.range_quality <= 1.0
    assert 0.0 <= engine_c_input.compression_quality <= 1.0
    assert 0.0 <= engine_c_input.volume_confirmation <= 1.0
    assert 0.0 <= engine_c_input.followthrough_room <= 1.0
    assert 0.0 <= engine_c_input.extension_pct <= 1.0
    assert 0.0 <= engine_c_input.retrace_risk <= 1.0


def test_fallback_resolution_still_validates_engine_c_input() -> None:
    """All-None microstructure → fallback floats (0.0), still validates."""
    resolution = resolve_breakout_microstructure_features(
        BreakoutMicrostructureInputs()
    )
    assert resolution.any_research_only_fallback is True

    floats = build_engine_c_input_from_breakout_features(resolution)
    engine_c_input = EngineCInput.model_validate({"pair": "BTCUSDT", **floats})

    # All structural fields default to 0.0 via fallback
    assert engine_c_input.breakout_strength == 0.0
    assert engine_c_input.retrace_risk == 0.0
