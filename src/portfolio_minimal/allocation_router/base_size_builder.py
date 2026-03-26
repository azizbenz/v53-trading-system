"""
Build-8 / allocation_router / base_size_builder
Define base allocation size from profile and available capital.

base_size = capital × base_fraction
Clamped to [min_size, max_size].
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SizeProfile(BaseModel, frozen=True):
    """Capital profile parameters for base size calculation."""

    available_capital: float  # total capital available for allocation
    base_fraction: float = 0.02  # fraction of capital per trade (2% default)
    min_size: float = 10.0  # minimum viable trade size (USD)
    max_size: float = 500.0  # maximum single trade size (USD)


class BaseSizeResult(BaseModel, frozen=True):
    """Result of base size calculation."""

    pair: str
    raw_base_size: float  # capital × fraction, before clamping
    base_size: float  # after clamping to [min, max]
    clamped: bool = False


def compute_base_size(
    pair: str,
    profile: SizeProfile,
) -> BaseSizeResult:
    """Compute the base trade size for a pair.

    base = available_capital × base_fraction, clamped to [min_size, max_size].
    """
    raw = profile.available_capital * profile.base_fraction
    clamped = max(profile.min_size, min(raw, profile.max_size))
    return BaseSizeResult(
        pair=pair,
        raw_base_size=raw,
        base_size=clamped,
        clamped=(clamped != raw),
    )
