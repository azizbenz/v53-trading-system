"""Fail-open loader for Local IA Lab execution runtime projection artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from execution_backbone.rate_limiter import ExecutionRateLimitModel
from execution_backbone.slippage_model import ExecutionSlippageModel
from execution_backbone.spread_guard import ExecutionSpreadGuardModel
from local_replay_runtime.local_lab_execution_runtime_projection import (
    LocalLabExecutionRuntimeConsumerProjection,
    LocalLabExecutionRuntimeProjection,
)


class ExecutionRuntimeProjectionBridgeStatus(BaseModel, frozen=True):
    """Operational status of the bounded Local IA Lab execution projection bridge."""

    configured: bool = True
    projection_path: str = ""
    projection_found: bool = False
    projection_loaded: bool = False
    projection_status: str = ""
    consumer_count: int = 0
    ready_consumer_count: int = 0
    partial_consumer_count: int = 0
    blocked_consumer_count: int = 0
    consumers: tuple[LocalLabExecutionRuntimeConsumerProjection, ...] = ()
    rate_limit_model_loaded: bool = False
    spread_guard_model_loaded: bool = False
    slippage_model_loaded: bool = False
    caution_flags: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    error_type: str = ""
    error_detail: str = ""


def load_execution_runtime_consumer_models(
    projection_path: str | Path,
) -> tuple[
    ExecutionRateLimitModel | None,
    ExecutionSpreadGuardModel | None,
    ExecutionSlippageModel | None,
]:
    """Load bounded execution consumers from a Lab-side runtime projection artifact."""

    status = inspect_execution_runtime_projection_bridge(projection_path)
    if not status.projection_loaded:
        return None, None, None
    projection = _load_projection_document(Path(projection_path))
    return (
        _load_rate_limit_model(projection),
        _load_spread_guard_model(projection),
        _load_slippage_model(projection),
    )


def inspect_execution_runtime_projection_bridge(
    projection_path: str | Path | None = None,
) -> ExecutionRuntimeProjectionBridgeStatus:
    """Inspect the current projection-bridge state without mutating runtime behavior."""

    if projection_path is None:
        return ExecutionRuntimeProjectionBridgeStatus(configured=False)
    path = Path(projection_path)
    if not path.exists():
        return ExecutionRuntimeProjectionBridgeStatus(
            projection_path=str(path),
            projection_found=False,
        )
    try:
        projection = _load_projection_document(path)
    except Exception as exc:
        return ExecutionRuntimeProjectionBridgeStatus(
            projection_path=str(path),
            projection_found=True,
            error_type=type(exc).__name__,
            error_detail=str(exc),
        )
    rate_limit_model = _load_rate_limit_model(projection)
    spread_guard_model = _load_spread_guard_model(projection)
    slippage_model = _load_slippage_model(projection)
    return ExecutionRuntimeProjectionBridgeStatus(
        projection_path=str(path),
        projection_found=True,
        projection_loaded=True,
        projection_status=projection.projection_status.value,
        consumer_count=projection.consumer_count,
        ready_consumer_count=projection.ready_consumer_count,
        partial_consumer_count=projection.partial_consumer_count,
        blocked_consumer_count=projection.blocked_consumer_count,
        consumers=projection.consumers,
        rate_limit_model_loaded=rate_limit_model is not None,
        spread_guard_model_loaded=spread_guard_model is not None,
        slippage_model_loaded=slippage_model is not None,
        caution_flags=projection.caution_flags,
        blocking_reasons=projection.blocking_reasons,
    )


def _load_projection_document(path: Path) -> LocalLabExecutionRuntimeProjection:
    return LocalLabExecutionRuntimeProjection.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _load_rate_limit_model(
    projection: LocalLabExecutionRuntimeProjection,
) -> ExecutionRateLimitModel | None:
    consumer = _find_consumer(projection, "rate_limiter")
    if consumer is None or not consumer.projection_ready or consumer.projection_value is None:
        return None
    return ExecutionRateLimitModel(
        threshold_id=consumer.threshold_id,
        method=consumer.method,
        unit=consumer.unit or "quota_ratio",
        quota_ratio_ceiling=consumer.projection_value,
    )


def _load_slippage_model(
    projection: LocalLabExecutionRuntimeProjection,
) -> ExecutionSlippageModel | None:
    consumer = _find_consumer(projection, "slippage_model")
    if consumer is None or not consumer.projection_ready:
        return None
    if (
        consumer.intercept_bps is None
        or consumer.sqrt_size_coefficient is None
        or consumer.reference_size is None
        or consumer.projection_value is None
        or consumer.r_squared is None
        or consumer.mean_absolute_error_bps is None
        or not consumer.size_proxy
    ):
        return None
    return ExecutionSlippageModel(
        threshold_id=consumer.threshold_id,
        method=consumer.method,
        unit=consumer.unit or "bps",
        size_proxy=consumer.size_proxy,
        intercept_bps=consumer.intercept_bps,
        sqrt_size_coefficient=consumer.sqrt_size_coefficient,
        r_squared=consumer.r_squared,
        mean_absolute_error_bps=consumer.mean_absolute_error_bps,
        reference_size=consumer.reference_size,
        reference_prediction_bps=consumer.projection_value,
    )


def _load_spread_guard_model(
    projection: LocalLabExecutionRuntimeProjection,
) -> ExecutionSpreadGuardModel | None:
    consumer = _find_consumer(projection, "spread_guard")
    if consumer is None or not consumer.projection_ready or consumer.projection_value is None:
        return None
    return ExecutionSpreadGuardModel(
        threshold_id=consumer.threshold_id,
        method=consumer.method,
        unit=consumer.unit or "bps",
        max_spread_bps=consumer.projection_value,
    )


def _find_consumer(
    projection: LocalLabExecutionRuntimeProjection,
    consumer_id: str,
) -> LocalLabExecutionRuntimeConsumerProjection | None:
    for consumer in projection.consumers:
        if consumer.consumer_id == consumer_id:
            return consumer
    return None


__all__ = [
    "ExecutionRuntimeProjectionBridgeStatus",
    "inspect_execution_runtime_projection_bridge",
    "load_execution_runtime_consumer_models",
]
