"""Local IA Lab execution-threshold review for THR-X01 to THR-X05."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from calibration_methods import (
    ExecutionCalibrationError,
    ExecutionSlippageModelEstimate,
    ExecutionThresholdEstimate,
    calibrate_rate_limit_throttle_ratio,
    calibrate_slippage_model_bps,
    calibrate_spread_guard_threshold_bps,
    calibrate_time_sync_threshold_ms,
    calibrate_websocket_gap_threshold_s,
)


class LocalLabExecutionReviewStatus(StrEnum):
    """Bounded statuses for execution-threshold review."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class LocalLabExecutionTelemetry(BaseModel, frozen=True):
    """Optional Local IA Lab execution telemetry sidecar."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    source_session_dates: tuple[str, ...] = ()
    time_sync_offsets_ms: tuple[float, ...] = ()
    time_sync_observation_days: float | None = Field(default=None, ge=0.0)
    time_sync_session_dates: tuple[str, ...] = ()
    time_sync_source_refs: tuple[str, ...] = ()
    quota_call_counts: tuple[int, ...] = ()
    quota_probe_durations_s: tuple[float, ...] = ()
    quota_limit_calls_per_minute_values: tuple[int, ...] = ()
    quota_calls_per_minute_observed: tuple[float, ...] = ()
    quota_observation_days: float | None = Field(default=None, ge=0.0)
    quota_session_dates: tuple[str, ...] = ()
    quota_source_refs: tuple[str, ...] = ()
    websocket_interarrival_s: tuple[float, ...] = ()
    websocket_observation_days: float | None = Field(default=None, ge=0.0)
    websocket_session_dates: tuple[str, ...] = ()
    websocket_source_refs: tuple[str, ...] = ()
    spread_bps: tuple[float, ...] = ()
    spread_observation_days: float | None = Field(default=None, ge=0.0)
    spread_session_dates: tuple[str, ...] = ()
    spread_source_refs: tuple[str, ...] = ()
    slippage_bps: tuple[float, ...] = ()
    slippage_observation_days: float | None = Field(default=None, ge=0.0)
    slippage_session_dates: tuple[str, ...] = ()
    slippage_source_refs: tuple[str, ...] = ()
    candidate_sizes: tuple[float, ...] = ()
    candidate_size_observation_days: float | None = Field(default=None, ge=0.0)
    candidate_size_session_dates: tuple[str, ...] = ()
    candidate_size_source_refs: tuple[str, ...] = ()
    final_sizes: tuple[float, ...] = ()
    final_size_observation_days: float | None = Field(default=None, ge=0.0)
    final_size_session_dates: tuple[str, ...] = ()
    final_size_source_refs: tuple[str, ...] = ()
    coverage_caution_flags: tuple[str, ...] = ()


class LocalLabExecutionThresholdReview(BaseModel, frozen=True):
    """Audit-ready review of one execution threshold."""

    threshold_id: str = Field(..., min_length=1)
    review_status: LocalLabExecutionReviewStatus
    fit_ready: bool = False
    observation_count: int = Field(default=0, ge=0)
    filtered_observation_count: int = Field(default=0, ge=0)
    observation_days: float | None = Field(default=None, ge=0.0)
    method: str = Field(default="not_evaluated", min_length=1)
    unit: str = ""
    published_value: float | None = None
    point_estimate: float | None = None
    hard_cap_human: float | None = None
    hard_cap_satisfied: bool | None = None
    hard_cap_binding: bool | None = None
    threshold_estimate: ExecutionThresholdEstimate | None = None
    slippage_model_estimate: ExecutionSlippageModelEstimate | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


class LocalLabExecutionReview(BaseModel, frozen=True):
    """Audit-ready Local IA Lab review over EXECUTION thresholds."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_status: LocalLabExecutionReviewStatus
    review_ready: bool = False
    telemetry_present: bool = False
    threshold_count: int = Field(default=0, ge=0)
    ready_threshold_count: int = Field(default=0, ge=0)
    partial_threshold_count: int = Field(default=0, ge=0)
    blocked_threshold_count: int = Field(default=0, ge=0)
    thresholds: tuple[LocalLabExecutionThresholdReview, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_local_lab_execution_review(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionReview:
    """Build the bounded Local IA Lab execution-threshold review."""

    if telemetry is not None:
        if telemetry.correlation_id != correlation_id:
            raise ValueError("Execution telemetry correlation_id must match the review correlation_id")
        if telemetry.export_dir != export_dir:
            raise ValueError("Execution telemetry export_dir must match the review export_dir")
        if telemetry.run_id != run_id:
            raise ValueError("Execution telemetry run_id must match the review run_id")

    x01 = _build_x01_review(telemetry)
    x02 = _build_x02_review(telemetry)
    x03 = _build_x03_review(telemetry)
    x04 = _build_x04_review(telemetry)
    x05 = _build_x05_review(telemetry)
    thresholds = (x01, x02, x03, x04, x05)
    ready_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "ready")
    partial_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "partial")
    blocked_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "blocked")

    if blocked_threshold_count > 0:
        review_status = LocalLabExecutionReviewStatus.BLOCKED
    elif partial_threshold_count > 0:
        review_status = LocalLabExecutionReviewStatus.PARTIAL
    else:
        review_status = LocalLabExecutionReviewStatus.READY

    return LocalLabExecutionReview(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        review_status=review_status,
        review_ready=review_status == LocalLabExecutionReviewStatus.READY,
        telemetry_present=telemetry is not None,
        threshold_count=len(thresholds),
        ready_threshold_count=ready_threshold_count,
        partial_threshold_count=partial_threshold_count,
        blocked_threshold_count=blocked_threshold_count,
        thresholds=thresholds,
        blocking_reasons=tuple(
            dict.fromkeys(reason for threshold in thresholds for reason in threshold.blocking_reasons)
        ),
        caution_flags=tuple(
            dict.fromkeys(
                (
                    tuple(telemetry.coverage_caution_flags)
                    if telemetry is not None
                    else ()
                )
                + tuple(flag for threshold in thresholds for flag in threshold.caution_flags)
            )
        ),
    )


def _build_x01_review(
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionThresholdReview:
    threshold_id = "THR-X01"
    if telemetry is None or not telemetry.time_sync_offsets_ms:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            caution_flags=("THR-X01_EXECUTION_TELEMETRY_MISSING",),
        )
    if telemetry.time_sync_observation_days is None or telemetry.time_sync_observation_days < 7.0:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.time_sync_offsets_ms),
            observation_days=telemetry.time_sync_observation_days,
            caution_flags=("THR-X01_EXECUTION_HISTORY_LT_7D",),
        )
    try:
        estimate = calibrate_time_sync_threshold_ms(tuple(telemetry.time_sync_offsets_ms))
    except ExecutionCalibrationError as exc:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.BLOCKED,
            observation_count=len(telemetry.time_sync_offsets_ms),
            observation_days=telemetry.time_sync_observation_days,
            blocking_reasons=("THR-X01_EXECUTION_CALIBRATION_INVALID",),
            caution_flags=(str(exc),),
        )
    return LocalLabExecutionThresholdReview(
        threshold_id=threshold_id,
        review_status=LocalLabExecutionReviewStatus.READY,
        fit_ready=True,
        observation_count=estimate.observation_count,
        filtered_observation_count=estimate.filtered_observation_count,
        observation_days=telemetry.time_sync_observation_days,
        method=estimate.method,
        unit=estimate.unit,
        published_value=estimate.published_value,
        point_estimate=estimate.point_estimate,
        hard_cap_human=estimate.hard_cap_human,
        hard_cap_satisfied=estimate.hard_cap_satisfied,
        hard_cap_binding=estimate.hard_cap_binding,
        threshold_estimate=estimate,
        caution_flags=(
            ("THR-X01_HUMAN_HARD_CAP_CLIPPED",) if estimate.hard_cap_binding else ()
        ),
    )


def _build_x02_review(
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionThresholdReview:
    threshold_id = "THR-X02"
    if telemetry is None or not telemetry.websocket_interarrival_s:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            caution_flags=("THR-X02_EXECUTION_TELEMETRY_MISSING",),
        )
    if telemetry.websocket_observation_days is None or telemetry.websocket_observation_days < 30.0:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.websocket_interarrival_s),
            observation_days=telemetry.websocket_observation_days,
            caution_flags=("THR-X02_EXECUTION_HISTORY_LT_30D",),
        )
    try:
        estimate = calibrate_websocket_gap_threshold_s(tuple(telemetry.websocket_interarrival_s))
    except ExecutionCalibrationError as exc:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.BLOCKED,
            observation_count=len(telemetry.websocket_interarrival_s),
            observation_days=telemetry.websocket_observation_days,
            blocking_reasons=("THR-X02_EXECUTION_CALIBRATION_INVALID",),
            caution_flags=(str(exc),),
        )
    return LocalLabExecutionThresholdReview(
        threshold_id=threshold_id,
        review_status=LocalLabExecutionReviewStatus.READY,
        fit_ready=True,
        observation_count=estimate.observation_count,
        filtered_observation_count=estimate.filtered_observation_count,
        observation_days=telemetry.websocket_observation_days,
        method=estimate.method,
        unit=estimate.unit,
        published_value=estimate.published_value,
        point_estimate=estimate.point_estimate,
        hard_cap_human=estimate.hard_cap_human,
        hard_cap_satisfied=estimate.hard_cap_satisfied,
        hard_cap_binding=estimate.hard_cap_binding,
        threshold_estimate=estimate,
        caution_flags=(
            ("THR-X02_HUMAN_HARD_CAP_CLIPPED",) if estimate.hard_cap_binding else ()
        ),
    )


def _build_x03_review(
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionThresholdReview:
    threshold_id = "THR-X03"
    if telemetry is None or not telemetry.quota_call_counts:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            caution_flags=("THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING",),
        )
    if not telemetry.quota_limit_calls_per_minute_values:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.quota_call_counts),
            observation_days=telemetry.quota_observation_days,
            caution_flags=("THR-X03_SERVICE_RATE_LIMIT_CAP_MISSING",),
        )
    if telemetry.quota_observation_days is None or telemetry.quota_observation_days < 30.0:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.quota_call_counts),
            observation_days=telemetry.quota_observation_days,
            caution_flags=("THR-X03_EXECUTION_HISTORY_LT_30D",),
        )
    try:
        estimate = calibrate_rate_limit_throttle_ratio(
            quota_call_counts=telemetry.quota_call_counts,
            quota_probe_durations_s=telemetry.quota_probe_durations_s,
            quota_limit_calls_per_minute_values=telemetry.quota_limit_calls_per_minute_values,
            observed_calls_per_minute=telemetry.quota_calls_per_minute_observed,
        )
    except ExecutionCalibrationError as exc:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.BLOCKED,
            observation_count=len(telemetry.quota_call_counts),
            observation_days=telemetry.quota_observation_days,
            blocking_reasons=("THR-X03_EXECUTION_CALIBRATION_INVALID",),
            caution_flags=(str(exc),),
        )
    return LocalLabExecutionThresholdReview(
        threshold_id=threshold_id,
        review_status=LocalLabExecutionReviewStatus.READY,
        fit_ready=True,
        observation_count=estimate.observation_count,
        filtered_observation_count=estimate.filtered_observation_count,
        observation_days=telemetry.quota_observation_days,
        method=estimate.method,
        unit=estimate.unit,
        published_value=estimate.published_value,
        point_estimate=estimate.point_estimate,
        hard_cap_human=estimate.hard_cap_human,
        hard_cap_satisfied=estimate.hard_cap_satisfied,
        hard_cap_binding=estimate.hard_cap_binding,
        threshold_estimate=estimate,
        caution_flags=(
            ("THR-X03_HUMAN_HARD_CAP_CLIPPED",) if estimate.hard_cap_binding else ()
        ),
    )


def _build_x04_review(
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionThresholdReview:
    threshold_id = "THR-X04"
    if telemetry is None or not telemetry.spread_bps:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            caution_flags=("THR-X04_EXECUTION_TELEMETRY_MISSING",),
        )
    if telemetry.spread_observation_days is None or telemetry.spread_observation_days < 30.0:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.spread_bps),
            observation_days=telemetry.spread_observation_days,
            caution_flags=("THR-X04_EXECUTION_HISTORY_LT_30D",),
        )
    try:
        estimate = calibrate_spread_guard_threshold_bps(tuple(telemetry.spread_bps))
    except ExecutionCalibrationError as exc:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.BLOCKED,
            observation_count=len(telemetry.spread_bps),
            observation_days=telemetry.spread_observation_days,
            blocking_reasons=("THR-X04_EXECUTION_CALIBRATION_INVALID",),
            caution_flags=(str(exc),),
        )
    return LocalLabExecutionThresholdReview(
        threshold_id=threshold_id,
        review_status=LocalLabExecutionReviewStatus.READY,
        fit_ready=True,
        observation_count=estimate.observation_count,
        filtered_observation_count=estimate.filtered_observation_count,
        observation_days=telemetry.spread_observation_days,
        method=estimate.method,
        unit=estimate.unit,
        published_value=estimate.published_value,
        point_estimate=estimate.point_estimate,
        hard_cap_human=estimate.hard_cap_human,
        hard_cap_satisfied=estimate.hard_cap_satisfied,
        hard_cap_binding=estimate.hard_cap_binding,
        threshold_estimate=estimate,
        caution_flags=(
            ("THR-X04_HUMAN_HARD_CAP_CLIPPED",) if estimate.hard_cap_binding else ()
        ),
    )


def _build_x05_review(
    telemetry: LocalLabExecutionTelemetry | None,
) -> LocalLabExecutionThresholdReview:
    threshold_id = "THR-X05"
    if telemetry is None or not telemetry.slippage_bps:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            caution_flags=("THR-X05_EXECUTION_TELEMETRY_MISSING",),
        )
    if telemetry.slippage_observation_days is None or telemetry.slippage_observation_days < 30.0:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.slippage_bps),
            observation_days=telemetry.slippage_observation_days,
            caution_flags=("THR-X05_EXECUTION_HISTORY_LT_30D",),
        )
    if not telemetry.final_sizes and not telemetry.candidate_sizes:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.PARTIAL,
            observation_count=len(telemetry.slippage_bps),
            observation_days=telemetry.slippage_observation_days,
            caution_flags=("THR-X05_SIZE_TELEMETRY_MISSING",),
        )
    try:
        model_estimate = calibrate_slippage_model_bps(
            telemetry.slippage_bps,
            candidate_sizes=telemetry.candidate_sizes,
            final_sizes=telemetry.final_sizes,
        )
    except ExecutionCalibrationError as exc:
        return LocalLabExecutionThresholdReview(
            threshold_id=threshold_id,
            review_status=LocalLabExecutionReviewStatus.BLOCKED,
            observation_count=len(telemetry.slippage_bps),
            observation_days=telemetry.slippage_observation_days,
            blocking_reasons=("THR-X05_EXECUTION_CALIBRATION_INVALID",),
            caution_flags=(str(exc),),
        )
    caution_flags: tuple[str, ...] = ()
    if model_estimate.size_proxy == "candidate_size":
        caution_flags = ("THR-X05_CANDIDATE_SIZE_PROXY_ONLY",)
    return LocalLabExecutionThresholdReview(
        threshold_id=threshold_id,
        review_status=LocalLabExecutionReviewStatus.READY,
        fit_ready=True,
        observation_count=model_estimate.observation_count,
        filtered_observation_count=model_estimate.filtered_observation_count,
        observation_days=telemetry.slippage_observation_days,
        method=model_estimate.method,
        unit=model_estimate.unit,
        published_value=model_estimate.reference_prediction_bps,
        point_estimate=model_estimate.reference_prediction_bps,
        slippage_model_estimate=model_estimate,
        caution_flags=caution_flags,
    )


__all__ = [
    "LocalLabExecutionReview",
    "LocalLabExecutionReviewStatus",
    "LocalLabExecutionTelemetry",
    "LocalLabExecutionThresholdReview",
    "build_local_lab_execution_review",
]
