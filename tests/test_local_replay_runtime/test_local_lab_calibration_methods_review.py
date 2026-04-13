from __future__ import annotations

from local_replay_runtime import (
    LocalLabCalibrationMethodsStatus,
    build_local_lab_calibration_methods_review,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _records_from_returns(returns: tuple[float, ...]):
    return tuple(
        build_dtr(
            dtr_id=f"dtr-calibration-{index}",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0004,
            realized_cost=0.0001,
            gross_return=value,
            ce_expected=0.0015,
            regime="trend" if index % 2 == 0 else "range",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=1.0,
            timestamp=1_700_000_000.0 + (index * 60.0),
        )
        for index, value in enumerate(returns)
    )


def test_local_lab_calibration_methods_review_is_ready_for_stable_positive_history():
    returns = tuple(
        0.0025 + (((index % 9) - 4) * 0.00015) + (0.0004 if index % 7 == 0 else -0.0001)
        for index in range(30)
    )

    review = build_local_lab_calibration_methods_review(
        correlation_id="corr-calibration-review",
        export_dir="E:/lab/export",
        run_id="run-calibration-review",
        records=_records_from_returns(returns),
    )

    assert review.review_status == LocalLabCalibrationMethodsStatus.READY
    assert review.review_ready is True
    assert review.walk_forward_plan_status == "ready"
    assert review.walk_forward_plan_ready is True
    assert review.walk_forward_plan is not None
    assert review.stationarity_status == "ready"
    assert review.stationarity_ready is True
    assert review.stationarity_pass is True
    assert review.stationarity_result is not None
    assert review.dsr_status == "ready"
    assert review.dsr_ready is True
    assert review.dsr_pass is True
    assert review.dsr_result is not None
    assert review.dsr_result.dsr >= review.dsr_floor
    assert review.blocking_reasons == ()


def test_local_lab_calibration_methods_review_is_partial_when_history_is_short():
    review = build_local_lab_calibration_methods_review(
        correlation_id="corr-calibration-review",
        export_dir="E:/lab/export",
        run_id="run-calibration-review",
        records=_records_from_returns((0.0011, 0.0015, 0.0012, 0.0010, 0.0013)),
    )

    assert review.review_status == LocalLabCalibrationMethodsStatus.PARTIAL
    assert review.review_ready is False
    assert review.walk_forward_plan_status == "insufficient_history"
    assert review.walk_forward_plan_ready is False
    assert review.stationarity_status == "insufficient_history"
    assert review.stationarity_ready is False
    assert review.stationarity_pass is None
    assert review.dsr_status == "insufficient_history"
    assert review.dsr_ready is False
    assert review.dsr_pass is None
    assert review.blocking_reasons == ()
    assert "CALIBRATION_METHODS_WALK_FORWARD_HISTORY_INSUFFICIENT" in review.caution_flags
    assert "CALIBRATION_METHODS_STATIONARITY_HISTORY_INSUFFICIENT" in review.caution_flags
    assert "CALIBRATION_METHODS_DSR_HISTORY_INSUFFICIENT" in review.caution_flags


def test_local_lab_calibration_methods_review_blocks_when_dsr_fails_floor():
    current = 0.0
    returns_series: list[float] = []
    shocks = (0.00020, -0.00012, 0.00008, -0.00005, 0.00003, -0.00002, 0.00001)
    for index in range(30):
        current = (0.65 * current) + shocks[index % len(shocks)]
        returns_series.append(current - 0.00006)
    returns = tuple(returns_series)

    review = build_local_lab_calibration_methods_review(
        correlation_id="corr-calibration-review",
        export_dir="E:/lab/export",
        run_id="run-calibration-review",
        records=_records_from_returns(returns),
    )

    assert review.review_status == LocalLabCalibrationMethodsStatus.BLOCKED
    assert review.review_ready is False
    assert review.walk_forward_plan_ready is True
    assert review.stationarity_ready is True
    assert review.stationarity_pass is True
    assert review.dsr_status == "failed_threshold"
    assert review.dsr_ready is True
    assert review.dsr_pass is False
    assert review.dsr_result is not None
    assert review.dsr_result.dsr < review.dsr_floor
    assert review.blocking_reasons == ("CALIBRATION_METHODS_DSR_BELOW_FLOOR",)


def test_local_lab_calibration_methods_review_blocks_when_stationarity_fails():
    returns = tuple(0.0002 * index for index in range(30))

    review = build_local_lab_calibration_methods_review(
        correlation_id="corr-calibration-review",
        export_dir="E:/lab/export",
        run_id="run-calibration-review",
        records=_records_from_returns(returns),
    )

    assert review.review_status == LocalLabCalibrationMethodsStatus.BLOCKED
    assert review.review_ready is False
    assert review.walk_forward_plan_ready is True
    assert review.stationarity_status == "failed_threshold"
    assert review.stationarity_ready is True
    assert review.stationarity_pass is False
    assert review.stationarity_result is not None
    assert review.dsr_ready is True
    assert "CALIBRATION_METHODS_STATIONARITY_FAILED" in review.blocking_reasons
