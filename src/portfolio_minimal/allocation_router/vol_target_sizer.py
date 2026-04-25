"""
Build-8 / allocation_router / vol_target_sizer
Additive Carver-style vol-target sizing seam for the canonical portfolio rail.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class VolTargetProfile(BaseModel, frozen=True):
    """Governed parameters for Carver-style vol-target sizing."""

    annual_vol_target: float = Field(gt=0.0)
    forecast_scale: float = Field(default=10.0, gt=0.0)
    trading_days_per_year: int = Field(default=252, gt=0)
    max_position_size: float | None = Field(default=None, gt=0.0)


class VolTargetCandidateInput(BaseModel, frozen=True):
    """Typed candidate inputs required by the vol-target sizing formula."""

    pair: str
    available_capital: float = Field(gt=0.0)
    forecast_strength: float = Field(ge=0.0)
    instrument_price: float = Field(gt=0.0)
    instrument_pct_vol: float = Field(gt=0.0)
    point_value: float = Field(default=1.0, gt=0.0)


class VolTargetSizeResult(BaseModel, frozen=True):
    """Auditable result of the Carver-style vol-target sizing formula."""

    pair: str
    instrument_value_vol: float
    daily_cash_vol_target: float
    vol_scalar: float
    raw_position_size: float
    position_size: float
    was_clipped: bool = False


def compute_vol_target_size(
    candidate: VolTargetCandidateInput,
    profile: VolTargetProfile,
) -> VolTargetSizeResult:
    """Compute Carver-style vol-target size for one candidate."""

    instrument_value_vol = (
        candidate.instrument_price * candidate.instrument_pct_vol * candidate.point_value
    )
    daily_cash_vol_target = (
        candidate.available_capital * profile.annual_vol_target
    ) / math.sqrt(profile.trading_days_per_year)
    vol_scalar = daily_cash_vol_target / instrument_value_vol
    raw_position_size = (candidate.forecast_strength / profile.forecast_scale) * vol_scalar
    position_size = raw_position_size
    was_clipped = False
    if profile.max_position_size is not None and raw_position_size > profile.max_position_size:
        position_size = profile.max_position_size
        was_clipped = True
    return VolTargetSizeResult(
        pair=candidate.pair,
        instrument_value_vol=instrument_value_vol,
        daily_cash_vol_target=daily_cash_vol_target,
        vol_scalar=vol_scalar,
        raw_position_size=raw_position_size,
        position_size=position_size,
        was_clipped=was_clipped,
    )
