"""Bounded execution-side consumer for Local IA Lab THR-X04 spread ceilings."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ExecutionSpreadGuardModel(BaseModel, frozen=True):
    """Typed runtime-consumer contract derived from the THR-X04 Lab projection."""

    model_version: str = "execution_spread_guard_model_v1"
    threshold_id: str = Field(default="THR-X04", min_length=1)
    method: str = Field(..., min_length=1)
    unit: str = Field(default="bps", min_length=1)
    max_spread_bps: float = Field(..., gt=0.0)


class ExecutionSpreadGuardDecision(BaseModel, frozen=True):
    """Bounded spread-guard outcome for one execution opportunity."""

    blocked: bool = False
    reason_code: str = ""
    detail: str = ""
    telemetry_status: str = ""
    current_spread_bps: float | None = Field(default=None, ge=0.0)
    max_spread_bps: float | None = Field(default=None, gt=0.0)


def evaluate_execution_spread_guard(
    model: ExecutionSpreadGuardModel,
    *,
    current_spread_bps: float,
) -> ExecutionSpreadGuardDecision:
    """Evaluate the bounded THR-X04 runtime guard against one observed spread."""

    if not math.isfinite(current_spread_bps):
        raise ValueError("current_spread_bps must be finite")
    if current_spread_bps < 0.0:
        raise ValueError("current_spread_bps must be >= 0")

    if current_spread_bps <= model.max_spread_bps:
        return ExecutionSpreadGuardDecision(
            blocked=False,
            telemetry_status="measured",
            current_spread_bps=current_spread_bps,
            max_spread_bps=model.max_spread_bps,
        )

    return ExecutionSpreadGuardDecision(
        blocked=True,
        reason_code="SPREAD_GUARD_THRESHOLD_EXCEEDED",
        detail=(
            f"spread {current_spread_bps:.6f} bps > "
            f"allowed ceiling {model.max_spread_bps:.6f} bps"
        ),
        telemetry_status="measured",
        current_spread_bps=current_spread_bps,
        max_spread_bps=model.max_spread_bps,
    )


__all__ = [
    "ExecutionSpreadGuardDecision",
    "ExecutionSpreadGuardModel",
    "evaluate_execution_spread_guard",
]
