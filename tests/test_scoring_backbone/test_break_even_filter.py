from __future__ import annotations

import pytest

from scoring_backbone import BreakEvenFilterConfig, evaluate_break_even_filter


def test_break_even_filter_blocks_when_gain_is_below_break_even() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0010,
        expected_cost=0.0010,
        candidate_size=100.0,
        delta_safe=0.0002,
        expected_ce=0.0001,
        ce_min=0.0001,
    )

    assert decision.allowed is False
    assert decision.reason_code == "BREAK_EVEN_NOT_CLEARED"


def test_break_even_filter_blocks_on_strict_boundary() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0012,
        expected_cost=0.0010,
        candidate_size=100.0,
        delta_safe=0.0002,
    )

    assert decision.allowed is False
    assert decision.reason_code == "BREAK_EVEN_NOT_CLEARED"


def test_break_even_filter_passes_when_gain_clears_break_even_and_ce_floor() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
        delta_safe=0.0002,
        expected_ce=0.0010,
        ce_min=0.0005,
    )

    assert decision.allowed is True
    assert decision.reason_code == ""
    assert decision.expected_break_even == pytest.approx(0.0012)
    assert decision.ev_net == pytest.approx(0.2)


def test_break_even_filter_blocks_when_ce_is_below_floor() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
        delta_safe=0.0002,
        expected_ce=0.0001,
        ce_min=0.0005,
    )

    assert decision.allowed is False
    assert decision.reason_code == "CE_BELOW_MINIMUM"


def test_break_even_filter_blocks_when_ev_net_is_below_floor() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
        delta_safe=0.0002,
        config=BreakEvenFilterConfig(min_ev_net=0.25),
    )

    assert decision.allowed is False
    assert decision.reason_code == "EV_NET_BELOW_FLOOR"


def test_break_even_filter_respects_shared_ev_net_floor_threshold() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.20,
        expected_cost=0.10,
        candidate_size=1.0,
        config=BreakEvenFilterConfig(min_ev_net=0.05),
    )

    assert decision.allowed is True
    assert decision.ev_net == pytest.approx(0.10)


def test_break_even_filter_zero_floor_keeps_strict_break_even_boundary() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.05,
        expected_cost=0.05,
        candidate_size=1.0,
        config=BreakEvenFilterConfig(min_ev_net=0.0),
    )

    assert decision.allowed is False
    assert decision.reason_code == "BREAK_EVEN_NOT_CLEARED"


def test_break_even_filter_rejects_negative_ev_net_floor() -> None:
    with pytest.raises(ValueError):
        BreakEvenFilterConfig(min_ev_net=-0.01)


def test_break_even_filter_rejects_invalid_candidate_size() -> None:
    with pytest.raises(ValueError, match="candidate_size"):
        evaluate_break_even_filter(
            expected_gain=0.0030,
            expected_cost=0.0010,
            candidate_size=0.0,
        )


def test_break_even_filter_rejects_incomplete_cost_model_when_strict_completeness_required() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
        cost_model_completeness_status="PARTIAL_NO_FEE_NO_IMPACT",
        config=BreakEvenFilterConfig(require_complete_cost_model=True),
    )

    assert decision.allowed is False
    assert decision.reason_code == "COST_MODEL_INCOMPLETE"
    assert decision.partial_cost_model is True
    assert decision.cost_gate_status == "COST_MODEL_INCOMPLETE"


def test_break_even_filter_labels_partial_cost_model_without_changing_math_when_not_strict() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
        cost_model_completeness_status="PARTIAL_NO_FEE_NO_IMPACT",
        config=BreakEvenFilterConfig(require_complete_cost_model=False),
    )

    assert decision.allowed is True
    assert decision.expected_break_even == pytest.approx(0.0010)
    assert decision.ev_net == pytest.approx(0.2)
    assert decision.partial_cost_model is True
    assert decision.cost_gate_status == "PARTIAL_COST_MODEL"


def test_break_even_filter_defaults_missing_cost_status_to_unknown_not_complete() -> None:
    decision = evaluate_break_even_filter(
        expected_gain=0.0030,
        expected_cost=0.0010,
        candidate_size=100.0,
    )

    assert decision.cost_model_completeness_status == "UNKNOWN"
    assert decision.partial_cost_model is True
    assert decision.cost_gate_status == "PARTIAL_COST_MODEL"
