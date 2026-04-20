from __future__ import annotations

import pytest

from engines.engine_c import (
    ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    EngineCDecision,
    EngineCInput,
    EngineCOutput,
    run_engine_c,
)
from engines.engine_c.engine_c_runner import NoTradeReasonC


def _good_inputs(**overrides: object) -> EngineCInput:
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
        cumulative_ofi=24.0,
        queue_pressure=0.36,
        vpin=0.22,
        kyle_lambda=0.0012,
        continuation_ofi_min=0.0,
        continuation_queue_min=0.0,
        continuation_vpin_max=0.35,
        continuation_kyle_lambda_max=0.01,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        realized_vol_current=2.0 / 105.0,
        realized_vol_at_break=2.0 / 105.0,
        atr=2.0,
        engine_a_overlap_ratio=0.28,
        marginal_portfolio_gain=9.2,
        covered_share_by_engine_a=0.22,
        keff_contribution=0.31,
        scoring_version="engine_c.v1",
    )
    defaults.update(overrides)
    return EngineCInput(**defaults)


def _terminal_no_trade_log(result: EngineCOutput) -> object:
    return [entry for entry in result.log_entries if entry.event == "engine_c_no_trade"][-1]


def test_breakout_strength_non_positive_rejected() -> None:
    result = run_engine_c(_good_inputs(breakout_strength=0.0))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons == (NoTradeReasonC.NON_LONG_BREAKOUT,)
    assert "engine_internal.engine_c.breakout.non_long" in result.reason_codes
    assert "breakout_strength" in " ".join(_terminal_no_trade_log(result).reasons)


def test_breakout_unstructured_branch() -> None:
    result = run_engine_c(_good_inputs(range_quality=0.30, compression_quality=0.40))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.BREAKOUT_UNSTRUCTURED
    assert "engine_internal.engine_c.breakout.unstructured" in result.reason_codes
    assert "breakout structure insufficient" in " ".join(_terminal_no_trade_log(result).reasons)


def test_continuation_not_viable_branch() -> None:
    result = run_engine_c(_good_inputs(extension_pct=0.86, followthrough_room=0.30))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.CONTINUATION_NOT_VIABLE
    assert "engine_internal.engine_c.continuation.not_viable" in result.reason_codes
    assert "engine_c.no_trade.continuation_not_viable" in result.reason_codes
    assert any("continuation" in reason for reason in _terminal_no_trade_log(result).reasons)


def test_microstructure_missing_branch() -> None:
    result = run_engine_c(_good_inputs(cumulative_ofi=None, continuation_ofi_min=5.0))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.MICROSTRUCTURE_UNCONFIRMED
    assert result.microstructure_missing is True
    assert "engine_internal.engine_c.microstructure.unconfirmed" in result.reason_codes
    assert "engine_c.microstructure.missing" in result.reason_codes


def test_microstructure_contradictory_branch() -> None:
    result = run_engine_c(_good_inputs(cumulative_ofi=-5.0))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.MICROSTRUCTURE_UNCONFIRMED
    assert result.microstructure_contradictory is True
    assert "engine_internal.engine_c.microstructure.unconfirmed" in result.reason_codes
    assert "engine_c.microstructure.contradictory" in result.reason_codes
    assert any("ofi_persistence" in reason for reason in _terminal_no_trade_log(result).reasons)


def test_fake_breakout_blocked_branch() -> None:
    result = run_engine_c(_good_inputs(retrace_risk=0.9, rejection_wick_ratio=0.8, volume_confirmation=0.2))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.FAKE_BREAKOUT_BLOCKED
    assert "engine_internal.engine_c.fake_breakout.blocked" in result.reason_codes
    assert "fake breakout risk too high" in " ".join(_terminal_no_trade_log(result).reasons)


def test_cost_infeasible_branch() -> None:
    result = run_engine_c(_good_inputs(expected_gain=0.002, expected_cost=0.0019))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.COST_INFEASIBLE
    assert "economics.engine_c.cost.infeasible" in result.reason_codes
    assert any("edge_below_cost_buffer" in reason for reason in _terminal_no_trade_log(result).reasons)


def test_low_conviction_cannot_emit() -> None:
    result = run_engine_c(
        _good_inputs(
            breakout_strength=0.55,
            range_quality=0.90,
            compression_quality=0.60,
            volume_confirmation=0.60,
            followthrough_room=0.70,
            extension_pct=0.72,
            retrace_risk=0.80,
            rejection_wick_ratio=0.60,
            regime_favorability=0.65,
            pair_health=0.65,
            data_freshness=0.65,
            flow_coherence=0.65,
            expected_gain=0.0030,
            expected_cost=0.0010,
            ce_min=0.0002,
        )
    )
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.LOW_CONVICTION
    assert "scoring.engine_c.conviction.low" in result.reason_codes
    assert _terminal_no_trade_log(result).conviction == "low"


def test_invalid_invalidation_inputs_rejected_before_emit() -> None:
    result = run_engine_c(_good_inputs(breakout_level=110.0, atr=0.0))
    assert result.decision == EngineCDecision.NO_TRADE
    assert result.no_trade_reasons[-1] == NoTradeReasonC.INVALID_STOP_GE_ENTRY
    assert "hard_block.engine_c.invalidation.invalid_stop_ge_entry" in result.reason_codes
    assert "engine_c.invalidation.invalid_stop_ge_entry" in result.reason_codes
    assert "stop_price must remain below entry_price" in " ".join(_terminal_no_trade_log(result).reasons)


def test_duplication_or_keff_policy_is_explicit() -> None:
    result = run_engine_c(
        _good_inputs(
            engine_a_overlap_ratio=0.8,
            covered_share_by_engine_a=0.8,
            marginal_portfolio_gain=-1.0,
            keff_contribution=0.1,
        )
    )
    assert result.decision == EngineCDecision.EMIT
    assert result.local_duplication_policy_triggered is True
    assert result.duplication_blocked is True
    assert result.keff_contribution == pytest.approx(0.1)
    assert "engine_c.duplication.local_policy_triggered" in result.reason_codes
    assert any(entry.event == "engine_c_duplication_policy_observed" for entry in result.log_entries)


def test_emit_path_valid_case() -> None:
    result = run_engine_c(_good_inputs())
    assert result.decision == EngineCDecision.EMIT
    assert result.breakout_type == "range_expansion"
    assert result.continuation_context == "fresh_breakout"
    assert result.local_duplication_policy_triggered is False
    assert result.duplication_blocked is False
    assert result.invalidation is not None
    assert "engine_internal.engine_c.breakout.range_expansion" in result.reason_codes
    assert "engine_internal.engine_c.continuation.fresh_breakout" in result.reason_codes
    assert "economics.engine_c.cost.feasible" in result.reason_codes
    assert "scoring.engine_c.conviction.medium" in result.reason_codes
    assert "engine_c.conviction.medium" in result.reason_codes
    assert "engine_c.invalidation.present" in result.reason_codes
    emit_log = next(entry for entry in result.log_entries if entry.event == "engine_c_emit")
    assert emit_log.breakout_type == "range_expansion"
    assert emit_log.range_width_pct > 0.0
    assert emit_log.conviction in {"medium", "high"}


def test_engine_c_input_continuation_threshold_defaults_are_governed() -> None:
    thresholds = ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE

    assert EngineCInput.model_fields["continuation_ofi_min"].default == thresholds.ofi_min
    assert EngineCInput.model_fields["continuation_queue_min"].default == thresholds.queue_min
    assert EngineCInput.model_fields["continuation_vpin_max"].default == thresholds.vpin_max
    assert EngineCInput.model_fields["continuation_kyle_lambda_max"].default == thresholds.kyle_lambda_max


def test_engine_c_input_cost_threshold_defaults_are_governed() -> None:
    thresholds = ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE

    assert EngineCInput.model_fields["ce_min"].default == thresholds.ce_min
    assert EngineCInput.model_fields["delta_safe"].default == thresholds.delta_safe
