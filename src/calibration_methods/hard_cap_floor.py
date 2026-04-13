"""Shared Local IA Lab helpers for human hard-floor / hard-cap publication."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class HumanHardCapPolicyError(ValueError):
    """Raised when a hard-floor / hard-cap publication request is invalid."""


class HumanHardCapPolicyResult(BaseModel, frozen=True):
    """Audit-ready result of applying a human minimum floor or maximum cap."""

    method_version: str = "human_hard_cap_policy_v1"
    candidate_value: float
    published_value: float
    hard_cap_human: float = Field(..., gt=0.0)
    bound_kind: str = Field(..., min_length=1)
    hard_cap_satisfied: bool
    hard_cap_binding: bool


def apply_human_minimum_floor(candidate_value: float, human_floor: float) -> HumanHardCapPolicyResult:
    """Publish a calibration value conservatively with a human minimum floor."""

    _validate_inputs(candidate_value, human_floor)
    published_value = max(candidate_value, human_floor)
    return HumanHardCapPolicyResult(
        candidate_value=candidate_value,
        published_value=published_value,
        hard_cap_human=human_floor,
        bound_kind="minimum_floor",
        hard_cap_satisfied=published_value >= human_floor,
        hard_cap_binding=candidate_value < human_floor,
    )


def apply_human_maximum_cap(candidate_value: float, human_cap: float) -> HumanHardCapPolicyResult:
    """Publish a calibration value conservatively with a human maximum cap."""

    _validate_inputs(candidate_value, human_cap)
    published_value = min(candidate_value, human_cap)
    return HumanHardCapPolicyResult(
        candidate_value=candidate_value,
        published_value=published_value,
        hard_cap_human=human_cap,
        bound_kind="maximum_cap",
        hard_cap_satisfied=published_value <= human_cap,
        hard_cap_binding=candidate_value > human_cap,
    )


def _validate_inputs(candidate_value: float, hard_cap_human: float) -> None:
    if not math.isfinite(candidate_value):
        raise HumanHardCapPolicyError("candidate_value must be finite")
    if not math.isfinite(hard_cap_human) or hard_cap_human <= 0.0:
        raise HumanHardCapPolicyError("hard_cap_human must be finite and > 0")


__all__ = [
    "HumanHardCapPolicyError",
    "HumanHardCapPolicyResult",
    "apply_human_maximum_cap",
    "apply_human_minimum_floor",
]
