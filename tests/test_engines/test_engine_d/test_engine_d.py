from __future__ import annotations

import pytest

from engines.engine_d import EngineDDecision, EngineDInput, run_engine_d


def _good_inputs(**overrides) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
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
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def test_emit_on_valid_reentry():
    result = run_engine_d(_good_inputs())
    assert result.decision == EngineDDecision.EMIT
    assert result.origin_context_id == "ctx-btc-01"
    assert result.origin_trade_id == "trade-btc-01"
    assert result.link_type == "prior_trade"
    assert result.structure_reformed_detected is True
    assert result.duplication_possible_with_engine_a is False
    assert result.duplication_overlap_with_engine_a == pytest.approx(0.24)
    assert result.covered_share_by_engine_a == pytest.approx(0.18)
    assert result.history_score > 0.7
    assert result.reformation_score > 0.6
    assert result.marginal_value_score > 0.6
    assert result.invalidation is not None
    emit_log = next(entry for entry in result.log_entries if entry.event == "engine_d_emit")
    assert emit_log.origin_trade_id == "trade-btc-01"
    assert emit_log.link_type == "prior_trade"


def test_rejects_weak_history():
    result = run_engine_d(_good_inputs(prior_trade_quality=0.2))
    assert result.decision == EngineDDecision.NO_TRADE
    assert "history_weak" in result.no_trade_reasons


def test_rejects_weak_reformation():
    result = run_engine_d(_good_inputs(reformation_quality=0.3, pullback_quality=0.35))
    assert result.decision == EngineDDecision.NO_TRADE
    assert "reformation_weak" in result.no_trade_reasons


def test_rejects_low_marginal_edge():
    result = run_engine_d(_good_inputs(marginal_edge=0.2, continuation_room=0.2))
    assert result.decision == EngineDDecision.NO_TRADE
    assert "marginal_edge_too_low" in result.no_trade_reasons


def test_rejects_concentration_block():
    result = run_engine_d(
        _good_inputs(
            concentration_headroom=0.15,
            reentry_lateness=0.7,
            marginal_edge=0.95,
            continuation_room=0.95,
        )
    )
    assert result.decision == EngineDDecision.NO_TRADE
    assert "concentration_blocked" in result.no_trade_reasons


def test_rejects_cost_infeasible():
    result = run_engine_d(_good_inputs(expected_gain=0.002, expected_cost=0.0018))
    assert result.decision == EngineDDecision.NO_TRADE
    assert "cost_infeasible" in result.no_trade_reasons


def test_result_is_frozen():
    result = run_engine_d(_good_inputs())
    with pytest.raises(Exception):
        result.raw_score = 0.0
