"""Feature-set selection helpers for walls/spoofing ML integration."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Literal


WALLS_AND_SPOOFING_FEATURE_SET_VERSION = "walls_and_spoofing.feature_sets.v1"
WALLS_AND_SPOOFING_FEATURE_SET_VERSION_HASH = sha256(
    WALLS_AND_SPOOFING_FEATURE_SET_VERSION.encode("utf-8")
).hexdigest()

WALLS_AND_SPOOFING_CORE_V1_FEATURES: tuple[str, ...] = (
    "real_wall_score_bid",
    "real_wall_score_ask",
    "spoof_like_suspicion_bid",
    "spoof_like_suspicion_ask",
    "deceptive_liquidity_score",
    "book_shape_skew",
    "microprice_pressure",
    "executed_vs_displayed_bid",
    "executed_vs_displayed_ask",
    "wall_pullaway_bid",
    "wall_pullaway_ask",
)

WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES: tuple[str, ...] = (
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
    "book_shape_skew",
    "microprice_pressure",
    "real_wall_score_bid",
    "real_wall_score_ask",
    "spoof_like_suspicion_bid",
    "spoof_like_suspicion_ask",
    "deceptive_liquidity_score",
)

WallsAndSpoofingFeatureProfile = Literal["core_v1", "extended_v2"]


def resolve_walls_and_spoofing_feature_set(
    profile: WallsAndSpoofingFeatureProfile = "core_v1",
) -> tuple[str, ...]:
    """Return the deterministic feature list for a bounded ML profile."""

    if profile == "core_v1":
        return WALLS_AND_SPOOFING_CORE_V1_FEATURES
    return WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES


def select_walls_and_spoofing_features(
    feature_values: Mapping[str, float],
    *,
    profile: WallsAndSpoofingFeatureProfile = "core_v1",
) -> dict[str, float]:
    """Project a feature mapping to the chosen walls/spoofing ML profile."""

    selected_ids = resolve_walls_and_spoofing_feature_set(profile)
    missing = tuple(feature_id for feature_id in selected_ids if feature_id not in feature_values)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing walls/spoofing features for profile {profile}: {joined}")
    return {feature_id: float(feature_values[feature_id]) for feature_id in selected_ids}


__all__ = [
    "WALLS_AND_SPOOFING_FEATURE_SET_VERSION",
    "WALLS_AND_SPOOFING_FEATURE_SET_VERSION_HASH",
    "WALLS_AND_SPOOFING_CORE_V1_FEATURES",
    "WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES",
    "WallsAndSpoofingFeatureProfile",
    "resolve_walls_and_spoofing_feature_set",
    "select_walls_and_spoofing_features",
]
