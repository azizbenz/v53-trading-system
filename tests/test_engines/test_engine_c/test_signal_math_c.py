from __future__ import annotations

from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_c.signal_math_c import (
    compute_breakout_score,
    compute_context_score,
    compute_continuation_score,
    compute_fake_breakout_risk,
)


def _inputs(**overrides: float | str) -> EngineCInput:
    defaults = dict(
        pair="BTCUSDT",
        breakout_strength=0.60,
        range_quality=0.60,
        compression_quality=0.60,
        volume_confirmation=0.60,
        followthrough_room=0.60,
        extension_pct=0.20,
        retrace_risk=0.20,
        rejection_wick_ratio=0.20,
        regime_favorability=0.60,
        pair_health=0.60,
        data_freshness=0.60,
        flow_coherence=0.60,
        expected_gain=0.010,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=1.0,
        entry_price=100.0,
        breakout_level=99.0,
        atr=1.0,
        scoring_version="engine_c.v1",
    )
    defaults.update(overrides)
    return EngineCInput(**defaults)


def test_breakout_score_monotonic_in_breakout_strength() -> None:
    low = compute_breakout_score(_inputs(breakout_strength=0.20))
    high = compute_breakout_score(_inputs(breakout_strength=0.80))
    assert high > low


def test_context_score_monotonic_in_regime_favorability() -> None:
    low = compute_context_score(_inputs(regime_favorability=0.20))
    high = compute_context_score(_inputs(regime_favorability=0.80))
    assert high > low


def test_continuation_score_decreases_when_extension_pct_increases() -> None:
    context_score = compute_context_score(_inputs())
    early = compute_continuation_score(_inputs(extension_pct=0.10), context_score=context_score)
    late = compute_continuation_score(_inputs(extension_pct=0.80), context_score=context_score)
    assert early > late


def test_fake_breakout_risk_increases_with_retrace_risk() -> None:
    low = compute_fake_breakout_risk(_inputs(retrace_risk=0.10))
    high = compute_fake_breakout_risk(_inputs(retrace_risk=0.80))
    assert high > low


def test_scores_bounded_zero_one() -> None:
    extreme = _inputs(
        breakout_strength=1.0,
        range_quality=1.0,
        compression_quality=1.0,
        volume_confirmation=1.0,
        followthrough_room=1.0,
        extension_pct=0.0,
        retrace_risk=1.0,
        rejection_wick_ratio=1.0,
        regime_favorability=1.0,
        pair_health=1.0,
        data_freshness=1.0,
        flow_coherence=1.0,
    )
    context_score = compute_context_score(extreme)
    assert 0.0 <= compute_breakout_score(extreme) <= 1.0
    assert 0.0 <= context_score <= 1.0
    assert 0.0 <= compute_continuation_score(extreme, context_score=context_score) <= 1.0
    assert 0.0 <= compute_fake_breakout_risk(extreme) <= 1.0
