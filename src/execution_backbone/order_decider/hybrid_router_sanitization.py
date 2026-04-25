"""Sanitization helpers for the Build-3 hybrid router V2."""

from __future__ import annotations

import math

from .hybrid_router_types import SanitizedField


def sanitize_unit_interval(name: str, raw: float) -> SanitizedField:
    if not math.isfinite(raw):
        return SanitizedField(raw_value=raw, sanitized_value=0.5, sanitization_action="fallback_missing")
    if raw < 0.0:
        return SanitizedField(raw_value=raw, sanitized_value=0.0, sanitization_action="clamped_low")
    if raw > 1.0:
        return SanitizedField(raw_value=raw, sanitized_value=1.0, sanitization_action="clamped_high")
    return SanitizedField(raw_value=raw, sanitized_value=raw, sanitization_action="ok")


def sanitize_vol_z(raw: float, *, clip: float) -> SanitizedField:
    if not math.isfinite(raw):
        return SanitizedField(raw_value=raw, sanitized_value=0.0, sanitization_action="fallback_missing")
    if raw < -clip:
        return SanitizedField(raw_value=raw, sanitized_value=-clip, sanitization_action="clamped_low")
    if raw > clip:
        return SanitizedField(raw_value=raw, sanitized_value=clip, sanitization_action="clamped_high")
    return SanitizedField(raw_value=raw, sanitized_value=raw, sanitization_action="ok")


def collect_reason_codes(fields: dict[str, SanitizedField]) -> tuple[str, ...]:
    reason_codes: list[str] = []
    for name, field in fields.items():
        if field.sanitization_action == "ok":
            continue
        reason_codes.append(f"{name}:{field.sanitization_action}")
        if name in {
            "market_toxicity_score",
            "regime_transition_risk",
            "regime_stability_score",
        }:
            reason_codes.append(f"regime_input_clamped:{name}:{field.sanitization_action}")
        if name == "short_window_volatility_z" and field.sanitization_action == "fallback_missing":
            reason_codes.append("vol_zscore_unavailable")
    return tuple(reason_codes)


__all__ = [
    "collect_reason_codes",
    "sanitize_unit_interval",
    "sanitize_vol_z",
]
