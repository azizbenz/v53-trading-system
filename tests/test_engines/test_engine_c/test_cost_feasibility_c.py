from __future__ import annotations

import pytest

from engines.engine_c.cost_feasibility_c import (
    ENGINE_C_CE_MIN_THRESHOLD_FAMILY_ID,
    ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_C_DELTA_SAFE_THRESHOLD_FAMILY_ID,
    CostReasonCodeC,
    EngineCCostCallerThresholds,
    evaluate_cost_feasibility_c,
)


def test_candidate_size_zero_is_not_feasible() -> None:
    """Fail-first: pre-patch candidate_size=0 still returned is_feasible=True."""
    result = evaluate_cost_feasibility_c(
        expected_gain=0.0100,
        expected_cost=0.0010,
        candidate_size=0.0,
        holding_period=1.0,
        delta_safe=0.0005,
        ce_min=0.0001,
    )

    assert result.is_feasible is False
    assert CostReasonCodeC.INVALID_CANDIDATE_SIZE in result.reason_codes
    assert CostReasonCodeC.NON_POSITIVE_EV_NET in result.reason_codes


def test_negative_candidate_size_rejected() -> None:
    with pytest.raises(ValueError, match="candidate_size must be >= 0"):
        evaluate_cost_feasibility_c(
            expected_gain=0.0100,
            expected_cost=0.0010,
            candidate_size=-1.0,
            holding_period=1.0,
            delta_safe=0.0005,
            ce_min=0.0001,
        )


def test_zero_holding_period_rejected_or_not_feasible() -> None:
    result = evaluate_cost_feasibility_c(
        expected_gain=0.0100,
        expected_cost=0.0010,
        candidate_size=100.0,
        holding_period=0.0,
        delta_safe=0.0005,
        ce_min=0.0001,
    )

    assert result.is_feasible is False
    assert CostReasonCodeC.INVALID_HOLDING_PERIOD in result.reason_codes


def test_cost_preference_score_bounded() -> None:
    result = evaluate_cost_feasibility_c(
        expected_gain=0.0,
        expected_cost=0.0010,
        candidate_size=100.0,
        holding_period=1.0,
        delta_safe=0.0005,
        ce_min=0.0001,
    )

    assert 0.0 <= result.cost_preference_score <= 1.0
    assert result.cost_preference_score == 0.0


def test_expected_gain_equal_boundary_not_feasible_if_strict() -> None:
    result = evaluate_cost_feasibility_c(
        expected_gain=0.0020,
        expected_cost=0.0015,
        candidate_size=100.0,
        holding_period=1.0,
        delta_safe=0.0005,
        ce_min=0.0001,
    )

    assert result.is_feasible is False
    assert CostReasonCodeC.EDGE_BELOW_COST_BUFFER in result.reason_codes


def test_reason_code_present_when_cost_infeasible() -> None:
    result = evaluate_cost_feasibility_c(
        expected_gain=0.0015,
        expected_cost=0.0014,
        candidate_size=100.0,
        holding_period=1.0,
        delta_safe=0.0005,
        ce_min=0.0003,
    )

    assert result.is_feasible is False
    assert result.reason_codes


def test_cost_threshold_ownership_is_explicit() -> None:
    thresholds = ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE

    assert isinstance(thresholds, EngineCCostCallerThresholds)
    assert thresholds.ce_min_threshold_family_id == ENGINE_C_CE_MIN_THRESHOLD_FAMILY_ID
    assert thresholds.delta_safe_threshold_family_id == ENGINE_C_DELTA_SAFE_THRESHOLD_FAMILY_ID
    assert thresholds.ce_min == pytest.approx(0.00015)
    assert thresholds.delta_safe == pytest.approx(0.0005)
