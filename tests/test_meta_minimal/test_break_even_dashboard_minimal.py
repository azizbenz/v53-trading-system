"""Build-9 tests for meta_minimal break_even_dashboard."""

from __future__ import annotations

import pytest

from meta_minimal.break_even_dashboard.break_even_reporter import build_break_even_report
from meta_minimal.break_even_dashboard.cost_distribution_aggregator import aggregate_costs
from meta_minimal.break_even_dashboard.expected_break_even_calculator import (
    compute_expected_break_even,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import (
    BreakEvenView,
    build_break_even_view,
    build_views_by_engine_and_pair,
)
from meta_minimal.break_even_dashboard.realized_break_even_calculator import (
    compute_realized_break_even,
)


class TestExpectedBreakEven:
    def test_simple_be(self) -> None:
        result = compute_expected_break_even(
            "BTC",
            "engine_a",
            expected_fee=0.001,
            expected_spread=0.0005,
            expected_slippage=0.0002,
            expected_adverse=0.0003,
        )
        assert result.simple_be == pytest.approx(0.002)

    def test_prudent_be_uses_p90(self) -> None:
        result = compute_expected_break_even(
            "BTC",
            "engine_a",
            expected_fee=0.001,
            spread_p90=0.002,
            slippage_p90=0.001,
            adverse_p90=0.001,
        )
        assert result.prudent_be == pytest.approx(0.005)
        assert result.prudent_be > result.simple_be


class TestRealizedBreakEven:
    def test_profitable_trade(self) -> None:
        result = compute_realized_break_even(
            "BTC",
            "a",
            realized_cost=0.002,
            expected_cost=0.001,
            gross_return=0.005,
        )
        assert result.was_profitable
        assert result.net_return == pytest.approx(0.003)
        assert result.cost_drift == pytest.approx(0.001)

    def test_unprofitable_trade(self) -> None:
        result = compute_realized_break_even(
            "X",
            "a",
            realized_cost=0.005,
            expected_cost=0.002,
            gross_return=0.003,
        )
        assert not result.was_profitable
        assert result.net_return == pytest.approx(-0.002)


class TestCostDistributionAggregator:
    def test_basic_aggregation(self) -> None:
        costs = tuple(float(index) for index in range(1, 11))
        result = aggregate_costs("engine_a", costs)
        assert result.sample_size == 10
        assert result.mean_cost == pytest.approx(5.5)
        assert result.min_cost == 1.0
        assert result.max_cost == 10.0

    def test_p90_p95(self) -> None:
        costs = tuple(float(index) for index in range(1, 101))
        result = aggregate_costs("all", costs)
        assert result.p90_cost == pytest.approx(90.1, abs=0.5)
        assert result.p95_cost == pytest.approx(95.05, abs=0.5)

    def test_empty(self) -> None:
        result = aggregate_costs("x", ())
        assert result.sample_size == 0
        assert result.mean_cost == 0.0


class TestBreakEvenView:
    def test_single_scope(self) -> None:
        records = (
            compute_realized_break_even("BTC", "a", 0.002, 0.001, 0.005),
            compute_realized_break_even("BTC", "a", 0.003, 0.001, 0.002),
        )
        view = build_break_even_view("engine_a", records)
        assert view.sample_size == 2
        assert view.profitable_rate == 0.5

    def test_views_by_engine_and_pair(self) -> None:
        records = (
            compute_realized_break_even("BTC", "a", 0.002, 0.001, 0.005),
            compute_realized_break_even("ETH", "b", 0.003, 0.002, 0.004),
        )
        views = build_views_by_engine_and_pair(records)
        assert len(views) == 4


class TestBreakEvenReporter:
    def test_no_drift(self) -> None:
        views = (
            BreakEvenView(
                scope="a",
                sample_size=10,
                mean_realized_cost=0.002,
                mean_expected_cost=0.002,
                mean_cost_drift=0.0,
                profitable_rate=0.5,
            ),
        )
        report = build_break_even_report(views)
        assert not report.has_cost_drift_alert

    def test_drift_detected(self) -> None:
        views = (
            BreakEvenView(
                scope="engine_a",
                sample_size=10,
                mean_realized_cost=0.004,
                mean_expected_cost=0.002,
                mean_cost_drift=0.002,
                profitable_rate=0.3,
            ),
        )
        report = build_break_even_report(views)
        assert report.has_cost_drift_alert
        assert "engine_a" in report.cost_drift_alert_scopes
