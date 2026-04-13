import pytest

from execution_backbone.rate_limiter import (
    ExecutionRateLimitModel,
    evaluate_execution_rate_limit,
)


def test_evaluate_execution_rate_limit_allows_below_ceiling():
    model = ExecutionRateLimitModel(
        method="little_law_burst_margin_capped",
        quota_ratio_ceiling=0.80,
    )

    decision = evaluate_execution_rate_limit(
        model,
        current_quota_ratio=0.62,
    )

    assert decision.blocked is False
    assert decision.current_quota_ratio == pytest.approx(0.62)
    assert decision.quota_ratio_ceiling == pytest.approx(0.80)


def test_evaluate_execution_rate_limit_blocks_at_or_above_ceiling():
    model = ExecutionRateLimitModel(
        method="little_law_burst_margin_capped",
        quota_ratio_ceiling=0.80,
    )

    decision = evaluate_execution_rate_limit(
        model,
        current_quota_ratio=0.80,
    )

    assert decision.blocked is True
    assert decision.reason_code == "RATE_LIMIT_QUOTA_RATIO_EXCEEDED"
    assert "0.800000" in decision.detail
