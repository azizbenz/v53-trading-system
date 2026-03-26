"""
Build-4 / exposure_budgeter / gross_exposure_calculator
Calculate current gross exposure.

GrossExp = Σ x_i (sum of all position sizes)
GrossUtil = GrossExp / X_gross,max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Position(BaseModel, frozen=True):
    """A single open position for exposure calculation."""

    pair: str
    engine_id: str
    size: float  # x_i — notional exposure (always positive)
    side: str = "buy"


class GrossExposure(BaseModel, frozen=True):
    """Current gross exposure snapshot."""

    gross_exposure: float  # Σ x_i
    position_count: int
    by_pair: dict[str, float] = Field(default_factory=dict)
    by_engine: dict[str, float] = Field(default_factory=dict)


def calculate_gross_exposure(positions: tuple[Position, ...]) -> GrossExposure:
    """Calculate gross exposure from open positions.

    GrossExp = Σ x_i
    """
    by_pair: dict[str, float] = {}
    by_engine: dict[str, float] = {}

    for p in positions:
        by_pair[p.pair] = by_pair.get(p.pair, 0.0) + p.size
        by_engine[p.engine_id] = by_engine.get(p.engine_id, 0.0) + p.size

    return GrossExposure(
        gross_exposure=sum(p.size for p in positions),
        position_count=len(positions),
        by_pair=by_pair,
        by_engine=by_engine,
    )
