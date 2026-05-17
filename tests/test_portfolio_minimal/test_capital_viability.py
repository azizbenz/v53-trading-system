from __future__ import annotations

import pytest

from portfolio_minimal.allocation_router.capital_viability import (
    analyze_capital_fragmentation,
    assess_pair_min_notional_viability,
)


def test_min_notional_infeasible_pair_is_blocked_for_bucket() -> None:
    assessment = assess_pair_min_notional_viability(
        pair="BTCUSDT",
        capital_bucket=400,
        planned_notional=8.0,
        min_notional=10.0,
        size_reduced=True,
        fragmented=True,
    )

    assert assessment.min_notional_viable is False
    assert assessment.min_notional_status == "MIN_NOTIONAL_NOT_VIABLE_FOR_BUCKET"
    assert "PAIR_BLOCKED_BY_MIN_NOTIONAL" in assessment.min_notional_reason_codes
    assert "PAIR_BLOCKED_BY_SIZE_REDUCTION" in assessment.min_notional_reason_codes
    assert "PAIR_BLOCKED_BY_CAPITAL_FRAGMENTATION" in assessment.min_notional_reason_codes


def test_missing_min_notional_data_stays_not_proven() -> None:
    assessment = assess_pair_min_notional_viability(
        pair="ETHUSDT",
        capital_bucket=500,
        planned_notional=None,
        min_notional=10.0,
    )

    assert assessment.min_notional_status == "MIN_NOTIONAL_NOT_PROVEN"
    assert assessment.min_notional_block_rate is None


def test_high_fragmentation_marks_pair_universe_too_wide_for_small_capital() -> None:
    assessment = analyze_capital_fragmentation(
        capital_bucket=400,
        candidate_pair_count=12,
        allocated_notionals=(14.0, 12.0, 10.0, 9.0),
        max_active_pairs=3,
    )

    assert assessment.pair_universe_too_wide_status == "PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL"
    assert assessment.recommended_max_active_pairs == 3
    assert assessment.fragmentation_rate == pytest.approx(0.75, abs=1e-6)


def test_fragmentation_without_measured_allocations_stays_not_proven() -> None:
    assessment = analyze_capital_fragmentation(
        capital_bucket=1500,
        candidate_pair_count=4,
        allocated_notionals=(),
        max_active_pairs=None,
    )

    assert assessment.pair_universe_too_wide_status == "FRAGMENTATION_NOT_PROVEN"
    assert assessment.fragmentation_rate is None
