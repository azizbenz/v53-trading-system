"""
V5.3 - MARKET PHYSICS MATH
==========================
Shared scalar math primitives for VPS/Lab market-physics calculations.

Prod-safe note:
- All scalar calculations intentionally use Python ``float``.
- On CPython, ``float`` is IEEE-754 binary64, i.e. float64 / double precision.
- This module must not downcast to float32.
"""

from __future__ import annotations

import math
from typing import SupportsFloat, Sequence

from interface_contracts.feature_lock_contracts import (
    DeltaProxyVariant,
    PHYSICS_FEATURE_ALIASES,
    PhysicsFeatureFamily,
)


Float64 = float
TO_CALIBRATE = "TO_CALIBRATE"
MARKET_PHYSICS_CALIBRATION_PROFILE_ID = "market_physics.to_calibrate.v1"
MARKET_PHYSICS_CALIBRATION_STATUS = TO_CALIBRATE
SWEEP_SCORE_V1_WEIGHTS: dict[str, Float64] = {
    "wick_ratio_capratio": 0.45,
    "vol_burst_capratio": 0.35,
    "reject_indicator_clip01": 0.20,
}
FRAGILITY_SCORE_V1_WEIGHTS: dict[str, Float64] = {
    "base_fragility": 0.70,
    "spread_regime_penalty": 0.20,
    "book_resiliency_penalty": 0.10,
}
TOXICITY_SCORE_V1_WEIGHTS: dict[str, Float64] = {
    "base_toxicity": 0.60,
    "fragility_score": 0.20,
    "spread_regime_penalty": 0.10,
    "vol_jump_penalty": 0.10,
}
EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS: dict[str, Float64] = {
    "fragility_score": 0.45,
    "toxicity_score": 0.35,
    "spread_regime_penalty": 0.15,
    "participation_penalty": 0.05,
}
MICRO_FRICTION_SCORE_V1_WEIGHTS: dict[str, Float64] = {
    "spread_regime_penalty": 0.40,
    "fragility_score": 0.25,
    "toxicity_score": 0.25,
    "participation_penalty": 0.10,
}
ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS: dict[str, Float64] = {
    "fragility_penalty": 0.10,
    "toxicity_penalty": 0.08,
    "micro_friction_penalty": 0.07,
}
DELTA_CONFIRMATION_V1_PROFILE_ID = "delta_confirmation.to_calibrate.v1"


def as_float64(value: SupportsFloat) -> Float64:
    """Normalize scalar inputs to Python float / IEEE-754 binary64."""

    return float(value)


def require_finite_float64(value: SupportsFloat, *, name: str = "value") -> Float64:
    """Reject NaN/Inf at the shared math boundary."""

    x = as_float64(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite")
    return x


def round_float64(value: SupportsFloat, digits: int = 6) -> Float64:
    """Apply a stable float64 rounding policy for audit-facing outputs."""

    if digits < 0:
        raise ValueError("round_float64 requires digits >= 0")
    return as_float64(round(require_finite_float64(value), digits))


def clip01(value: SupportsFloat) -> Float64:
    """Clamp a scalar to the canonical [0, 1] interval."""

    x = require_finite_float64(value)
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x


def zplus(value: SupportsFloat, z_cap: SupportsFloat = 3.0) -> Float64:
    """Positive, capped z-score normalization fixed by the P2 patch."""

    cap = require_finite_float64(z_cap, name="z_cap")
    if cap <= 0.0:
        raise ValueError("zplus requires z_cap > 0")
    return clip01(max(require_finite_float64(value), 0.0) / cap)


def capratio(value: SupportsFloat, cap: SupportsFloat) -> Float64:
    """Capped ratio normalization fixed by the P2 patch."""

    cap_value = require_finite_float64(cap, name="cap")
    if cap_value <= 0.0:
        raise ValueError("capratio requires cap > 0")
    return clip01(require_finite_float64(value) / cap_value)


def delta_proxy_soft(
    open_price: SupportsFloat,
    high_price: SupportsFloat,
    low_price: SupportsFloat,
    close_price: SupportsFloat,
    volume: SupportsFloat,
    *,
    epsilon: SupportsFloat = 1e-12,
) -> Float64:
    """Canonical soft delta proxy."""

    o = require_finite_float64(open_price, name="open_price")
    h = require_finite_float64(high_price, name="high_price")
    l = require_finite_float64(low_price, name="low_price")
    c = require_finite_float64(close_price, name="close_price")
    v = require_finite_float64(volume, name="volume")
    eps = require_finite_float64(epsilon, name="epsilon")
    if eps <= 0.0:
        raise ValueError("delta_proxy_soft requires epsilon > 0")
    return ((c - o) / max(h - l, eps)) * v


def delta_proxy_sign(
    open_price: SupportsFloat,
    close_price: SupportsFloat,
    volume: SupportsFloat,
) -> Float64:
    """Canonical sign delta proxy fallback."""

    o = require_finite_float64(open_price, name="open_price")
    c = require_finite_float64(close_price, name="close_price")
    v = require_finite_float64(volume, name="volume")
    sign = 1.0 if c > o else -1.0 if c < o else 0.0
    return sign * v


def delta_confirmation_v1(
    delta_proxy_value: SupportsFloat,
    reference_volume: SupportsFloat,
    *,
    epsilon: SupportsFloat = 1e-12,
) -> Float64:
    """Map a signed delta proxy back to a bounded [0, 1] confirmation score."""

    proxy = require_finite_float64(delta_proxy_value, name="delta_proxy_value")
    volume = require_finite_float64(reference_volume, name="reference_volume")
    eps = require_finite_float64(epsilon, name="epsilon")
    if eps <= 0.0:
        raise ValueError("delta_confirmation_v1 requires epsilon > 0")
    if volume <= 0.0:
        raise ValueError("delta_confirmation_v1 requires reference_volume > 0")
    signed_ratio = proxy / max(abs(volume), eps)
    signed_ratio = max(-1.0, min(1.0, signed_ratio))
    return clip01(0.5 + 0.5 * signed_ratio)


def resolve_delta_confirmation(
    *,
    delta_confirmation: SupportsFloat | None = None,
    delta_proxy_soft_value: SupportsFloat | None = None,
    delta_proxy_sign_value: SupportsFloat | None = None,
    reference_volume: SupportsFloat | None = None,
) -> Float64:
    """Resolve the governed delta confirmation used on the open runtime rail."""

    if delta_confirmation is not None:
        return clip01(delta_confirmation)
    if delta_proxy_soft_value is not None:
        if reference_volume is None:
            raise ValueError(
                "resolve_delta_confirmation requires reference_volume with delta_proxy_soft_value"
            )
        return delta_confirmation_v1(
            delta_proxy_soft_value,
            reference_volume,
        )
    if delta_proxy_sign_value is not None:
        if reference_volume is None:
            raise ValueError(
                "resolve_delta_confirmation requires reference_volume with delta_proxy_sign_value"
            )
        return delta_confirmation_v1(
            delta_proxy_sign_value,
            reference_volume,
        )
    return 0.5


def participation_ratio(
    order_size: SupportsFloat,
    mean_volume_1m: SupportsFloat,
    *,
    epsilon: SupportsFloat = 1e-12,
) -> Float64:
    """Helper feature Participation_t attached to slippage_friction_proxy."""

    eps = require_finite_float64(epsilon, name="epsilon")
    if eps <= 0.0:
        raise ValueError("participation_ratio requires epsilon > 0")
    return require_finite_float64(order_size, name="order_size") / (
        require_finite_float64(mean_volume_1m, name="mean_volume_1m") + eps
    )


def void_score_discrete(
    region_volumes: Sequence[SupportsFloat],
    mean_window_volume: SupportsFloat,
    *,
    epsilon: SupportsFloat = 1e-12,
) -> Float64:
    """Discrete Class-B void score using the canonical P2/P4 corridor formula."""

    if not region_volumes:
        raise ValueError("void_score_discrete requires a non-empty region")
    eps = require_finite_float64(epsilon, name="epsilon")
    mean_volume = require_finite_float64(
        mean_window_volume, name="mean_window_volume"
    )
    if eps <= 0.0:
        raise ValueError("void_score_discrete requires epsilon > 0")
    if mean_volume < 0.0:
        raise ValueError("void_score_discrete requires mean_window_volume >= 0")
    total_region_volume = sum(
        require_finite_float64(value, name="region_volume") for value in region_volumes
    )
    baseline = len(region_volumes) * mean_volume + eps
    return clip01(1.0 - (total_region_volume / baseline))


def sweep_score_v1(
    wick_ratio: SupportsFloat,
    vol_burst: SupportsFloat,
    reject_indicator: SupportsFloat,
) -> Float64:
    """Canonical V1 sweep score fixed by the P2 patch."""

    return (
        SWEEP_SCORE_V1_WEIGHTS["wick_ratio_capratio"] * capratio(wick_ratio, 3.0)
        + SWEEP_SCORE_V1_WEIGHTS["vol_burst_capratio"] * capratio(vol_burst, 3.0)
        + SWEEP_SCORE_V1_WEIGHTS["reject_indicator_clip01"]
        * clip01(reject_indicator)
    )


def fragility_score_v1(
    base_fragility: SupportsFloat,
    *,
    spread_regime_penalty: SupportsFloat = 0.0,
    book_resiliency_penalty: SupportsFloat = 0.0,
) -> Float64:
    """Canonical bounded fragility helper for runtime/Lab shared use."""

    fragility = clip01(base_fragility)
    spread = clip01(spread_regime_penalty)
    resiliency = clip01(book_resiliency_penalty)
    return clip01(
        FRAGILITY_SCORE_V1_WEIGHTS["base_fragility"] * fragility
        + FRAGILITY_SCORE_V1_WEIGHTS["spread_regime_penalty"] * spread
        + FRAGILITY_SCORE_V1_WEIGHTS["book_resiliency_penalty"] * resiliency
    )


def toxicity_score_v1(
    base_toxicity: SupportsFloat,
    *,
    fragility_score: SupportsFloat = 0.0,
    spread_regime_penalty: SupportsFloat = 0.0,
    vol_jump_penalty: SupportsFloat = 0.0,
) -> Float64:
    """Canonical bounded toxicity helper fixed on explicit normalized inputs."""

    toxicity = clip01(base_toxicity)
    fragility = clip01(fragility_score)
    spread = clip01(spread_regime_penalty)
    vol_jump = clip01(vol_jump_penalty)
    return clip01(
        TOXICITY_SCORE_V1_WEIGHTS["base_toxicity"] * toxicity
        + TOXICITY_SCORE_V1_WEIGHTS["fragility_score"] * fragility
        + TOXICITY_SCORE_V1_WEIGHTS["spread_regime_penalty"] * spread
        + TOXICITY_SCORE_V1_WEIGHTS["vol_jump_penalty"] * vol_jump
    )


def execution_survivability_score_v1(
    *,
    fragility_score: SupportsFloat,
    toxicity_score: SupportsFloat,
    spread_regime_penalty: SupportsFloat = 0.0,
    participation_penalty: SupportsFloat = 0.0,
) -> Float64:
    """Canonical bounded execution survivability score."""

    fragility = clip01(fragility_score)
    toxicity = clip01(toxicity_score)
    spread = clip01(spread_regime_penalty)
    participation = clip01(participation_penalty)
    risk_load = (
        EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS["fragility_score"] * fragility
        + EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS["toxicity_score"] * toxicity
        + EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS["spread_regime_penalty"] * spread
        + EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS["participation_penalty"]
        * participation
    )
    return clip01(1.0 - risk_load)


def micro_friction_score_v1(
    *,
    spread_regime_penalty: SupportsFloat,
    fragility_score: SupportsFloat,
    toxicity_score: SupportsFloat,
    participation_penalty: SupportsFloat = 0.0,
) -> Float64:
    """Canonical bounded micro-friction score."""

    spread = clip01(spread_regime_penalty)
    fragility = clip01(fragility_score)
    toxicity = clip01(toxicity_score)
    participation = clip01(participation_penalty)
    return clip01(
        MICRO_FRICTION_SCORE_V1_WEIGHTS["spread_regime_penalty"] * spread
        + MICRO_FRICTION_SCORE_V1_WEIGHTS["fragility_score"] * fragility
        + MICRO_FRICTION_SCORE_V1_WEIGHTS["toxicity_score"] * toxicity
        + MICRO_FRICTION_SCORE_V1_WEIGHTS["participation_penalty"] * participation
    )


__all__ = [
    "Float64",
    "TO_CALIBRATE",
    "MARKET_PHYSICS_CALIBRATION_PROFILE_ID",
    "MARKET_PHYSICS_CALIBRATION_STATUS",
    "DELTA_CONFIRMATION_V1_PROFILE_ID",
    "SWEEP_SCORE_V1_WEIGHTS",
    "FRAGILITY_SCORE_V1_WEIGHTS",
    "TOXICITY_SCORE_V1_WEIGHTS",
    "EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS",
    "MICRO_FRICTION_SCORE_V1_WEIGHTS",
    "PhysicsFeatureFamily",
    "DeltaProxyVariant",
    "PHYSICS_FEATURE_ALIASES",
    "as_float64",
    "require_finite_float64",
    "round_float64",
    "clip01",
    "zplus",
    "capratio",
    "delta_proxy_soft",
    "delta_proxy_sign",
    "delta_confirmation_v1",
    "resolve_delta_confirmation",
    "participation_ratio",
    "void_score_discrete",
    "sweep_score_v1",
    "fragility_score_v1",
    "toxicity_score_v1",
    "execution_survivability_score_v1",
    "micro_friction_score_v1",
]
