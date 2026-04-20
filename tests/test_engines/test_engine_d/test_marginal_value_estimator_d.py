from __future__ import annotations

import pytest

from engines.engine_d import (
    ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A,
    ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID,
    EngineDMarginalValueCallerThresholds,
    marginal_value_floor_cleared,
)


def test_marginal_value_threshold_ownership_is_explicit() -> None:
    thresholds = ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A

    assert (
        thresholds.marginal_value_score_min_threshold_id
        == ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID
    )
    assert thresholds.marginal_value_score_min == pytest.approx(0.56)
    assert thresholds.calibration_status == "LOCAL_MODEL_A_GOVERNANCE"


def test_marginal_value_floor_cleared_respects_current_score_boundary() -> None:
    floor = ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A.marginal_value_score_min

    assert marginal_value_floor_cleared(floor) is True
    assert marginal_value_floor_cleared(floor + 0.01) is True
    assert marginal_value_floor_cleared(floor - 0.01) is False


def test_marginal_value_threshold_model_is_frozen() -> None:
    thresholds = ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A

    with pytest.raises(Exception):
        thresholds.marginal_value_score_min = 0.1  # type: ignore[misc]

    with pytest.raises(Exception):
        EngineDMarginalValueCallerThresholds(marginal_value_score_min=1.5)
