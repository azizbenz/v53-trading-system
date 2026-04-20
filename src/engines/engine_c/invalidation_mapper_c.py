"""Pure invalidation helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel

ENGINE_C_INVALIDATION_PROFILE_ID = "engine_c_invalidation.realized_vol_bridge.v2"
ENGINE_C_INVALIDATION_STATUS = "TRANSITIONAL_REALIZED_VOL_BRIDGE"

INVALID_BREAKOUT_LEVEL_CODE = "INVALID_BREAKOUT_LEVEL"
INVALID_REALIZED_VOL_CURRENT_CODE = "INVALID_REALIZED_VOL_CURRENT"
INVALID_REALIZED_VOL_AT_BREAK_CODE = "INVALID_REALIZED_VOL_AT_BREAK"
INVALID_STOP_GE_ENTRY_CODE = "INVALID_STOP_GE_ENTRY"
INVALID_TARGET_LE_ENTRY_CODE = "INVALID_TARGET_LE_ENTRY"
INVALID_RISK_MULTIPLE_CODE = "INVALID_RISK_MULTIPLE"


class InvalidationLevelsC(BaseModel, frozen=True):
    stop_price: float
    target_price: float
    risk_multiple: float
    reference_source: str


def build_invalidation_levels_c(
    *,
    entry_price: float,
    breakout_level: float,
    realized_vol_current: float | None,
    realized_vol_at_break: float | None,
    expected_gain: float,
) -> InvalidationLevelsC:
    """Build a realized-vol breakout invalidation with explicit fallback provenance."""
    if entry_price <= 0.0:
        raise ValueError("entry_price must be > 0")
    if breakout_level <= 0.0:
        _raise_invalid_invalidation(
            INVALID_BREAKOUT_LEVEL_CODE,
            "breakout_level must be > 0",
        )
    if realized_vol_current is not None and realized_vol_current < 0.0:
        _raise_invalid_invalidation(
            INVALID_REALIZED_VOL_CURRENT_CODE,
            "realized_vol_current must be >= 0 when provided",
        )
    if realized_vol_at_break is not None and realized_vol_at_break < 0.0:
        _raise_invalid_invalidation(
            INVALID_REALIZED_VOL_AT_BREAK_CODE,
            "realized_vol_at_break must be >= 0 when provided",
        )
    if expected_gain < 0.0:
        raise ValueError("expected_gain must be >= 0")

    realized_vol, reference_source = _resolve_realized_vol_source(
        realized_vol_current=realized_vol_current,
        realized_vol_at_break=realized_vol_at_break,
    )
    stop_price = breakout_level - max(entry_price * realized_vol * 0.35, entry_price * 0.004)
    if stop_price <= 0.0:
        stop_price = entry_price * 0.985
    if stop_price >= entry_price:
        _raise_invalid_invalidation(
            INVALID_STOP_GE_ENTRY_CODE,
            "stop_price must remain below entry_price",
        )

    target_price = entry_price + max(
        entry_price * realized_vol * 1.8,
        entry_price * max(expected_gain, 0.01),
    )
    if target_price <= entry_price:
        _raise_invalid_invalidation(
            INVALID_TARGET_LE_ENTRY_CODE,
            "target_price must remain above entry_price",
        )

    risk_multiple = (target_price - entry_price) / max(entry_price - stop_price, 1e-6)
    if risk_multiple <= 0.0:
        _raise_invalid_invalidation(
            INVALID_RISK_MULTIPLE_CODE,
            "risk_multiple must be > 0",
        )

    return InvalidationLevelsC(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=risk_multiple,
        reference_source=reference_source,
    )


def _resolve_realized_vol_source(
    *,
    realized_vol_current: float | None,
    realized_vol_at_break: float | None,
) -> tuple[float, str]:
    """Resolve the governed realized-vol source without silently falling back to legacy vol."""

    if realized_vol_at_break is not None and realized_vol_at_break > 0.0:
        return realized_vol_at_break, "realized_vol_at_break"
    if realized_vol_current is not None and realized_vol_current > 0.0:
        return realized_vol_current, "realized_vol_current_fallback"
    return 0.0, "entry_price_floor_fallback"


def _raise_invalid_invalidation(code: str, detail: str) -> None:
    raise ValueError(f"{code}: {detail}")


__all__ = [
    "ENGINE_C_INVALIDATION_PROFILE_ID",
    "ENGINE_C_INVALIDATION_STATUS",
    "INVALID_BREAKOUT_LEVEL_CODE",
    "INVALID_REALIZED_VOL_AT_BREAK_CODE",
    "INVALID_REALIZED_VOL_CURRENT_CODE",
    "INVALID_RISK_MULTIPLE_CODE",
    "INVALID_STOP_GE_ENTRY_CODE",
    "INVALID_TARGET_LE_ENTRY_CODE",
    "InvalidationLevelsC",
    "build_invalidation_levels_c",
]
