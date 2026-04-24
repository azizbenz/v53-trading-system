"""Feature-profile selection helpers for RegimeDetectorML training."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Literal

from calibration_methods.walls_and_spoofing_calibration import (
    WALLS_AND_SPOOFING_CORE_V1_FEATURES,
    WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES,
)


REGIME_DETECTOR_FEATURE_PROFILE_VERSION = "regime_detector.feature_profiles.v1"
REGIME_DETECTOR_FEATURE_PROFILE_VERSION_HASH = sha256(
    REGIME_DETECTOR_FEATURE_PROFILE_VERSION.encode("utf-8")
).hexdigest()

REGIME_DETECTOR_BASE_V1_FEATURES: tuple[str, ...] = (
    "spread_bps",
    "order_book_imbalance",
    "liquidity_thinning_score",
    "ofi_short_window",
    "aggressive_trade_imbalance",
    "short_window_volatility",
)

REGIME_DETECTOR_EXTENDED_V2_OBSERVATION_FEATURES: tuple[str, ...] = (
    "wall_persistence_conditional_bid",
    "wall_persistence_conditional_ask",
    "observation_coverage_ratio",
)

REGIME_DETECTOR_CORE_V1_FEATURES: tuple[str, ...] = (
    *REGIME_DETECTOR_BASE_V1_FEATURES,
    *WALLS_AND_SPOOFING_CORE_V1_FEATURES,
)

REGIME_DETECTOR_EXTENDED_V2_FEATURES: tuple[str, ...] = (
    *REGIME_DETECTOR_BASE_V1_FEATURES,
    *WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES,
    *REGIME_DETECTOR_EXTENDED_V2_OBSERVATION_FEATURES,
)

REGIME_DETECTOR_FULL_V2_FEATURES: tuple[str, ...] = (
    "spread_bps",
    "order_book_imbalance",
    "microprice_pressure",
    "depth_skew",
    "book_shape_skew",
    "liquidity_thinning_score",
    "wall_strength_bid",
    "wall_strength_ask",
    "wall_persistence_bid",
    "wall_persistence_ask",
    "wall_pullaway_bid",
    "wall_pullaway_ask",
    "near_touch_cancel_ratio_bid",
    "near_touch_cancel_ratio_ask",
    "executed_vs_displayed_bid",
    "executed_vs_displayed_ask",
    "real_wall_score_bid",
    "real_wall_score_ask",
    "spoof_like_suspicion_bid",
    "spoof_like_suspicion_ask",
    "deceptive_liquidity_score",
    "ofi_short_window",
    "aggressive_trade_imbalance",
    "short_window_volatility",
    "wall_persistence_conditional_bid",
    "wall_persistence_conditional_ask",
    "observation_coverage_ratio",
)

RegimeDetectorFeatureProfile = Literal["core_v1", "extended_v2", "full_v2"]


def resolve_regime_detector_feature_set(
    profile: RegimeDetectorFeatureProfile = "extended_v2",
) -> tuple[str, ...]:
    """Return the deterministic feature list for a bounded regime-detector profile."""

    if profile == "core_v1":
        return REGIME_DETECTOR_CORE_V1_FEATURES
    if profile == "extended_v2":
        return REGIME_DETECTOR_EXTENDED_V2_FEATURES
    return REGIME_DETECTOR_FULL_V2_FEATURES


def select_regime_detector_features(
    feature_values: Mapping[str, float],
    *,
    profile: RegimeDetectorFeatureProfile = "extended_v2",
) -> dict[str, float]:
    """Project a regime-detector feature mapping to a stable profile order."""

    selected_ids = resolve_regime_detector_feature_set(profile)
    missing = tuple(feature_id for feature_id in selected_ids if feature_id not in feature_values)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing regime-detector features for profile {profile}: {joined}")
    return {feature_id: float(feature_values[feature_id]) for feature_id in selected_ids}


__all__ = [
    "REGIME_DETECTOR_FEATURE_PROFILE_VERSION",
    "REGIME_DETECTOR_FEATURE_PROFILE_VERSION_HASH",
    "REGIME_DETECTOR_BASE_V1_FEATURES",
    "REGIME_DETECTOR_EXTENDED_V2_OBSERVATION_FEATURES",
    "REGIME_DETECTOR_CORE_V1_FEATURES",
    "REGIME_DETECTOR_EXTENDED_V2_FEATURES",
    "REGIME_DETECTOR_FULL_V2_FEATURES",
    "RegimeDetectorFeatureProfile",
    "resolve_regime_detector_feature_set",
    "select_regime_detector_features",
]
