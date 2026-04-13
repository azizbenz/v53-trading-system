from __future__ import annotations

from local_replay_runtime.local_lab_execution_review import (
    LocalLabExecutionTelemetry,
    build_local_lab_execution_review,
)
from local_replay_runtime.local_lab_execution_runtime_projection import (
    build_local_lab_execution_runtime_projection,
)


def test_local_lab_execution_runtime_projection_is_partial_without_execution_telemetry():
    review = build_local_lab_execution_review(
        correlation_id="corr-projection",
        export_dir="E:/lab/export",
        run_id="run-projection",
        telemetry=None,
    )

    projection = build_local_lab_execution_runtime_projection(review)

    assert projection.projection_status == "partial"
    assert projection.projection_ready is False
    assert projection.consumer_count == 3
    assert projection.partial_consumer_count == 3
    assert projection.blocked_consumer_count == 0
    assert projection.consumers[0].consumer_id == "rate_limiter"
    assert projection.consumers[0].projection_status == "partial"
    assert projection.consumers[1].consumer_id == "spread_guard"
    assert projection.consumers[1].projection_status == "partial"
    assert projection.consumers[2].consumer_id == "slippage_model"
    assert projection.consumers[2].projection_status == "partial"


def test_local_lab_execution_runtime_projection_becomes_ready_when_x03_x05_models_fit():
    telemetry = LocalLabExecutionTelemetry(
        correlation_id="corr-projection",
        export_dir="E:/lab/export",
        run_id="run-projection",
        time_sync_offsets_ms=(120.0, 180.0, 220.0, 310.0),
        time_sync_observation_days=7.0,
        websocket_interarrival_s=(0.10, 0.15, 0.20, 0.25),
        websocket_observation_days=30.0,
        quota_call_counts=(35, 42, 48, 50),
        quota_probe_durations_s=(60.0, 60.0, 60.0, 60.0),
        quota_calls_per_minute_observed=(35.0, 42.0, 48.0, 50.0),
        quota_limit_calls_per_minute_values=(90, 90, 90, 90),
        quota_observation_days=30.0,
        spread_bps=(8.0, 11.0, 15.0, 22.0),
        spread_observation_days=30.0,
        slippage_bps=(1.5, 1.8, 2.0, 2.4),
        slippage_observation_days=30.0,
        candidate_sizes=(6.0, 9.0, 12.0, 16.0),
        candidate_size_observation_days=30.0,
        final_sizes=(6.0, 9.0, 12.0, 16.0),
        final_size_observation_days=30.0,
        coverage_caution_flags=("THR-X02_ACCEPTED_EVENTS_ONLY",),
    )
    review = build_local_lab_execution_review(
        correlation_id="corr-projection",
        export_dir="E:/lab/export",
        run_id="run-projection",
        telemetry=telemetry,
    )

    projection = build_local_lab_execution_runtime_projection(review)

    assert projection.projection_status == "ready"
    assert projection.projection_ready is True
    assert projection.ready_consumer_count == 3
    assert projection.partial_consumer_count == 0
    assert projection.blocked_consumer_count == 0
    rate_limiter = projection.consumers[0]
    assert rate_limiter.consumer_id == "rate_limiter"
    assert rate_limiter.projection_status == "ready"
    assert rate_limiter.projection_value == 0.8
    assert rate_limiter.projection_value_semantics == "max_observed_quota_ratio_before_throttle"
    spread_guard = projection.consumers[1]
    assert spread_guard.consumer_id == "spread_guard"
    assert spread_guard.projection_status == "ready"
    assert spread_guard.projection_value is not None and spread_guard.projection_value > 0.0
    assert spread_guard.projection_value_semantics == "max_observed_spread_bps_before_no_trade"
    slippage_model = projection.consumers[2]
    assert slippage_model.consumer_id == "slippage_model"
    assert slippage_model.projection_status == "ready"
    assert slippage_model.reference_size is not None
    assert slippage_model.r_squared is not None and slippage_model.r_squared >= 0.3
    assert slippage_model.projection_value_semantics == "reference_slippage_bps_at_q95_size"
