"""
Build-3 / execution_backbone / execution_runtime
Drive a real execution path across decision, fills, costs, and reconciliation.

This runtime stays adapter-driven: no hardcoded exchange, but the path is
actually executable end-to-end when an adapter is injected.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from .execution_cost_meter.adverse_selection_meter import compute_adverse_selection
from .execution_cost_meter.cost_aggregator import CostAggregate, CostAggregator, compute_trade_cost
from .execution_cost_meter.elw_meter import compute_elw
from .execution_cost_meter.fee_meter import estimate_fee
from .execution_cost_meter.partial_fill_cost_meter import compute_partial_fill_cost
from .fill_tracker.fill_aggregator import FillAggregator, FillEvent
from .fill_tracker.fill_reporter import FillReporter, FillStats
from .fill_tracker.latency_meter import LatencyMeter, LatencyStats
from .fill_tracker.order_state_tracker import OrderState, OrderStateTracker
from .fill_tracker.order_terminal_state_resolver import TerminalResolution, resolve_terminal
from .order_decider.decision_reporter import DecisionReporter, DecisionStats
from .order_decider.execution_guard import BlockReason, GuardResult, GuardVerdict, check_execution_guards
from .order_decider.intent_builder import (
    ExecutionIntent,
    NoTradeDecision,
    NoTradeReason,
    OrderType,
    build_intent,
)
from .order_decider.order_type_selector import select_order_type
from .order_decider.timeout_policy_selector import select_timeout_policy
from .reconciliation_layer.divergence_classifier import DivergenceClassification, classify_all, classify_divergence
from .reconciliation_layer.fill_reconciler import FillReconciliationResult, reconcile_fills
from .reconciliation_layer.order_reconciler import OrderReconciliationResult, reconcile_orders
from .reconciliation_layer.position_reconciler import PositionReconciliationResult, reconcile_positions
from .reconciliation_layer.recovery_trigger import RecoveryDecision, RecoveryTrigger


_KNOWN_QUOTE_SUFFIXES = (
    "USDT",
    "FDUSD",
    "USDC",
    "BUSD",
    "TUSD",
    "EUR",
    "USD",
    "BTC",
    "ETH",
    "BNB",
)


class ExecutionOpportunity(BaseModel, frozen=True):
    """A validated execution opportunity ready for the execution backbone."""

    intent_id: str
    pair: str
    engine_id: str
    side: str
    quantity: float
    expected_gain: float
    expected_cost: float
    score: float
    justification: str
    spread_bps: float = 0.0
    safety_margin: float = 0.0005
    pair_suspended: bool = False
    pair_health_score: float = 1.0
    pair_health_min: float = 0.3
    risk_budget_available: bool = True
    infrastructure_ok: bool = True
    data_stale: bool = False
    max_acceptable_cost: float = 0.01
    reference_price: float | None = None
    price_limit: float | None = None
    profile: str = "LIGHT"
    metadata: dict[str, object] = Field(default_factory=dict)


class SubmitReceipt(BaseModel, frozen=True):
    """Venue acknowledgement that the order has been submitted."""

    order_id: str
    submitted_at: float


class ReplaceReceipt(BaseModel, frozen=True):
    """Venue acknowledgement that an order was replaced."""

    original_order_id: str
    replacement_order_id: str
    replaced_at: float
    submitted_at: float


class RemoteExecutionState(BaseModel, frozen=True):
    """Remote execution state fetched from the venue or exchange adapter."""

    orders: dict[str, str] = Field(default_factory=dict)
    fills: dict[str, float] = Field(default_factory=dict)
    positions: dict[str, float] = Field(default_factory=dict)


class VenueOrderEventType(StrEnum):
    ACK = "ack"
    FILL = "fill"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"


class VenueOrderEvent(BaseModel, frozen=True):
    """A venue event consumed by the runtime."""

    order_id: str
    event_type: VenueOrderEventType
    timestamp: float
    fill_id: str | None = None
    fill_quantity: float = 0.0
    fill_price: float = 0.0
    fee_amount: float = 0.0
    fee_asset: str = ""
    maker: bool = False
    mid_price: float | None = None
    post_fill_mid_price: float | None = None
    adverse_selection_delay_s: float = 5.0
    current_mid: float | None = None
    market_impact: float = 0.0
    fee_rate: float | None = None
    reason: str = ""


class ExecutionSubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    NO_TRADE = "no_trade"
    BLOCKED = "blocked"
    REPLACED = "replaced"


class ExecutionSubmission(BaseModel, frozen=True):
    """Submission outcome for an execution opportunity."""

    status: ExecutionSubmissionStatus
    order_id: str | None = None
    replaced_order_id: str | None = None
    intent: ExecutionIntent | None = None
    no_trade: NoTradeDecision | None = None
    guard: GuardResult | None = None
    detail: str = ""


class TimeoutSweepResult(BaseModel, frozen=True):
    """Result of a timeout sweep across open orders."""

    cancelled_order_ids: tuple[str, ...] = ()


class RuntimeProcessingSummary(BaseModel, frozen=True):
    """Summary after processing venue events."""

    processed_events: int
    terminal_resolutions: tuple[TerminalResolution, ...] = ()
    fill_stats: FillStats = Field(default_factory=FillStats)
    decision_stats: DecisionStats = Field(default_factory=DecisionStats)
    latency_stats: LatencyStats = Field(default_factory=LatencyStats)
    cost_aggregate: CostAggregate = Field(default_factory=CostAggregate)


class RuntimeReconciliationResult(BaseModel, frozen=True):
    """Reconciliation result with downstream recovery decision."""

    order_result: OrderReconciliationResult
    fill_result: FillReconciliationResult
    position_result: PositionReconciliationResult
    divergence_summary: DivergenceClassification
    recovery_decision: RecoveryDecision


class ExecutionVenueAdapter(Protocol):
    """Adapter contract for the Build-3 execution runtime."""

    def submit_order(self, intent: ExecutionIntent, now: float) -> SubmitReceipt:
        ...

    def replace_order(self, original_order_id: str, intent: ExecutionIntent, now: float) -> ReplaceReceipt:
        ...

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        ...

    def poll_order_events(self) -> tuple[VenueOrderEvent, ...]:
        ...

    def fetch_remote_state(self) -> RemoteExecutionState:
        ...


class _OrderCostContext(BaseModel):
    mid_price: float | None = None
    post_fill_mid_price: float | None = None
    adverse_selection_delay_s: float = 5.0
    current_mid: float | None = None
    market_impact_total: float = 0.0
    fee_rate: float | None = None


class ExecutionRuntime:
    """Adapter-backed Build-3 runtime across decision, fills, costs and reconciliation."""

    def __init__(
        self,
        adapter: ExecutionVenueAdapter,
        *,
        default_fee_rate: float = 0.001,
        max_recon_age_s: float = 60.0,
    ) -> None:
        self._adapter = adapter
        self._default_fee_rate = default_fee_rate
        self._decision_reporter = DecisionReporter()
        self._state_tracker = OrderStateTracker()
        self._fill_aggregator = FillAggregator()
        self._fill_reporter = FillReporter()
        self._latency_meter = LatencyMeter()
        self._cost_aggregator = CostAggregator()
        self._recovery_trigger = RecoveryTrigger(max_recon_age_s=max_recon_age_s)
        self._intents: dict[str, ExecutionIntent] = {}
        self._timeout_by_order_id: dict[str, float] = {}
        self._cost_context: dict[str, _OrderCostContext] = {}
        self._cost_recorded: set[str] = set()
        self._finalized_orders: set[str] = set()
        self._pending_cancels: set[str] = set()
        self._local_positions: dict[str, float] = {}

    def submit_opportunity(self, opportunity: ExecutionOpportunity, now: float) -> ExecutionSubmission:
        """Turn an execution opportunity into a real submitted order or an explicit no-trade."""
        decision = select_order_type(
            expected_gain=opportunity.expected_gain,
            expected_cost=opportunity.expected_cost,
            safety_margin=opportunity.safety_margin,
            spread_bps=opportunity.spread_bps,
        )
        if decision.order_type == OrderType.NO_TRADE:
            reason = NoTradeReason.COST_EXCEEDS_EDGE if decision.net_expected <= 0 else NoTradeReason.HARD_BLOCKER
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=reason,
                detail=decision.reason,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=decision.reason,
            )

        guard = check_execution_guards(
            pair_suspended=opportunity.pair_suspended,
            pair_health_score=opportunity.pair_health_score,
            pair_health_min=opportunity.pair_health_min,
            risk_budget_available=opportunity.risk_budget_available,
            infrastructure_ok=opportunity.infrastructure_ok,
            data_stale=opportunity.data_stale,
            expected_cost=opportunity.expected_cost,
            max_acceptable_cost=opportunity.max_acceptable_cost,
        )
        if guard.verdict == GuardVerdict.BLOCK:
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=self._map_guard_reason(guard),
                detail=guard.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.BLOCKED,
                no_trade=no_trade,
                guard=guard,
                detail=guard.detail,
            )

        price_limit = opportunity.price_limit
        if decision.order_type == OrderType.LIMIT and price_limit is None:
            price_limit = opportunity.reference_price
        if decision.order_type == OrderType.LIMIT and price_limit is None:
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=NoTradeReason.HARD_BLOCKER,
                detail="limit order selected without a usable price limit",
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=no_trade.detail,
            )

        timeout_policy = select_timeout_policy(decision.order_type)
        intent = build_intent(
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            side=opportunity.side,
            order_type=decision.order_type,
            quantity=opportunity.quantity,
            expected_cost=opportunity.expected_cost,
            expected_gain=opportunity.expected_gain,
            score=opportunity.score,
            justification=opportunity.justification or decision.reason,
            price_limit=price_limit,
            timeout_s=timeout_policy.timeout_s,
            profile=opportunity.profile,
        )
        receipt = self._adapter.submit_order(intent, now)
        self._register_live_order(receipt.order_id, intent, receipt.submitted_at)
        self._decision_reporter.record_trade(intent, timestamp=now)
        return ExecutionSubmission(
            status=ExecutionSubmissionStatus.SUBMITTED,
            order_id=receipt.order_id,
            intent=intent,
            detail=decision.reason,
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

        replacement_intent = intent.model_copy(
            update={
                "intent_id": f"{intent.intent_id}:replace:{int(now * 1000)}",
                "price_limit": new_price_limit,
                "timeout_s": intent.timeout_s if new_timeout_s is None else new_timeout_s,
            },
        )
        receipt = self._adapter.replace_order(order_id, replacement_intent, now)
        self._state_tracker.mark_cancelled(order_id, receipt.replaced_at, "replaced")
        self._finalize_terminal_order(order_id)
        self._register_live_order(receipt.replacement_order_id, replacement_intent, receipt.submitted_at)
        self._decision_reporter.record_trade(replacement_intent, timestamp=now)
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
        return TimeoutSweepResult(cancelled_order_ids=tuple(cancelled_order_ids))

    def process_events(self) -> RuntimeProcessingSummary:
        """Consume venue events and update local execution state."""
        terminal_resolutions: list[TerminalResolution] = []
        events = self._adapter.poll_order_events()
        for event in events:
            record = self._state_tracker.get(event.order_id)
            if record is None:
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
        order_result = reconcile_orders(self._local_order_states(), remote_state.orders)
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
        context.adverse_selection_delay_s = event.adverse_selection_delay_s
        context.current_mid = event.current_mid if event.current_mid is not None else context.current_mid
        context.market_impact_total += event.market_impact
        context.fee_rate = event.fee_rate if event.fee_rate is not None else context.fee_rate
        self._cost_context[event.order_id] = context

    def _finalize_terminal_order(self, order_id: str) -> TerminalResolution | None:
        if order_id in self._finalized_orders:
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
        self._finalized_orders.add(order_id)
        return resolution

    def _record_trade_cost(self, order_id: str, record) -> None:
        if order_id in self._cost_recorded:
            return
        intent = self._intents.get(order_id)
        aggregated = self._fill_aggregator.get_aggregated(order_id)
        if intent is None or aggregated is None or aggregated.total_filled_qty <= 0:
            return

        context = self._cost_context.get(order_id, _OrderCostContext())
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
                delay_s=context.adverse_selection_delay_s,
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
        notional = max(record.quantity * max(aggregated.average_price, 1.0), 1e-9)
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

    def _map_guard_reason(self, guard: GuardResult) -> NoTradeReason:
        if not guard.blocks:
            return NoTradeReason.HARD_BLOCKER
        mapping = {
            BlockReason.PAIR_SUSPENDED: NoTradeReason.PAIR_SUSPENDED,
            BlockReason.RISK_BUDGET_EXHAUSTED: NoTradeReason.RISK_BUDGET_EXHAUSTED,
            BlockReason.INFRASTRUCTURE_DOWN: NoTradeReason.INFRASTRUCTURE_DOWN,
            BlockReason.COST_TOO_HIGH: NoTradeReason.COST_EXCEEDS_EDGE,
            BlockReason.PAIR_HEALTH_LOW: NoTradeReason.HARD_BLOCKER,
            BlockReason.STALE_DATA: NoTradeReason.HARD_BLOCKER,
        }
        return mapping.get(guard.blocks[0], NoTradeReason.HARD_BLOCKER)

    def _update_local_position(self, pair: str, side: str, quantity: float) -> None:
        base_asset = self._extract_base_asset(pair)
        signed_quantity = quantity if side.lower() == "buy" else -quantity
        self._local_positions[base_asset] = self._local_positions.get(base_asset, 0.0) + signed_quantity

    def _local_order_states(self) -> dict[str, str]:
        return {record.order_id: record.state.value for record in self._state_tracker.get_all()}

    def _local_fill_quantities(self) -> dict[str, float]:
        return {
            aggregated.order_id: aggregated.total_filled_qty
            for aggregated in (
                self._fill_aggregator.get_aggregated(order_id)
                for order_id in self._intents
            )
            if aggregated is not None
        }

    def _extract_base_asset(self, pair: str) -> str:
        for suffix in _KNOWN_QUOTE_SUFFIXES:
            if pair.endswith(suffix) and len(pair) > len(suffix):
                return pair[: -len(suffix)]
        return pair
