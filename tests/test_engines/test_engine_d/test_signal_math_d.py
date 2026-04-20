from __future__ import annotations

from engines.engine_d.engine_d_runner import EngineDInput
from engines.engine_d.signal_math_d import (
    compute_context_score,
    compute_history_score,
    compute_marginal_value_score,
    compute_reformation_score,
)


def _inputs(**overrides: float | str) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        prior_trade_quality=0.60,
        reformation_quality=0.60,
        pullback_quality=0.60,
        continuation_room=0.60,
        concentration_headroom=0.60,
        marginal_edge=0.60,
        reentry_lateness=0.20,
        regime_favorability=0.60,
        pair_health=0.60,
        data_freshness=0.60,
        flow_coherence=0.60,
        expected_gain=0.010,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=1.0,
        entry_price=100.0,
        reentry_anchor_price=99.0,
        atr=1.0,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def test_history_score_monotonic_in_prior_trade_quality() -> None:
    low = compute_history_score(_inputs(prior_trade_quality=0.20))
    high = compute_history_score(_inputs(prior_trade_quality=0.80))
    assert high > low


def test_reformation_score_monotonic_in_reformation_quality() -> None:
    context_score = compute_context_score(_inputs())
    low = compute_reformation_score(_inputs(reformation_quality=0.20), context_score=context_score)
    high = compute_reformation_score(_inputs(reformation_quality=0.90), context_score=context_score)
    assert high > low


def test_marginal_value_score_monotonic_in_marginal_edge() -> None:
    low = compute_marginal_value_score(_inputs(marginal_edge=0.20))
    high = compute_marginal_value_score(_inputs(marginal_edge=0.90))
    assert high > low


def test_marginal_value_score_decreases_when_reentry_lateness_increases() -> None:
    early = compute_marginal_value_score(_inputs(reentry_lateness=0.10))
    late = compute_marginal_value_score(_inputs(reentry_lateness=0.80))
    assert early > late


def test_scores_bounded_zero_one() -> None:
    extreme = _inputs(
        prior_trade_quality=5.0,
        reformation_quality=5.0,
        pullback_quality=5.0,
        continuation_room=5.0,
        concentration_headroom=5.0,
        marginal_edge=5.0,
        reentry_lateness=-2.0,
        regime_favorability=5.0,
        pair_health=5.0,
        data_freshness=5.0,
        flow_coherence=5.0,
    )
    context_score = compute_context_score(extreme)
    assert 0.0 <= compute_history_score(extreme) <= 1.0
    assert 0.0 <= context_score <= 1.0
    assert 0.0 <= compute_reformation_score(extreme, context_score=context_score) <= 1.0
    assert 0.0 <= compute_marginal_value_score(extreme) <= 1.0
