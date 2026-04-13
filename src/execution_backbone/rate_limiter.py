"""Bounded execution-side consumer for Local IA Lab THR-X03 quota-ratio ceilings."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ExecutionRateLimitModel(BaseModel, frozen=True):
    """Typed runtime-consumer contract derived from the THR-X03 Lab projection."""

    model_version: str = "execution_rate_limit_model_v1"
    threshold_id: str = Field(default="THR-X03", min_length=1)
    method: str = Field(..., min_length=1)
    unit: str = Field(default="quota_ratio", min_length=1)
    quota_ratio_ceiling: float = Field(..., gt=0.0, le=1.0)


class ExecutionRateLimitDecision(BaseModel, frozen=True):
    """Bounded rate-limit gate outcome for one execution opportunity."""

    blocked: bool = False
    reason_code: str = ""
    detail: str = ""
    current_quota_ratio: float | None = Field(default=None, ge=0.0)
    quota_ratio_ceiling: float | None = Field(default=None, gt=0.0)


def evaluate_execution_rate_limit(
    model: ExecutionRateLimitModel,
    *,
    current_quota_ratio: float,
) -> ExecutionRateLimitDecision:
    """Evaluate the bounded THR-X03 runtime guard against one observed quota ratio."""

    if not math.isfinite(current_quota_ratio):
        raise ValueError("current_quota_ratio must be finite")
    if current_quota_ratio < 0.0:
        raise ValueError("current_quota_ratio must be >= 0")

    if current_quota_ratio < model.quota_ratio_ceiling:
        return ExecutionRateLimitDecision(
            blocked=False,
            current_quota_ratio=current_quota_ratio,
            quota_ratio_ceiling=model.quota_ratio_ceiling,
        )

    return ExecutionRateLimitDecision(
        blocked=True,
        reason_code="RATE_LIMIT_QUOTA_RATIO_EXCEEDED",
        detail=(
            f"rest quota ratio {current_quota_ratio:.6f} >= "
            f"allowed ceiling {model.quota_ratio_ceiling:.6f}"
        ),
        current_quota_ratio=current_quota_ratio,
        quota_ratio_ceiling=model.quota_ratio_ceiling,
    )


__all__ = [
    "ExecutionRateLimitDecision",
    "ExecutionRateLimitModel",
    "evaluate_execution_rate_limit",
]
