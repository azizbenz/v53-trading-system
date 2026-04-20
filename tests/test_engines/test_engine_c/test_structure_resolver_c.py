from __future__ import annotations

import pytest

from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_c.structure_resolver_c import resolve_engine_c_structure


def _inputs(**overrides: float | str | bool) -> EngineCInput:
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


def test_range_high_fallback() -> None:
    structure = resolve_engine_c_structure(_inputs(range_high=0.0))
    assert structure["range_high"] == pytest.approx(105.0)
    assert structure["resolved_range_high_fallback_used"] is True


def test_range_low_fallback() -> None:
    structure = resolve_engine_c_structure(_inputs(range_low=0.0))
    assert structure["range_low"] < structure["range_high"]
    assert structure["resolved_range_low_fallback_used"] is True


def test_range_low_fallback_uses_realized_vol_width_when_available() -> None:
    structure = resolve_engine_c_structure(
        _inputs(
            range_low=0.0,
            range_quality=0.0,
            realized_vol_current=2.0 / 105.0,
            realized_vol_at_break=2.0 / 105.0,
        )
    )
    assert structure["range_high"] == pytest.approx(101.0)
    assert structure["range_low"] == pytest.approx(98.0)


def test_duplication_overlap_clamped() -> None:
    structure = resolve_engine_c_structure(_inputs(engine_a_overlap_ratio=1.0))
    assert structure["duplication_overlap_with_engine_a"] == pytest.approx(1.0)


def test_covered_share_fallback() -> None:
    structure = resolve_engine_c_structure(_inputs(engine_a_overlap_ratio=0.42, covered_share_by_engine_a=0.0))
    assert structure["covered_share_by_engine_a"] == pytest.approx(0.42)
    assert structure["covered_share_fallback_used"] is True


def test_marginal_portfolio_gain_fallback() -> None:
    structure = resolve_engine_c_structure(
        _inputs(marginal_portfolio_gain=0.0, expected_gain=0.01, expected_cost=0.001, candidate_size=200.0)
    )
    assert structure["marginal_portfolio_gain"] == pytest.approx(1.8)
    assert structure["marginal_portfolio_gain_fallback_used"] is True


def test_keff_contribution_bounded() -> None:
    structure = resolve_engine_c_structure(_inputs(keff_contribution=1.0))
    assert structure["keff_contribution"] == pytest.approx(1.0)


def test_decisionnel_vs_observability_contract() -> None:
    observability_only = resolve_engine_c_structure(
        _inputs(
            engine_a_overlap_ratio=0.8,
            covered_share_by_engine_a=0.8,
            marginal_portfolio_gain=2.0,
        )
    )
    assert observability_only["duplication_possible_with_engine_a"] is True
    assert observability_only["local_duplication_policy_triggered"] is False
    assert observability_only["duplication_blocked"] is False

    blocked = resolve_engine_c_structure(
        _inputs(
            engine_a_overlap_ratio=0.8,
            covered_share_by_engine_a=0.8,
            marginal_portfolio_gain=-1.0,
        )
    )
    assert blocked["local_duplication_policy_triggered"] is True
    assert blocked["duplication_blocked"] is True
