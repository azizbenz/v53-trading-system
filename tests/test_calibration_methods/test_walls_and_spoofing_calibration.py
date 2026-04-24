from __future__ import annotations

import pytest

from calibration_methods import (
    WALLS_AND_SPOOFING_CORE_V1_FEATURES,
    WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES,
    resolve_walls_and_spoofing_feature_set,
    select_walls_and_spoofing_features,
)


def test_walls_and_spoofing_core_v1_profile_is_stable() -> None:
    selected = resolve_walls_and_spoofing_feature_set("core_v1")

    assert selected == WALLS_AND_SPOOFING_CORE_V1_FEATURES
    assert len(selected) == len(set(selected))
    assert selected[0] == "real_wall_score_bid"
    assert selected[-1] == "wall_pullaway_ask"


def test_walls_and_spoofing_extended_v2_profile_contains_full_family() -> None:
    selected = resolve_walls_and_spoofing_feature_set("extended_v2")

    assert selected == WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES
    assert len(selected) == 17
    assert "book_shape_skew" in selected
    assert "deceptive_liquidity_score" in selected


def test_select_walls_and_spoofing_features_projects_in_profile_order() -> None:
    values = {
        feature_id: float(index)
        for index, feature_id in enumerate(WALLS_AND_SPOOFING_EXTENDED_V2_FEATURES, start=1)
    }

    selected = select_walls_and_spoofing_features(values, profile="core_v1")

    assert tuple(selected) == WALLS_AND_SPOOFING_CORE_V1_FEATURES
    assert selected["real_wall_score_bid"] == pytest.approx(
        values["real_wall_score_bid"]
    )
    assert selected["wall_pullaway_ask"] == pytest.approx(values["wall_pullaway_ask"])


def test_select_walls_and_spoofing_features_fails_on_missing_feature() -> None:
    values = {"real_wall_score_bid": 0.7}

    with pytest.raises(ValueError, match="missing walls/spoofing features"):
        select_walls_and_spoofing_features(values, profile="core_v1")
