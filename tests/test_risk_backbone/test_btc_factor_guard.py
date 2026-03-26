"""Tests for risk_backbone.btc_factor_guard — Build-4."""
import pytest

from risk_backbone.btc_factor_guard.pair_beta_registry import PairBeta, PairBetaRegistry
from risk_backbone.btc_factor_guard.portfolio_beta_calculator import (
    PortfolioBeta,
    calculate_portfolio_beta,
)
from risk_backbone.btc_factor_guard.projected_beta_checker import (
    ProjectedBeta,
    check_projected_beta,
)
from risk_backbone.btc_factor_guard.beta_cap_guard import (
    BetaCapVerdict,
    BetaCapResult,
    evaluate_beta_cap,
)
from risk_backbone.btc_factor_guard.beta_reporter import BetaReporter


# ── pair_beta_registry ──


class TestPairBetaRegistry:
    def test_default_beta(self):
        reg = PairBetaRegistry()
        pb = reg.get_beta("UNKNOWNUSDT")
        assert pb.beta == pytest.approx(0.8)
        assert pb.source == "default"

    def test_set_and_get(self):
        reg = PairBetaRegistry()
        reg.set_beta("BTCUSDT", 1.0, confidence=0.95)
        pb = reg.get_beta("BTCUSDT")
        assert pb.beta == pytest.approx(1.0)
        assert pb.confidence == pytest.approx(0.95)

    def test_default_confidence_for_unknown(self):
        reg = PairBetaRegistry()
        pb = reg.get_beta("UNKNOWNUSDT")
        assert pb.confidence == pytest.approx(0.5)

    def test_update_beta(self):
        reg = PairBetaRegistry()
        reg.set_beta("BTCUSDT", 1.0, confidence=0.9)
        reg.set_beta("BTCUSDT", 1.05, confidence=0.95)
        pb = reg.get_beta("BTCUSDT")
        assert pb.beta == pytest.approx(1.05)

    def test_has_explicit_beta(self):
        reg = PairBetaRegistry()
        assert reg.has_explicit_beta("BTCUSDT") is False
        reg.set_beta("BTCUSDT", 1.0)
        assert reg.has_explicit_beta("BTCUSDT") is True

    def test_get_all(self):
        reg = PairBetaRegistry()
        reg.set_beta("BTCUSDT", 1.0)
        reg.set_beta("ETHUSDT", 0.6)
        assert reg.count == 2
        assert len(reg.get_all()) == 2

    def test_custom_default_beta(self):
        reg = PairBetaRegistry(default_beta=0.5)
        pb = reg.get_beta("UNKNOWNUSDT")
        assert pb.beta == pytest.approx(0.5)


# ── portfolio_beta_calculator ──


class TestPortfolioBetaCalculator:
    def test_empty_portfolio(self):
        result = calculate_portfolio_beta(positions={}, betas={})
        assert result.beta_port == pytest.approx(0.0)

    def test_single_position(self):
        """β_port = w_1·β_1 = 1.0·1.0 = 1.0."""
        result = calculate_portfolio_beta(
            positions={"BTCUSDT": 1000.0},
            betas={"BTCUSDT": 1.0},
        )
        assert result.beta_port == pytest.approx(1.0)

    def test_two_positions_equal_weight(self):
        """β_port = Σ w_j·β_j."""
        positions = {"BTCUSDT": 500.0, "ETHUSDT": 500.0}
        betas = {"BTCUSDT": 1.0, "ETHUSDT": 0.6}
        result = calculate_portfolio_beta(positions=positions, betas=betas)
        assert result.beta_port == pytest.approx(0.8)

    def test_unequal_weights(self):
        positions = {"BTCUSDT": 800.0, "ETHUSDT": 200.0}
        betas = {"BTCUSDT": 1.0, "ETHUSDT": 0.5}
        result = calculate_portfolio_beta(positions=positions, betas=betas)
        assert result.beta_port == pytest.approx(0.9)

    def test_missing_beta_uses_default_0_8(self):
        """Pair with no beta entry uses default 0.8."""
        positions = {"BTCUSDT": 500.0, "UNKNOWN": 500.0}
        betas = {"BTCUSDT": 1.0}
        result = calculate_portfolio_beta(positions=positions, betas=betas)
        # w_btc=0.5, w_unknown=0.5 → β = 0.5*1.0 + 0.5*0.8 = 0.9
        assert result.beta_port == pytest.approx(0.9)

    def test_contributions(self):
        positions = {"BTCUSDT": 500.0, "ETHUSDT": 500.0}
        betas = {"BTCUSDT": 1.0, "ETHUSDT": 0.6}
        result = calculate_portfolio_beta(positions=positions, betas=betas)
        assert result.contributions["BTCUSDT"] == pytest.approx(0.5)
        assert result.contributions["ETHUSDT"] == pytest.approx(0.3)

    def test_result_frozen(self):
        result = calculate_portfolio_beta(positions={}, betas={})
        with pytest.raises(Exception):
            result.beta_port = 999.0


# ── projected_beta_checker ──


class TestProjectedBetaChecker:
    def test_within_cap(self):
        result = check_projected_beta(
            current_positions={"BTCUSDT": 500.0},
            betas={"BTCUSDT": 1.0},
            candidate_pair="ETHUSDT",
            candidate_size=500.0,
            candidate_beta=0.6,
            beta_cap=1.0,
        )
        assert result.within_cap is True
        # β_proj = 0.5*1.0 + 0.5*0.6 = 0.8
        assert result.projected_beta == pytest.approx(0.8)

    def test_exceeds_cap(self):
        result = check_projected_beta(
            current_positions={"BTCUSDT": 500.0},
            betas={"BTCUSDT": 1.0},
            candidate_pair="BTCUSDT",
            candidate_size=500.0,
            candidate_beta=1.0,
            beta_cap=0.9,
        )
        assert result.within_cap is False

    def test_empty_portfolio_adds_first(self):
        result = check_projected_beta(
            current_positions={},
            betas={},
            candidate_pair="BTCUSDT",
            candidate_size=100.0,
            candidate_beta=1.0,
            beta_cap=1.5,
        )
        assert result.within_cap is True
        assert result.projected_beta == pytest.approx(1.0)

    def test_candidate_pair_stored(self):
        result = check_projected_beta(
            current_positions={},
            betas={},
            candidate_pair="SOLUSDT",
            candidate_size=100.0,
            candidate_beta=0.7,
            beta_cap=1.0,
        )
        assert result.candidate_pair == "SOLUSDT"


# ── beta_cap_guard ──


class TestBetaCapGuard:
    def test_accepted(self):
        result = evaluate_beta_cap(
            pair="BTCUSDT",
            current_beta=0.5,
            projected_beta=0.8,
            beta_cap=1.0,
        )
        assert result.verdict == BetaCapVerdict.ACCEPTED

    def test_rejected(self):
        result = evaluate_beta_cap(
            pair="BTCUSDT",
            current_beta=0.8,
            projected_beta=1.1,
            beta_cap=1.0,
        )
        assert result.verdict == BetaCapVerdict.REJECTED
        assert result.reason != ""

    def test_negative_beta_uses_abs(self):
        """| β_port_proj | ≤ B_max."""
        result = evaluate_beta_cap(
            pair="BTCUSDT",
            current_beta=-0.5,
            projected_beta=-1.1,
            beta_cap=1.0,
        )
        assert result.verdict == BetaCapVerdict.REJECTED

    def test_at_cap_boundary(self):
        result = evaluate_beta_cap(
            pair="BTCUSDT",
            current_beta=0.5,
            projected_beta=1.0,
            beta_cap=1.0,
        )
        assert result.verdict == BetaCapVerdict.ACCEPTED

    def test_result_contains_pair(self):
        result = evaluate_beta_cap(
            pair="ETHUSDT",
            current_beta=0.1,
            projected_beta=0.2,
            beta_cap=1.0,
        )
        assert result.pair == "ETHUSDT"


# ── beta_reporter ──


class TestBetaReporter:
    def test_initial_state(self):
        reporter = BetaReporter(beta_cap=1.0)
        stats = reporter.get_stats()
        assert stats.total_accepted == 0
        assert stats.total_refused == 0

    def test_record_accepted(self):
        reporter = BetaReporter(beta_cap=1.0)
        reporter.record_accepted(pair="BTCUSDT", pair_beta=1.0, portfolio_beta=0.5)
        stats = reporter.get_stats()
        assert stats.total_accepted == 1
        assert stats.current_portfolio_beta == pytest.approx(0.5)

    def test_record_refused(self):
        reporter = BetaReporter(beta_cap=1.0)
        reporter.record_refused(pair="BTCUSDT", pair_beta=1.0, reason="over cap")
        stats = reporter.get_stats()
        assert stats.total_refused == 1

    def test_utilization(self):
        reporter = BetaReporter(beta_cap=1.0)
        reporter.record_accepted(pair="BTCUSDT", pair_beta=1.0, portfolio_beta=0.5)
        stats = reporter.get_stats()
        assert stats.utilization == pytest.approx(0.5)

    def test_utilization_uses_abs(self):
        reporter = BetaReporter(beta_cap=1.0)
        reporter.record_accepted(pair="BTCUSDT", pair_beta=1.0, portfolio_beta=-0.3)
        stats = reporter.get_stats()
        assert stats.utilization == pytest.approx(0.3)
