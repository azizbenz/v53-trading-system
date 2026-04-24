from __future__ import annotations

import pytest

from calibration_methods import (
    REGIME_DETECTOR_CORE_V1_FEATURES,
    REGIME_DETECTOR_EXTENDED_V2_FEATURES,
    REGIME_DETECTOR_FULL_V2_FEATURES,
    resolve_regime_detector_feature_set,
    select_regime_detector_features,
)


def test_regime_detector_core_v1_profile_is_stable() -> None:
    selected = resolve_regime_detector_feature_set("core_v1")

    assert selected == REGIME_DETECTOR_CORE_V1_FEATURES
    assert selected[0] == "spread_bps"
    assert "observation_coverage_ratio" not in selected


def test_regime_detector_extended_v2_profile_includes_observation_metrics() -> None:
    selected = resolve_regime_detector_feature_set("extended_v2")

    assert selected == REGIME_DETECTOR_EXTENDED_V2_FEATURES
    assert "observation_coverage_ratio" in selected
    assert "wall_persistence_conditional_bid" in selected


def test_regime_detector_full_v2_profile_matches_complete_schema() -> None:
    selected = resolve_regime_detector_feature_set("full_v2")

    assert selected == REGIME_DETECTOR_FULL_V2_FEATURES
    assert "depth_skew" in selected
    assert "observation_coverage_ratio" in selected


def test_select_regime_detector_features_projects_profile_order() -> None:
    values = {
        feature_id: float(index)
        for index, feature_id in enumerate(REGIME_DETECTOR_EXTENDED_V2_FEATURES, start=1)
    }

    selected = select_regime_detector_features(values, profile="core_v1")

    assert tuple(selected) == REGIME_DETECTOR_CORE_V1_FEATURES
    assert selected["spread_bps"] == pytest.approx(values["spread_bps"])


def test_select_regime_detector_features_fails_on_missing_feature() -> None:
    with pytest.raises(ValueError, match="missing regime-detector features"):
        select_regime_detector_features({"spread_bps": 1.0}, profile="extended_v2")
