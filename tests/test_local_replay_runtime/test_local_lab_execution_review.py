from __future__ import annotations

from local_replay_runtime.local_lab_execution_review import (
    LocalLabExecutionTelemetry,
    build_local_lab_execution_review,
)


def test_local_lab_execution_review_is_partial_when_telemetry_is_missing():
    review = build_local_lab_execution_review(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        telemetry=None,
    )

    assert review.review_status == "partial"
    assert review.review_ready is False
    assert review.telemetry_present is False
    assert review.threshold_count == 5
    assert review.ready_threshold_count == 0
    assert review.partial_threshold_count == 5
    assert review.blocked_threshold_count == 0
    assert review.thresholds[0].threshold_id == "THR-X01"
    assert review.thresholds[1].threshold_id == "THR-X02"
    assert review.thresholds[2].threshold_id == "THR-X03"
    assert review.thresholds[3].threshold_id == "THR-X04"
    assert review.thresholds[4].threshold_id == "THR-X05"


def test_local_lab_execution_review_becomes_ready_when_x03_x05_models_fit():
    telemetry = LocalLabExecutionTelemetry(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        source_session_dates=("2026-04-01", "2026-04-02"),
        time_sync_offsets_ms=(20.0, 25.0, 30.0, 35.0, 40.0, 42.0, 45.0, 4_000.0),
        time_sync_observation_days=7.5,
        quota_call_counts=(8, 9, 10),
        quota_probe_durations_s=(4.0, 4.5, 5.0),
        quota_limit_calls_per_minute_values=(120, 120, 120),
        quota_calls_per_minute_observed=(120.0, 120.0, 120.0),
        quota_observation_days=31.0,
        websocket_interarrival_s=(0.05, 0.08, 0.11, 0.12, 0.15, 0.18, 0.22, 0.30),
        websocket_observation_days=31.0,
        spread_bps=(1.0, 1.4, 1.8, 2.0, 2.4, 2.7, 3.2, 4.1),
        spread_observation_days=31.0,
        slippage_bps=(1.5, 1.9, 2.1, 2.8),
        slippage_observation_days=31.0,
        candidate_sizes=(6.5, 9.5, 12.5, 16.5),
        candidate_size_observation_days=31.0,
        final_sizes=(6.0, 9.0, 12.0, 16.0),
        final_size_observation_days=31.0,
        coverage_caution_flags=("THR-X02_ACCEPTED_EVENTS_ONLY",),
    )

    review = build_local_lab_execution_review(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        telemetry=telemetry,
    )

    assert review.review_status == "ready"
    assert review.review_ready is True
    assert review.telemetry_present is True
    assert review.ready_threshold_count == 5
    assert review.partial_threshold_count == 0
    assert review.thresholds[0].threshold_id == "THR-X01"
    assert review.thresholds[0].published_value is not None
    assert review.thresholds[0].published_value <= 1_000.0
    assert review.thresholds[1].threshold_id == "THR-X02"
    assert review.thresholds[1].published_value is not None
    assert review.thresholds[1].published_value <= 5.0
    assert review.thresholds[2].threshold_id == "THR-X03"
    assert review.thresholds[2].review_status == "ready"
    assert review.thresholds[2].published_value == 0.8
    assert review.thresholds[2].caution_flags == ("THR-X03_HUMAN_HARD_CAP_CLIPPED",)
    assert review.thresholds[3].threshold_id == "THR-X04"
    assert review.thresholds[3].published_value is not None
    assert review.thresholds[3].published_value <= 50.0
    assert review.thresholds[4].threshold_id == "THR-X05"
    assert review.thresholds[4].review_status == "ready"
    assert review.thresholds[4].published_value is not None
    assert review.thresholds[4].slippage_model_estimate is not None
    assert review.thresholds[4].slippage_model_estimate.r_squared >= 0.3
    assert review.thresholds[4].caution_flags == ()
    assert "THR-X02_ACCEPTED_EVENTS_ONLY" in review.caution_flags
    assert "THR-X03_HUMAN_HARD_CAP_CLIPPED" in review.caution_flags


def test_local_lab_execution_review_is_partial_when_spread_history_is_insufficient():
    telemetry = LocalLabExecutionTelemetry(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        time_sync_offsets_ms=(20.0, 25.0, 30.0, 35.0, 40.0, 42.0, 45.0, 4_000.0),
        time_sync_observation_days=7.5,
        websocket_interarrival_s=(0.05, 0.08, 0.11, 0.12, 0.15, 0.18, 0.22, 0.30),
        websocket_observation_days=31.0,
        spread_bps=(1.0, 1.4, 1.8, 2.0, 2.4, 2.7, 3.2, 4.1),
        spread_observation_days=14.0,
    )

    review = build_local_lab_execution_review(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        telemetry=telemetry,
    )

    assert review.review_status == "partial"
    assert review.review_ready is False
    assert review.ready_threshold_count == 2
    assert review.partial_threshold_count == 3
    assert review.thresholds[3].threshold_id == "THR-X04"
    assert review.thresholds[3].review_status == "partial"
    assert review.thresholds[3].caution_flags == ("THR-X04_EXECUTION_HISTORY_LT_30D",)


def test_local_lab_execution_review_marks_x03_partial_when_quota_cap_is_missing():
    telemetry = LocalLabExecutionTelemetry(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        quota_call_counts=(8, 9, 10),
        quota_probe_durations_s=(4.0, 4.5, 5.0),
        quota_calls_per_minute_observed=(120.0, 120.0, 120.0),
        quota_observation_days=31.0,
    )

    review = build_local_lab_execution_review(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        telemetry=telemetry,
    )

    assert review.review_status == "partial"
    assert review.thresholds[2].threshold_id == "THR-X03"
    assert review.thresholds[2].review_status == "partial"
    assert review.thresholds[2].observation_count == 3
    assert review.thresholds[2].observation_days == 31.0
    assert review.thresholds[2].caution_flags == ("THR-X03_SERVICE_RATE_LIMIT_CAP_MISSING",)


def test_local_lab_execution_review_marks_x05_ready_with_final_size_slippage_model():
    telemetry = LocalLabExecutionTelemetry(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        slippage_bps=(1.5, 1.8, 2.0, 2.4),
        slippage_observation_days=31.0,
        final_sizes=(6.0, 9.0, 12.0, 16.0),
        final_size_observation_days=31.0,
    )

    review = build_local_lab_execution_review(
        correlation_id="corr-execution",
        export_dir="E:/lab/export_dir",
        run_id="run-execution",
        telemetry=telemetry,
    )

    assert review.thresholds[4].threshold_id == "THR-X05"
    assert review.thresholds[4].review_status == "ready"
    assert review.thresholds[4].slippage_model_estimate is not None
    assert review.thresholds[4].slippage_model_estimate.size_proxy == "final_size"
    assert review.thresholds[4].slippage_model_estimate.r_squared >= 0.3
