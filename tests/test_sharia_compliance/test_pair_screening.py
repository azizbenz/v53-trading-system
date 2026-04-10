from datetime import datetime, UTC
from decimal import Decimal

from sharia_compliance import evaluate_pair_screening, load_sharia_policy
from sharia_compliance.contracts import AaoifiPairScreeningSnapshot


def _snapshot(
    *,
    pair: str = "BTCUSDT",
    debt_to_total_assets: str = "0.20",
    cash_and_interest_bearing_to_total_assets: str = "0.15",
    interest_income_to_total_revenue: str = "0.01",
) -> AaoifiPairScreeningSnapshot:
    return AaoifiPairScreeningSnapshot(
        pair=pair,
        screening_provider="manual_fixture",
        provider_version="v1",
        reviewed_at=datetime(2026, 4, 10, 12, 0, tzinfo=UTC),
        debt_to_total_assets=Decimal(debt_to_total_assets),
        cash_and_interest_bearing_to_total_assets=Decimal(cash_and_interest_bearing_to_total_assets),
        interest_income_to_total_revenue=Decimal(interest_income_to_total_revenue),
    )


def test_pair_screening_passes_safe_ratios():
    result = evaluate_pair_screening(_snapshot(), policy=load_sharia_policy("config/sharia/policy_v1.yml"))

    assert result.passed is True
    assert result.failure_codes == ()


def test_pair_screening_fails_debt_ratio():
    result = evaluate_pair_screening(
        _snapshot(debt_to_total_assets="0.34"),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
    )

    assert result.passed is False
    assert result.failure_codes == ("AAOIFI_DEBT_RATIO_EXCEEDED",)


def test_pair_screening_fails_cash_ratio():
    result = evaluate_pair_screening(
        _snapshot(cash_and_interest_bearing_to_total_assets="0.35"),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
    )

    assert result.passed is False
    assert result.failure_codes == ("AAOIFI_CASH_RATIO_EXCEEDED",)


def test_pair_screening_fails_interest_income_ratio():
    result = evaluate_pair_screening(
        _snapshot(interest_income_to_total_revenue="0.06"),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
    )

    assert result.passed is False
    assert result.failure_codes == ("AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED",)
