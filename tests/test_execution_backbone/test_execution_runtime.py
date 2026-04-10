"""Runtime tests for execution_backbone Build-3."""
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from execution_backbone.execution_runtime import (
    ExecutionNoTradeFilterInput,
    ExecutionNoTradeFilterOutcome,
    ExecutionOpportunity,
    ExecutionRuntime,
    ExecutionSubmissionStatus,
    RemoteExecutionState,
    ReplaceReceipt,
    SubmitReceipt,
    VenueOrderEvent,
    VenueOrderEventType,
)
from execution_backbone.execution_cost_meter.adverse_selection_meter import (
    AdverseSelectionDelayPolicy,
)
from execution_backbone.fill_tracker.order_terminal_state_resolver import TerminalCategory
from execution_backbone.order_decider.intent_builder import NoTradeReason, VenueConstraintSnapshot
from execution_backbone.reconciliation_layer.recovery_trigger import RecoveryAction
from protocols import (
    ExecutionNoTradeHookInput,
    ExecutionNoTradeHookPlanPayload,
    run_execution_no_trade_hook,
)
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from scoring_backbone import FeeAwareEdgeGateConfig
from sharia_compliance import ShariaRuntime, load_sharia_policy


pytestmark = pytest.mark.build3


class FakeExecutionVenue:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, object, float]] = []
        self.replacements: list[tuple[str, str, object, float]] = []
        self.cancel_requests: list[tuple[str, float, str]] = []
        self._events: list[VenueOrderEvent] = []
        self.remote_state = RemoteExecutionState()
        self._counter = 0
        self.constraints_by_pair: dict[str, VenueConstraintSnapshot] = {}

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        return self.constraints_by_pair.get(pair)

    def submit_order(self, intent, now: float) -> SubmitReceipt:
        self._counter += 1
        order_id = f"ord-{self._counter}"
        self.submissions.append((order_id, intent, now))
        return SubmitReceipt(order_id=order_id, submitted_at=now)

    def replace_order(self, original_order_id: str, intent, now: float) -> ReplaceReceipt:
        self._counter += 1
        replacement_order_id = f"ord-{self._counter}"
        self.replacements.append((original_order_id, replacement_order_id, intent, now))
        return ReplaceReceipt(
            original_order_id=original_order_id,
            replacement_order_id=replacement_order_id,
            replaced_at=now,
            submitted_at=now,
        )

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        self.cancel_requests.append((order_id, now, reason))

    def poll_order_events(self) -> tuple[VenueOrderEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def fetch_remote_state(self) -> RemoteExecutionState:
        return self.remote_state

    def push_events(self, *events: VenueOrderEvent) -> None:
        self._events.extend(events)


class FakeVenueConstraintProvider:
    def __init__(self) -> None:
        self.constraints_by_pair: dict[str, VenueConstraintSnapshot] = {}

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        return self.constraints_by_pair.get(pair)


@pytest.fixture
def fee_aware_edge_tmpdir() -> Path:
    root = Path("build/pytest-execution-fee-aware-edge") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _edge_dtr(
    *,
    dtr_id: str,
    expected_cost: float,
    realized_cost: float,
    gross_return: float,
):
    return build_dtr(
        dtr_id=dtr_id,
        pair="BTCUSDT",
        engine_id="engine_a",
        decision_state=DecisionState.EXECUTED,
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        gross_return=gross_return,
        ce_expected=gross_return - expected_cost,
        runtime_mode="local_replay",
        input_source="local_replay",
        timestamp=1_700_000_000.0,
    )


def _write_fee_aware_edge_artifact(root) -> None:
    records = (
        _edge_dtr(dtr_id="dtr-1", expected_cost=0.0010, realized_cost=0.0008, gross_return=0.0038),
        _edge_dtr(dtr_id="dtr-2", expected_cost=0.0011, realized_cost=0.0009, gross_return=0.0041),
        _edge_dtr(dtr_id="dtr-3", expected_cost=0.0012, realized_cost=0.0010, gross_return=0.0040),
        _edge_dtr(dtr_id="dtr-4", expected_cost=0.0013, realized_cost=0.0011, gross_return=0.0047),
        _edge_dtr(dtr_id="dtr-5", expected_cost=0.0014, realized_cost=0.0012, gross_return=0.0048),
        _edge_dtr(dtr_id="dtr-6", expected_cost=0.0015, realized_cost=0.0013, gross_return=0.0050),
    )
    config = EdgeGateCalibrationConfig(
        min_positive_trades=5,
        min_cost_observations=6,
        bootstrap_samples=250,
        rng_seed=7,
    )
    report = calibrate_edge_gate_thresholds(
        records,
        config=config,
        generated_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
    )
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by="operator.aziz",
        config=config,
        signed_at=datetime(2026, 4, 10, 13, 5, tzinfo=timezone.utc),
    )
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "edge_gate.yml").write_text(
        yaml.safe_dump(artifact.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def _opportunity(
    *,
    intent_id: str = "intent-1",
    pair: str = "BTCUSDT",
    side: str = "buy",
    quantity: float = 0.25,
    expected_gain: float = 0.0100,
    expected_cost: float = 0.0015,
    spread_bps: float = 2.0,
    reference_price: float | None = None,
    metadata: dict[str, object] | None = None,
) -> ExecutionOpportunity:
    return ExecutionOpportunity(
        intent_id=intent_id,
        pair=pair,
        engine_id="engine_a",
        side=side,
        quantity=quantity,
        expected_gain=expected_gain,
        expected_cost=expected_cost,
        score=0.82,
        justification="validated execution path",
        spread_bps=spread_bps,
        reference_price=reference_price,
        metadata={} if metadata is None else metadata,
    )


def _compiled_execution_no_trade_filter(
    payload: ExecutionNoTradeHookPlanPayload,
):
    def _evaluate(hook_input: ExecutionNoTradeFilterInput) -> ExecutionNoTradeFilterOutcome:
        outcome = run_execution_no_trade_hook(
            ExecutionNoTradeHookInput.model_validate(hook_input.model_dump()),
            payload,
        )
        return ExecutionNoTradeFilterOutcome.model_validate(outcome.model_dump())

    return _evaluate


class TestExecutionRuntime:
    def test_runtime_resolves_adverse_selection_delay_from_policy(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            adverse_selection_delay_policy=AdverseSelectionDelayPolicy(
                policy_id="adverse_selection_delay.runtime-test.v1",
                default_delay_s=5.0,
                pair_delay_overrides_s={"NEARUSDT": 9.0},
            ),
        )

        assert runtime._resolve_adverse_selection_delay_s(
            pair="NEARUSDT",
            event_delay_s=None,
        ) == pytest.approx(9.0)
        assert runtime._resolve_adverse_selection_delay_s(
            pair="NEARUSDT",
            event_delay_s=1.25,
        ) == pytest.approx(1.25)

    def test_runtime_executes_real_path_across_fill_cost_and_reconciliation(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.order_id == "ord-1"
        assert len(adapter.submissions) == 1

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.5,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
                market_impact=0.0002,
            ),
        )

        processing = runtime.process_events()
        assert processing.processed_events == 2
        assert len(processing.terminal_resolutions) == 1
        assert processing.terminal_resolutions[0].category == TerminalCategory.FULL_FILL
        assert processing.fill_stats.full_fills == 1
        assert processing.latency_stats.count == 1
        assert processing.cost_aggregate.count == 1
        assert runtime.get_local_positions()["BTC"] == pytest.approx(0.25)

        adapter.remote_state = RemoteExecutionState(
            orders={},
            fills={"ord-1": 0.25},
            positions={"BTC": 0.25},
        )
        runtime.reconcile(now=100.6)
        reconciliation = runtime.reconcile(now=100.7)
        assert reconciliation.order_result.aligned is True
        assert reconciliation.fill_result.aligned is True
        assert reconciliation.position_result.aligned is True
        assert reconciliation.recovery_decision.action == RecoveryAction.NONE

    def test_runtime_reconciliation_ignores_terminal_orders_returned_by_remote(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.5,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
            ),
        )
        runtime.process_events()

        adapter.remote_state = RemoteExecutionState(
            orders={"ord-1": "filled"},
            fills={"ord-1": 0.25},
            positions={"BTC": 0.25},
        )
        first_reconciliation = runtime.reconcile(now=100.6)
        assert first_reconciliation.recovery_decision.action == RecoveryAction.SOFT_RESYNC

        reconciliation = runtime.reconcile(now=100.7)
        assert reconciliation.order_result.aligned is True
        assert reconciliation.order_result.order_diff == 0
        assert reconciliation.divergence_summary.is_critical is False
        assert reconciliation.recovery_decision.action == RecoveryAction.NONE

    def test_runtime_releases_detailed_terminal_state_but_keeps_compact_fill_snapshot(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.5,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
            ),
        )

        runtime.process_events()

        assert "ord-1" not in runtime._intents
        assert "ord-1" not in runtime._timeout_by_order_id
        assert "ord-1" not in runtime._cost_context
        assert runtime._state_tracker.get("ord-1") is None
        assert runtime._fill_aggregator.get_aggregated("ord-1") is None
        assert runtime._local_fill_quantities()["ord-1"] == pytest.approx(0.25)

    def test_runtime_bounds_terminal_snapshot_retention(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, terminal_order_retention=1)

        first = runtime.submit_opportunity(_opportunity(intent_id="intent-1"), now=100.0)
        assert first.status == ExecutionSubmissionStatus.SUBMITTED
        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.2,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
            ),
        )
        runtime.process_events()

        second = runtime.submit_opportunity(_opportunity(intent_id="intent-2"), now=101.0)
        assert second.status == ExecutionSubmissionStatus.SUBMITTED
        adapter.push_events(
            VenueOrderEvent(order_id="ord-2", event_type=VenueOrderEventType.ACK, timestamp=101.1),
            VenueOrderEvent(
                order_id="ord-2",
                event_type=VenueOrderEventType.FILL,
                timestamp=101.2,
                fill_id="fill-2",
                fill_quantity=0.25,
                fill_price=50020.0,
                fee_amount=12.5,
                mid_price=50010.0,
                post_fill_mid_price=49990.0,
            ),
        )
        runtime.process_events()

        assert "ord-1" not in runtime._terminal_orders
        assert "ord-2" in runtime._terminal_orders

    def test_runtime_rejects_no_trade_when_cost_kills_edge(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(expected_gain=0.0010, expected_cost=0.0050),
            now=10.0,
        )
        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.COST_EXCEEDS_EDGE
        assert len(adapter.submissions) == 0

    def test_runtime_blocks_trade_when_fee_aware_edge_gate_rejects(self, fee_aware_edge_tmpdir: Path):
        _write_fee_aware_edge_artifact(fee_aware_edge_tmpdir)
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            fee_aware_edge_gate_config=FeeAwareEdgeGateConfig(calibration_root=fee_aware_edge_tmpdir),
        )

        submission = runtime.submit_opportunity(
            _opportunity(expected_gain=0.0013, expected_cost=0.0007),
            now=10.1,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.COST_EXCEEDS_EDGE
        assert "threshold=" in submission.detail
        assert submission.no_trade.context["gate"] == "fee_aware_edge"
        assert submission.no_trade.context["reason_code"] == "EDGE_INSUFFICIENT_VS_FEES"
        assert float(submission.no_trade.context["expected_edge_bps"]) == pytest.approx(13.0)
        assert float(submission.no_trade.context["expected_cost_bps"]) == pytest.approx(7.0)
        assert float(submission.no_trade.context["threshold_bps"]) > 13.0
        no_trade_events = [event for event in runtime._decision_reporter.get_events() if not event.is_trade]
        assert len(no_trade_events) == 1
        assert no_trade_events[0].no_trade_reason == "cost_exceeds_edge"
        assert no_trade_events[0].context == submission.no_trade.context
        assert len(adapter.submissions) == 0

    def test_runtime_submits_trade_when_fee_aware_edge_gate_allows(self, fee_aware_edge_tmpdir: Path):
        _write_fee_aware_edge_artifact(fee_aware_edge_tmpdir)
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            fee_aware_edge_gate_config=FeeAwareEdgeGateConfig(calibration_root=fee_aware_edge_tmpdir),
        )

        submission = runtime.submit_opportunity(
            _opportunity(expected_gain=0.0030, expected_cost=0.0007),
            now=10.2,
        )

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.order_id == "ord-1"
        assert len(adapter.submissions) == 1

    def test_runtime_blocks_submission_from_execution_no_trade_filter(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            execution_no_trade_filter=_compiled_execution_no_trade_filter(
                ExecutionNoTradeHookPlanPayload(
                    blocked=True,
                    block_reason_codes=("ARTIFACT_EXECUTION_BLOCK",),
                    detail="artifact veto at execution boundary",
                )
            ),
        )

        submission = runtime.submit_opportunity(_opportunity(intent_id="artifact-block"), now=12.0)

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.HARD_BLOCKER
        assert submission.detail == "artifact veto at execution boundary"
        assert len(adapter.submissions) == 0

    def test_runtime_blocks_submission_from_sharia_trade_authorizer(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            sharia_trade_authorizer=ShariaRuntime(load_sharia_policy("config/sharia/policy_v1.yml")),
        )

        submission = runtime.submit_opportunity(
            _opportunity(intent_id="sharia-block", pair="AAVEUSDT"),
            now=12.5,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.SHARIA_BLOCKED
        assert len(adapter.submissions) == 0

    def test_runtime_blocks_submission_from_pair_screening_failure(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(
            adapter,
            sharia_trade_authorizer=ShariaRuntime(load_sharia_policy("config/sharia/policy_v1.yml")),
        )

        submission = runtime.submit_opportunity(
            _opportunity(
                intent_id="screening-block",
                metadata={
                    "pair_screening": {
                        "pair": "BTCUSDT",
                        "screening_provider": "fixture",
                        "provider_version": "v1",
                        "reviewed_at": "2026-04-10T12:00:00Z",
                        "debt_to_total_assets": "0.34",
                        "cash_and_interest_bearing_to_total_assets": "0.10",
                        "interest_income_to_total_revenue": "0.01",
                    }
                },
            ),
            now=12.5,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.SHARIA_BLOCKED
        assert len(adapter.submissions) == 0

    def test_runtime_timeout_requests_cancel_and_finalizes_partial_cancel(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(intent_id="limit-intent", spread_bps=6.0, reference_price=50000.0, quantity=1.0),
            now=200.0,
        )
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.intent is not None
        assert submission.intent.order_type.value == "limit"

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=200.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=200.4,
                fill_id="fill-1",
                fill_quantity=0.4,
                fill_price=50000.0,
                fee_rate=0.001,
                mid_price=49995.0,
                post_fill_mid_price=49990.0,
                current_mid=49992.0,
            ),
        )
        first_processing = runtime.process_events()
        assert first_processing.fill_stats.open_orders == 1
        assert first_processing.cost_aggregate.count == 0

        timeout_result = runtime.sweep_timeouts(now=231.0)
        assert timeout_result.cancelled_order_ids == ("ord-1",)
        assert adapter.cancel_requests == [("ord-1", 231.0, "timeout")]

        adapter.push_events(
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.CANCELLED,
                timestamp=231.5,
                reason="timeout",
            ),
        )
        final_processing = runtime.process_events()
        assert len(final_processing.terminal_resolutions) == 1
        assert final_processing.terminal_resolutions[0].category == TerminalCategory.PARTIAL_FILL_CANCELLED
        assert final_processing.fill_stats.partial_fills == 1
        assert final_processing.cost_aggregate.count == 1

    def test_runtime_replace_order_cancels_old_and_submits_new(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        first = runtime.submit_opportunity(
            _opportunity(intent_id="replace-me", spread_bps=6.0, reference_price=50000.0),
            now=50.0,
        )
        replacement = runtime.replace_order(first.order_id, new_price_limit=49990.0, now=55.0)

        assert replacement.status == ExecutionSubmissionStatus.REPLACED
        assert replacement.replaced_order_id == "ord-1"
        assert replacement.order_id == "ord-2"
        assert len(adapter.replacements) == 1
        fill_stats = runtime.get_fill_stats()
        assert fill_stats.cancellations == 1
        assert fill_stats.open_orders == 1

    def test_runtime_normalizes_limit_order_to_venue_tick_and_step(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(
                intent_id="limit-normalize",
                side="buy",
                quantity=1.234,
                spread_bps=6.0,
                reference_price=50000.03,
            ).model_copy(
                update={
                    "venue_constraints": VenueConstraintSnapshot(
                        tick_size="0.1",
                        step_size="0.01",
                        min_notional="10",
                    )
                }
            ),
            now=10.0,
        )

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.intent is not None
        assert submission.intent.order_type.value == "limit"
        assert submission.intent.quantity == pytest.approx(1.23)
        assert submission.intent.quantity_exact == "1.23"
        assert submission.intent.price_limit == pytest.approx(50000.0)
        assert submission.intent.price_limit_exact == "50000"

    def test_runtime_can_source_venue_constraints_from_adapter(self):
        adapter = FakeExecutionVenue()
        adapter.constraints_by_pair["BTCUSDT"] = VenueConstraintSnapshot(
            tick_size="0.1",
            step_size="0.01",
            min_notional="10",
        )
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(
                intent_id="adapter-constraints",
                side="buy",
                quantity=1.234,
                spread_bps=6.0,
                reference_price=50000.03,
            ),
            now=10.5,
        )

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.intent is not None
        assert submission.intent.venue_constraints is not None
        assert submission.intent.quantity_exact == "1.23"
        assert submission.intent.price_limit_exact == "50000"

    def test_runtime_can_source_venue_constraints_from_provider_fallback(self):
        adapter = FakeExecutionVenue()
        provider = FakeVenueConstraintProvider()
        provider.constraints_by_pair["BTCUSDT"] = VenueConstraintSnapshot(
            tick_size="0.1",
            step_size="0.01",
            min_notional="10",
        )
        runtime = ExecutionRuntime(adapter, venue_constraint_provider=provider)

        submission = runtime.submit_opportunity(
            _opportunity(
                intent_id="provider-constraints",
                side="buy",
                quantity=1.234,
                spread_bps=6.0,
                reference_price=50000.03,
            ),
            now=10.7,
        )

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.intent is not None
        assert submission.intent.venue_constraints is not None
        assert submission.intent.quantity_exact == "1.23"
        assert submission.intent.price_limit_exact == "50000"

    def test_runtime_blocks_when_normalized_order_breaks_min_notional(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(
                intent_id="min-notional-block",
                quantity=0.001,
                spread_bps=6.0,
                reference_price=1000.0,
            ).model_copy(
                update={
                    "venue_constraints": VenueConstraintSnapshot(
                        tick_size="0.1",
                        step_size="0.001",
                        min_notional="10",
                    )
                }
            ),
            now=11.0,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.VENUE_CONSTRAINTS
        assert "min_notional" in submission.detail

    def test_runtime_replace_order_applies_side_aware_tick_rounding(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        first = runtime.submit_opportunity(
            _opportunity(
                intent_id="replace-sell",
                pair="BTCUSDT",
                side="sell",
                quantity=0.5,
                spread_bps=6.0,
                reference_price=50000.01,
            ).model_copy(
                update={
                    "venue_constraints": VenueConstraintSnapshot(
                        tick_size="0.1",
                        step_size="0.01",
                        min_notional="10",
                    )
                }
            ),
            now=20.0,
        )

        replacement = runtime.replace_order(first.order_id, new_price_limit=49999.91, now=21.0)

        assert replacement.status == ExecutionSubmissionStatus.REPLACED
        assert replacement.intent is not None
        assert replacement.intent.price_limit == pytest.approx(50000.0)
        assert replacement.intent.price_limit_exact == "50000"

    def test_runtime_replace_order_generates_unique_intent_ids_even_with_same_timestamp(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        first = runtime.submit_opportunity(
            _opportunity(intent_id="replace-a", spread_bps=6.0, reference_price=50000.0),
            now=10.0,
        )
        second = runtime.submit_opportunity(
            _opportunity(intent_id="replace-b", spread_bps=6.0, reference_price=50010.0),
            now=11.0,
        )

        replacement_a = runtime.replace_order(first.order_id, new_price_limit=49990.0, now=0.0)
        replacement_b = runtime.replace_order(second.order_id, new_price_limit=50020.0, now=0.0)

        assert replacement_a.intent is not None
        assert replacement_b.intent is not None
        assert replacement_a.intent.intent_id == "replace-a:replace:ord-1:1"
        assert replacement_b.intent.intent_id == "replace-b:replace:ord-2:2"
        assert replacement_a.intent.intent_id != replacement_b.intent.intent_id

    def test_runtime_rejects_float_bridge_loss_above_tick_bound(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        with pytest.raises(ValueError, match="above allowed"):
            runtime.submit_opportunity(
                _opportunity(
                    intent_id="bridge-loss",
                    quantity=0.1,
                    spread_bps=6.0,
                    reference_price=0.1,
                ).model_copy(
                    update={
                        "venue_constraints": VenueConstraintSnapshot(
                            tick_size="0.00000000000000000001",
                            step_size="0.00000000000000000001",
                            min_notional="0.00000000000000000001",
                        )
                    }
                ),
                now=22.0,
            )

    def test_runtime_critical_reconciliation_triggers_halt(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        runtime.submit_opportunity(_opportunity(quantity=0.1), now=300.0)
        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=300.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=300.4,
                fill_id="fill-1",
                fill_quantity=0.1,
                fill_price=50000.0,
                fee_amount=5.0,
                mid_price=49995.0,
                post_fill_mid_price=49970.0,
            ),
        )
        runtime.process_events()

        adapter.remote_state = RemoteExecutionState(
            orders={"ord-1": "filled"},
            fills={"ord-1": 0.1},
            positions={"BTC": 2.0},
        )
        reconciliation = runtime.reconcile(now=301.0)
        assert reconciliation.position_result.aligned is False
        assert reconciliation.divergence_summary.is_critical is True
        assert reconciliation.recovery_decision.action == RecoveryAction.HALT_TRADING

    def test_runtime_emits_structured_logs(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert any(record.message == "execution_submission_submitted" for record in caplog.records)

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.2,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
            ),
        )
        runtime.process_events()
        adapter.remote_state = RemoteExecutionState(orders={}, fills={"ord-1": 0.25}, positions={"BTC": 0.25})
        runtime.reconcile(now=100.3)
        assert any(record.message == "execution_reconciliation_completed" for record in caplog.records)
