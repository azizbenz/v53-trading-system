"""
Build-6 / engine_a / invalidation_mapper_A
Define structural invalidation for Engine A signals.

A premium signal without readable invalidation is not exploitable.

Direction policy:
  direction_score > 0 → long bias (invalidation below entry)
  direction_score < 0 → short bias (invalidation above entry)
  Engine A supports both abstract directions. Spot-only constraint
  enforcement is the responsibility of the hard_block_gate / risk_backbone,
  not the engine itself. The engine maps invalidation symmetrically.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class InvalidationType(StrEnum):
    PRICE_LEVEL = "price_level"
    STRUCTURE_BREAK = "structure_break"
    TIME_EXPIRY = "time_expiry"
    REGIME_CHANGE = "regime_change"


class InvalidationRule(BaseModel, frozen=True):
    """A single invalidation condition."""

    invalidation_type: InvalidationType
    description: str
    level: float | None = None  # price level if applicable
    horizon_hours: float | None = None  # time-based expiry


class InvalidationMap(BaseModel, frozen=True):
    """Complete invalidation specification for a signal."""

    pair: str
    engine_id: str = "engine_a"
    rules: tuple[InvalidationRule, ...] = ()
    primary_invalidation: str = ""
    expected_holding_hours: float = 0.0
    has_invalidation: bool = False


def build_invalidation(
    pair: str,
    direction_score: float,
    entry_price: float,
    atr: float,
    holding_hours: float = 4.0,
) -> InvalidationMap:
    """Build invalidation map for an Engine A signal.

    Primary invalidation: price level based on ATR.
    Secondary: structure break, time expiry, regime change.
    """
    rules: list[InvalidationRule] = []

    # Price-level invalidation: opposite direction from entry
    if atr > 0 and entry_price > 0:
        if direction_score > 0:
            # Long: invalidation below entry
            inv_level = entry_price - 1.5 * atr
        else:
            # Short: invalidation above entry
            inv_level = entry_price + 1.5 * atr

        rules.append(InvalidationRule(
            invalidation_type=InvalidationType.PRICE_LEVEL,
            description=f"structural invalidation at {inv_level:.2f}",
            level=inv_level,
        ))

    # Time-based expiry
    rules.append(InvalidationRule(
        invalidation_type=InvalidationType.TIME_EXPIRY,
        description=f"time expiry after {holding_hours:.1f}h",
        horizon_hours=holding_hours,
    ))

    # Structure break (always present as concept)
    rules.append(InvalidationRule(
        invalidation_type=InvalidationType.STRUCTURE_BREAK,
        description="trend structure broken — continuation invalidated",
    ))

    # Regime change
    rules.append(InvalidationRule(
        invalidation_type=InvalidationType.REGIME_CHANGE,
        description="regime shifted to unfavorable",
    ))

    primary = rules[0].description if rules else ""

    return InvalidationMap(
        pair=pair,
        rules=tuple(rules),
        primary_invalidation=primary,
        expected_holding_hours=holding_hours,
        has_invalidation=len(rules) > 0,
    )
