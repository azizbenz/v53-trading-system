"""Build-9 tests for meta_minimal edge_tracker_prudent_minimal."""

from __future__ import annotations

import pytest

from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import build_edge_report
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
    PortfolioContext,
    classify_edge,
)
from meta_minimal.edge_tracker_prudent_minimal.return_aggregator import aggregate_returns
from meta_minimal.edge_tracker_prudent_minimal.sample_size_tracker import (
    SampleAdequacy,
    assess_sample_size,
)
from meta_minimal.edge_tracker_prudent_minimal.uncertainty_estimator import (
    estimate_uncertainty,
)


class TestReturnAggregator:
    def test_basic_aggregation(self) -> None:
        result = aggregate_returns("a", (0.01, 0.02, 0.03), (0.005, 0.005, 0.005))
        assert result.sample_size == 3
        assert result.mean_net == pytest.approx(0.015)
        assert result.mean_cost == pytest.approx(0.005)

    def test_mismatched_lengths(self) -> None:
        result = aggregate_returns("a", (0.01,), (0.005, 0.005))
        assert result.sample_size == 0

    def test_empty(self) -> None:
        result = aggregate_returns("a", (), ())
        assert result.sample_size == 0


class TestSampleSizeTracker:
    def test_insufficient(self) -> None:
        result = assess_sample_size("a", 5)
        assert result.adequacy == SampleAdequacy.INSUFFICIENT

    def test_marginal(self) -> None:
        result = assess_sample_size("a", 20)
        assert result.adequacy == SampleAdequacy.MARGINAL

    def test_adequate(self) -> None:
        result = assess_sample_size("a", 50)
        assert result.adequacy == SampleAdequacy.ADEQUATE

    def test_boundary_min(self) -> None:
        result = assess_sample_size("a", 10)
        assert result.adequacy == SampleAdequacy.MARGINAL

    def test_boundary_comfortable(self) -> None:
        result = assess_sample_size("a", 30)
        assert result.adequacy == SampleAdequacy.ADEQUATE


class TestUncertaintyEstimator:
    def test_basic_uncertainty(self) -> None:
        returns = (0.01, 0.02, 0.03, 0.04, 0.05)
        result = estimate_uncertainty("a", returns)
        assert result.mean_return == pytest.approx(0.03)
        assert result.sample_size == 5
        assert result.std_dev > 0.0
        assert result.standard_error > 0.0
        assert result.confidence_lower < result.mean_return
        assert result.confidence_upper > result.mean_return

    def test_single_observation(self) -> None:
        result = estimate_uncertainty("a", (0.05,))
        assert result.mean_return == 0.05
        assert result.std_dev == 0.0

    def test_sharpe(self) -> None:
        returns = (0.10, 0.10, 0.10, 0.10)
        result = estimate_uncertainty("a", returns)
        assert result.sharpe_per_trade == 0.0

    def test_negative_returns(self) -> None:
        returns = (-0.01, -0.02, -0.03)
        result = estimate_uncertainty("a", returns)
        assert result.mean_return < 0.0
        assert result.confidence_upper < 0.0


class TestEdgeStatusClassifier:
    def test_insufficient_sample(self) -> None:
        uncertainty = estimate_uncertainty("a", (0.01, 0.02))
        sample_size = assess_sample_size("a", 2)
        classification = classify_edge(uncertainty, sample_size)
        assert classification.status == EdgeStatus.INSUFFICIENT

    def test_degraded_negative_edge(self) -> None:
        uncertainty = estimate_uncertainty("a", tuple(-0.01 for _ in range(30)))
        sample_size = assess_sample_size("a", 30)
        classification = classify_edge(uncertainty, sample_size)
        assert classification.status == EdgeStatus.DEGRADED

    def test_under_surveillance_ci_includes_zero(self) -> None:
        returns = tuple(0.01 * (1 if index % 2 == 0 else -1) for index in range(30))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 30)
        classification = classify_edge(uncertainty, sample_size)
        assert classification.status in (
            EdgeStatus.UNDER_SURVEILLANCE,
            EdgeStatus.DEGRADED,
        )

    def test_credible_strong_edge(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        classification = classify_edge(uncertainty, sample_size)
        assert classification.status == EdgeStatus.CREDIBLE

    def test_marginal_sample_surveillance(self) -> None:
        returns = tuple(0.05 for _ in range(15))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 15)
        classification = classify_edge(uncertainty, sample_size)
        assert classification.status == EdgeStatus.UNDER_SURVEILLANCE

    def test_classification_output_includes_full_reading(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        context = PortfolioContext(cluster_utilization=0.3)
        classification = classify_edge(
            uncertainty,
            sample_size,
            mean_cost_p90=0.01,
            ce_observed=0.005,
            portfolio_context=context,
        )
        assert classification.mean_cost_p90 == 0.01
        assert classification.ce_observed == 0.005
        assert classification.cluster_utilization == 0.3

    def test_degraded_destructive_cost_p90(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        classification = classify_edge(uncertainty, sample_size, mean_cost_p90=0.20)
        assert classification.status == EdgeStatus.DEGRADED
        assert "destructive" in classification.reason

    def test_surveillance_weak_ce(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        classification = classify_edge(
            uncertainty,
            sample_size,
            ce_observed=0.00005,
        )
        assert classification.status == EdgeStatus.UNDER_SURVEILLANCE
        assert "CE=" in classification.reason

    def test_surveillance_crowded_portfolio(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        context = PortfolioContext(cluster_utilization=0.9, is_crowded=True)
        classification = classify_edge(
            uncertainty,
            sample_size,
            portfolio_context=context,
        )
        assert classification.status == EdgeStatus.UNDER_SURVEILLANCE
        assert "crowded" in classification.reason

    def test_credible_with_all_inputs_good(self) -> None:
        returns = tuple(0.05 + 0.001 * index for index in range(50))
        uncertainty = estimate_uncertainty("a", returns)
        sample_size = assess_sample_size("a", 50)
        context = PortfolioContext(cluster_utilization=0.3, is_crowded=False)
        classification = classify_edge(
            uncertainty,
            sample_size,
            mean_cost_p90=0.01,
            ce_observed=0.005,
            portfolio_context=context,
        )
        assert classification.status == EdgeStatus.CREDIBLE


class TestEdgeReporter:
    def test_report_counts(self) -> None:
        classifications = (
            EdgeClassification(
                scope="a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.05,
                sample_size=50,
            ),
            EdgeClassification(
                scope="b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.01,
                sample_size=30,
            ),
            EdgeClassification(
                scope="c",
                status=EdgeStatus.INSUFFICIENT,
                sample_size=3,
            ),
        )
        report = build_edge_report(classifications)
        assert report.total_scopes == 3
        assert report.credible_count == 1
        assert report.degraded_count == 1
        assert report.insufficient_count == 1
        assert report.has_drift_warning
        assert "b" in report.drift_scopes

    def test_no_drift(self) -> None:
        report = build_edge_report(
            (
                EdgeClassification(
                    scope="a",
                    status=EdgeStatus.CREDIBLE,
                    mean_net_return=0.05,
                    sample_size=50,
                ),
            )
        )
        assert not report.has_drift_warning
