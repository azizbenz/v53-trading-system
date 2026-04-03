from __future__ import annotations

import pytest

from engine_c import EngineCDecision, EngineCInput, run_engine_c


def _good_inputs(**overrides) -> EngineCInput:
    defaults = dict(
        pair="BTCUSDT",
        breakout_strength=0.88,
        range_quality=0.78,
        compression_quality=0.74,
        volume_confirmation=0.81,
        followthrough_room=0.76,
        extension_pct=0.24,
        retrace_risk=0.18,
        rejection_wick_ratio=0.12,
        regime="breakout",
        regime_favorability=0.80,
        pair_health=0.92,
        data_freshness=0.95,
        flow_coherence=0.79,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        atr=2.0,
        scoring_version="engine_c.v1",
    )
    defaults.update(overrides)
    return EngineCInput(**defaults)


def test_emit_on_structured_breakout():
    result = run_engine_c(_good_inputs())
    assert result.decision == EngineCDecision.EMIT
    assert result.breakout_score > 0.7
    assert result.continuation_score > 0.6
    assert result.invalidation is not None
    assert result.invalidation.stop_price < 105.0
    assert result.invalidation.target_price > 105.0


def test_rejects_non_long_breakout():
    result = run_engine_c(_good_inputs(breakout_strength=-0.1))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons == ("non_long_breakout",)


def test_rejects_unstructured_breakout():
    result = run_engine_c(_good_inputs(range_quality=0.3, compression_quality=0.4))
    assert result.decision == EngineCDecision.NO_TRADE
    assert "breakout_unstructured" in result.no_trade_reasons


def test_rejects_late_continuation():
    result = run_engine_c(_good_inputs(extension_pct=0.86, followthrough_room=0.30))
    assert result.decision == EngineCDecision.NO_TRADE
    assert "continuation_not_viable" in result.no_trade_reasons


def test_rejects_fake_breakout_risk():
    result = run_engine_c(_good_inputs(retrace_risk=0.9, rejection_wick_ratio=0.8, volume_confirmation=0.2))
    assert result.decision == EngineCDecision.NO_TRADE
    assert "fake_breakout_blocked" in result.no_trade_reasons


def test_rejects_cost_infeasible_breakout():
    result = run_engine_c(_good_inputs(expected_gain=0.002, expected_cost=0.0019))
    assert result.decision == EngineCDecision.NO_TRADE
    assert "cost_infeasible" in result.no_trade_reasons


def test_result_is_frozen():
    result = run_engine_c(_good_inputs())
    with pytest.raises(Exception):
        result.raw_score = 0.0
