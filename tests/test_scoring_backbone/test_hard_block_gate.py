"""Tests for scoring_backbone.hard_block_gate — Build-5."""
import pytest

from scoring_backbone.hard_block_gate.blocker_registry import (
    BlockerID,
    BlockerDefinition,
    BlockerRegistry,
    DEFAULT_BLOCKERS,
)
from scoring_backbone.hard_block_gate.blocker_evaluator import (
    BlockerCondition,
    BlockerEvaluation,
    evaluate_blockers,
)
from scoring_backbone.hard_block_gate.blocker_reason_encoder import (
    EncodedBlockReason,
    encode_reasons,
)
from scoring_backbone.hard_block_gate.blocker_decision_builder import (
    HardBlockDecision,
    build_decision,
)
from scoring_backbone.hard_block_gate.blocker_reporter import (
    BlockerStats,
    BlockerReporter,
)


# ── blocker_registry ──


class TestBlockerRegistry:
    def test_default_blockers_loaded(self):
        reg = BlockerRegistry()
        assert reg.count == 5

    def test_get_blocker(self):
        reg = BlockerRegistry()
        b = reg.get(BlockerID.STALE_HARD)
        assert b is not None
        assert b.blocker_id == BlockerID.STALE_HARD

    def test_is_registered(self):
        reg = BlockerRegistry()
        assert reg.is_registered(BlockerID.PAIR_SUSPENDED) is True

    def test_version(self):
        reg = BlockerRegistry(version="2.0")
        assert reg.version == "2.0"

    def test_custom_blockers(self):
        custom = (BlockerDefinition(blocker_id=BlockerID.STALE_HARD, description="test"),)
        reg = BlockerRegistry(blockers=custom)
        assert reg.count == 1


# ── blocker_evaluator ──


class TestBlockerEvaluator:
    def test_no_triggers(self):
        """Healthy case — no hard block."""
        evals = evaluate_blockers(BlockerCondition())
        triggered = [e for e in evals if e.triggered]
        assert len(triggered) == 0

    def test_stale_hard_block(self):
        evals = evaluate_blockers(BlockerCondition(is_stale_hard=True))
        triggered = [e for e in evals if e.triggered]
        assert len(triggered) == 1
        assert triggered[0].blocker_id == BlockerID.STALE_HARD

    def test_pair_suspended_block(self):
        evals = evaluate_blockers(BlockerCondition(is_pair_suspended=True))
        triggered = [e for e in evals if e.triggered]
        assert triggered[0].blocker_id == BlockerID.PAIR_SUSPENDED

    def test_risk_budget_block(self):
        evals = evaluate_blockers(BlockerCondition(is_risk_budget_exceeded=True))
        triggered = [e for e in evals if e.triggered]
        assert triggered[0].blocker_id == BlockerID.RISK_BUDGET_EXCEEDED

    def test_reconciliation_critical_block(self):
        evals = evaluate_blockers(BlockerCondition(is_reconciliation_critical=True))
        triggered = [e for e in evals if e.triggered]
        assert triggered[0].blocker_id == BlockerID.RECONCILIATION_CRITICAL

    def test_multiple_triggers(self):
        """Several reasons simultaneously."""
        evals = evaluate_blockers(BlockerCondition(
            is_stale_hard=True,
            is_pair_suspended=True,
            is_infra_down=True,
        ))
        triggered = [e for e in evals if e.triggered]
        assert len(triggered) == 3

    def test_reason_populated_when_triggered(self):
        evals = evaluate_blockers(BlockerCondition(is_stale_hard=True))
        triggered = [e for e in evals if e.triggered]
        assert triggered[0].reason != ""

    def test_reason_empty_when_not_triggered(self):
        evals = evaluate_blockers(BlockerCondition())
        for e in evals:
            assert e.reason == ""


# ── blocker_reason_encoder ──


class TestBlockerReasonEncoder:
    def test_encode_single(self):
        encoded = encode_reasons(((BlockerID.STALE_HARD, "data stale"),))
        assert len(encoded) == 1
        assert encoded[0].code == "HB_STALE_HARD"
        assert encoded[0].source_subsystem == "data_backbone"

    def test_encode_multiple(self):
        encoded = encode_reasons((
            (BlockerID.STALE_HARD, "stale"),
            (BlockerID.RISK_BUDGET_EXCEEDED, "budget"),
        ))
        assert len(encoded) == 2
        assert encoded[1].source_subsystem == "risk_backbone"

    def test_reason_preserved(self):
        encoded = encode_reasons(((BlockerID.INFRA_DOWN, "ws gateway down"),))
        assert encoded[0].human_reason == "ws gateway down"

    def test_empty_triggers(self):
        encoded = encode_reasons(())
        assert len(encoded) == 0


# ── blocker_decision_builder ──


class TestBlockerDecisionBuilder:
    def test_not_blocked(self):
        decision = build_decision("BTCUSDT", "eng1", ())
        assert decision.is_blocked is False
        assert decision.may_proceed_to_ranking is True
        assert decision.reason_count == 0

    def test_blocked_single_reason(self):
        reasons = encode_reasons(((BlockerID.STALE_HARD, "stale"),))
        decision = build_decision("BTCUSDT", "eng1", reasons)
        assert decision.is_blocked is True
        assert decision.may_proceed_to_ranking is False
        assert decision.reason_count == 1

    def test_blocked_multiple_reasons(self):
        reasons = encode_reasons((
            (BlockerID.STALE_HARD, "stale"),
            (BlockerID.PAIR_SUSPENDED, "suspended"),
        ))
        decision = build_decision("BTCUSDT", "eng1", reasons)
        assert decision.reason_count == 2

    def test_decision_frozen(self):
        decision = build_decision("BTC", "eng1", ())
        with pytest.raises(Exception):
            decision.is_blocked = True


# ── blocker_reporter ──


class TestBlockerReporter:
    def test_initial_state(self):
        reporter = BlockerReporter()
        stats = reporter.get_stats()
        assert stats.total_candidates == 0
        assert stats.hb_rate == 0.0

    def test_record_passed(self):
        reporter = BlockerReporter()
        reporter.record_passed()
        stats = reporter.get_stats()
        assert stats.total_passed == 1
        assert stats.total_blocked == 0

    def test_record_blocked(self):
        reporter = BlockerReporter()
        reporter.record_blocked(("HB_STALE_HARD",))
        stats = reporter.get_stats()
        assert stats.total_blocked == 1
        assert stats.by_reason["HB_STALE_HARD"] == 1

    def test_hb_rate(self):
        """HBRate = N_HB / N_candidates."""
        reporter = BlockerReporter()
        reporter.record_passed()
        reporter.record_passed()
        reporter.record_blocked(("HB_STALE_HARD",))
        stats = reporter.get_stats()
        assert stats.hb_rate == pytest.approx(1 / 3)

    def test_multiple_reasons_counted(self):
        reporter = BlockerReporter()
        reporter.record_blocked(("HB_STALE_HARD", "HB_PAIR_SUSPENDED"))
        stats = reporter.get_stats()
        assert stats.by_reason["HB_STALE_HARD"] == 1
        assert stats.by_reason["HB_PAIR_SUSPENDED"] == 1
        assert stats.total_blocked == 1
