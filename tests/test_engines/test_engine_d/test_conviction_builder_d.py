from __future__ import annotations

import pytest

from engines.engine_d.conviction_builder_d import build_conviction_d


def test_low_conviction_is_not_emittable() -> None:
    """Fail-first: pre-patch low conviction still mapped to tier_1."""
    result = build_conviction_d(
        history_score=0.20,
        reformation_score=0.20,
        marginal_value_score=0.20,
        ce_expected=0.00002,
        ce_min=0.00012,
        concentration_risk=0.0,
    )

    assert result.conviction_name == "low"
    assert result.tier_name == "no_trade"
    assert result.is_emittable is False


def test_medium_boundary_exact() -> None:
    result = build_conviction_d(
        history_score=0.64,
        reformation_score=0.64,
        marginal_value_score=0.64,
        ce_expected=0.64 * 0.00012,
        ce_min=0.00012,
        concentration_risk=0.0,
    )

    assert result.raw_score == pytest.approx(0.64)
    assert result.conviction_score == pytest.approx(0.64)
    assert result.conviction_name == "medium"
    assert result.tier_name == "tier_1"
    assert result.is_emittable is True


def test_high_boundary_exact() -> None:
    result = build_conviction_d(
        history_score=0.80,
        reformation_score=0.80,
        marginal_value_score=0.80,
        ce_expected=0.80 * 0.00012,
        ce_min=0.00012,
        concentration_risk=0.0,
    )

    assert result.raw_score == pytest.approx(0.80)
    assert result.conviction_score == pytest.approx(0.80)
    assert result.conviction_name == "high"
    assert result.tier_name == "tier_2"


def test_concentration_penalty_reduces_conviction() -> None:
    low_risk = build_conviction_d(
        history_score=0.85,
        reformation_score=0.85,
        marginal_value_score=0.85,
        ce_expected=0.0002,
        ce_min=0.00012,
        concentration_risk=0.1,
    )
    high_risk = build_conviction_d(
        history_score=0.85,
        reformation_score=0.85,
        marginal_value_score=0.85,
        ce_expected=0.0002,
        ce_min=0.00012,
        concentration_risk=0.6,
    )

    assert high_risk.conviction_score < low_risk.conviction_score


def test_ce_component_is_capped_at_one() -> None:
    result = build_conviction_d(
        history_score=0.80,
        reformation_score=0.80,
        marginal_value_score=0.80,
        ce_expected=10.0,
        ce_min=0.00012,
        concentration_risk=0.0,
    )

    assert result.ce_component == 1.0
