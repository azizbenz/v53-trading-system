"""
REGRESSION TESTS â€” Phase 2 codeâ†’docs alignment verification.

Covers all 14 modified modules from the alignment pass.
Each test class targets one specific GEM/correction.
"""

import ast
import json
import time
import textwrap
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R1: market_event_contracts â€” GEM-01 crossed book guard
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from interface_contracts.market_event_contracts import DepthEvent, DepthLevel


class TestCrossedBookGuard:
    """GEM-01: crossed book (best_bid > best_ask) must be rejected."""

    def test_valid_book_accepted(self):
        event = DepthEvent(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            bids=[DepthLevel(price=42000.0, quantity=1.0)],
            asks=[DepthLevel(price=42001.0, quantity=1.0)],
        )
        assert event.best_bid == 42000.0
        assert event.best_ask == 42001.0

    def test_crossed_book_rejected(self):
        with pytest.raises(ValidationError, match="Crossed book"):
            DepthEvent(
                timestamp_ms=1700000000000,
                pair="BTCUSDT",
                bids=[DepthLevel(price=42001.0, quantity=1.0)],
                asks=[DepthLevel(price=42000.0, quantity=1.0)],
            )

    def test_equal_bid_ask_accepted(self):
        """Equal bid/ask is not a crossed book."""
        event = DepthEvent(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            bids=[DepthLevel(price=42000.0, quantity=1.0)],
            asks=[DepthLevel(price=42000.0, quantity=1.0)],
        )
        assert event.spread_bps == 0.0


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R2: decision_contracts â€” GEM-02 epsilon guard + GEM-11 expiry
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from interface_contracts.decision_contracts import BlockReason, SignalCandidate, SignalType
from interface_contracts.domain_types import Side


class TestEpsilonRiskGuard:
    """GEM-02: risk < 1e-6 returns None for risk/reward."""

    def _make_signal(self, entry: float, sl: float, tp: float) -> SignalCandidate:
        return SignalCandidate(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            engine_id="engine_a",
            signal_type=SignalType.ENTRY,
            side=Side.BUY,
            confidence=0.8,
            regime="trending_up",
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
        )

    def test_normal_risk_reward(self):
        sig = self._make_signal(entry=42000.0, sl=41000.0, tp=44000.0)
        rr = sig.expected_risk_reward
        assert rr is not None
        assert rr == pytest.approx(2.0)

    def test_zero_risk_returns_none(self):
        sig = self._make_signal(entry=42000.0, sl=42000.0, tp=44000.0)
        assert sig.expected_risk_reward is None

    def test_near_zero_risk_returns_none(self):
        sig = self._make_signal(entry=42000.0, sl=42000.0 - 1e-8, tp=44000.0)
        assert sig.expected_risk_reward is None


class TestSignalExpiry:
    """GEM-11: is_expired() and SIGNAL_EXPIRED block reason."""

    def test_signal_without_max_hold_never_expires(self):
        sig = SignalCandidate(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            engine_id="engine_a",
            signal_type=SignalType.ENTRY,
            side=Side.BUY,
            confidence=0.8,
            regime="trending_up",
            entry_price=42000.0,
        )
        assert sig.is_expired(1700000000000 + 999_999_999) is False

    def test_signal_expired_when_past_max_hold(self):
        sig = SignalCandidate(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            engine_id="engine_a",
            signal_type=SignalType.ENTRY,
            side=Side.BUY,
            confidence=0.8,
            regime="trending_up",
            entry_price=42000.0,
            max_hold_ms=60_000,
        )
        assert sig.is_expired(1700000000000 + 60_001) is True
        assert sig.is_expired(1700000000000 + 59_999) is False

    def test_signal_expired_block_reason_exists(self):
        assert BlockReason.SIGNAL_EXPIRED == "signal_expired"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R3: import_scanner â€” GEM-03 dynamic import detection
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from dag_validator.import_scanner import _detect_dynamic_imports, DynamicImportRecord


class TestDynamicImportDetection:
    """GEM-03: detect importlib.import_module and __import__."""

    def test_detects_importlib_import_module(self):
        code = textwrap.dedent("""\
            import importlib
            mod = importlib.import_module("some.module")
        """)
        tree = ast.parse(code)
        records = _detect_dynamic_imports(tree, "test.py")
        assert len(records) == 1
        assert records[0].call_text == "importlib.import_module"

    def test_detects_dunder_import(self):
        code = textwrap.dedent("""\
            mod = __import__("some.module")
        """)
        tree = ast.parse(code)
        records = _detect_dynamic_imports(tree, "test.py")
        assert len(records) == 1
        assert records[0].call_text == "__import__"

    def test_no_false_positive_on_normal_import(self):
        code = textwrap.dedent("""\
            import os
            from pathlib import Path
            x = some_function()
        """)
        tree = ast.parse(code)
        records = _detect_dynamic_imports(tree, "test.py")
        assert len(records) == 0

    def test_no_false_positive_on_import_attribute(self):
        """import_module as method on non-importlib object should not trigger."""
        code = textwrap.dedent("""\
            loader = ModuleLoader()
            loader.import_module("x")
        """)
        tree = ast.parse(code)
        records = _detect_dynamic_imports(tree, "test.py")
        assert len(records) == 0

    def test_multiple_detections(self):
        code = textwrap.dedent("""\
            import importlib
            importlib.import_module("a")
            __import__("b")
            importlib.import_module("c")
        """)
        tree = ast.parse(code)
        records = _detect_dynamic_imports(tree, "test.py")
        assert len(records) == 3


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R4: recovery_runner â€” GEM-04 backoff + resource release
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from smoke_bootstrap_recovery.recovery_runner import (
    _backoff_delay,
    run_recovery_cycle,
)
from smoke_bootstrap_recovery.smoke_models import SmokeStatus


class _BackoffTestModule:
    def __init__(self):
        self.boot_count = 0

    def bootstrap(self, config):
        self.boot_count += 1

    def shutdown(self):
        pass


class _ResourceLeakModule:
    def bootstrap(self, config):
        pass

    def shutdown(self):
        pass


class TestRecoveryBackoff:
    """GEM-04: exponential backoff on re-bootstrap retry."""

    def test_backoff_delay_formula(self):
        assert _backoff_delay(0, base=1.0, factor=2.0, cap=30.0) == 1.0
        assert _backoff_delay(1, base=1.0, factor=2.0, cap=30.0) == 2.0
        assert _backoff_delay(2, base=1.0, factor=2.0, cap=30.0) == 4.0
        assert _backoff_delay(10, base=1.0, factor=2.0, cap=30.0) == 30.0  # capped

    def test_resource_release_failure_blocks_restart(self):
        mod = _ResourceLeakModule()
        result = run_recovery_cycle(
            "test_leak", mod, {},
            resource_release_checker=lambda: False,
            max_retries=0,
        )
        assert not result.passed
        assert "Resource release check failed" in result.message

    def test_resource_release_success_allows_restart(self):
        mod = _BackoffTestModule()
        result = run_recovery_cycle(
            "test_ok", mod, {},
            resource_release_checker=lambda: True,
            max_retries=0,
        )
        assert result.passed
        assert mod.boot_count == 2


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R5: trace_persistence_layer â€” GEM-19 flush_to_disk
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from meta_minimal.dtr_core.trace_persistence_layer import DTRStore
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.decision_state_encoder import DecisionState


class TestDTRFlushToDisk:
    """GEM-19: flush_to_disk writes valid JSON atomically."""

    def _make_record(self, pair: str = "BTCUSDT") -> DTRRecord:
        return DTRRecord(
            dtr_id="dtr_001",
            timestamp=1700000000.0,
            pair=pair,
            engine_id="engine_a",
            decision_state=DecisionState.EVALUATED,
        )

    def test_flush_writes_valid_json(self, repo_tmp_path):
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(self._make_record())
        store.persist(self._make_record("ETHUSDT"))
        count = store.flush_to_disk()
        assert count == 2

        output = repo_tmp_path / "dtr_records.json"
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["pair"] == "BTCUSDT"
        assert data[1]["pair"] == "ETHUSDT"

    def test_incremental_flush(self, repo_tmp_path):
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(self._make_record())
        assert store.flush_to_disk() == 1
        store.persist(self._make_record("ETHUSDT"))
        assert store.flush_to_disk() == 1  # only new record

    def test_flush_no_records_returns_zero(self, repo_tmp_path):
        store = DTRStore(flush_dir=repo_tmp_path)
        assert store.flush_to_disk() == 0

    def test_pending_flush_count(self, repo_tmp_path):
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(self._make_record())
        store.persist(self._make_record())
        assert store.pending_flush_count == 2
        store.flush_to_disk()
        assert store.pending_flush_count == 0


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R6: state_sanity_checker â€” FD leak + kill switch persistence
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from smoke_bootstrap_recovery.state_sanity_checker import (
    check_kill_switch_persisted,
)


class TestStateSanityCheckerSmoke:
    """Smoke tests for state_sanity_checker alignment changes."""

    def test_kill_switch_persistence_without_factory_fails_gracefully(self):
        """Without injected factory, check returns meaningful failure."""
        check = check_kill_switch_persisted("dummy_path")
        ok, msg = check()
        assert ok is False
        assert "requires" in msg.lower()

    def test_kill_switch_persistence_with_real_factory(self, repo_tmp_path):
        """With properly injected factory, kill switch persistence works."""
        from risk_backbone.emergency_kill_switch.circuit_breaker import (
            EmergencyCircuitBreaker,
            KillSwitchReason,
            KillSwitchState,
        )

        check = check_kill_switch_persisted(
            str(repo_tmp_path),
            breaker_factory=EmergencyCircuitBreaker,
            trip_reason=KillSwitchReason.CRITICAL_DIVERGENCE,
            tripped_state=KillSwitchState.TRIPPED,
        )
        ok, msg = check()
        assert ok is True
        assert "verified" in msg.lower()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R7: contradiction_checker â€” GEM-06 jitter tolerance
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from data_backbone.consistency_checker.contradiction_checker import (
    ContradictionChecker,
    ContradictionType,
)


class TestJitterTolerance:
    """GEM-06: 10ms jitter tolerance for timestamp reversals."""

    def test_within_jitter_tolerated(self):
        cc = ContradictionChecker()
        cc.check_timestamp_order("BTCUSDT", "trade", 100.000, recv_time=100.0)
        # 5ms backward = within 10ms tolerance
        result = cc.check_timestamp_order("BTCUSDT", "trade", 99.995, recv_time=100.0)
        assert result is None  # tolerated
        assert cc.total_contradictions == 0

    def test_beyond_jitter_flagged(self):
        cc = ContradictionChecker()
        cc.check_timestamp_order("BTCUSDT", "trade", 100.000, recv_time=100.0)
        # 15ms backward = beyond tolerance
        result = cc.check_timestamp_order("BTCUSDT", "trade", 99.985, recv_time=100.0)
        assert result is not None
        assert result.contradiction_type == ContradictionType.TIMESTAMP_REVERSAL

    def test_exactly_at_boundary(self):
        cc = ContradictionChecker()
        cc.check_timestamp_order("BTCUSDT", "trade", 100.000, recv_time=100.0)
        # Exactly 10ms backward = not beyond tolerance (requires strictly less)
        result = cc.check_timestamp_order("BTCUSDT", "trade", 99.990, recv_time=100.0)
        assert result is None  # exactly at boundary = tolerated

    def test_custom_jitter_tolerance(self):
        cc = ContradictionChecker(jitter_tolerance_s=0.050)  # 50ms
        cc.check_timestamp_order("BTCUSDT", "trade", 100.000, recv_time=100.0)
        result = cc.check_timestamp_order("BTCUSDT", "trade", 99.960, recv_time=100.0)
        assert result is None  # 40ms < 50ms tolerance


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R8: queue_manager â€” GEM-05 drop_oldest + saturation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from data_backbone.internal_router.queue_manager import QueueManager
from data_backbone.websocket_gateway.raw_message_emitter import RawMessage, RawMessageEmitter
from data_backbone.freshness_checker.stale_hard_guard import (
    StaleVerdict as Build2StaleVerdict,
    evaluate_exchange_staleness,
)
from interface_contracts import RuntimeMode


class TestQueueDropOldest:
    """GEM-05: drop_oldest evicts oldest, saturation helpers."""

    def test_drop_oldest_evicts_first(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=2)
        qm.enqueue("c1", "a")
        qm.enqueue("c1", "b")
        assert qm.enqueue("c1", "c") is True  # accepted, oldest dropped
        items = qm.dequeue("c1")
        assert items == ("b", "c")

    def test_drop_oldest_counted(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=1)
        qm.enqueue("c1", "a")
        qm.enqueue("c1", "b")
        stats = qm.get_stats("c1")
        assert stats.total_dropped == 1
        assert stats.depth == 1

    def test_saturation_detection(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=10)
        for i in range(9):
            qm.enqueue("c1", f"item_{i}")
        assert qm.is_saturated("c1", threshold=0.9) is True
        assert qm.is_saturated("c1", threshold=0.95) is False

    def test_saturated_queues(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=10)
        qm.create_queue("c2", max_size=10)
        for i in range(9):
            qm.enqueue("c1", f"item_{i}")
        for i in range(5):
            qm.enqueue("c2", f"item_{i}")
        saturated = qm.saturated_queues(threshold=0.9)
        assert "c1" in saturated
        assert "c2" not in saturated

    def test_high_water_mark_visible(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=3)
        qm.enqueue("c1", "a")
        qm.enqueue("c1", "b")
        qm.enqueue("c1", "c")
        qm.dequeue("c1", max_count=2)
        stats = qm.get_stats("c1")
        assert stats.high_water_mark == 3
        assert stats.capacity == 3


class TestRawMessageEmitterDropOldest:
    """Build-2 raw emitter must keep the newest messages."""

    def test_drop_oldest_keeps_latest(self):
        emitter = RawMessageEmitter(max_buffer_size=2)
        emitter.emit(RawMessage(pair="BTCUSDT", stream_type="trade", payload={"n": 1}, recv_time=1.0))
        emitter.emit(RawMessage(pair="BTCUSDT", stream_type="trade", payload={"n": 2}, recv_time=2.0))
        assert emitter.emit(RawMessage(pair="BTCUSDT", stream_type="trade", payload={"n": 3}, recv_time=3.0))
        items = emitter.consume()
        assert [item.payload["n"] for item in items] == [2, 3]
        assert emitter.total_dropped == 1


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R9: latency_meter â€” GEM-07 monotonic clock
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from execution_backbone.fill_tracker.latency_meter import (
    LatencyMeter,
    monotonic_now,
)


class TestMonotonicClock:
    """GEM-07: monotonic_now and latency invariants."""

    def test_monotonic_now_is_monotonic(self):
        t1 = monotonic_now()
        t2 = monotonic_now()
        assert t2 >= t1

    def test_latency_with_monotonic_timestamps(self):
        meter = LatencyMeter()
        t0 = monotonic_now()
        t1 = t0 + 0.005  # 5ms ack
        t2 = t0 + 0.020  # 20ms fill
        m = meter.record("ord1", sent_time=t0, ack_time=t1, full_fill_time=t2)
        assert m.submit_to_ack_s == pytest.approx(0.005)
        assert m.submit_to_full_fill_s == pytest.approx(0.020)
        assert m.submit_to_ack_s >= 0  # no negative latency


class TestBuild2ExchangeStaleRuntimeMode:
    """Build-2 stale local/exchange behavior depends on runtime_mode."""

    def test_shadow_blocks(self):
        result = evaluate_exchange_staleness(
            "BTCUSDT",
            "trade",
            local_timestamp=100.5,
            exchange_timestamp=100.0,
            runtime_mode=RuntimeMode.SHADOW,
        )
        assert result.verdict == Build2StaleVerdict.HARD_STALE
        assert result.blocked is True

    def test_micro_live_blocks(self):
        result = evaluate_exchange_staleness(
            "BTCUSDT",
            "trade",
            local_timestamp=100.5,
            exchange_timestamp=100.0,
            runtime_mode=RuntimeMode.MICRO_LIVE,
        )
        assert result.verdict == Build2StaleVerdict.HARD_STALE
        assert result.blocked is True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R10: cost_aggregator â€” GEM-08 market_impact
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from execution_backbone.execution_cost_meter.cost_aggregator import (
    CostAggregator,
    compute_trade_cost,
)


class TestMarketImpact:
    """GEM-08: market_impact included in total cost formula."""

    def test_market_impact_in_total(self):
        cost = compute_trade_cost(
            order_id="o1",
            pair="BTCUSDT",
            engine_id="engine_a",
            explicit_fee=0.001,
            implicit_cost=0.0005,
            adverse_selection=0.0002,
            partial_fill_cost=0.0001,
            market_impact=0.0003,
        )
        expected = 0.001 + 0.0005 + 0.0002 + 0.0001 + 0.0003
        assert cost.total_cost == pytest.approx(expected)
        assert cost.market_impact == 0.0003

    def test_zero_market_impact_default(self):
        cost = compute_trade_cost(
            order_id="o1", pair="BTCUSDT", engine_id="engine_a",
            explicit_fee=0.001, implicit_cost=0.0005,
        )
        assert cost.market_impact == 0.0

    def test_cost_surprise_includes_impact(self):
        cost = compute_trade_cost(
            order_id="o1", pair="BTCUSDT", engine_id="engine_a",
            explicit_fee=0.001, implicit_cost=0.0005,
            market_impact=0.001, expected_cost=0.001,
        )
        # total = 0.001 + 0.0005 + 0.001 = 0.0025, expected = 0.001
        assert cost.cost_surprise == pytest.approx(0.0025 - 0.001)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R11: alert_manager â€” illusion verte + queue drop rate
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from monitoring.alert_manager import build_monitoring_alerts
from monitoring.contracts import (
    EngineMetrics,
    InfraMetrics,
    MetaMetrics,
    MonitoringSnapshot,
    PairMetrics,
    PortfolioMetrics,
)


def _make_meta(**overrides) -> MetaMetrics:
    defaults = dict(
        dtr_coverage=0.0,
        cra_sterilization_rate=0.0,
        cra_alert_count=0,
        edge_credible_count=0,
        edge_degraded_count=0,
        edge_surveillance_count=0,
    )
    defaults.update(overrides)
    return MetaMetrics(**defaults)


def _make_snapshot(**overrides) -> MonitoringSnapshot:
    """Build a minimal MonitoringSnapshot for testing alerts."""
    defaults = dict(
        timestamp_ms=1700000000000,
        correlation_id="test_corr",
        profile="light",
        runtime_mode="shadow",
        portfolio=PortfolioMetrics(
            allocated_opportunities=0,
            gross_capacity_used_pct=0.0,
            loss_capacity_used_pct=0.0,
            beta_utilization=0.0,
            capital_deployed_usdt=0.0,
            ce_net=0.0,
        ),
        engines=(),
        pairs=(),
        infra=InfraMetrics(),
        meta=_make_meta(),
    )
    defaults.update(overrides)
    return MonitoringSnapshot(**defaults)


class TestIllusionVerte:
    """GEM-14: illusion verte alert fires when system looks healthy but isn't."""

    def test_illusion_verte_fires(self):
        snap = _make_snapshot(
            portfolio=PortfolioMetrics(
                allocated_opportunities=0,
                gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0,
                beta_utilization=0.0,
                capital_deployed_usdt=0.0,
                ce_net=0.0,  # CE_net <= 0
            ),
        )
        # Verify preconditions for illusion verte
        assert snap.active_alert_count == 0
        assert snap.portfolio.ce_net <= 0.0
        assert snap.meta.dtr_coverage < 0.5

        alerts = build_monitoring_alerts(snap)
        iv_alerts = [a for a in alerts if "illusion_verte" in a.alert_id]
        assert len(iv_alerts) == 1
        assert "Illusion verte" in iv_alerts[0].message

    def test_no_illusion_verte_when_ce_positive(self):
        snap = _make_snapshot(
            portfolio=PortfolioMetrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=10.0,
                loss_capacity_used_pct=5.0,
                beta_utilization=0.5,
                capital_deployed_usdt=1000.0,
                ce_net=0.001,
            ),
        )
        alerts = build_monitoring_alerts(snap)
        iv_alerts = [a for a in alerts if "illusion_verte" in a.alert_id]
        assert len(iv_alerts) == 0


class TestQueueDropRateAlert:
    """GEM-13: queue drop rate > 5% triggers alert."""

    def test_drop_rate_alert_fires(self):
        """Alert fires when total_dropped/total_enqueued > 5%."""
        # Create an InfraMetrics-like object with extra attributes
        class InfraWithDropRate(InfraMetrics):
            model_config = {"frozen": False}
            total_enqueued: int = 0
            total_dropped: int = 0

        infra = InfraWithDropRate(
            queue_backlog=10, total_enqueued=100, total_dropped=10  # 10% > 5%
        )
        snap = _make_snapshot(infra=infra)
        alerts = build_monitoring_alerts(snap)
        drop_alerts = [a for a in alerts if "drop_rate" in a.alert_id]
        assert len(drop_alerts) == 1

    def test_no_drop_rate_alert_when_low(self):
        snap = _make_snapshot(infra=InfraMetrics(queue_backlog=0))
        alerts = build_monitoring_alerts(snap)
        drop_alerts = [a for a in alerts if "drop_rate" in a.alert_id]
        assert len(drop_alerts) == 0


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R12: shadow_runtime â€” check_shadow_30j_gate
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from protocols.shadow_runtime import check_shadow_30j_gate
from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


def _complete_shadow_metrics(day_index: int) -> dict[str, float | str]:
    metrics = {
        "dtr_coverage": 1.0,
        "ce_net": 0.0012 + day_index * 0.000001,
        "estimated_cost_bps": 4.2,
        "edge_net": 0.0015,
        "drawdown_pct": 0.018,
        "stale_rate": 0.01,
        "economic_pass_rate": 0.67,
        "pair_health_ratio": 0.98,
        "backlog_avg": 2.0,
        "capital_simulated_usdt": 10000.0,
        "gross_exposure_shadow_pct": 18.0,
        "loss_budget_shadow_pct": 4.0,
        "capital_free_usdt": 8200.0,
        "beta_btc_shadow": 0.31,
        "dominant_cluster": "cluster_btc_beta",
        "pnl_shadow": 12.0 + day_index * 0.1,
        "dtr_loss_rate": 0.0,
        "log_loss_rate": 0.0,
        "event_latency_ms": 95.0,
        "hard_block_rate": 0.03,
        "phantom_trade_count": 0.0,
        "dtr_complete": 1.0,
        "decisions_reproducible": 1.0,
        "infra_stable": 1.0,
        "costs_plausible": 1.0,
        "break_even_visible": 1.0,
        "critical_alerts_visible": 1.0,
        "operator_actions_logged": 1.0,
        "ui_locked": 1.0,
        "go_no_go_rendered": 1.0,
    }
    for engine_id, gross_frequency in (
        ("engine_a", 8.0),
        ("engine_b", 7.0),
        ("engine_c", 6.0),
        ("engine_d", 5.0),
    ):
        metrics[f"{engine_id}.gross_frequency"] = gross_frequency
        metrics[f"{engine_id}.useful_frequency"] = gross_frequency * 0.4
        metrics[f"{engine_id}.estimated_cost_bps"] = 4.0
        metrics[f"{engine_id}.edge_net"] = 0.0012
        metrics[f"{engine_id}.economic_pass_rate"] = 0.66
        metrics[f"{engine_id}.conflict_rate"] = 0.04
        metrics[f"{engine_id}.marginal_edge"] = 0.0003
    for component_id, contribution_score in (
        ("build14_microstructure", 0.32),
        ("build14_regime", 0.28),
        ("build14_covariance", 0.25),
        ("build14_risk_contribution", 0.22),
        ("build14_edge_diversity", 0.20),
    ):
        metrics[f"{component_id}.contribution_score"] = contribution_score
        metrics[f"{component_id}.interaction_score"] = 0.08
    return metrics


class TestShadow30jGate:
    """HARD STATEMENT: check_shadow_30j_gate requires 30j plus a complete report."""

    def test_gate_fails_with_no_history(self, repo_tmp_path):
        passed, report = check_shadow_30j_gate(repo_tmp_path, profile="light")
        assert passed is False
        assert report["consecutive_days"] == 0
        assert report["remaining_days"] == 30

    def test_gate_passes_with_30_days(self, repo_tmp_path):
        c = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)
        base = 1700000000.0
        for i in range(30):
            c.record_shadow_day(
                passed_all_gates=True,
                metrics_summary=_complete_shadow_metrics(i),
                now=base + i * 80000,
            )
        passed, report = check_shadow_30j_gate(repo_tmp_path, profile="light")
        assert passed is True
        assert report["is_complete"] is True
        assert report["shadow_report_ready"] is True

    def test_gate_fails_with_30_days_but_incomplete_report(self, repo_tmp_path):
        c = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)
        base = 1700000000.0
        for i in range(30):
            c.record_shadow_day(
                passed_all_gates=True,
                metrics_summary={"dtr_coverage": 1.0},
                now=base + i * 80000,
            )
        passed, report = check_shadow_30j_gate(repo_tmp_path, profile="light")
        assert passed is False
        assert report["is_complete"] is True
        assert report["shadow_report_ready"] is False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R13: live_light_runtime â€” 30j prerequisite
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from protocols.live_light_runtime import run_live_light_gate


class TestLiveLightShadowPrerequisite:
    """HARD STATEMENT: live_light_runtime requires 30j plus report-ready Shadow."""

    def _make_minimal_input(self):
        """Build a minimal LiveLightInput that would pass all gates EXCEPT shadow."""
        from protocols.contracts import LiveLightInput, ShadowPortfolioJudgment
        from protocols.enums import MicroLiveRunState, MicroLiveVerdict
        return LiveLightInput(
            correlation_id="test_corr_001",
            profile="complete",
            runtime_mode="live",
            micro_live_run_id="mlr_001",
            shadow_run_id="sr_001",
            micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            micro_live_run_state=MicroLiveRunState.READY_TO_PROBE,
            micro_live_blocking_reasons=(),
            shadow_days_completed=30,
            shadow_required_days=30,
            component_verdicts_rendered=True,
            shadow_report_ready=True,
            shadow_portfolio_judgment=ShadowPortfolioJudgment(
                judgment_verdict="promotable",
                rationale="regression helper default",
            ),
            micro_live_stable_days=7,
            micro_live_required_days=7,
            micro_live_import_artifact_id="art_001",
            micro_live_import_lineage_version="v1.0",
            import_artifact_id="art_001",
            import_exported_from="local",
            import_lineage_version="v1.0",
            import_validation_status="accepted",
            import_source_profile="complete",
            import_review_state="pending",
            import_rejection_reasons=(),
            import_dataset_ref="dataset-1",
            import_clock_ref="clock-1",
            import_activation_stage="shadow_ready",
            import_health_state="active",
            import_compatibility_status="not_evaluated",
            import_compatibility_reasons=(),
            import_feature_lineage_required=True,
            import_feature_lineage_present=True,
            import_feature_lineage_status="ok",
            import_feature_lineage_reasons=(),
            import_transform_whitelist_required=True,
            import_transform_whitelist_present=True,
            import_transform_whitelist_status="ok",
            import_transform_whitelist_reasons=(),
            import_signature_check_status="verified",
            import_signature_check_reasons=(),
            import_conflict_resolution_mode="no_trade_then_strictest",
            import_conflict_hard_veto_action="no_trade",
            import_conflict_score_aggregation_mode="bounded_sum_with_global_cap",
            import_conflict_size_reduce_mode="min_factor_wins",
            import_conflict_rank_adjust_mode="bounded_sum",
            import_conflict_additive_soft_boosts_allowed=True,
            import_conflict_additive_soft_reduces_allowed=True,
            import_registry_atomicity_mode="atomic_snapshot_swap",
            import_registry_concurrency_model="single_writer_multi_reader",
            import_registry_publish_requires_atomic_replace=True,
            import_registry_publish_requires_fsync=True,
            import_registry_rollback_to_last_known_good=True,
            import_payload_ref_count=5,
            import_payload_bundle_present=True,
            import_review_export_ref="exports/review.md",
            import_feature_bridge_ref="exports/feature_bridge.json",
            import_parity_diagnostics_ref="exports/parity.json",
            import_replay_metrics_ref="exports/replay_metrics.json",
            import_replay_dtr_ref="exports/replay_dtr.json",
            onboarding_accepted=True,
            onboarding_review_state="pending",
            onboarding_reasons=(),
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            active_engines=("engine_a",),
            micro_live_planned_engines=("engine_a",),
            live_pairs=("BTCUSDT",),
            micro_live_planned_pairs=("BTCUSDT",),
            requested_total_notional_usdt=100.0,
            requested_pair_notional_usdt=50.0,
            max_total_notional_usdt=200.0,
            max_pair_notional_usdt=100.0,
        )

    def test_blocks_when_shadow_dir_with_no_days(self, repo_tmp_path):
        live_input = self._make_minimal_input()
        result = run_live_light_gate(live_input, shadow_state_dir=repo_tmp_path)
        assert result.decision.allowed_to_execute_small is False
        reasons = " ".join(result.decision.blocking_reasons)
        assert "HARD STATEMENT" in reasons
        assert "30 consecutive days" in reasons

    def test_passes_when_shadow_30j_and_report_ready_met(
        self,
        repo_tmp_path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "protocols.shadow_runtime.check_shadow_30j_gate",
            lambda state_dir, profile: (
                True,
                {"consecutive_days": 30, "shadow_report_ready": True},
            ),
        )

        live_input = self._make_minimal_input()
        result = run_live_light_gate(live_input, shadow_state_dir=repo_tmp_path)
        assert result.decision.allowed_to_execute_small is True
        reasons = " ".join(result.decision.blocking_reasons)
        assert "HARD STATEMENT" not in reasons

    def test_no_shadow_dir_skips_check(self):
        """Without shadow_state_dir, the gate is not checked."""
        live_input = self._make_minimal_input()
        result = run_live_light_gate(live_input, shadow_state_dir=None)
        reasons = " ".join(result.decision.blocking_reasons)
        assert "HARD STATEMENT" not in reasons


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# R14: correlation_conflict_checker â€” GEM-14 rejection audit
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from portfolio_minimal.opportunity_selector.correlation_conflict_checker import (
    ConflictType,
    RejectionAuditEntry,
    check_conflicts,
)
from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate


class TestRejectionAudit:
    """GEM-14: CONTRADICTORY_SIGNAL + RejectionAuditEntry audit trail."""

    def test_contradictory_signal_enum_exists(self):
        assert ConflictType.CONTRADICTORY_SIGNAL == "contradictory_signal"

    def test_rejection_audit_populated_on_duplicate(self):
        c1 = OpportunityCandidate(
            pair="BTCUSDT", engine_id="engine_a",
            penalized_score=0.7, cluster_id="crypto_major",
        )
        c2 = OpportunityCandidate(
            pair="BTCUSDT", engine_id="engine_b",
            penalized_score=0.5, cluster_id="crypto_major",
        )
        result = check_conflicts((c1, c2))
        assert result.duplicates_removed == 1
        assert len(result.rejection_audit) == 1
        audit = result.rejection_audit[0]
        assert audit.pair == "BTCUSDT"
        assert audit.conflict_type == ConflictType.DUPLICATE_PAIR
        assert "outranked" in audit.reason

    def test_no_audit_without_duplicates(self):
        c1 = OpportunityCandidate(
            pair="BTCUSDT", engine_id="engine_a",
            penalized_score=0.7, cluster_id="crypto_major",
        )
        c2 = OpportunityCandidate(
            pair="ETHUSDT", engine_id="engine_a",
            penalized_score=0.5, cluster_id="crypto_major",
        )
        result = check_conflicts((c1, c2))
        assert result.duplicates_removed == 0
        assert len(result.rejection_audit) == 0
