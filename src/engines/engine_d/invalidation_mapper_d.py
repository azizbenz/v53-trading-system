"""Pure invalidation helpers for Engine D."""

from __future__ import annotations

from pydantic import BaseModel


class InvalidationLevelsD(BaseModel, frozen=True):
    stop_price: float
    target_price: float
    risk_multiple: float
    reference_source: str


def build_invalidation_levels_d(
    *,
    entry_price: float,
    reentry_anchor_price: float,
    realized_vol_current: float | None,
    realized_vol_post_close: float | None,
    expected_gain: float,
) -> InvalidationLevelsD:
    if entry_price <= 0.0:
        raise ValueError("entry_price must be > 0")
    if reentry_anchor_price <= 0.0:
        raise ValueError("reentry_anchor_price must be > 0")
    if realized_vol_current is not None and realized_vol_current < 0.0:
        raise ValueError("realized_vol_current must be >= 0 when provided")
    if realized_vol_post_close is not None and realized_vol_post_close < 0.0:
        raise ValueError("realized_vol_post_close must be >= 0 when provided")
    if expected_gain < 0.0:
        raise ValueError("expected_gain must be >= 0")

    realized_vol, reference_source = _resolve_realized_vol_source(
        realized_vol_current=realized_vol_current,
        realized_vol_post_close=realized_vol_post_close,
    )
    stop_price = reentry_anchor_price - max(entry_price * realized_vol * 0.30, entry_price * 0.0035)
    if stop_price <= 0:
        stop_price = entry_price * 0.987

    target_price = entry_price + max(
        entry_price * realized_vol * 1.4,
        entry_price * max(expected_gain, 0.008),
    )
    risk_multiple = (target_price - entry_price) / max(entry_price - stop_price, 1e-6)
    if risk_multiple <= 0.0:
        raise ValueError("risk_multiple must be > 0")

    return InvalidationLevelsD(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=risk_multiple,
        reference_source=reference_source,
    )


def _resolve_realized_vol_source(
    *,
    realized_vol_current: float | None,
    realized_vol_post_close: float | None,
) -> tuple[float, str]:
    if realized_vol_post_close is not None and realized_vol_post_close > 0.0:
        return realized_vol_post_close, "realized_vol_post_close"
    if realized_vol_current is not None and realized_vol_current > 0.0:
        return realized_vol_current, "realized_vol_current_fallback"
    return 0.0, "entry_price_floor_fallback"
