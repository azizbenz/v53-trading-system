"""Tests for data_backbone.pair_health_scorer — Build-2."""
import pytest

from data_backbone.pair_health_scorer.quality_aggregator import (
    QualityInputs,
    compute_health_score,
)
from data_backbone.pair_health_scorer.suspension_decider import (
    SuspensionReason,
    evaluate_suspension,
)
from data_backbone.pair_health_scorer.recovery_evaluator import evaluate_recovery
from data_backbone.pair_health_scorer.health_state_tracker import (
    HealthStateTracker,
    PairHealthState,
)
from data_backbone.pair_health_scorer.health_reporter import (
    HealthReporter,
    PairHealthReport,
)


pytestmark = pytest.mark.build2


# --- Quality Aggregator ---

class TestQualityAggregator:
    def test_perfect_health(self):
        inputs = QualityInputs(pair="BTC")
        result = compute_health_score(inputs)
        assert result.score == 1.0

    def test_degraded_health(self):
        inputs = QualityInputs(pair="BTC", freshness_score=0.5, consistency_score=0.5)
        result = compute_health_score(inputs)
        assert 0.0 < result.score < 1.0

    def test_zero_health(self):
        inputs = QualityInputs(
            pair="BTC", freshness_score=0.0, consistency_score=0.0,
            latency_score=0.0, recovery_score=0.0,
        )
        result = compute_health_score(inputs)
        assert result.score == 0.0

    def test_weighted(self):
        inputs = QualityInputs(pair="BTC", freshness_score=1.0, consistency_score=0.0,
                               latency_score=0.0, recovery_score=0.0)
        result = compute_health_score(inputs, w_freshness=1.0, w_consistency=0.0,
                                      w_latency=0.0, w_recovery=0.0)
        assert result.score == 1.0


# --- Suspension Decider ---

class TestSuspensionDecider:
    def test_healthy_no_suspend(self):
        result = evaluate_suspension("BTC", health_score=0.8, threshold=0.3)
        assert result.should_suspend is False

    def test_unhealthy_suspend(self):
        result = evaluate_suspension("BTC", health_score=0.1, threshold=0.3)
        assert result.should_suspend is True
        assert result.reason == SuspensionReason.HEALTH_BELOW_THRESHOLD

    def test_hard_stale_suspend(self):
        result = evaluate_suspension("BTC", health_score=0.8, hard_stale=True)
        assert result.should_suspend is True
        assert result.reason == SuspensionReason.HARD_STALE

    def test_consistency_failure_suspend(self):
        result = evaluate_suspension("BTC", health_score=0.8, consistency_failed=True)
        assert result.should_suspend is True
        assert result.reason == SuspensionReason.CONSISTENCY_FAILURE


# --- Recovery Evaluator ---

class TestRecoveryEvaluator:
    def test_cannot_recover_below_threshold(self):
        result = evaluate_recovery("BTC", health_score=0.3, recovery_threshold=0.5)
        assert result.can_recover is False

    def test_cannot_recover_insufficient_consecutive(self):
        result = evaluate_recovery("BTC", health_score=0.8, consecutive_healthy=1, required_consecutive=3)
        assert result.can_recover is False
        assert result.consecutive_healthy == 2  # incremented

    def test_can_recover(self):
        result = evaluate_recovery("BTC", health_score=0.8, consecutive_healthy=2, required_consecutive=3)
        assert result.can_recover is True

    def test_resets_on_unhealthy(self):
        result = evaluate_recovery("BTC", health_score=0.2, consecutive_healthy=5)
        assert result.consecutive_healthy == 0
        assert result.can_recover is False


# --- Health State Tracker ---

class TestHealthStateTracker:
    def test_default_active(self):
        tracker = HealthStateTracker()
        assert tracker.get_state("BTC") == PairHealthState.ACTIVE

    def test_suspend(self):
        tracker = HealthStateTracker()
        t = tracker.suspend("BTC", "health low", 100.0)
        assert t is not None
        assert tracker.get_state("BTC") == PairHealthState.SUSPENDED

    def test_no_transition_if_same_state(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "reason", 100.0)
        t = tracker.suspend("BTC", "reason again", 101.0)
        assert t is None  # already suspended

    def test_recovery_flow(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "test", 100.0)
        tracker.start_recovery("BTC", 105.0)
        assert tracker.get_state("BTC") == PairHealthState.RECOVERING
        tracker.activate("BTC", "recovered", 110.0)
        assert tracker.get_state("BTC") == PairHealthState.ACTIVE

    def test_transitions_logged(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "test", 100.0)
        tracker.activate("BTC", "ok", 110.0)
        transitions = tracker.get_transitions("BTC")
        assert len(transitions) == 2

    def test_suspended_pairs(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "test", 100.0)
        tracker.suspend("ETH", "test", 100.0)
        tracker.activate("ETH", "ok", 101.0)
        assert tracker.get_suspended_pairs() == frozenset({"BTC"})

    def test_quarantine_is_explicit_for_recovering_and_suspended(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "test", 100.0)
        tracker.start_recovery("ETH", 101.0)
        assert tracker.is_quarantined("BTC") is True
        assert tracker.is_quarantined("ETH") is True
        assert tracker.get_quarantined_pairs() == frozenset({"BTC", "ETH"})

    def test_quarantined_pair_cannot_receive_signals(self):
        tracker = HealthStateTracker()
        tracker.suspend("BTC", "test", 100.0)
        assert tracker.can_receive_signals("BTC") is False
        tracker.activate("BTC", "ok", 105.0)
        assert tracker.can_receive_signals("BTC") is True


# --- Health Reporter ---

class TestHealthReporter:
    def test_report_and_summary(self):
        reporter = HealthReporter()
        reporter.update_report(PairHealthReport(
            pair="BTC", state=PairHealthState.ACTIVE, health_score=0.9,
        ))
        reporter.update_report(PairHealthReport(
            pair="ETH", state=PairHealthState.SUSPENDED, health_score=0.2,
        ))
        summary = reporter.get_summary()
        assert summary.total_pairs == 2
        assert summary.active_count == 1
        assert summary.suspended_count == 1
        assert summary.min_health_score == 0.2

    def test_unhealthy_pairs(self):
        reporter = HealthReporter()
        reporter.update_report(PairHealthReport(
            pair="BTC", state=PairHealthState.ACTIVE, health_score=0.9,
        ))
        reporter.update_report(PairHealthReport(
            pair="ETH", state=PairHealthState.DEGRADED, health_score=0.3,
        ))
        unhealthy = reporter.get_unhealthy_pairs(threshold=0.5)
        assert len(unhealthy) == 1
        assert unhealthy[0].pair == "ETH"
