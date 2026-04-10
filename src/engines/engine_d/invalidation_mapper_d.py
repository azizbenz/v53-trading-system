"""Pure invalidation helpers for Engine D."""

from __future__ import annotations

from pydantic import BaseModel


class InvalidationLevelsD(BaseModel, frozen=True):
    stop_price: float
    target_price: float
    risk_multiple: float


def build_invalidation_levels_d(
    *,
    entry_price: float,
    reentry_anchor_price: float,
    atr: float,
    expected_gain: float,
) -> InvalidationLevelsD:
    stop_price = reentry_anchor_price - max(atr * 0.30, entry_price * 0.0035)
    if stop_price <= 0:
        stop_price = entry_price * 0.987

    target_price = entry_price + max(atr * 1.4, entry_price * max(expected_gain, 0.008))

    return InvalidationLevelsD(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=(target_price - entry_price) / max(entry_price - stop_price, 1e-6),
    )
