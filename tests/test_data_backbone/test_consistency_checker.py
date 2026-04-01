"""Tests for data_backbone.consistency_checker — Build-2."""
import pytest

from data_backbone.consistency_checker.sequence_checker import (
    SequenceChecker,
    SequenceVerdict,
)
from data_backbone.consistency_checker.gap_detector import GapDetector
from data_backbone.consistency_checker.duplicate_detector import DuplicateDetector
from data_backbone.consistency_checker.contradiction_checker import (
    ContradictionChecker,
    ContradictionType,
)
from data_backbone.consistency_checker.consistency_reporter import (
    ConsistencyScore,
    ConsistencyReporter,
    compute_consistency_score,
)


pytestmark = pytest.mark.build2


# --- Sequence Checker ---

class TestSequenceChecker:
    def test_first_message(self):
        sc = SequenceChecker()
        result = sc.check("BTCUSDT", "trade", 1)
        assert result.verdict == SequenceVerdict.FIRST_MESSAGE

    def test_in_order(self):
        sc = SequenceChecker()
        sc.check("BTC", "trade", 1)
        result = sc.check("BTC", "trade", 2)
        assert result.verdict == SequenceVerdict.IN_ORDER

    def test_out_of_order(self):
        sc = SequenceChecker()
        sc.check("BTC", "trade", 5)
        result = sc.check("BTC", "trade", 3)
        assert result.verdict == SequenceVerdict.OUT_OF_ORDER

    def test_disorder_count(self):
        sc = SequenceChecker()
        sc.check("BTC", "trade", 1)
        sc.check("BTC", "trade", 5)
        sc.check("BTC", "trade", 3)  # disorder
        sc.check("BTC", "trade", 2)  # disorder
        assert sc.get_disorder_count("BTC", "trade") == 2
        assert sc.total_disorders == 2


# --- Gap Detector ---

class TestGapDetector:
    def test_no_gap(self):
        gd = GapDetector()
        gd.check("BTC", "trade", 1)
        gap = gd.check("BTC", "trade", 2)
        assert gap is None

    def test_gap_detected(self):
        gd = GapDetector()
        gd.check("BTC", "trade", 1)
        gap = gd.check("BTC", "trade", 5)
        assert gap is not None
        assert gap.gap_size == 3  # expected 2, got 5

    def test_gap_rate(self):
        gd = GapDetector()
        gd.check("BTC", "trade", 1)
        gd.check("BTC", "trade", 2)
        gd.check("BTC", "trade", 5)  # gap
        assert gd.gap_rate == pytest.approx(1 / 3)

    def test_multiple_gaps(self):
        gd = GapDetector()
        gd.check("BTC", "trade", 1)
        gd.check("BTC", "trade", 5)
        gd.check("BTC", "trade", 10)
        assert gd.total_gaps == 2


# --- Duplicate Detector ---

class TestDuplicateDetector:
    def test_no_duplicate(self):
        dd = DuplicateDetector()
        assert dd.check("BTC", "trade", 1) is None
        assert dd.check("BTC", "trade", 2) is None

    def test_duplicate_detected(self):
        dd = DuplicateDetector()
        dd.check("BTC", "trade", 1)
        dup = dd.check("BTC", "trade", 1)
        assert dup is not None
        assert dup.occurrence == 2

    def test_dup_rate(self):
        dd = DuplicateDetector()
        dd.check("BTC", "trade", 1)
        dd.check("BTC", "trade", 1)  # dup
        dd.check("BTC", "trade", 2)
        assert dd.dup_rate == pytest.approx(1 / 3)


# --- Contradiction Checker ---

class TestContradictionChecker:
    def test_no_contradiction(self):
        cc = ContradictionChecker()
        result = cc.check_timestamp_order("BTC", "trade", 100.0, 100.5)
        assert result is None
        result = cc.check_timestamp_order("BTC", "trade", 101.0, 101.5)
        assert result is None

    def test_timestamp_reversal(self):
        cc = ContradictionChecker()
        cc.check_timestamp_order("BTC", "trade", 100.0, 100.5)
        result = cc.check_timestamp_order("BTC", "trade", 99.0, 101.0)
        assert result is not None
        assert result.contradiction_type == ContradictionType.TIMESTAMP_REVERSAL

    def test_bid_ask_cross(self):
        cc = ContradictionChecker()
        result = cc.check_bid_ask_cross("BTC", best_bid=50001.0, best_ask=50000.0, recv_time=100.0)
        assert result is not None
        assert result.contradiction_type == ContradictionType.BID_ASK_CROSS

    def test_bid_ask_normal(self):
        cc = ContradictionChecker()
        result = cc.check_bid_ask_cross("BTC", best_bid=49999.0, best_ask=50000.0, recv_time=100.0)
        assert result is None


# --- Consistency Reporter ---

class TestConsistencyReporter:
    def test_compute_score_perfect(self):
        score = compute_consistency_score()
        assert score == 1.0

    def test_compute_score_degraded(self):
        score = compute_consistency_score(gap_rate=0.5, dup_rate=0.3)
        assert 0.0 < score < 1.0

    def test_compute_score_clamped(self):
        score = compute_consistency_score(gap_rate=5.0, dup_rate=5.0)
        assert score == 0.0

    def test_reporter_tracks_scores(self):
        reporter = ConsistencyReporter()
        reporter.update_score(ConsistencyScore(pair="BTC", score=0.9))
        reporter.update_score(ConsistencyScore(pair="ETH", score=0.5))
        assert reporter.get_worst_pair().pair == "ETH"
        assert len(reporter.get_all_scores()) == 2

    def test_reporter_tracks_anomaly_totals(self):
        reporter = ConsistencyReporter()
        reporter.record_gap(2)
        reporter.record_duplicate()
        reporter.record_disorder(3)
        reporter.record_contradiction(4)
        stats = reporter.get_stats()
        assert stats.total_gaps == 2
        assert stats.total_duplicates == 1
        assert stats.total_disorders == 3
        assert stats.total_contradictions == 4
