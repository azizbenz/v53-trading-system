"""Bounded loader for replay-side execution runtime projection consumers."""

from __future__ import annotations

from pathlib import Path

from execution_backbone.slippage_model import ExecutionSlippageModel
from execution_backbone.spread_guard import ExecutionSpreadGuardModel
from local_replay_runtime.local_lab_execution_runtime_projection import (
    LocalLabExecutionRuntimeConsumerProjection,
    LocalLabExecutionRuntimeProjection,
)


def load_replay_execution_projection_models(
    projection_path: str | Path,
) -> tuple[ExecutionSpreadGuardModel | None, ExecutionSlippageModel | None]:
    """Load replay-safe canonical execution consumers from one Lab projection artifact."""

    projection = LocalLabExecutionRuntimeProjection.model_validate_json(
        Path(projection_path).read_text(encoding="utf-8")
    )
    return (
        _load_spread_guard_model(projection),
        _load_slippage_model(projection),
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
    "load_replay_execution_projection_models",
]
