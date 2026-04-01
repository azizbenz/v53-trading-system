"""
Build-5 / penalty_aggregator / size_penalty_builder
Build multiplicative size penalty.

m_i = Π m_{i,ℓ}  where 0 < m_{i,ℓ} ≤ 1
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyRegistry,
    validate_penalty_ids,
)


class SizePenaltyItem(BaseModel, frozen=True):
    """A single size multiplier penalty."""

    penalty_id: str
    multiplier: float  # 0 < m ≤ 1
    reason: str = ""


class SizePenaltyResult(BaseModel, frozen=True):
    """Aggregated size penalty."""

    total_multiplier: float
    log_multiplier: float
    penalties: tuple[SizePenaltyItem, ...] = ()


def build_size_penalty(
    penalties: tuple[SizePenaltyItem, ...],
    registry: PenaltyRegistry,
) -> SizePenaltyResult:
    """Compute m_i = Π m_{i,ℓ}.

    Each multiplier is clamped to (0, 1].
    """
    validate_penalty_ids(
        tuple(p.penalty_id for p in penalties),
        registry=registry,
    )
    total = 1.0
    for p in penalties:
        clamped = max(0.001, min(1.0, p.multiplier))
        total *= clamped

    log_m = math.log(total) if total > 0 else float("-inf")

    return SizePenaltyResult(
        total_multiplier=total,
        log_multiplier=log_m,
        penalties=penalties,
    )
