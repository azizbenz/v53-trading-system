"""
Build-8 / allocation_router / phantom_trade_guard
Detect allocations too small to be economically useful.

A phantom trade costs fees but generates negligible P&L.
If final_size < min_viable_size → reject as phantom.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PhantomVerdict(StrEnum):
    VIABLE = "viable"
    PHANTOM = "phantom"


class PhantomCheckResult(BaseModel, frozen=True):
    """Result of phantom trade detection."""

    pair: str
    final_size: float
    min_viable_size: float
    verdict: PhantomVerdict
    reason: str = ""


# Default minimum viable size (USD)
_MIN_VIABLE_SIZE = 10.0


def check_phantom(
    pair: str,
    final_size: float,
    min_viable_size: float = _MIN_VIABLE_SIZE,
) -> PhantomCheckResult:
    """Check if an allocation is too small to be economically useful.

    If final_size < min_viable_size → phantom (would lose money on fees alone).
    """
    if final_size < min_viable_size:
        return PhantomCheckResult(
            pair=pair,
            final_size=final_size,
            min_viable_size=min_viable_size,
            verdict=PhantomVerdict.PHANTOM,
            reason=f"size {final_size:.2f} < min viable {min_viable_size:.2f}",
        )

    return PhantomCheckResult(
        pair=pair,
        final_size=final_size,
        min_viable_size=min_viable_size,
        verdict=PhantomVerdict.VIABLE,
    )
