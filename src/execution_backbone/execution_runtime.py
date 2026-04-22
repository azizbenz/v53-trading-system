"""
Build-3 / execution_backbone / execution_runtime
Drive a real execution path across decision, fills, costs, and reconciliation.

This runtime stays adapter-driven: no hardcoded exchange, but the path is
actually executable end-to-end when an adapter is injected.
"""

from __future__ import annotations

from collections import deque
import logging

from interface_contracts import VenueRateLimitExceededError
from .fee_aware_edge_gate import (
    FeeAwareEdgeGateConfig,
)
from .execution_cost_meter.adverse_selection_meter import (
    CANONICAL_ADVERSE_SELECTION_DELAY_POLICY,
    AdverseSelectionDelayPolicy,
    compute_adverse_selection,
)
from .execution_cost_meter.cost_aggregator import CostAggregate, CostAggregator, compute_trade_cost
from .execution_cost_meter.elw_meter import compute_elw
from .execution_cost_meter.fee_meter import estimate_fee
from .execution_cost_meter.partial_fill_cost_meter import compute_partial_fill_cost
from .fill_tracker.fill_aggregator import FillAggregator, FillEvent
from .fill_tracker.fill_reporter import FillReporter, FillStats
from .fill_tracker.latency_meter import LatencyMeter, LatencyStats
from .fill_tracker.order_state_tracker import OrderRecord, OrderState, OrderStateTracker
from .fill_tracker.order_terminal_state_resolver import TerminalResolution, resolve_terminal
from .gatekeeper import (
    ExecutionGateRefusalDisposition,
    ExecutionGatekeeper,
    GatekeeperAuditLogger,
    ExecutionRefusal,
)
from .order_decider.decision_reporter import DecisionReporter, DecisionStats
from .order_decider.intent_builder import ExecutionIntent
from .rate_limiter import ExecutionRateLimitModel
from .spread_guard import ExecutionSpreadGuardModel

from .reconciliation_layer.divergence_classifier import DivergenceClassification, classify_all, classify_divergence
from .reconciliation_layer.fill_reconciler import FillReconciliationResult, reconcile_fills
from .reconciliation_layer.order_reconciler import OrderReconciliationResult, reconcile_orders
from .reconciliation_layer.position_reconciler import PositionReconciliationResult, reconcile_positions
from .reconciliation_layer.recovery_trigger import RecoveryDecision, RecoveryTrigger
from .slippage_model import ExecutionSlippageModel
from .execution_runtime_models import (
    ExecutionNoTradeFilter,
    ExecutionNoTradeFilterInput,
    ExecutionNoTradeFilterOutcome,
    ExecutionOpportunity,
    ExecutionRefusalSink,
    ExecutionSubmission,
    ExecutionSubmissionStatus,
    ExecutionVenueAdapter,
    RemoteExecutionState,
    ReplaceReceipt,
    RuntimeProcessingSummary,
    RuntimeReconciliationResult,
    ShariaTradeAuthorizer,
    SubmitReceipt,
    TimeoutSweepResult,
    VenueOrderEvent,
    VenueOrderEventType,
    _OrderCostContext,
    _TerminalOrderSnapshot,
)
from .execution_runtime_support import ExecutionRuntimeSupportMixin
from .venue_constraints_provider import VenueConstraintProvider


logger = logging.getLogger(__name__)

class ExecutionRuntime(ExecutionRuntimeSupportMixin):
    """Adapter-backed Build-3 runtime across decision, fills, costs and reconciliation."""

    def __init__(
        self,
        adapter: ExecutionVenueAdapter,
        *,
        default_fee_rate: float = 0.001,
        max_recon_age_s: float = 60.0,
        terminal_order_retention: int = 2048,
        adverse_selection_delay_policy: AdverseSelectionDelayPolicy = CANONICAL_ADVERSE_SELECTION_DELAY_POLICY,
        venue_constraint_provider: VenueConstraintProvider | None = None,
        execution_no_trade_filter: ExecutionNoTradeFilter | None = None,
        sharia_trade_authorizer: ShariaTradeAuthorizer | None = None,
        fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
        rate_limit_model: ExecutionRateLimitModel | None = None,
        spread_guard_model: ExecutionSpreadGuardModel | None = None,
        slippage_model: ExecutionSlippageModel | None = None,
        gatekeeper_audit_logger: GatekeeperAuditLogger | None = None,
        refusal_sink: ExecutionRefusalSink | None = None,
    ) -> None:
        if terminal_order_retention <= 0:
            raise ValueError("terminal_order_retention must be > 0")
        self._adapter = adapter
        self._default_fee_rate = default_fee_rate
        self._terminal_order_retention = terminal_order_retention
        self._adverse_selection_delay_policy = adverse_selection_delay_policy
        self._venue_constraint_provider = venue_constraint_provider
        self._execution_no_trade_filter = execution_no_trade_filter
        self._sharia_trade_authorizer = sharia_trade_authorizer
        self._fee_aware_edge_gate_config = fee_aware_edge_gate_config
        self._rate_limit_model = rate_limit_model
        self._spread_guard_model = spread_guard_model
        self._slippage_model = slippage_model
        self._gatekeeper_audit_logger = gatekeeper_audit_logger
        self._refusal_sink = refusal_sink
        self._decision_reporter = DecisionReporter()
        self._state_tracker = OrderStateTracker()
        self._fill_aggregator = FillAggregator()
        self._fill_reporter = FillReporter()
        self._latency_meter = LatencyMeter()
        self._cost_aggregator = CostAggregator()
        self._recovery_trigger = RecoveryTrigger(max_recon_age_s=max_recon_age_s)
        self._intents: dict[str, ExecutionIntent] = {}
        self._replacement_intent_nonce = 0
        self._timeout_by_order_id: dict[str, float] = {}
        self._cost_context: dict[str, _OrderCostContext] = {}
        self._cost_recorded: set[str] = set()
        self._pending_cancels: set[str] = set()
        self._local_positions: dict[str, float] = {}
        self._terminal_orders: dict[str, _TerminalOrderSnapshot] = {}
        self._terminal_order_sequence: deque[str] = deque()
        self._gatekeeper = ExecutionGatekeeper(
            resolve_spread_guard=self._run_spread_guard,
            resolve_fee_aware_edge=self._run_fee_aware_edge_gate,
            authorize_sharia=self._run_sharia_trade_authorizer,
            resolve_rate_limit=self._run_rate_limit_guard,
            resolve_venue_constraints=self._resolve_venue_constraints,
            normalize_venue_order_fields=self._normalize_venue_order_fields,
            resolve_max_spread_for_market=self._resolve_max_spread_for_market,
            evaluate_execution_no_trade_filter=self._run_execution_no_trade_filter,
        )

    def submit_opportunity(self, opportunity: ExecutionOpportunity, now: float) -> ExecutionSubmission:
        """Turn an execution opportunity into a real submitted order or an explicit no-trade."""
        opportunity = self._apply_runtime_slippage_model(opportunity)
        authorization = self._gatekeeper.authorize(opportunity)
        if isinstance(authorization, ExecutionRefusal):
            self._decision_reporter.record_no_trade(authorization.no_trade, timestamp=now)
            self._log_gatekeeper_refusal(authorization, opportunity, now)
            self._record_runtime_refusal(
                refusal=authorization,
                opportunity=opportunity,
                now=now,
            )
            self._record_gatekeeper_refusal_audit(
                refusal=authorization,
                opportunity=opportunity,
                now=now,
            )
            status = (
                ExecutionSubmissionStatus.BLOCKED
                if authorization.disposition == ExecutionGateRefusalDisposition.BLOCKED
                else ExecutionSubmissionStatus.NO_TRADE
            )
            return ExecutionSubmission(
                status=status,
                no_trade=authorization.no_trade,
                guard=authorization.guard,
                detail=authorization.detail,
                gate_trace=authorization.trace,
            )
        intent = authorization.intent
        try:
            receipt = self._adapter.submit_order(intent, now)
        except VenueRateLimitExceededError as exc:
            logger.warning(
                "execution_submission_rate_limited",
                extra={
                    "intent_id": intent.intent_id,
                    "pair": intent.pair,
                    "engine_id": intent.engine_id,
                    "error": str(exc),
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.BLOCKED,
                no_trade=f"RATE_LIMIT: {exc}",
                guard="venue_rate_limiter",
                detail=str(exc),
                gate_trace=authorization.trace,
            )
        submit_latency = self._latency_meter.record_submit(
            receipt.order_id,
            signal_arrival_time=opportunity.signal_arrival_monotonic_s,
            scoring_completed_time=opportunity.scoring_completed_monotonic_s,
            risk_completed_time=opportunity.risk_completed_monotonic_s,
            portfolio_completed_time=opportunity.portfolio_completed_monotonic_s,
            submit_time=now,
        )
        self._register_live_order(receipt.order_id, intent, receipt.submitted_at)
        self._decision_reporter.record_trade(intent, timestamp=now)
        self._record_gatekeeper_submission_audit(
            permit=authorization,
            opportunity=opportunity,
            order_id=receipt.order_id,
            now=now,
        )
        logger.info(
            "execution_submission_submitted",
            extra={
                "intent_id": intent.intent_id,
                "order_id": receipt.order_id,
                "pair": intent.pair,
                "engine_id": intent.engine_id,
                "order_type": intent.order_type.value,
                "signal_to_submit_s": (
                    None if submit_latency is None else submit_latency.signal_to_submit_s
                ),
                "signal_to_scoring_s": (
                    None if submit_latency is None else submit_latency.signal_to_scoring_s
                ),
                "scoring_to_risk_s": (
                    None if submit_latency is None else submit_latency.scoring_to_risk_s
                ),
                "risk_to_portfolio_s": (
                    None if submit_latency is None else submit_latency.risk_to_portfolio_s
                ),
                "portfolio_to_submit_s": (
                    None if submit_latency is None else submit_latency.portfolio_to_submit_s
                ),
                "gate_trace": tuple(step.model_dump(mode="json") for step in authorization.trace),
                "timestamp": now,
            },
        )
        return ExecutionSubmission(
            status=ExecutionSubmissionStatus.SUBMITTED,
            order_id=receipt.order_id,
            intent=intent,
            signal_to_submit_s=(
                None if submit_latency is None else submit_latency.signal_to_submit_s
            ),
            signal_to_scoring_s=(
                None if submit_latency is None else submit_latency.signal_to_scoring_s
            ),
            scoring_to_risk_s=(
                None if submit_latency is None else submit_latency.scoring_to_risk_s
            ),
            risk_to_portfolio_s=(
                None if submit_latency is None else submit_latency.risk_to_portfolio_s
            ),
            portfolio_to_submit_s=(
                None if submit_latency is None else submit_latency.portfolio_to_submit_s
            ),
            detail=authorization.detail,
            gate_trace=authorization.trace,
        )

    def replace_order(
        self,
        order_id: str,
        *,
        new_price_limit: float,
        now: float,
        new_timeout_s: float | None = None,
    ) -> ExecutionSubmission:
        """Replace an open order through the injected adapter."""
        record = self._state_tracker.get(order_id)
        intent = self._intents.get(order_id)
        if record is None or intent is None:
            raise KeyError(f"Unknown order '{order_id}'")
        if self._state_tracker.is_terminal(order_id):
            raise ValueError(f"Cannot replace terminal order '{order_id}'")

        price_limit = new_price_limit
        price_limit_exact: str | None = None
        if intent.venue_constraints is not None:
            normalization = self._normalize_venue_order_fields(
                quantity=intent.quantity,
                side=intent.side,
                order_type=intent.order_type,
                price_limit=new_price_limit,
                reference_price=new_price_limit,
                constraints=intent.venue_constraints,
            )
            if normalization.error_detail is not None:
                raise ValueError(normalization.error_detail)
            price_limit = normalization.price_limit
            price_limit_exact = normalization.price_limit_exact

        replacement_intent = intent.model_copy(
            update={
                "intent_id": self._next_replacement_intent_id(
                    base_intent_id=intent.intent_id,
                    order_id=order_id,
                ),
                "price_limit": price_limit,
                "price_limit_exact": price_limit_exact,
                "timeout_s": intent.timeout_s if new_timeout_s is None else new_timeout_s,
            },
        )
        receipt = self._adapter.replace_order(order_id, replacement_intent, now)
        self._state_tracker.mark_cancelled(order_id, receipt.replaced_at, "replaced")
        self._finalize_terminal_order(order_id)
        self._register_live_order(receipt.replacement_order_id, replacement_intent, receipt.submitted_at)
        self._decision_reporter.record_trade(replacement_intent, timestamp=now)
        logger.info(
            "execution_submission_replaced",
            extra={
                "replaced_order_id": order_id,
                "replacement_order_id": receipt.replacement_order_id,
                "pair": replacement_intent.pair,
                "engine_id": replacement_intent.engine_id,
                "timestamp": now,
            },
        )
        return ExecutionSubmission(
            status=ExecutionSubmissionStatus.REPLACED,
            order_id=receipt.replacement_order_id,
            replaced_order_id=order_id,
            intent=replacement_intent,
            detail="order replaced via adapter",
        )

    def sweep_timeouts(self, now: float) -> TimeoutSweepResult:
        """Request cancellations for open orders whose timeout has elapsed."""
        cancelled_order_ids: list[str] = []
        for record in self._state_tracker.get_open_orders():
            if record.order_id in self._pending_cancels:
                continue
            timeout_s = self._timeout_by_order_id.get(record.order_id, 0.0)
            if timeout_s <= 0 or record.sent_time is None:
                continue
            if now - record.sent_time < timeout_s:
                continue
            self._adapter.cancel_order(record.order_id, now, reason="timeout")
            self._pending_cancels.add(record.order_id)
            cancelled_order_ids.append(record.order_id)
            logger.warning(
                "execution_timeout_cancel_requested",
                extra={"order_id": record.order_id, "timestamp": now, "timeout_s": timeout_s},
            )
        return TimeoutSweepResult(cancelled_order_ids=tuple(cancelled_order_ids))

    def process_events(self) -> RuntimeProcessingSummary:
        """Consume venue events and update local execution state."""
        terminal_resolutions: list[TerminalResolution] = []
        events = self._adapter.poll_order_events()
        for event in events:
            record = self._state_tracker.get(event.order_id)
            if record is None:
                logger.warning(
                    "execution_event_unknown_order",
                    extra={
                        "order_id": event.order_id,
                        "event_type": event.event_type.value,
                        "timestamp": event.timestamp,
                    },
                )
                continue

            if event.event_type == VenueOrderEventType.ACK:
                self._state_tracker.mark_acked(event.order_id, event.timestamp)
                continue

            if event.event_type == VenueOrderEventType.FILL:
                updated = self._state_tracker.mark_fill(
                    event.order_id,
                    event.fill_quantity,
                    event.fill_price,
                    event.timestamp,
                    fill_id=event.fill_id,
                )
                self._record_fill_event(event)
                if updated.state == OrderState.FILLED:
                    resolution = self._finalize_terminal_order(event.order_id)
                    if resolution is not None:
                        terminal_resolutions.append(resolution)
                continue

            if event.event_type == VenueOrderEventType.CANCELLED:
                self._state_tracker.mark_cancelled(event.order_id, event.timestamp, event.reason)
                self._pending_cancels.discard(event.order_id)
            elif event.event_type == VenueOrderEventType.EXPIRED:
                self._state_tracker.mark_expired(event.order_id, event.timestamp)
            elif event.event_type == VenueOrderEventType.REJECTED:
                self._state_tracker.mark_rejected(event.order_id, event.timestamp, event.reason)

            resolution = self._finalize_terminal_order(event.order_id)
            if resolution is not None:
                terminal_resolutions.append(resolution)

        return RuntimeProcessingSummary(
            processed_events=len(events),
            terminal_resolutions=tuple(terminal_resolutions),
            fill_stats=self._fill_reporter.get_stats(),
            decision_stats=self._decision_reporter.get_stats(),
            latency_stats=self._latency_meter.get_stats(),
            cost_aggregate=self._cost_aggregator.get_aggregate(),
        )

    def reconcile(self, now: float) -> RuntimeReconciliationResult:
        """Run local vs remote reconciliation against an adapter-backed external state."""
        remote_state = self._adapter.fetch_remote_state()
        order_result = reconcile_orders(
            self._local_open_order_states(),
            self._remote_open_order_states(remote_state.orders),
        )
        fill_result = reconcile_fills(self._local_fill_quantities(), remote_state.fills)
        position_result = reconcile_positions(dict(self._local_positions), remote_state.positions)

        classified = []
        for divergence in order_result.divergences:
            classified.append(classify_divergence("order", divergence.detail, abs_diff=1.0))
        for divergence in fill_result.divergences:
            classified.append(classify_divergence("fill", divergence.detail, abs_diff=divergence.qty_diff))
        for divergence in position_result.divergences:
            classified.append(classify_divergence("position", "position mismatch", abs_diff=divergence.abs_diff))

        summary = classify_all(tuple(classified))
        recovery_decision = self._recovery_trigger.evaluate(
            summary.max_severity,
            now=now,
            divergence_count=summary.total_divergences,
        )
        self._recovery_trigger.record_reconciliation(now)
        logger.info(
            "execution_reconciliation_completed",
            extra={
                "timestamp": now,
                "order_aligned": order_result.aligned,
                "fill_aligned": fill_result.aligned,
                "position_aligned": position_result.aligned,
                "max_severity": summary.max_severity.value,
                "recovery_action": recovery_decision.action.value,
            },
        )
        return RuntimeReconciliationResult(
            order_result=order_result,
            fill_result=fill_result,
            position_result=position_result,
            divergence_summary=summary,
            recovery_decision=recovery_decision,
        )

    def get_decision_stats(self) -> DecisionStats:
        return self._decision_reporter.get_stats()

    def get_fill_stats(self) -> FillStats:
        return self._fill_reporter.get_stats()

    def get_latency_stats(self) -> LatencyStats:
        return self._latency_meter.get_stats()

    def get_cost_aggregate(self) -> CostAggregate:
        return self._cost_aggregator.get_aggregate()

    def get_local_positions(self) -> dict[str, float]:
        return dict(self._local_positions)

    def _register_live_order(self, order_id: str, intent: ExecutionIntent, submitted_at: float) -> None:
        self._intents[order_id] = intent
        self._timeout_by_order_id[order_id] = intent.timeout_s
        self._state_tracker.register_order(
            order_id,
            intent.pair,
            intent.engine_id,
            intent.side,
            intent.order_type.value,
            intent.quantity,
        )
        self._state_tracker.mark_sent(order_id, submitted_at)
        self._fill_reporter.record_order_created()

    def _record_fill_event(self, event: VenueOrderEvent) -> None:
        intent = self._intents.get(event.order_id)
        if intent is None:
            return
        fill_event = FillEvent(
            fill_id=event.fill_id or f"{event.order_id}:{int(event.timestamp * 1000)}",
            order_id=event.order_id,
            pair=intent.pair,
            side=intent.side,
            quantity=event.fill_quantity,
            price=event.fill_price,
            fee=event.fee_amount,
            fee_asset=event.fee_asset,
            timestamp=event.timestamp,
        )
        self._fill_aggregator.record_fill(fill_event)
        self._update_local_position(intent.pair, intent.side, event.fill_quantity)

        context = self._cost_context.get(event.order_id, _OrderCostContext())
        context.mid_price = event.mid_price if event.mid_price is not None else context.mid_price
        context.post_fill_mid_price = (
            event.post_fill_mid_price if event.post_fill_mid_price is not None else context.post_fill_mid_price
        )
        context.adverse_selection_delay_s = (
            event.adverse_selection_delay_s
            if event.adverse_selection_delay_s is not None
            else context.adverse_selection_delay_s
        )
        context.current_mid = event.current_mid if event.current_mid is not None else context.current_mid
        context.market_impact_total += event.market_impact
        context.fee_rate = event.fee_rate if event.fee_rate is not None else context.fee_rate
        self._cost_context[event.order_id] = context

    def _finalize_terminal_order(self, order_id: str) -> TerminalResolution | None:
        if order_id in self._terminal_orders:
            return None
        record = self._state_tracker.get(order_id)
        if record is None or record.state not in {OrderState.FILLED, OrderState.CANCELLED, OrderState.EXPIRED, OrderState.REJECTED}:
            return None

        resolution = resolve_terminal(order_id, record.state, record.quantity, record.filled_quantity)
        self._fill_reporter.record_terminal(record.state, had_partial_fills=record.filled_quantity > 0.0)
        self._latency_meter.record(
            order_id,
            sent_time=record.sent_time,
            ack_time=record.ack_time,
            first_fill_time=record.first_fill_time,
            full_fill_time=record.last_update_time if record.state == OrderState.FILLED else None,
        )
        if record.filled_quantity > 0.0:
            self._record_trade_cost(order_id, record)
        self._retain_terminal_snapshot(order_id, filled_quantity=record.filled_quantity)
        self._release_terminal_order_state(order_id)
        return resolution

    def _record_trade_cost(self, order_id: str, record: OrderRecord) -> None:
        if order_id in self._cost_recorded:
            return
        intent = self._intents.get(order_id)
        aggregated = self._fill_aggregator.get_aggregated(order_id)
        if intent is None or aggregated is None or aggregated.total_filled_qty <= 0:
            return

        context = self._cost_context.get(order_id, _OrderCostContext())
        adverse_selection_delay_s = self._resolve_adverse_selection_delay_s(
            pair=intent.pair,
            event_delay_s=context.adverse_selection_delay_s,
        )
        fee_rate = self._default_fee_rate if context.fee_rate is None else context.fee_rate
        explicit_fee = aggregated.total_fees
        if explicit_fee <= 0:
            explicit_fee = estimate_fee(aggregated.average_price, aggregated.total_filled_qty, fee_rate=fee_rate)

        mid_price = aggregated.average_price if context.mid_price is None else context.mid_price
        post_fill_mid_price = mid_price if context.post_fill_mid_price is None else context.post_fill_mid_price
        implicit_cost = compute_elw(
            order_id,
            intent.pair,
            exec_price=aggregated.average_price,
            mid_price=mid_price,
            side=intent.side,
        ).elw
        adverse_selection = max(
            0.0,
            -compute_adverse_selection(
                order_id,
                intent.pair,
                intent.side,
                exec_price=aggregated.average_price,
                mid_after=post_fill_mid_price,
                delay_s=adverse_selection_delay_s,
            ).adverse_selection,
        )
        partial_fill = compute_partial_fill_cost(
            order_id,
            intent.pair,
            ordered_quantity=record.quantity,
            fill_prices=tuple(fill.price for fill in aggregated.fills),
            fill_quantities=tuple(fill.quantity for fill in aggregated.fills),
            current_mid=post_fill_mid_price if context.current_mid is None else context.current_mid,
        )
        notional = max(aggregated.total_notional, 1e-9)
        variance_component = 0.0
        if aggregated.average_price > 0:
            variance_component = partial_fill.price_variance / max(aggregated.average_price**2, 1e-9)
        partial_fill_cost = variance_component + (partial_fill.unfilled_cost / notional)

        self._cost_aggregator.record(
            compute_trade_cost(
                order_id,
                intent.pair,
                intent.engine_id,
                explicit_fee=explicit_fee,
                implicit_cost=implicit_cost,
                adverse_selection=adverse_selection,
                partial_fill_cost=partial_fill_cost,
                market_impact=context.market_impact_total,
                expected_cost=intent.expected_cost,
            ),
        )
        self._cost_recorded.add(order_id)
