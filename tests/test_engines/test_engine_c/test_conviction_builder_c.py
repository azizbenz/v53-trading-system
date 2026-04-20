from __future__ import annotations

import pytest

from engines.engine_c.conviction_builder_c import build_conviction_c


def test_low_conviction_is_not_emittable() -> None:
    """Fail-first: pre-patch low conviction still mapped to tier_1."""
    result = build_conviction_c(
        breakout_score=0.20,
        continuation_score=0.20,
        context_score=0.20,
        ce_expected=0.00002,
        ce_min=0.00012,
        fake_breakout_risk=0.0,
    )

    assert result.conviction_name == "low"
    assert result.tier_name == "no_trade"
    assert result.is_emittable is False


def test_medium_boundary_exact() -> None:
    result = build_conviction_c(
        breakout_score=0.67,
        continuation_score=0.67,
        context_score=0.67,
        ce_expected=0.67 * 0.00012,
        ce_min=0.00012,
        fake_breakout_risk=0.0,
    )

    assert result.raw_score == pytest.approx(0.67)
    assert result.conviction_score == pytest.approx(0.67)
    assert result.conviction_name == "medium"
    assert result.tier_name == "tier_1"
    assert result.is_emittable is True


def test_high_boundary_exact() -> None:
    result = build_conviction_c(
        breakout_score=0.82,
        continuation_score=0.82,
        context_score=0.82,
        ce_expected=0.82 * 0.00012,
        ce_min=0.00012,
        fake_breakout_risk=0.0,
    )

    assert result.raw_score == pytest.approx(0.82)
    assert result.conviction_score == pytest.approx(0.82)
    assert result.conviction_name == "high"
    assert result.tier_name == "tier_2"


def test_fake_breakout_penalty_reduces_conviction() -> None:
    low_risk = build_conviction_c(
        breakout_score=0.85,
        continuation_score=0.85,
        context_score=0.85,
        ce_expected=0.0002,
        ce_min=0.00012,
        fake_breakout_risk=0.1,
    )
    high_risk = build_conviction_c(
        breakout_score=0.85,
        continuation_score=0.85,
        context_score=0.85,
        ce_expected=0.0002,
        ce_min=0.00012,
        fake_breakout_risk=0.6,
    )

    assert high_risk.conviction_score < low_risk.conviction_score


def test_ce_component_is_capped_at_one() -> None:
    result = build_conviction_c(
        breakout_score=0.80,
        continuation_score=0.80,
        context_score=0.80,
        ce_expected=10.0,
        ce_min=0.00012,
        fake_breakout_risk=0.0,
    )

    assert result.ce_component == 1.0
