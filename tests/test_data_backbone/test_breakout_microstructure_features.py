"""Tests for breakout_microstructure_features — NEUTRAL primitives layer.

Validates:
  - BreakoutMicrostructureField envelope contract
  - 7 resolver functions handle missing inputs (fallback)
  - Full inputs produce [0, 1] values
  - to_score_dict() projects 7 named float scores (engine-neutral)
  - any_fallback_used / any_research_only_fallback aggregate correctly
"""

from __future__ import annotations

from data_backbone.microstructure.breakout_microstructure_features import (
    FRESHNESS_FRESH,
    FRESHNESS_MISSING,
    BreakoutMicrostructureField,
    BreakoutMicrostructureInputs,
    BreakoutMicrostructureResolution,
    resolve_breakout_microstructure_features,
)


def _make_full_inputs() -> BreakoutMicrostructureInputs:
    return BreakoutMicrostructureInputs(
        breakout_price=100.5,
        entry_price=101.0,
        range_high=100.0,
        range_low=99.0,
        recent_range_width=1.0,
        realized_vol_current=0.001,
        realized_vol_at_break=0.0012,
        realized_vol_lookback_mean=0.0015,
        realized_vol_lookback_p50=0.0014,
        ofi_normalized=0.4,
        cumulative_ofi=0.3,
        aggressive_buy_ratio=0.62,
        signed_trade_imbalance=0.25,
        queue_pressure=0.55,
        queue_pressure_stability=0.7,
        microprice_stability=0.8,
        microprice_reversal=0.1,
        distance_to_ask_wall_bps=25.0,
        distance_to_bid_wall_bps=20.0,
        liquidity_gap_above_bps=30.0,
        depth_thinning_score=0.6,
        expected_slippage_bps=2.0,
        spread_bps=4.0,
        spread_stability=0.85,
        spread_widening_recent=1.05,
        vpin=0.3,
        vpin_spike=0.05,
        bid_support_strength=0.7,
        ask_absorption_failure=0.2,
        wick_noise_ratio=0.15,
        inputs_freshness_status=FRESHNESS_FRESH,
    )


def test_envelope_field_contract() -> None:
    f = BreakoutMicrostructureField(
        value=0.7,
        provenance="TEST",
        input_features=("ofi", "vpin"),
        freshness_status=FRESHNESS_FRESH,
        confidence=0.8,
        fallback_used=False,
        research_only_if_legacy_fallback=False,
    )

    assert f.value == 0.7
    assert f.input_features == ("ofi", "vpin")
    assert f.confidence == 0.8


def test_full_inputs_returns_7_fields_in_unit_interval() -> None:
    inputs = _make_full_inputs()

    result = resolve_breakout_microstructure_features(inputs)

    assert isinstance(result, BreakoutMicrostructureResolution)
    for name in (
        "breakout_strength",
        "range_quality",
        "compression_quality",
        "volume_confirmation",
        "followthrough_room",
        "extension_pct",
        "retrace_risk",
    ):
        field = getattr(result, name)
        assert isinstance(field, BreakoutMicrostructureField)
        assert 0.0 <= field.value <= 1.0
        assert field.fallback_used is False
        assert field.provenance.startswith("MICROSTRUCTURE_")
        assert len(field.input_features) > 0

    assert result.any_fallback_used is False
    assert result.any_research_only_fallback is False


def test_empty_inputs_triggers_fallback_research_only_flagged() -> None:
    inputs = BreakoutMicrostructureInputs()

    result = resolve_breakout_microstructure_features(inputs)

    for name in (
        "breakout_strength",
        "range_quality",
        "compression_quality",
        "volume_confirmation",
        "followthrough_room",
        "extension_pct",
        "retrace_risk",
    ):
        field = getattr(result, name)
        assert field.value == 0.0
        assert field.fallback_used is True
        assert field.research_only_if_legacy_fallback is True
        assert field.freshness_status == FRESHNESS_MISSING

    assert result.any_fallback_used is True
    assert result.any_research_only_fallback is True


def test_to_score_dict_projects_seven_named_floats() -> None:
    inputs = _make_full_inputs()
    result = resolve_breakout_microstructure_features(inputs)

    scores = result.to_score_dict()

    expected = {
        "breakout_strength",
        "range_quality",
        "compression_quality",
        "volume_confirmation",
        "followthrough_room",
        "extension_pct",
        "retrace_risk",
    }
    assert set(scores.keys()) == expected
    for k, v in scores.items():
        assert isinstance(v, float)
        assert 0.0 <= v <= 1.0
