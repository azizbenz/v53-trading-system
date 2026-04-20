from __future__ import annotations

import pytest

from engines.engine_d import (
    ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    EngineDDecision,
    EngineDInput,
    run_engine_d,
)
from engines.engine_d.engine_d_runner import NoTradeReasonD


def _good_inputs(**overrides: float | str | bool | int | None) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
        first_episode_id="episode-btc-01",
        first_episode_engine_id="engine_a",
        first_episode_close_reason="time_stop",
        consecutive_stop_count=0,
        last_fresh_a_detection_at_ns=1_700_000_100_000_000_000,
        anti_revenge_state="reset_required",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        structure_reformed_detected=True,
        regime="trending_up",
        regime_favorability=0.78,
        pair_health=0.90,
        data_freshness=0.94,
        flow_coherence=0.81,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=1.8 / 104.0,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def _assert_terminal_no_trade(result: object, reason: NoTradeReasonD) -> None:
    assert result.decision == EngineDDecision.NO_TRADE
    assert reason in result.no_trade_reasons
    assert result.invalidation is None
    assert f"engine_d.no_trade.{reason.value}" in result.reason_codes
    assert result.log_entries[-1].event == "engine_d_no_trade"


def test_emit_path_valid_case() -> None:
    result = run_engine_d(_good_inputs())
    assert result.decision == EngineDDecision.EMIT
    assert result.conviction.value == "high"
    assert result.tier_suggestion.value == "tier_2"
    assert result.invalidation is not None
    assert result.anti_revenge_blocked is False
    assert result.duplication_blocked is False
    assert "scoring.engine_d.conviction.high" in result.reason_codes
    assert "engine_d.conviction.high" in result.reason_codes
    assert "engine_internal.engine_d.link_type.prior_trade" in result.reason_codes
    assert "engine_d.link_type.prior_trade" in result.reason_codes
    assert result.log_entries[-1].event == "engine_d_emit"


def test_entry_price_zero_rejected_with_specific_reason() -> None:
    result = run_engine_d(_good_inputs(entry_price=0.0))
    _assert_terminal_no_trade(result, NoTradeReasonD.INVALID_ENTRY_PRICE)
    assert "entry_price" in result.log_entries[-1].reasons[0]


def test_candidate_size_zero_rejected_before_emit() -> None:
    """Fail-first: pre-patch candidate_size=0 could still flow through COST checks."""
    result = run_engine_d(_good_inputs(candidate_size=0.0))
    _assert_terminal_no_trade(result, NoTradeReasonD.INVALID_CANDIDATE_SIZE)
    assert "candidate_size" in result.log_entries[-1].reasons[0]


def test_holding_period_zero_rejected_before_emit() -> None:
    result = run_engine_d(_good_inputs(holding_period=0.0))
    _assert_terminal_no_trade(result, NoTradeReasonD.INVALID_HOLDING_PERIOD)
    assert "holding_period" in result.log_entries[-1].reasons[0]


def test_history_weak_branch() -> None:
    result = run_engine_d(_good_inputs(prior_trade_quality=0.2))
    _assert_terminal_no_trade(result, NoTradeReasonD.HISTORY_WEAK)
    assert "engine_internal.engine_d.history.weak" in result.reason_codes
    assert "prior context too weak" in result.log_entries[-1].reasons[0]


def test_reformation_weak_branch() -> None:
    result = run_engine_d(_good_inputs(reformation_quality=0.3, pullback_quality=0.35))
    _assert_terminal_no_trade(result, NoTradeReasonD.REFORMATION_WEAK)
    assert "engine_internal.engine_d.reformation.weak" in result.reason_codes
    assert "reformation too weak" in result.log_entries[-1].reasons[0]


def test_marginal_edge_too_low_branch() -> None:
    result = run_engine_d(_good_inputs(marginal_edge=0.2, continuation_room=0.2))
    _assert_terminal_no_trade(result, NoTradeReasonD.MARGINAL_EDGE_TOO_LOW)
    assert "engine_internal.engine_d.marginal_value.below_floor" in result.reason_codes
    assert "insufficient marginal value" in result.log_entries[-1].reasons[0]


def test_concentration_blocked_branch() -> None:
    result = run_engine_d(
        _good_inputs(
            concentration_headroom=0.15,
            reentry_lateness=0.7,
            marginal_edge=0.95,
            continuation_room=0.95,
        )
    )
    _assert_terminal_no_trade(result, NoTradeReasonD.CONCENTRATION_BLOCKED)
    assert "engine_internal.engine_d.concentration.blocked" in result.reason_codes
    assert "concentration" in result.log_entries[-1].reasons[0]


def test_cost_infeasible_branch() -> None:
    result = run_engine_d(_good_inputs(expected_gain=0.002, expected_cost=0.0018))
    _assert_terminal_no_trade(result, NoTradeReasonD.COST_INFEASIBLE)
    assert result.expected_cost == pytest.approx(0.0018)
    assert "economics.engine_d.cost.infeasible" in result.reason_codes
    assert "edge_below_cost_buffer" in result.reason_codes
    assert "edge_below_cost_buffer" in result.log_entries[-1].reasons


def test_low_conviction_cannot_emit() -> None:
    """Fail-first: pre-patch low conviction still emitted as tier_1."""
    result = run_engine_d(
        _good_inputs(
            prior_trade_quality=0.42,
            pair_health=0.82,
            data_freshness=0.59,
            reformation_quality=0.60,
            pullback_quality=0.60,
            regime_favorability=0.55,
            flow_coherence=0.55,
            marginal_edge=1.0,
            continuation_room=1.0,
            concentration_headroom=0.30,
            reentry_lateness=0.45,
            expected_gain=0.0028,
            expected_cost=0.0010,
            ce_min=0.0009,
        )
    )
    _assert_terminal_no_trade(result, NoTradeReasonD.CONVICTION_TOO_LOW)
    assert result.conviction.value == "none"
    assert "scoring.engine_d.conviction.too_low" in result.reason_codes
    assert "conviction below minimum" in result.log_entries[-1].reasons[0]


def test_anti_revenge_state_blocks_when_policy_requires() -> None:
    result = run_engine_d(
        _good_inputs(
            anti_revenge_state="blocked",
            last_fresh_a_detection_at_ns=None,
        )
    )
    _assert_terminal_no_trade(result, NoTradeReasonD.ANTI_REVENGE_BLOCKED)
    assert result.anti_revenge_blocked is True
    assert "hard_block.engine_d.anti_revenge.blocked" in result.reason_codes


def test_duplication_or_low_marginal_gain_blocks_if_made_decisionnel() -> None:
    result = run_engine_d(
        _good_inputs(
            duplication_overlap_with_engine_a=0.82,
            covered_share_by_engine_a=0.81,
            marginal_portfolio_gain=-0.5,
        )
    )
    _assert_terminal_no_trade(result, NoTradeReasonD.DUPLICATION_BLOCKED)
    assert result.duplication_blocked is True
    assert "engine_internal.engine_d.duplication.blocked" in result.reason_codes
    assert "Engine A already covers this re-entry" in result.log_entries[-1].reasons[0]


def test_result_is_frozen() -> None:
    result = run_engine_d(_good_inputs())
    with pytest.raises(Exception):
        result.raw_score = 0.0


def test_engine_d_input_defaults_follow_governed_cost_threshold_surface() -> None:
    thresholds = ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE
    defaults = _good_inputs(candidate_size=1.0, entry_price=1.0, reentry_anchor_price=1.0)

    assert defaults.ce_min == pytest.approx(thresholds.ce_min)
    assert defaults.delta_safe == pytest.approx(thresholds.delta_safe)
