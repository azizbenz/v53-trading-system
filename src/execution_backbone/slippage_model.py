"""Bounded execution-side consumer for Local IA Lab THR-X05 slippage models."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ExecutionSlippageModel(BaseModel, frozen=True):
    """Typed runtime-consumer contract derived from the THR-X05 Lab projection."""

    model_version: str = "execution_slippage_model_v1"
    threshold_id: str = Field(default="THR-X05", min_length=1)
    method: str = Field(..., min_length=1)
    unit: str = Field(default="bps", min_length=1)
    size_proxy: str = Field(..., min_length=1)
    intercept_bps: float
    sqrt_size_coefficient: float = Field(..., ge=0.0)
    r_squared: float = Field(..., ge=0.0, le=1.0)
    mean_absolute_error_bps: float = Field(..., ge=0.0)
    reference_size: float = Field(..., gt=0.0)
    reference_prediction_bps: float = Field(..., ge=0.0)


class ExecutionSlippageEstimate(BaseModel, frozen=True):
    """One bounded runtime estimate derived from the THR-X05 slippage model."""

    predicted_slippage_bps: float = Field(..., ge=0.0)
    cost_addition: float = Field(..., ge=0.0)
    size_value: float = Field(..., gt=0.0)
    size_proxy: str = Field(..., min_length=1)
    source_threshold_id: str = Field(..., min_length=1)


def predict_execution_slippage(
    model: ExecutionSlippageModel,
    *,
    size_value: float,
) -> ExecutionSlippageEstimate:
    """Predict bounded slippage for one candidate execution size."""

    if not math.isfinite(size_value):
        raise ValueError("size_value must be finite")
    if size_value <= 0.0:
        raise ValueError("size_value must be > 0")

    predicted_slippage_bps = max(
        0.0,
        model.intercept_bps + model.sqrt_size_coefficient * math.sqrt(size_value),
    )
    return ExecutionSlippageEstimate(
        predicted_slippage_bps=predicted_slippage_bps,
        cost_addition=predicted_slippage_bps / 10_000.0,
        size_value=size_value,
        size_proxy=model.size_proxy,
        source_threshold_id=model.threshold_id,
    )


__all__ = [
    "ExecutionSlippageEstimate",
    "ExecutionSlippageModel",
    "predict_execution_slippage",
]
