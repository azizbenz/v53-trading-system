from __future__ import annotations

import pytest

from engines.engine_d.context_resolver_d import resolve_engine_d_context
from engines.engine_d.engine_d_runner import EngineDInput


def _inputs(**overrides: float | str | bool | int | None) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        prior_trade_quality=0.80,
        reformation_quality=0.80,
        pullback_quality=0.70,
        continuation_room=0.70,
        concentration_headroom=0.80,
        marginal_edge=0.70,
        reentry_lateness=0.20,
        expected_gain=0.010,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=1.0,
        entry_price=100.0,
        reentry_anchor_price=99.0,
        realized_vol_current=0.01,
        realized_vol_post_close=0.01,
        atr=1.0,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def test_link_type_fallback() -> None:
    assert resolve_engine_d_context(_inputs(link_type="   ", origin_trade_id="trade-1"))["link_type"] == "prior_trade"
    assert resolve_engine_d_context(_inputs(link_type="   ", origin_trade_id=""))["link_type"] == "prior_context"


def test_duplication_overlap_clamped() -> None:
    context = resolve_engine_d_context(_inputs(duplication_overlap_with_engine_a=2.5))
    assert context["duplication_overlap_with_engine_a"] == pytest.approx(1.0)


def test_covered_share_fallback() -> None:
    context = resolve_engine_d_context(_inputs(duplication_overlap_with_engine_a=0.42, covered_share_by_engine_a=0.0))
    assert context["covered_share_by_engine_a"] == pytest.approx(0.42)


def test_marginal_portfolio_gain_fallback() -> None:
    context = resolve_engine_d_context(_inputs(marginal_portfolio_gain=0.0, expected_gain=0.01, expected_cost=0.001, candidate_size=200.0))
    assert context["marginal_portfolio_gain"] == pytest.approx(1.8)


def test_concentration_risk_bounds() -> None:
    low = resolve_engine_d_context(_inputs(concentration_headroom=1.0, reentry_lateness=0.0))
    high = resolve_engine_d_context(_inputs(concentration_headroom=0.0, reentry_lateness=1.0))
    assert 0.0 <= float(low["concentration_risk"]) <= 1.0
    assert 0.0 <= float(high["concentration_risk"]) <= 1.0
    assert float(high["concentration_risk"]) == pytest.approx(1.0)


def test_decisionnel_vs_observability_contract() -> None:
    observability_only = resolve_engine_d_context(
        _inputs(
            duplication_overlap_with_engine_a=0.8,
            covered_share_by_engine_a=0.8,
            marginal_portfolio_gain=2.0,
            anti_revenge_state="reset_required",
            last_fresh_a_detection_at_ns=1_700_000_000_000_000_000,
        )
    )
    assert observability_only["duplication_possible_with_engine_a"] is True
    assert observability_only["duplication_blocked"] is False
    assert observability_only["anti_revenge_blocked"] is False

    blocked = resolve_engine_d_context(
        _inputs(
            duplication_overlap_with_engine_a=0.8,
            covered_share_by_engine_a=0.8,
            marginal_portfolio_gain=-1.0,
            anti_revenge_state="blocked",
        )
    )
    assert blocked["duplication_blocked"] is True
    assert blocked["anti_revenge_blocked"] is True
