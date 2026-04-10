"""Pure invalidation helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel


class InvalidationLevelsC(BaseModel, frozen=True):
    stop_price: float
    target_price: float
    risk_multiple: float


def build_invalidation_levels_c(
    *,
    entry_price: float,
    breakout_level: float,
    atr: float,
    expected_gain: float,
) -> InvalidationLevelsC:
    stop_price = breakout_level - max(atr * 0.35, entry_price * 0.004)
    if stop_price <= 0:
        stop_price = entry_price * 0.985

    target_price = entry_price + max(atr * 1.8, entry_price * max(expected_gain, 0.01))

    return InvalidationLevelsC(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=(target_price - entry_price) / max(entry_price - stop_price, 1e-6),
    )
