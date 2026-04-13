import pytest

from execution_backbone.spread_guard import (
    ExecutionSpreadGuardModel,
    evaluate_execution_spread_guard,
)


def test_evaluate_execution_spread_guard_allows_below_ceiling():
    model = ExecutionSpreadGuardModel(
        method="lognormal_mu_plus_2sigma_capped",
        max_spread_bps=18.0,
    )

    decision = evaluate_execution_spread_guard(
        model,
        current_spread_bps=12.5,
    )

    assert decision.blocked is False
    assert decision.current_spread_bps == pytest.approx(12.5)
    assert decision.max_spread_bps == pytest.approx(18.0)


def test_evaluate_execution_spread_guard_blocks_above_ceiling():
    model = ExecutionSpreadGuardModel(
        method="lognormal_mu_plus_2sigma_capped",
        max_spread_bps=18.0,
    )

    decision = evaluate_execution_spread_guard(
        model,
        current_spread_bps=18.1,
    )

    assert decision.blocked is True
    assert decision.reason_code == "SPREAD_GUARD_THRESHOLD_EXCEEDED"
    assert "18.100000" in decision.detail
