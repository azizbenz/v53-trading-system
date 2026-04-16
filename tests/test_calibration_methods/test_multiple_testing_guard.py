from __future__ import annotations

import math

import pytest

from calibration_methods import (
    CURRENT_REPO_PAIR_UNIVERSE_COUNT,
    V53_CANONICAL_SHADOW_PAIR_FLOOR,
    HarveyLiuZhuPairCountMode,
    MultipleTestingGuardError,
    compose_hlz_test_count,
    compute_harvey_liu_zhu_deflated_sharpe,
)


def test_compose_hlz_test_count_uses_observed_pairs_by_default() -> None:
    result = compose_hlz_test_count(observed_pair_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT)

    assert result.observed_pair_count == 12
    assert result.effective_test_count == 12
    assert result.floor_applied is False


def test_compose_hlz_test_count_applies_promotion_floor_when_requested() -> None:
    result = compose_hlz_test_count(
        observed_pair_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT,
        pair_count_mode=HarveyLiuZhuPairCountMode.PROMOTION_FLOOR,
    )

    assert result.observed_pair_count == 12
    assert result.promotion_pair_floor == V53_CANONICAL_SHADOW_PAIR_FLOOR
    assert result.effective_test_count == 20
    assert result.floor_applied is True


def test_hlz_deflated_sharpe_matches_observed_pair_default() -> None:
    result = compute_harvey_liu_zhu_deflated_sharpe(
        1.0,
        observation_count=50,
        observed_pair_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT,
    )

    expected = math.sqrt(38.0 / 49.0)
    assert result.effective_test_count == 12
    assert result.scale_factor == pytest.approx(expected)
    assert result.deflated_sharpe == pytest.approx(expected)


def test_hlz_deflated_sharpe_matches_v53_promotion_floor_mode() -> None:
    result = compute_harvey_liu_zhu_deflated_sharpe(
        1.0,
        observation_count=50,
        observed_pair_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT,
        pair_count_mode=HarveyLiuZhuPairCountMode.PROMOTION_FLOOR,
    )

    expected = math.sqrt(30.0 / 49.0)
    assert result.effective_test_count == 20
    assert result.scale_factor == pytest.approx(expected)
    assert result.deflated_sharpe == pytest.approx(expected)


def test_hlz_deflated_sharpe_rejects_non_positive_radicand() -> None:
    with pytest.raises(MultipleTestingGuardError, match="positive radicand"):
        compute_harvey_liu_zhu_deflated_sharpe(
            1.0,
            observation_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT,
            observed_pair_count=CURRENT_REPO_PAIR_UNIVERSE_COUNT,
        )
