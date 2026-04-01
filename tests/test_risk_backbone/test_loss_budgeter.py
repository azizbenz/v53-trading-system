"""Tests for risk_backbone.loss_budgeter — Build-4."""
import pytest

from risk_backbone.loss_budgeter.position_loss_estimator import (
    PositionLossEstimate,
    estimate_position_loss,
)
from risk_backbone.loss_budgeter.aggregate_loss_budgeter import (
    AggregateLossBudget,
    aggregate_loss_budget,
)
from risk_backbone.loss_budgeter.projected_loss_checker import (
    ProjectedLoss,
    check_projected_loss,
)
from risk_backbone.loss_budgeter.loss_cap_guard import (
    LossCapVerdict,
    LossCapResult,
    evaluate_loss_cap,
)
from risk_backbone.loss_budgeter.loss_reporter import LossReporter
from risk_backbone.loss_budgeter.drawdown_guard import (
    DrawdownVerdict,
    evaluate_drawdown_guard,
)


# ── position_loss_estimator ──


class TestPositionLossEstimator:
    def test_basic_loss(self):
        """L_i = size × |entry - stop| / entry."""
        result = estimate_position_loss(
            pair="BTCUSDT", engine_id="eng1", size=1000.0,
            entry_price=50000.0, stop_price=49000.0,
        )
        expected = 1000.0 * abs(50000.0 - 49000.0) / 50000.0
        assert result.loss_amount == pytest.approx(expected)

    def test_loss_pct(self):
        result = estimate_position_loss(
            pair="BTCUSDT", engine_id="eng1", size=1000.0,
            entry_price=50000.0, stop_price=49000.0,
        )
        assert result.loss_pct == pytest.approx(0.02)

    def test_zero_size(self):
        result = estimate_position_loss(
            pair="BTCUSDT", engine_id="eng1", size=0.0,
            entry_price=50000.0, stop_price=49000.0,
        )
        assert result.loss_amount == pytest.approx(0.0)

    def test_stop_above_entry(self):
        """Short position: stop above entry still uses abs()."""
        result = estimate_position_loss(
            pair="BTCUSDT", engine_id="eng1", size=1000.0,
            entry_price=50000.0, stop_price=51000.0,
        )
        expected = 1000.0 * 1000.0 / 50000.0
        assert result.loss_amount == pytest.approx(expected)

    def test_invalid_entry_price(self):
        with pytest.raises(ValueError):
            estimate_position_loss(
                pair="BTCUSDT", engine_id="eng1", size=100.0,
                entry_price=0.0, stop_price=90.0,
            )

    def test_negative_stop_price(self):
        with pytest.raises(ValueError):
            estimate_position_loss(
                pair="BTCUSDT", engine_id="eng1", size=100.0,
                entry_price=100.0, stop_price=-10.0,
            )

    def test_result_frozen(self):
        result = estimate_position_loss(
            pair="BTCUSDT", engine_id="eng1", size=100.0,
            entry_price=100.0, stop_price=90.0,
        )
        with pytest.raises(Exception):
            result.loss_amount = 0.0

    def test_pair_and_engine_stored(self):
        result = estimate_position_loss(
            pair="ETHUSDT", engine_id="eng2", size=100.0,
            entry_price=3000.0, stop_price=2900.0,
        )
        assert result.pair == "ETHUSDT"
        assert result.engine_id == "eng2"


# ── aggregate_loss_budgeter ──


class TestAggregateLossBudgeter:
    def test_empty_estimates(self):
        result = aggregate_loss_budget(estimates=(), loss_cap=1000.0)
        assert result.total_loss_budget == pytest.approx(0.0)
        assert result.utilization == pytest.approx(0.0)

    def test_single_estimate(self):
        e = PositionLossEstimate(
            pair="BTCUSDT", engine_id="eng1", size=1000.0,
            entry_price=50000.0, stop_price=49000.0, loss_amount=20.0, loss_pct=0.02,
        )
        result = aggregate_loss_budget(estimates=(e,), loss_cap=100.0)
        assert result.total_loss_budget == pytest.approx(20.0)
        assert result.utilization == pytest.approx(0.2)

    def test_multiple_estimates_sum(self):
        """LossBudget = Σ L_i."""
        e1 = PositionLossEstimate(
            pair="BTCUSDT", engine_id="eng1", size=1000.0,
            entry_price=50000.0, stop_price=49000.0, loss_amount=20.0, loss_pct=0.02,
        )
        e2 = PositionLossEstimate(
            pair="ETHUSDT", engine_id="eng1", size=500.0,
            entry_price=3000.0, stop_price=2900.0, loss_amount=16.67, loss_pct=0.0333,
        )
        result = aggregate_loss_budget(estimates=(e1, e2), loss_cap=100.0)
        assert result.total_loss_budget == pytest.approx(36.67)

    def test_remaining_capacity(self):
        e = PositionLossEstimate(
            pair="BTCUSDT", engine_id="eng1", size=100.0,
            entry_price=100.0, stop_price=90.0, loss_amount=10.0, loss_pct=0.1,
        )
        result = aggregate_loss_budget(estimates=(e,), loss_cap=100.0)
        assert result.remaining_capacity == pytest.approx(90.0)

    def test_by_pair(self):
        e = PositionLossEstimate(
            pair="BTCUSDT", engine_id="eng1", size=100.0,
            entry_price=100.0, stop_price=90.0, loss_amount=10.0, loss_pct=0.1,
        )
        result = aggregate_loss_budget(estimates=(e,), loss_cap=100.0)
        assert result.by_pair["BTCUSDT"] == pytest.approx(10.0)

    def test_by_engine(self):
        e = PositionLossEstimate(
            pair="BTCUSDT", engine_id="eng1", size=100.0,
            entry_price=100.0, stop_price=90.0, loss_amount=10.0, loss_pct=0.1,
        )
        result = aggregate_loss_budget(estimates=(e,), loss_cap=100.0)
        assert result.by_engine["eng1"] == pytest.approx(10.0)


# ── projected_loss_checker ──


class TestProjectedLossChecker:
    def test_within_cap(self):
        result = check_projected_loss(
            current_loss_budget=50.0, candidate_loss=30.0, loss_cap=100.0,
        )
        assert result.within_cap is True
        assert result.projected_loss_budget == pytest.approx(80.0)

    def test_exactly_at_cap(self):
        result = check_projected_loss(
            current_loss_budget=50.0, candidate_loss=50.0, loss_cap=100.0,
        )
        assert result.within_cap is True

    def test_exceeds_cap(self):
        result = check_projected_loss(
            current_loss_budget=80.0, candidate_loss=30.0, loss_cap=100.0,
        )
        assert result.within_cap is False
        assert result.projected_loss_budget == pytest.approx(110.0)

    def test_remaining_capacity(self):
        result = check_projected_loss(
            current_loss_budget=40.0, candidate_loss=20.0, loss_cap=100.0,
        )
        assert result.remaining_capacity == pytest.approx(40.0)


# ── loss_cap_guard ──


class TestLossCapGuard:
    def test_accepted(self):
        result = evaluate_loss_cap(
            pair="BTCUSDT", candidate_loss=20.0,
            current_budget=30.0, loss_cap=100.0,
        )
        assert result.verdict == LossCapVerdict.ACCEPTED

    def test_rejected_budget_exceeded(self):
        result = evaluate_loss_cap(
            pair="BTCUSDT", candidate_loss=80.0,
            current_budget=30.0, loss_cap=100.0,
        )
        assert result.verdict == LossCapVerdict.REJECTED_BUDGET_EXCEEDED
        assert result.reason != ""

    def test_rejected_no_loss_estimate(self):
        result = evaluate_loss_cap(
            pair="BTCUSDT", candidate_loss=None,
            current_budget=30.0, loss_cap=100.0,
        )
        assert result.verdict == LossCapVerdict.REJECTED_NO_LOSS_ESTIMATE

    def test_accepted_at_boundary(self):
        result = evaluate_loss_cap(
            pair="BTCUSDT", candidate_loss=70.0,
            current_budget=30.0, loss_cap=100.0,
        )
        assert result.verdict == LossCapVerdict.ACCEPTED

    def test_projected_budget_in_result(self):
        result = evaluate_loss_cap(
            pair="BTCUSDT", candidate_loss=20.0,
            current_budget=30.0, loss_cap=100.0,
        )
        assert result.projected_budget == pytest.approx(50.0)


# ── loss_reporter ──


class TestLossReporter:
    def test_initial_state(self):
        reporter = LossReporter(loss_cap=500.0)
        stats = reporter.get_stats()
        assert stats.total_accepted == 0
        assert stats.total_refused == 0

    def test_record_accepted(self):
        reporter = LossReporter(loss_cap=500.0)
        reporter.record_accepted(pair="BTCUSDT", loss_amount=20.0)
        stats = reporter.get_stats()
        assert stats.total_accepted == 1
        assert stats.current_budget == pytest.approx(20.0)

    def test_record_refused(self):
        reporter = LossReporter(loss_cap=500.0)
        reporter.record_refused(pair="BTCUSDT", loss_amount=20.0, reason="over budget")
        stats = reporter.get_stats()
        assert stats.total_refused == 1

    def test_utilization(self):
        reporter = LossReporter(loss_cap=100.0)
        reporter.record_accepted(pair="BTCUSDT", loss_amount=25.0)
        reporter.record_accepted(pair="ETHUSDT", loss_amount=25.0)
        stats = reporter.get_stats()
        assert stats.utilization == pytest.approx(0.5)

    def test_record_position_closed(self):
        reporter = LossReporter(loss_cap=500.0)
        reporter.record_accepted(pair="BTCUSDT", loss_amount=50.0)
        reporter.record_position_closed(loss_amount=50.0)
        stats = reporter.get_stats()
        assert stats.current_budget == pytest.approx(0.0)

    def test_remaining_capacity(self):
        reporter = LossReporter(loss_cap=100.0)
        reporter.record_accepted(pair="BTCUSDT", loss_amount=30.0)
        stats = reporter.get_stats()
        assert stats.remaining_capacity == pytest.approx(70.0)


class TestDrawdownGuard:
    def test_no_drawdown_is_accepted(self):
        result = evaluate_drawdown_guard(
            current_equity=1000.0,
            session_peak_equity=1000.0,
            warning_threshold_pct=0.02,
            observe_threshold_pct=0.04,
        )
        assert result.verdict == DrawdownVerdict.ACCEPTED
        assert result.drawdown_pct == pytest.approx(0.0)

    def test_warning_drawdown_reduces_exposure(self):
        result = evaluate_drawdown_guard(
            current_equity=970.0,
            session_peak_equity=1000.0,
            warning_threshold_pct=0.02,
            observe_threshold_pct=0.04,
        )
        assert result.verdict == DrawdownVerdict.REDUCE_EXPOSURE

    def test_observe_threshold_switches_to_observation(self):
        result = evaluate_drawdown_guard(
            current_equity=950.0,
            session_peak_equity=1000.0,
            warning_threshold_pct=0.02,
            observe_threshold_pct=0.04,
        )
        assert result.verdict == DrawdownVerdict.OBSERVE_ONLY

    def test_invalid_peak_raises(self):
        with pytest.raises(ValueError):
            evaluate_drawdown_guard(
                current_equity=1000.0,
                session_peak_equity=0.0,
            )
