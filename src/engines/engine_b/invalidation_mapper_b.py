"""
Build-7 / engine_b / invalidation_mapper_B
Define mean-reversion invalidation conditions.

Engine B invalidation:
- target: local mean (reversion target)
- stop: deviation extends further (breakout confirmation)
- time: holding duration exceeds expected horizon
- ce_degradation: CE drops below minimum

Engine B is LONG-ONLY (spot-halal profile).
Only long mean-reversion entries are mapped.
"""

from __future__ import annotations

from pydantic import BaseModel


class InvalidationMapB(BaseModel, frozen=True):
    """Engine B invalidation — mean-reversion specific."""

    pair: str
    direction: str  # always "long" for spot-halal
    entry_price: float
    target_price: float  # local mean — reversion target
    stop_price: float  # breakout confirmation level
    max_holding_hours: float  # time-based invalidation
    primary_invalidation: str  # human-readable summary
    reason: str = ""


_DEFAULT_MAX_HOLDING_HOURS = 8.0
_STOP_MULTIPLIER = 1.5  # stop at 1.5x the deviation from mean


def build_invalidation_b(
    pair: str,
    entry_price: float,
    local_mean: float,
    local_std: float,
    holding_hours: float = _DEFAULT_MAX_HOLDING_HOURS,
) -> InvalidationMapB:
    """Build invalidation for a long mean-reversion trade.

    Target: local_mean (price should revert here).
    Stop: entry_price - 1.5 × local_std (breakout confirmation below).
    Max holding: capped at holding_hours (B should be short).
    """
    # For long entry below the mean (buying the dip):
    # target is the mean, stop is below entry
    target = local_mean
    stop = entry_price - _STOP_MULTIPLIER * local_std if local_std > 0 else entry_price * 0.98

    primary = (
        f"Long reversion {pair}: "
        f"entry={entry_price:.4f}, target={target:.4f}, "
        f"stop={stop:.4f}, max_hold={holding_hours:.1f}h"
    )

    return InvalidationMapB(
        pair=pair,
        direction="long",
        entry_price=entry_price,
        target_price=target,
        stop_price=stop,
        max_holding_hours=holding_hours,
        primary_invalidation=primary,
    )
