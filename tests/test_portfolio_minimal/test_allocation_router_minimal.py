"""Typed regression tests for Build-8 allocation router components."""

from __future__ import annotations

import pytest

from portfolio_minimal.allocation_router.allocation_reporter import build_report
from portfolio_minimal.allocation_router.base_size_builder import (
    SizeProfile,
    compute_base_size,
)
from portfolio_minimal.allocation_router.phantom_trade_guard import (
    PhantomVerdict,
    check_phantom,
)
from portfolio_minimal.allocation_router.portfolio_cap_applier import apply_caps
from portfolio_minimal.allocation_router.score_size_mapper import compute_modulated_size

from ._portfolio_support import build_allocation_entry


class TestBaseSizeBuilder:
    def test_normal_base_size(self) -> None:
        result = compute_base_size("BTC/USDT", SizeProfile(available_capital=10000.0))
        assert result.base_size == 200.0
        assert not result.clamped

    def test_clamped_to_max(self) -> None:
        result = compute_base_size(
            "BTC/USDT",
            SizeProfile(available_capital=100000.0, max_size=500.0),
        )
        assert result.base_size == 500.0
        assert result.clamped

    def test_clamped_to_min(self) -> None:
        result = compute_base_size(
            "BTC/USDT",
            SizeProfile(available_capital=100.0, min_size=10.0),
        )
        assert result.base_size == 10.0
        assert result.clamped

    def test_custom_fraction(self) -> None:
        result = compute_base_size(
            "X",
            SizeProfile(available_capital=10000.0, base_fraction=0.05),
        )
        assert result.base_size == 500.0

    def test_raw_base_preserved(self) -> None:
        result = compute_base_size(
            "X",
            SizeProfile(available_capital=100.0, min_size=10.0),
        )
        assert result.raw_base_size == 2.0
        assert result.base_size == 10.0


class TestScoreSizeMapper:
    def test_tier_1_full_size(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_1")
        assert result.modulated_size == 100.0

    def test_tier_2_reduced(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_2")
        assert result.modulated_size == 60.0

    def test_no_trade_zero(self) -> None:
        result = compute_modulated_size("X", 100.0, "no_trade")
        assert result.modulated_size == 0.0

    def test_unknown_tier_zero(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_99")
        assert result.modulated_size == 0.0

    def test_score_boost_applied(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_1", ranking_score=0.85)
        assert result.score_boost > 0.0
        assert result.modulated_size > 100.0

    def test_no_boost_below_threshold(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_1", ranking_score=0.5)
        assert result.score_boost == 0.0
        assert result.modulated_size == 100.0

    def test_max_boost_capped(self) -> None:
        result = compute_modulated_size("X", 100.0, "tier_1", ranking_score=1.0)
        assert result.score_boost == pytest.approx(0.20, abs=1e-9)
        assert result.modulated_size == pytest.approx(120.0, abs=1e-6)


class TestPortfolioCapApplier:
    def test_no_cap_needed(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
        )
        assert result.final_size == 100.0
        assert not result.was_capped

    def test_gross_cap(self) -> None:
        result = apply_caps(
            "X",
            200.0,
            remaining_gross_capacity=50.0,
            remaining_cluster_capacity=500.0,
        )
        assert result.final_size == 50.0
        assert result.was_capped

    def test_cluster_cap(self) -> None:
        result = apply_caps(
            "X",
            200.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=30.0,
        )
        assert result.final_size == 30.0
        assert result.was_capped

    def test_position_cap(self) -> None:
        result = apply_caps(
            "X",
            600.0,
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity=1000.0,
            position_cap=500.0,
        )
        assert result.final_size == 500.0
        assert result.was_capped

    def test_tightest_cap_wins(self) -> None:
        result = apply_caps(
            "X",
            200.0,
            remaining_gross_capacity=150.0,
            remaining_cluster_capacity=100.0,
            position_cap=80.0,
        )
        assert result.final_size == 80.0

    def test_zero_floor(self) -> None:
        result = apply_caps(
            "X",
            200.0,
            remaining_gross_capacity=-10.0,
            remaining_cluster_capacity=500.0,
        )
        assert result.final_size == 0.0

    def test_loss_budget_reduces_size(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            estimated_loss_at_candidate_size=10.0,
            candidate_size=100.0,
        )
        assert result.final_size == pytest.approx(50.0)
        assert result.was_capped
        assert "loss_budget" in result.cap_reason

    def test_beta_budget_reduces_size(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_beta_capacity=0.1,
            beta_impact_at_candidate_size=0.5,
            candidate_size=100.0,
        )
        assert result.final_size == pytest.approx(20.0)
        assert result.was_capped
        assert "beta_budget" in result.cap_reason

    def test_loss_and_beta_combined_tightest_wins(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            remaining_beta_capacity=0.1,
            estimated_loss_at_candidate_size=10.0,
            beta_impact_at_candidate_size=0.5,
            candidate_size=100.0,
        )
        assert result.final_size == pytest.approx(20.0)

    def test_no_loss_budget_when_no_loss_estimate(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            estimated_loss_at_candidate_size=0.0,
            candidate_size=100.0,
        )
        assert result.final_size == 100.0
        assert not result.was_capped

    def test_negative_beta_uses_abs(self) -> None:
        result = apply_caps(
            "X",
            100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_beta_capacity=0.1,
            beta_impact_at_candidate_size=-0.5,
            candidate_size=100.0,
        )
        assert result.final_size == pytest.approx(20.0)
        assert result.was_capped


class TestPhantomTradeGuard:
    def test_viable(self) -> None:
        result = check_phantom("X", 50.0)
        assert result.verdict == PhantomVerdict.VIABLE

    def test_phantom(self) -> None:
        result = check_phantom("X", 5.0)
        assert result.verdict == PhantomVerdict.PHANTOM

    def test_exact_boundary_viable(self) -> None:
        result = check_phantom("X", 10.0)
        assert result.verdict == PhantomVerdict.VIABLE

    def test_just_below_phantom(self) -> None:
        result = check_phantom("X", 9.99)
        assert result.verdict == PhantomVerdict.PHANTOM

    def test_custom_min_viable(self) -> None:
        result = check_phantom("X", 15.0, min_viable_size=20.0)
        assert result.verdict == PhantomVerdict.PHANTOM

    def test_cost_exceeds_edge_after_allocation(self) -> None:
        result = check_phantom(
            "X",
            100.0,
            candidate_size=100.0,
            expected_cost=0.02,
            ev_net=0.01,
        )
        assert result.verdict == PhantomVerdict.COST_EXCEEDS_EDGE_AFTER_ALLOCATION
        assert "COST_EXCEEDS_EDGE_AFTER_ALLOCATION" in result.reason


class TestAllocationReporter:
    def test_all_viable(self) -> None:
        report = build_report(
            (
                build_allocation_entry("A", 100.0),
                build_allocation_entry("B", 200.0),
            )
        )
        assert report.count_allocated == 2
        assert report.count_phantom == 0
        assert report.total_allocated == 300.0

    def test_mix_viable_phantom(self) -> None:
        report = build_report(
            (
                build_allocation_entry("A", 100.0),
                build_allocation_entry("B", 5.0, phantom=True),
            )
        )
        assert report.count_allocated == 1
        assert report.count_phantom == 1
        assert report.total_allocated == 100.0
        assert report.total_phantom == 5.0

    def test_all_phantom(self) -> None:
        report = build_report((build_allocation_entry("A", 3.0, phantom=True),))
        assert report.count_allocated == 0
        assert report.count_phantom == 1

    def test_empty(self) -> None:
        report = build_report(())
        assert report.count_allocated == 0
        assert report.total_allocated == 0.0

    def test_remaining_capacities_exposed(self) -> None:
        report = build_report(
            (build_allocation_entry("A", 100.0),),
            capital_remaining=900.0,
            remaining_loss_capacity=40.0,
            remaining_beta_capacity=0.8,
            remaining_cluster_capacity={"btc_cluster": 400.0},
        )
        assert report.capital_remaining == 900.0
        assert report.remaining_loss_capacity == 40.0
        assert report.remaining_beta_capacity == 0.8
        assert report.remaining_cluster_capacity["btc_cluster"] == 400.0
