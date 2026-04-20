from __future__ import annotations

from engines.engine_a.cost_feasibility_a import (
    ENGINE_A_CE_MIN_THRESHOLD_ID,
    ENGINE_A_COST_CALIBRATION_STATUS,
    ENGINE_A_COST_PROFILE_ID,
    ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE,
    ENGINE_A_DELTA_SAFE_THRESHOLD_ID,
    CostInput,
)
from engines.engine_a.engine_a_runner import EngineAInput


def test_engine_a_cost_threshold_defaults_are_single_source_of_truth() -> None:
    assert EngineAInput.model_fields["holding_period"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.holding_period
    assert EngineAInput.model_fields["delta_safe"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.delta_safe
    assert EngineAInput.model_fields["ce_min"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.ce_min
    assert CostInput.model_fields["holding_period"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.holding_period
    assert CostInput.model_fields["delta_safe"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.delta_safe
    assert CostInput.model_fields["ce_min"].default == ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.ce_min


def test_engine_a_cost_threshold_metadata_is_explicit() -> None:
    assert ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.delta_safe_threshold_id == ENGINE_A_DELTA_SAFE_THRESHOLD_ID
    assert ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.ce_min_threshold_id == ENGINE_A_CE_MIN_THRESHOLD_ID
    assert ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.calibration_profile_id == ENGINE_A_COST_PROFILE_ID
    assert ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.calibration_status == ENGINE_A_COST_CALIBRATION_STATUS
