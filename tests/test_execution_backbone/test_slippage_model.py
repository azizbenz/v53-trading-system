import pytest

from execution_backbone.slippage_model import (
    ExecutionSlippageModel,
    predict_execution_slippage,
)


def test_predict_execution_slippage_uses_sqrt_size_relation():
    model = ExecutionSlippageModel(
        method="sqrt_size_huber_linear_v1",
        size_proxy="final_size",
        intercept_bps=1.0,
        sqrt_size_coefficient=2.0,
        r_squared=0.71,
        mean_absolute_error_bps=0.6,
        reference_size=9.0,
        reference_prediction_bps=7.0,
    )

    estimate = predict_execution_slippage(
        model,
        size_value=9.0,
    )

    assert estimate.predicted_slippage_bps == pytest.approx(7.0)
    assert estimate.cost_addition == pytest.approx(0.0007)
    assert estimate.source_threshold_id == "THR-X05"


def test_predict_execution_slippage_rejects_non_positive_size():
    model = ExecutionSlippageModel(
        method="sqrt_size_huber_linear_v1",
        size_proxy="candidate_size",
        intercept_bps=0.5,
        sqrt_size_coefficient=1.5,
        r_squared=0.63,
        mean_absolute_error_bps=0.5,
        reference_size=4.0,
        reference_prediction_bps=3.5,
    )

    with pytest.raises(ValueError, match="size_value must be > 0"):
        predict_execution_slippage(
            model,
            size_value=0.0,
        )
