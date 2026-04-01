"""
INTEGRATION TESTS — Phase 3 alignment verification.

INT-1: Build-1/2 chain (market event → validation → queue → jitter)
INT-2: Build-11/13 chain (shadow counter → gate → live-light prerequisite)
INT-3: Kill switch persistence chain (trip → persist → restart → blocked)
"""

import json
import pytest

from pydantic import ValidationError


def _complete_shadow_metrics(day_index: int) -> dict[str, float]:
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
        "dtr_complete": 1.0,
        "decisions_reproducible": 1.0,
        "infra_stable": 1.0,
        "costs_plausible": 1.0,
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


# ─────────────────────────────────────────────────────────
# INT-1: Build-1/2 — Market event → validation → queue → jitter
# ─────────────────────────────────────────────────────────


class TestIntegrationBuild1Build2:
    """INT-1: valid market event flows through validation, queue, and jitter checks."""

    def test_valid_event_through_queue_no_corruption(self):
        """Market event enters, gets queued, dequeued, and data is intact."""
        from interface_contracts.market_event_contracts import (
            DepthEvent,
            DepthLevel,
            TradeEvent,
        )
        from data_backbone.internal_router.queue_manager import QueueManager
        from data_backbone.consistency_checker.contradiction_checker import ContradictionChecker

        # Step 1: Create valid market events
        trade = TradeEvent(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            price=42000.0,
            quantity=0.1,
            side="buy",
            trade_id="t001",
        )
        depth = DepthEvent(
            timestamp_ms=1700000000000,
            pair="BTCUSDT",
            bids=[DepthLevel(price=42000.0, quantity=1.0)],
            asks=[DepthLevel(price=42001.0, quantity=1.0)],
        )

        # Step 2: Validate market event constraints
        assert trade.notional_usdt == pytest.approx(4200.0)
        assert depth.spread_bps > 0
        assert depth.best_bid < depth.best_ask  # not crossed

        # Step 3: Queue management — events enqueued/dequeued correctly
        qm = QueueManager()
        qm.create_queue("engine_a", max_size=100)
        assert qm.enqueue("engine_a", trade) is True
        assert qm.enqueue("engine_a", depth) is True
        items = qm.dequeue("engine_a")
        assert len(items) == 2
        assert items[0].pair == "BTCUSDT"

        # Step 4: Contradiction checker — normal event flow, no jitter issues
        cc = ContradictionChecker()
        result = cc.check_timestamp_order("BTCUSDT", "trade", 100.000, recv_time=100.0)
        assert result is None  # first event, no contradiction
        # Normal forward progression
        result = cc.check_timestamp_order("BTCUSDT", "trade", 100.005, recv_time=100.01)
        assert result is None
        assert cc.total_contradictions == 0

    def test_crossed_book_rejected_before_queue(self):
        """Crossed book event is rejected at validation, never enters queue."""
        from interface_contracts.market_event_contracts import DepthEvent, DepthLevel
        from data_backbone.internal_router.queue_manager import QueueManager

        qm = QueueManager()
        qm.create_queue("engine_a", max_size=100)

        with pytest.raises(ValidationError, match="Crossed book"):
            event = DepthEvent(
                timestamp_ms=1700000000000,
                pair="BTCUSDT",
                bids=[DepthLevel(price=42001.0, quantity=1.0)],
                asks=[DepthLevel(price=42000.0, quantity=1.0)],
            )
        # Nothing entered the queue
        assert qm.get_depth("engine_a") == 0

    def test_jitter_within_tolerance_no_interruption(self):
        """Small timestamp reversals within 10ms don't disrupt the flow."""
        from data_backbone.consistency_checker.contradiction_checker import ContradictionChecker

        cc = ContradictionChecker()
        timestamps = [100.000, 100.005, 100.003, 100.010, 100.008]
        contradictions = 0
        for ts in timestamps:
            result = cc.check_timestamp_order("BTCUSDT", "trade", ts, recv_time=ts)
            if result is not None:
                contradictions += 1
        # Only check pairs where reversal > 10ms — none here
        assert contradictions == 0

    def test_queue_drop_oldest_under_pressure(self):
        """When queue fills up, oldest events are evicted, system continues."""
        from data_backbone.internal_router.queue_manager import QueueManager

        qm = QueueManager()
        qm.create_queue("engine_a", max_size=3)
        for i in range(5):
            qm.enqueue("engine_a", f"event_{i}")

        stats = qm.get_stats("engine_a")
        assert stats.depth == 3
        assert stats.total_dropped == 2
        assert qm.is_saturated("engine_a", threshold=0.9) is True

        items = qm.dequeue("engine_a")
        assert items == ("event_2", "event_3", "event_4")  # oldest 2 evicted


# ─────────────────────────────────────────────────────────
# INT-2: Build-11/13 — Shadow counter → gate → live-light
# ─────────────────────────────────────────────────────────


class TestIntegrationBuild11Build13:
    """INT-2: shadow_day_counter persists → gate evaluates → live_light blocks/passes."""

    def test_full_30j_cycle_to_live_light(self, repo_tmp_path):
        """Complete 30-day shadow cycle enables Live-Light promotion."""
        from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile
        from protocols.shadow_runtime import check_shadow_30j_gate
        from protocols.promotion_gates import check_light_to_micro_live

        base_ts = 1700000000.0
        one_day = 86_400.0

        # Phase 1: Record 30 consecutive shadow days
        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)
        for i in range(30):
            rec = counter.record_shadow_day(
                passed_all_gates=True,
                metrics_summary=_complete_shadow_metrics(i),
                now=base_ts + i * one_day * 0.9,
            )
        assert counter.is_promotion_ready() is True

        # Phase 2: Verify persistence survives reload
        counter2 = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)
        assert counter2.get_status().consecutive_days == 30

        # Phase 3: Shadow gate passes
        gate_passed, report = check_shadow_30j_gate(repo_tmp_path, profile="light")
        assert gate_passed is True
        assert report["is_complete"] is True
        assert report["shadow_report_ready"] is True

        # Phase 4: Promotion gate agrees
        promo_result = check_light_to_micro_live(repo_tmp_path)
        assert promo_result.passed is True

    def test_incomplete_shadow_blocks_live_light(self, repo_tmp_path):
        """Incomplete shadow trading blocks Live-Light."""
        from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile
        from protocols.shadow_runtime import check_shadow_30j_gate
        from protocols.live_light_runtime import run_live_light_gate
        from protocols.contracts import LiveLightInput
        from protocols.enums import MicroLiveRunState, MicroLiveVerdict

        base_ts = 1700000000.0
        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)
        for i in range(15):  # Only 15 days
            counter.record_shadow_day(
                passed_all_gates=True, now=base_ts + i * 80000
            )

        # Gate should fail
        gate_passed, _ = check_shadow_30j_gate(repo_tmp_path, profile="light")
        assert gate_passed is False

        # Live-Light gate should block with HARD STATEMENT
        live_input = LiveLightInput(
            correlation_id="test_int2",
            profile="light",
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
            micro_live_stable_days=7,
            micro_live_required_days=7,
            micro_live_import_artifact_id="art_001",
            micro_live_import_lineage_version="v1.0",
            import_artifact_id="art_001",
            import_lineage_version="v1.0",
            import_validation_status="accepted",
            import_rejection_reasons=(),
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
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=100.0,
            requested_pair_notional_usdt=50.0,
            max_total_notional_usdt=200.0,
            max_pair_notional_usdt=100.0,
        )
        result = run_live_light_gate(live_input, shadow_state_dir=repo_tmp_path)
        assert result.decision.allowed_to_execute_small is False
        reasons = " ".join(result.decision.blocking_reasons)
        assert "HARD STATEMENT" in reasons
        assert "15/30" in reasons

    def test_gap_reset_blocks_promotion(self, repo_tmp_path):
        """A gap > 24h resets the counter and blocks promotion."""
        from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile
        from protocols.promotion_gates import check_light_to_micro_live

        base_ts = 1700000000.0
        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.LIGHT)

        # Record 29 days
        for i in range(29):
            counter.record_shadow_day(
                passed_all_gates=True, now=base_ts + i * 80000
            )

        # Gap > 24h then one more day
        gap_ts = base_ts + 29 * 80000 + 200_000  # way beyond 24h
        counter.record_shadow_day(passed_all_gates=True, now=gap_ts)

        # Counter was reset, so only 1 day now
        assert counter.get_status().consecutive_days == 1
        assert counter.get_status().resets >= 1

        result = check_light_to_micro_live(repo_tmp_path)
        assert result.passed is False


# ─────────────────────────────────────────────────────────
# INT-3: Kill switch persistence chain
# ─────────────────────────────────────────────────────────


class TestIntegrationKillSwitch:
    """INT-3: trip → persist → restart → blocked → reset → unblocked."""

    def test_full_kill_switch_lifecycle(self, repo_tmp_path):
        """Complete kill switch lifecycle: trip → restart → still blocked → reset."""
        from risk_backbone.emergency_kill_switch.circuit_breaker import (
            EmergencyCircuitBreaker,
            KillSwitchReason,
            KillSwitchState,
        )

        # Step 1: Trip the kill switch
        cb1 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb1.is_trading_allowed() is True
        cb1.trip(KillSwitchReason.LOSS_BUDGET_BREACH, "test loss limit")
        assert cb1.is_trading_allowed() is False

        # Step 2: Verify persistence on disk
        state_file = repo_tmp_path / "kill_switch_state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["state"] == "tripped"

        # Step 3: Simulate restart — new instance reads persisted state
        cb2 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb2.is_trading_allowed() is False
        assert cb2.current_state == KillSwitchState.TRIPPED
        assert cb2.current_reason == KillSwitchReason.LOSS_BUDGET_BREACH

        # Step 4: System stays blocked across multiple restarts
        cb3 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb3.is_trading_allowed() is False

        # Step 5: Operator reset
        cb3.reset("operator approved recovery")
        assert cb3.is_trading_allowed() is True

        # Step 6: After reset, restart shows armed
        cb4 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb4.is_trading_allowed() is True
        assert cb4.current_state == KillSwitchState.ARMED

    def test_external_flag_triggers_and_persists(self, repo_tmp_path):
        """External KILL_SWITCH_ACTIVE file trips and persists across restart."""
        from risk_backbone.emergency_kill_switch.circuit_breaker import (
            EmergencyCircuitBreaker,
            KillSwitchReason,
        )

        # Step 1: Create external flag file
        flag = repo_tmp_path / "KILL_SWITCH_ACTIVE"
        flag.write_text("operator emergency", encoding="utf-8")

        # Step 2: New instance detects and trips
        cb = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb.is_trading_allowed() is False
        assert cb.current_reason == KillSwitchReason.EXTERNAL_FILE_FLAG

        # Step 3: State persisted
        state_file = repo_tmp_path / "kill_switch_state.json"
        assert state_file.exists()

        # Step 4: Remove flag, but state remains tripped until explicit reset
        flag.unlink()
        cb2 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb2.is_trading_allowed() is False  # still tripped from persistence

        # Step 5: Reset clears everything
        cb2.reset("cleared by operator")
        cb3 = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb3.is_trading_allowed() is True

    def test_corrupted_state_assumes_tripped(self, repo_tmp_path):
        """Corrupted state file = assume tripped for safety."""
        from risk_backbone.emergency_kill_switch.circuit_breaker import (
            EmergencyCircuitBreaker,
            KillSwitchState,
        )

        state_file = repo_tmp_path / "kill_switch_state.json"
        state_file.write_text("CORRUPTED DATA!!!", encoding="utf-8")

        cb = EmergencyCircuitBreaker(state_dir=repo_tmp_path)
        assert cb.is_trading_allowed() is False
        assert cb.current_state == KillSwitchState.TRIPPED
