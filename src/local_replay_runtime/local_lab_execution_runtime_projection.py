"""Project Local IA Lab execution review outputs into future runtime consumer contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.domain_types import RuntimeMode

from local_replay_runtime.local_lab_execution_review import (
    LocalLabExecutionReview,
    LocalLabExecutionThresholdReview,
)


class LocalLabExecutionRuntimeProjectionStatus(StrEnum):
    """Bounded projection statuses for future runtime consumers."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class LocalLabExecutionRuntimeConsumerProjection(BaseModel, frozen=True):
    """Typed handoff for one future runtime consumer."""

    consumer_id: str = Field(..., min_length=1)
    consumer_interface: str = Field(..., min_length=1)
    threshold_id: str = Field(..., min_length=1)
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    projection_status: LocalLabExecutionRuntimeProjectionStatus
    projection_ready: bool = False
    threshold_review_status: str = Field(..., min_length=1)
    threshold_fit_ready: bool = False
    method: str = Field(default="not_evaluated", min_length=1)
    unit: str = ""
    projection_value: float | None = None
    projection_value_semantics: str = ""
    hard_cap_human: float | None = None
    hard_cap_binding: bool | None = None
    reference_size: float | None = None
    size_proxy: str = ""
    intercept_bps: float | None = None
    sqrt_size_coefficient: float | None = None
    r_squared: float | None = None
    mean_absolute_error_bps: float | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


class LocalLabExecutionRuntimeProjection(BaseModel, frozen=True):
    """Audit-ready future runtime handoff derived from execution review evidence."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    projection_status: LocalLabExecutionRuntimeProjectionStatus
    projection_ready: bool = False
    execution_review_status: str = Field(..., min_length=1)
    execution_review_ready: bool = False
    consumer_count: int = Field(default=0, ge=0)
    ready_consumer_count: int = Field(default=0, ge=0)
    partial_consumer_count: int = Field(default=0, ge=0)
    blocked_consumer_count: int = Field(default=0, ge=0)
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    consumers: tuple[LocalLabExecutionRuntimeConsumerProjection, ...] = ()


def build_local_lab_execution_runtime_projection(
    execution_review: LocalLabExecutionReview,
) -> LocalLabExecutionRuntimeProjection:
    """Build a typed future runtime handoff for execution models already validated in the Lab."""

    x03 = _project_rate_limiter(_require_threshold(execution_review, "THR-X03"))
    x04 = _project_spread_guard(_require_threshold(execution_review, "THR-X04"))
    x05 = _project_slippage_model(_require_threshold(execution_review, "THR-X05"))
    consumers = (x03, x04, x05)
    ready_consumer_count = sum(
        1 for consumer in consumers if consumer.projection_status == "ready"
    )
    partial_consumer_count = sum(
        1 for consumer in consumers if consumer.projection_status == "partial"
    )
    blocked_consumer_count = sum(
        1 for consumer in consumers if consumer.projection_status == "blocked"
    )

    if blocked_consumer_count > 0:
        projection_status = LocalLabExecutionRuntimeProjectionStatus.BLOCKED
    elif partial_consumer_count > 0:
        projection_status = LocalLabExecutionRuntimeProjectionStatus.PARTIAL
    else:
        projection_status = LocalLabExecutionRuntimeProjectionStatus.READY

    return LocalLabExecutionRuntimeProjection(
        correlation_id=execution_review.correlation_id,
        export_dir=execution_review.export_dir,
        run_id=execution_review.run_id,
        projection_status=projection_status,
        projection_ready=projection_status == LocalLabExecutionRuntimeProjectionStatus.READY,
        execution_review_status=execution_review.review_status.value,
        execution_review_ready=execution_review.review_ready,
        consumer_count=len(consumers),
        ready_consumer_count=ready_consumer_count,
        partial_consumer_count=partial_consumer_count,
        blocked_consumer_count=blocked_consumer_count,
        blocking_reasons=tuple(
            dict.fromkeys(reason for consumer in consumers for reason in consumer.blocking_reasons)
        ),
        caution_flags=tuple(
            dict.fromkeys(flag for consumer in consumers for flag in consumer.caution_flags)
        ),
        consumers=consumers,
    )


def _require_threshold(
    execution_review: LocalLabExecutionReview,
    threshold_id: str,
) -> LocalLabExecutionThresholdReview:
    for threshold in execution_review.thresholds:
        if threshold.threshold_id == threshold_id:
            return threshold
    raise ValueError(f"Execution review is missing required threshold {threshold_id}")


def _project_rate_limiter(
    threshold: LocalLabExecutionThresholdReview,
) -> LocalLabExecutionRuntimeConsumerProjection:
    status = LocalLabExecutionRuntimeProjectionStatus(threshold.review_status.value)
    estimate = threshold.threshold_estimate
    return LocalLabExecutionRuntimeConsumerProjection(
        consumer_id="rate_limiter",
        consumer_interface="quota_ratio_ceiling",
        threshold_id=threshold.threshold_id,
        projection_status=status,
        projection_ready=status == LocalLabExecutionRuntimeProjectionStatus.READY,
        threshold_review_status=threshold.review_status.value,
        threshold_fit_ready=threshold.fit_ready,
        method=threshold.method,
        unit=threshold.unit,
        projection_value=None if estimate is None else estimate.published_value,
        projection_value_semantics="max_observed_quota_ratio_before_throttle",
        hard_cap_human=threshold.hard_cap_human,
        hard_cap_binding=threshold.hard_cap_binding,
        blocking_reasons=threshold.blocking_reasons,
        caution_flags=threshold.caution_flags,
    )


def _project_slippage_model(
    threshold: LocalLabExecutionThresholdReview,
) -> LocalLabExecutionRuntimeConsumerProjection:
    status = LocalLabExecutionRuntimeProjectionStatus(threshold.review_status.value)
    model = threshold.slippage_model_estimate
    return LocalLabExecutionRuntimeConsumerProjection(
        consumer_id="slippage_model",
        consumer_interface="sqrt_size_slippage_predictor",
        threshold_id=threshold.threshold_id,
        projection_status=status,
        projection_ready=status == LocalLabExecutionRuntimeProjectionStatus.READY,
        threshold_review_status=threshold.review_status.value,
        threshold_fit_ready=threshold.fit_ready,
        method=threshold.method,
        unit=threshold.unit,
        projection_value=None if model is None else model.reference_prediction_bps,
        projection_value_semantics="reference_slippage_bps_at_q95_size",
        reference_size=None if model is None else model.reference_size,
        size_proxy="" if model is None else model.size_proxy,
        intercept_bps=None if model is None else model.intercept_bps,
        sqrt_size_coefficient=None if model is None else model.sqrt_size_coefficient,
        r_squared=None if model is None else model.r_squared,
        mean_absolute_error_bps=None if model is None else model.mean_absolute_error_bps,
        blocking_reasons=threshold.blocking_reasons,
        caution_flags=threshold.caution_flags,
    )


def _project_spread_guard(
    threshold: LocalLabExecutionThresholdReview,
) -> LocalLabExecutionRuntimeConsumerProjection:
    status = LocalLabExecutionRuntimeProjectionStatus(threshold.review_status.value)
    estimate = threshold.threshold_estimate
    return LocalLabExecutionRuntimeConsumerProjection(
        consumer_id="spread_guard",
        consumer_interface="spread_bps_ceiling",
        threshold_id=threshold.threshold_id,
        projection_status=status,
        projection_ready=status == LocalLabExecutionRuntimeProjectionStatus.READY,
        threshold_review_status=threshold.review_status.value,
        threshold_fit_ready=threshold.fit_ready,
        method=threshold.method,
        unit=threshold.unit,
        projection_value=None if estimate is None else estimate.published_value,
        projection_value_semantics="max_observed_spread_bps_before_no_trade",
        hard_cap_human=threshold.hard_cap_human,
        hard_cap_binding=threshold.hard_cap_binding,
        blocking_reasons=threshold.blocking_reasons,
        caution_flags=threshold.caution_flags,
    )


__all__ = [
    "LocalLabExecutionRuntimeConsumerProjection",
    "LocalLabExecutionRuntimeProjection",
    "LocalLabExecutionRuntimeProjectionStatus",
    "build_local_lab_execution_runtime_projection",
]
