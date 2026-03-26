"""
Build-4 / exposure_budgeter / position_cap_guard
Enforce per-position size cap.

x_i ≤ x_max,pos
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PositionCapVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class PositionCapResult(BaseModel, frozen=True):
    """Result of position cap check."""

    pair: str
    position_size: float
    position_cap: float
    verdict: PositionCapVerdict
    excess: float = 0.0  # how much over cap (0 if accepted)


def check_position_cap(
    pair: str,
    position_size: float,
    position_cap: float,
) -> PositionCapResult:
    """Check if a position size is within per-position cap.

    x_i ≤ x_max,pos
    """
    if position_size <= position_cap:
        return PositionCapResult(
            pair=pair,
            position_size=position_size,
            position_cap=position_cap,
            verdict=PositionCapVerdict.ACCEPTED,
        )

    return PositionCapResult(
        pair=pair,
        position_size=position_size,
        position_cap=position_cap,
        verdict=PositionCapVerdict.REJECTED,
        excess=position_size - position_cap,
    )
