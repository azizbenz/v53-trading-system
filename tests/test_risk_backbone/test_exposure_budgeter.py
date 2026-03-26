"""Tests for risk_backbone.exposure_budgeter — Build-4."""
import pytest

from risk_backbone.exposure_budgeter.gross_exposure_calculator import (
    Position,
    GrossExposure,
    calculate_gross_exposure,
)
from risk_backbone.exposure_budgeter.projected_exposure_checker import (
    ProjectedExposure,
    check_projected_exposure,
)
from risk_backbone.exposure_budgeter.position_cap_guard import (
    PositionCapResult,
    PositionCapVerdict,
    check_position_cap,
)
from risk_backbone.exposure_budgeter.gross_cap_guard import (
    GrossCapVerdict,
    GrossCapResult,
    evaluate_gross_cap,
)
from risk_backbone.exposure_budgeter.exposure_reporter import ExposureReporter


# ── gross_exposure_calculator ──


class TestGrossExposureCalculator:
    def test_empty_positions(self):
        result = calculate_gross_exposure(())
        assert result.gross_exposure == 0.0
        assert result.position_count == 0

    def test_single_position(self):
        positions = (Position(pair="BTCUSDT", engine_id="eng1", size=100.0),)
        result = calculate_gross_exposure(positions)
        assert result.gross_exposure == 100.0
        assert result.position_count == 1

    def test_multiple_positions_sum(self):
        """GrossExp = Σ x_i."""
        positions = (
            Position(pair="BTCUSDT", engine_id="eng1", size=100.0),
            Position(pair="ETHUSDT", engine_id="eng1", size=50.0),
            Position(pair="SOLUSDT", engine_id="eng2", size=25.0),
        )
        result = calculate_gross_exposure(positions)
        assert result.gross_exposure == 175.0
        assert result.position_count == 3

    def test_by_pair_aggregation(self):
        positions = (
            Position(pair="BTCUSDT", engine_id="eng1", size=60.0),
            Position(pair="BTCUSDT", engine_id="eng2", size=40.0),
        )
        result = calculate_gross_exposure(positions)
        assert result.by_pair["BTCUSDT"] == pytest.approx(100.0)

    def test_by_engine_aggregation(self):
        positions = (
            Position(pair="BTCUSDT", engine_id="eng1", size=60.0),
            Position(pair="ETHUSDT", engine_id="eng1", size=40.0),
        )
        result = calculate_gross_exposure(positions)
        assert result.by_engine["eng1"] == pytest.approx(100.0)

    def test_result_is_frozen(self):
        result = calculate_gross_exposure(())
        with pytest.raises(Exception):
            result.gross_exposure = 999.0


# ── projected_exposure_checker ──


class TestProjectedExposureChecker:
    def test_within_cap(self):
        result = check_projected_exposure(
            current_exposure=100.0, candidate_size=50.0, gross_cap=200.0,
        )
        assert result.within_cap is True
        assert result.projected_exposure == 150.0

    def test_exactly_at_cap(self):
        result = check_projected_exposure(
            current_exposure=100.0, candidate_size=100.0, gross_cap=200.0,
        )
        assert result.within_cap is True
        assert result.projected_exposure == 200.0

    def test_exceeds_cap(self):
        result = check_projected_exposure(
            current_exposure=150.0, candidate_size=100.0, gross_cap=200.0,
        )
        assert result.within_cap is False
        assert result.projected_exposure == 250.0

    def test_remaining_capacity(self):
        result = check_projected_exposure(
            current_exposure=100.0, candidate_size=50.0, gross_cap=200.0,
        )
        assert result.remaining_capacity == pytest.approx(50.0)

    def test_negative_remaining_when_over(self):
        result = check_projected_exposure(
            current_exposure=180.0, candidate_size=30.0, gross_cap=200.0,
        )
        assert result.remaining_capacity == pytest.approx(-10.0)


# ── position_cap_guard ──


class TestPositionCapGuard:
    def test_accepted_under_cap(self):
        result = check_position_cap(pair="BTCUSDT", position_size=50.0, position_cap=100.0)
        assert result.verdict == PositionCapVerdict.ACCEPTED
        assert result.excess == 0.0

    def test_accepted_at_cap(self):
        result = check_position_cap(pair="BTCUSDT", position_size=100.0, position_cap=100.0)
        assert result.verdict == PositionCapVerdict.ACCEPTED

    def test_rejected_over_cap(self):
        result = check_position_cap(pair="BTCUSDT", position_size=150.0, position_cap=100.0)
        assert result.verdict == PositionCapVerdict.REJECTED
        assert result.excess == pytest.approx(50.0)

    def test_result_contains_pair(self):
        result = check_position_cap(pair="ETHUSDT", position_size=10.0, position_cap=100.0)
        assert result.pair == "ETHUSDT"


# ── gross_cap_guard ──


class TestGrossCapGuard:
    def test_accepted_both_caps(self):
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=50.0,
            current_gross=100.0,
            position_cap=200.0,
            gross_cap=300.0,
            current_pair_exposure=0.0,
        )
        assert result.verdict == GrossCapVerdict.ACCEPTED

    def test_rejected_position_cap(self):
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=250.0,
            current_gross=100.0,
            position_cap=200.0,
            gross_cap=500.0,
            current_pair_exposure=0.0,
        )
        assert result.verdict == GrossCapVerdict.REJECTED_POSITION_CAP

    def test_rejected_gross_cap(self):
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=50.0,
            current_gross=280.0,
            position_cap=200.0,
            gross_cap=300.0,
            current_pair_exposure=0.0,
        )
        assert result.verdict == GrossCapVerdict.REJECTED_GROSS_CAP

    def test_position_cap_checked_first(self):
        """If both caps exceeded, position cap rejection takes priority."""
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=250.0,
            current_gross=280.0,
            position_cap=200.0,
            gross_cap=300.0,
            current_pair_exposure=0.0,
        )
        assert result.verdict == GrossCapVerdict.REJECTED_POSITION_CAP

    def test_reason_populated_on_rejection(self):
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=250.0,
            current_gross=100.0,
            position_cap=200.0,
            gross_cap=500.0,
            current_pair_exposure=0.0,
        )
        assert len(result.reason) > 0

    def test_projected_pair_exposure_rejected(self):
        """existing 80 + candidate 30 > cap 100 => REJECTED_POSITION_CAP."""
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=30.0,
            current_gross=200.0,
            position_cap=100.0,
            gross_cap=500.0,
            current_pair_exposure=80.0,
        )
        assert result.verdict == GrossCapVerdict.REJECTED_POSITION_CAP

    def test_projected_pair_exposure_accepted(self):
        """existing 80 + candidate 20 = cap 100 => ACCEPTED."""
        result = evaluate_gross_cap(
            pair="BTCUSDT",
            candidate_size=20.0,
            current_gross=200.0,
            position_cap=100.0,
            gross_cap=500.0,
            current_pair_exposure=80.0,
        )
        assert result.verdict == GrossCapVerdict.ACCEPTED


# ── exposure_reporter ──


class TestExposureReporter:
    def test_initial_state(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        stats = reporter.get_stats()
        assert stats.total_accepted == 0
        assert stats.total_refused == 0

    def test_record_accepted(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        reporter.record_accepted(pair="BTCUSDT", size=100.0)
        stats = reporter.get_stats()
        assert stats.total_accepted == 1
        assert stats.current_gross == pytest.approx(100.0)

    def test_record_refused(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        reporter.record_refused(pair="BTCUSDT", size=100.0, reason="over cap")
        stats = reporter.get_stats()
        assert stats.total_refused == 1

    def test_utilization(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        reporter.record_accepted(pair="BTCUSDT", size=250.0)
        reporter.record_accepted(pair="ETHUSDT", size=250.0)
        stats = reporter.get_stats()
        assert stats.utilization == pytest.approx(0.5)

    def test_record_position_closed(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        reporter.record_accepted(pair="BTCUSDT", size=300.0)
        reporter.record_position_closed(size=300.0)
        stats = reporter.get_stats()
        assert stats.current_gross == pytest.approx(0.0)

    def test_refusal_rate(self):
        reporter = ExposureReporter(gross_cap=1000.0)
        reporter.record_accepted(pair="BTCUSDT", size=100.0)
        reporter.record_refused(pair="ETHUSDT", size=100.0, reason="cap")
        stats = reporter.get_stats()
        assert stats.refusal_rate == pytest.approx(0.5)
