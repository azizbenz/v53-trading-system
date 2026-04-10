"""
Build-3 / execution_backbone / execution_runtime
Drive a real execution path across decision, fills, costs, and reconciliation.

This runtime stays adapter-driven: no hardcoded exchange, but the path is
actually executable end-to-end when an adapter is injected.
"""

from __future__ import annotations

from collections import deque
from enum import StrEnum
import logging
from typing import Protocol

from pydantic import BaseModel, Field
from sharia_compliance.contracts import ShariaPermit, ShariaRejection, ShariaTradeRequest

from interface_contracts import (
    decimal_to_canonical_str,
    decimal_to_float64,
    execution_decimal,
    multiply_exact,
    quantize_down_to_step,
    quantize_up_to_step,
)
from scoring_backbone.fee_aware_edge_gate import (
    FeeAwareEdgeDecision,
    FeeAwareEdgeGateConfig,
    evaluate_fee_aware_edge,
)
from .execution_cost_meter.adverse_selection_meter import (
    CANONICAL_ADVERSE_SELECTION_DELAY_POLICY,
    AdverseSelectionDelayPolicy,
    compute_adverse_selection,
    resolve_adverse_selection_delay_s,
)
from .execution_cost_meter.cost_aggregator import CostAggregate, CostAggregator, compute_trade_cost
from .execution_cost_meter.elw_meter import compute_elw
from .execution_cost_meter.fee_meter import estimate_fee
from .execution_cost_meter.partial_fill_cost_meter import compute_partial_fill_cost
from .fill_tracker.fill_aggregator import FillAggregator, FillEvent
from .fill_tracker.fill_reporter import FillReporter, FillStats
from .fill_tracker.latency_meter import LatencyMeter, LatencyStats
from .fill_tracker.order_state_tracker import OrderState, OrderStateTracker, TERMINAL_STATES
from .fill_tracker.order_terminal_state_resolver import TerminalResolution, resolve_terminal
from .order_decider.decision_reporter import DecisionReporter, DecisionStats
from .order_decider.execution_guard import BlockReason, GuardResult, GuardVerdict, check_execution_guards
from .order_decider.intent_builder import (
    ExecutionIntent,
    NoTradeDecision,
    NoTradeReason,
    OrderType,
    VenueConstraintSnapshot,
    build_intent,
)
from .order_decider.order_type_selector import select_order_type
from .order_decider.timeout_policy_selector import select_timeout_policy
from .reconciliation_layer.divergence_classifier import DivergenceClassification, classify_all, classify_divergence
from .reconciliation_layer.fill_reconciler import FillReconciliationResult, reconcile_fills
from .reconciliation_layer.order_reconciler import OrderReconciliationResult, reconcile_orders
from .reconciliation_layer.position_reconciler import PositionReconciliationResult, reconcile_positions
from .reconciliation_layer.recovery_trigger import RecoveryDecision, RecoveryTrigger
from .venue_constraints_provider import VenueConstraintProvider


logger = logging.getLogger(__name__)


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
    profile: str = "COMPLETE"  # BS-49: LIGHT removed — COMPLETE is the only governed profile
    venue_constraints: VenueConstraintSnapshot | None = None
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
    adverse_selection_delay_s: float | None = None
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


class ExecutionNoTradeFilterInput(BaseModel, frozen=True):
    """Bounded typed input for a pre-submit execution no-trade filter."""

    intent_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    expected_cost: float = 0.0
    expected_gain: float = 0.0
    score: float = 0.0


class ExecutionNoTradeFilterOutcome(BaseModel, frozen=True):
    """Bounded typed output for a pre-submit execution no-trade filter."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    detail: str = ""


class ExecutionVenueAdapter(Protocol):
    """Adapter contract for the Build-3 execution runtime."""

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        ...

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


class ExecutionNoTradeFilter(Protocol):
    """Bounded pre-submit veto surface for the execution edge."""

    def __call__(self, hook_input: ExecutionNoTradeFilterInput) -> ExecutionNoTradeFilterOutcome:
        ...


class ShariaTradeAuthorizer(Protocol):
    """Bounded halal authorization surface before any venue submit."""

    def authorize_trade(self, request: ShariaTradeRequest) -> ShariaPermit | ShariaRejection:
        ...


class _OrderCostContext(BaseModel):
    mid_price: float | None = None
    post_fill_mid_price: float | None = None
    adverse_selection_delay_s: float | None = None
    current_mid: float | None = None
    market_impact_total: float = 0.0
    fee_rate: float | None = None


class _TerminalOrderSnapshot(BaseModel, frozen=True):
    """Compact retained state for finalized orders after detailed cleanup."""

    filled_quantity: float = 0.0


class ExecutionRuntime:
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
            logger.warning(
                "execution_submission_no_trade",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "reason": no_trade.reason.value,
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=decision.reason,
            )

        edge_gate_decision = self._run_fee_aware_edge_gate(opportunity)
        if edge_gate_decision is not None and not edge_gate_decision.allowed:
            fee_aware_context = self._build_fee_aware_edge_no_trade_context(edge_gate_decision)
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=NoTradeReason.COST_EXCEEDS_EDGE,
                detail=edge_gate_decision.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=fee_aware_context,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            logger.warning(
                "execution_submission_fee_aware_edge_blocked",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "reason_code": edge_gate_decision.reason_code,
                    "expected_edge_bps": edge_gate_decision.expected_edge_bps,
                    "expected_cost_bps": edge_gate_decision.expected_cost_bps,
                    "threshold_bps": edge_gate_decision.threshold_bps,
                    "edge_multiplier": edge_gate_decision.edge_multiplier,
                    "min_absolute_edge_bps": edge_gate_decision.min_absolute_edge_bps,
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=edge_gate_decision.detail,
            )

        sharia_decision = self._run_sharia_trade_authorizer(opportunity)
        if sharia_decision is not None and not sharia_decision.allowed:
            detail = sharia_decision.detail.strip() or sharia_decision.reason_code
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=NoTradeReason.SHARIA_BLOCKED,
                detail=detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            logger.warning(
                "execution_submission_sharia_blocked",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "reason_code": sharia_decision.reason_code,
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=detail,
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
            logger.warning(
                "execution_submission_blocked",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "blocks": tuple(block.value for block in guard.blocks),
                    "timestamp": now,
                },
            )
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
            logger.warning(
                "execution_submission_invalid_limit",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=no_trade.detail,
            )

        resolved_constraints = self._resolve_venue_constraints(opportunity)
        quantity = opportunity.quantity
        quantity_exact = ""
        price_limit_exact: str | None = None
        if resolved_constraints is not None:
            normalization = self._normalize_venue_order_fields(
                quantity=opportunity.quantity,
                side=opportunity.side,
                order_type=decision.order_type,
                price_limit=price_limit,
                reference_price=opportunity.reference_price,
                constraints=resolved_constraints,
            )
            if normalization.error_detail is not None:
                no_trade = NoTradeDecision(
                    pair=opportunity.pair,
                    engine_id=opportunity.engine_id,
                    reason=NoTradeReason.VENUE_CONSTRAINTS,
                    detail=normalization.error_detail,
                    expected_cost=opportunity.expected_cost,
                    expected_gain=opportunity.expected_gain,
                    score=opportunity.score,
                )
                self._decision_reporter.record_no_trade(no_trade, timestamp=now)
                logger.warning(
                    "execution_submission_venue_constraints",
                    extra={
                        "intent_id": opportunity.intent_id,
                        "pair": opportunity.pair,
                        "engine_id": opportunity.engine_id,
                        "detail": normalization.error_detail,
                        "timestamp": now,
                    },
                )
                return ExecutionSubmission(
                    status=ExecutionSubmissionStatus.NO_TRADE,
                    no_trade=no_trade,
                    detail=no_trade.detail,
                )
            quantity = normalization.quantity
            quantity_exact = normalization.quantity_exact
            price_limit = normalization.price_limit
            price_limit_exact = normalization.price_limit_exact

        timeout_policy = select_timeout_policy(decision.order_type)
        intent = build_intent(
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            side=opportunity.side,
            order_type=decision.order_type,
            quantity=quantity,
            quantity_exact=quantity_exact,
            expected_cost=opportunity.expected_cost,
            expected_gain=opportunity.expected_gain,
            score=opportunity.score,
            justification=opportunity.justification or decision.reason,
            price_limit=price_limit,
            price_limit_exact=price_limit_exact,
            timeout_s=timeout_policy.timeout_s,
            profile=opportunity.profile,
            venue_constraints=resolved_constraints,
        )
        hook_outcome = self._run_execution_no_trade_filter(opportunity)
        if hook_outcome is not None and hook_outcome.blocked:
            detail = hook_outcome.detail.strip()
            if not detail:
                detail = (
                    f"execution no-trade filter blocked {opportunity.pair} / "
                    f"{opportunity.engine_id}"
                )
            no_trade = NoTradeDecision(
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                reason=NoTradeReason.HARD_BLOCKER,
                detail=detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
            )
            self._decision_reporter.record_no_trade(no_trade, timestamp=now)
            logger.warning(
                "execution_submission_filtered",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "block_reason_codes": hook_outcome.block_reason_codes,
                    "timestamp": now,
                },
            )
            return ExecutionSubmission(
                status=ExecutionSubmissionStatus.NO_TRADE,
                no_trade=no_trade,
                detail=detail,
            )
        receipt = self._adapter.submit_order(intent, now)
        self._register_live_order(receipt.order_id, intent, receipt.submitted_at)
        self._decision_reporter.record_trade(intent, timestamp=now)
        logger.info(
            "execution_submission_submitted",
            extra={
                "intent_id": intent.intent_id,
                "order_id": receipt.order_id,
                "pair": intent.pair,
                "engine_id": intent.engine_id,
                "order_type": intent.order_type.value,
                "timestamp": now,
            },
        )
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

    def _record_trade_cost(self, order_id: str, record) -> None:
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

    def _run_execution_no_trade_filter(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ExecutionNoTradeFilterOutcome | None:
        if self._execution_no_trade_filter is None:
            return None
        hook_input = ExecutionNoTradeFilterInput(
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            expected_cost=opportunity.expected_cost,
            expected_gain=opportunity.expected_gain,
            score=opportunity.score,
        )
        return self._execution_no_trade_filter(hook_input)

    def _run_fee_aware_edge_gate(
        self,
        opportunity: ExecutionOpportunity,
    ) -> FeeAwareEdgeDecision | None:
        if self._fee_aware_edge_gate_config is None:
            return None
        return evaluate_fee_aware_edge(
            expected_edge_bps=opportunity.expected_gain * 10_000.0,
            expected_cost=opportunity.expected_cost,
            config=self._fee_aware_edge_gate_config,
        )

    @staticmethod
    def _build_fee_aware_edge_no_trade_context(
        decision: FeeAwareEdgeDecision,
    ) -> dict[str, str | float | int | bool]:
        return {
            "gate": "fee_aware_edge",
            "reason_code": decision.reason_code,
            "expected_edge_bps": decision.expected_edge_bps,
            "expected_cost_bps": decision.expected_cost_bps,
            "threshold_bps": decision.threshold_bps,
            "edge_multiplier": decision.edge_multiplier,
            "min_absolute_edge_bps": decision.min_absolute_edge_bps,
        }

    def _run_sharia_trade_authorizer(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ShariaPermit | ShariaRejection | None:
        if self._sharia_trade_authorizer is None:
            return None
        return self._sharia_trade_authorizer.authorize_trade(
            ShariaTradeRequest(
                intent_id=opportunity.intent_id,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                side=opportunity.side,
                profile=opportunity.profile,
                metadata=dict(opportunity.metadata),
            )
        )

    def _resolve_adverse_selection_delay_s(
        self,
        *,
        pair: str,
        event_delay_s: float | None,
    ) -> float:
        return resolve_adverse_selection_delay_s(
            pair=pair,
            event_delay_s=event_delay_s,
            policy=self._adverse_selection_delay_policy,
        )

    def _next_replacement_intent_id(self, *, base_intent_id: str, order_id: str) -> str:
        self._replacement_intent_nonce += 1
        return f"{base_intent_id}:replace:{order_id}:{self._replacement_intent_nonce}"

    def _update_local_position(self, pair: str, side: str, quantity: float) -> None:
        base_asset = self._extract_base_asset(pair)
        signed_quantity = quantity if side.lower() == "buy" else -quantity
        self._local_positions[base_asset] = self._local_positions.get(base_asset, 0.0) + signed_quantity

    def _local_open_order_states(self) -> dict[str, str]:
        return {record.order_id: record.state.value for record in self._state_tracker.get_open_orders()}

    def _remote_open_order_states(self, remote_orders: dict[str, str]) -> dict[str, str]:
        terminal_values = {state.value for state in TERMINAL_STATES}
        return {
            order_id: state
            for order_id, state in remote_orders.items()
            if state not in terminal_values
        }

    def _local_fill_quantities(self) -> dict[str, float]:
        fill_quantities = {
            aggregated.order_id: aggregated.total_filled_qty
            for aggregated in (
                self._fill_aggregator.get_aggregated(order_id)
                for order_id in self._intents
            )
            if aggregated is not None
        }
        for order_id, snapshot in self._terminal_orders.items():
            fill_quantities.setdefault(order_id, snapshot.filled_quantity)
        return fill_quantities

    def _retain_terminal_snapshot(self, order_id: str, *, filled_quantity: float) -> None:
        self._terminal_orders[order_id] = _TerminalOrderSnapshot(
            filled_quantity=filled_quantity
        )
        self._terminal_order_sequence.append(order_id)
        self._prune_terminal_snapshots()

    def _prune_terminal_snapshots(self) -> None:
        while len(self._terminal_order_sequence) > self._terminal_order_retention:
            oldest_order_id = self._terminal_order_sequence.popleft()
            self._terminal_orders.pop(oldest_order_id, None)

    def _release_terminal_order_state(self, order_id: str) -> None:
        self._pending_cancels.discard(order_id)
        self._timeout_by_order_id.pop(order_id, None)
        self._cost_context.pop(order_id, None)
        self._cost_recorded.discard(order_id)
        self._intents.pop(order_id, None)
        self._fill_aggregator.evict_order(order_id)
        self._state_tracker.evict_order(order_id)

    def _extract_base_asset(self, pair: str) -> str:
        for suffix in _KNOWN_QUOTE_SUFFIXES:
            if pair.endswith(suffix) and len(pair) > len(suffix):
                return pair[: -len(suffix)]
        return pair

    def _resolve_venue_constraints(
        self,
        opportunity: ExecutionOpportunity,
    ) -> VenueConstraintSnapshot | None:
        if opportunity.venue_constraints is not None:
            return opportunity.venue_constraints
        adapter_constraints = self._adapter.fetch_venue_constraints(opportunity.pair)
        if adapter_constraints is not None:
            return adapter_constraints
        if self._venue_constraint_provider is None:
            return None
        return self._venue_constraint_provider.fetch_venue_constraints(opportunity.pair)

    def _normalize_venue_order_fields(
        self,
        *,
        quantity: float,
        side: str,
        order_type: OrderType,
        price_limit: float | None,
        reference_price: float | None,
        constraints: VenueConstraintSnapshot,
    ) -> "_NormalizedVenueOrderFields":
        quantity_decimal = execution_decimal(quantity, name="quantity")
        quantity_decimal = (
            quantize_down_to_step(quantity_decimal, constraints.step_size)
            if constraints.step_size is not None
            else quantity_decimal
        )
        if quantity_decimal <= 0:
            return _NormalizedVenueOrderFields(
                quantity=0.0,
                quantity_exact="0",
                error_detail="venue constraints reduce quantity to zero",
            )

        normalized_price_limit: float | None = price_limit
        price_limit_exact: str | None = None
        price_anchor_decimal = (
            execution_decimal(price_limit, name="price_limit")
            if price_limit is not None
            else (
                execution_decimal(reference_price, name="reference_price")
                if reference_price is not None
                else None
            )
        )

        if price_limit is not None and constraints.tick_size is not None:
            normalized_price_decimal = (
                quantize_down_to_step(price_limit, constraints.tick_size)
                if side.lower() == "buy"
                else quantize_up_to_step(price_limit, constraints.tick_size)
            )
            if normalized_price_decimal <= 0:
                return _NormalizedVenueOrderFields(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="venue constraints reduce price limit to zero",
                )
            normalized_price_limit = decimal_to_float64(
                normalized_price_decimal,
                max_abs_loss=constraints.tick_size,
                name="normalized_price_limit",
            )
            price_limit_exact = decimal_to_canonical_str(normalized_price_decimal)
            price_anchor_decimal = normalized_price_decimal

        if constraints.min_notional is not None:
            if price_anchor_decimal is None:
                return _NormalizedVenueOrderFields(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="min_notional requires a usable price anchor",
                )
            normalized_notional = multiply_exact(quantity_decimal, price_anchor_decimal)
            if normalized_notional < execution_decimal(
                constraints.min_notional, name="min_notional"
            ):
                return _NormalizedVenueOrderFields(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="normalized order violates venue min_notional",
                )

        return _NormalizedVenueOrderFields(
            quantity=decimal_to_float64(
                quantity_decimal,
                max_abs_loss=constraints.step_size,
                name="normalized_quantity",
            )
            if constraints.step_size is not None
            else decimal_to_float64(quantity_decimal, name="normalized_quantity"),
            quantity_exact=decimal_to_canonical_str(quantity_decimal),
            price_limit=normalized_price_limit,
            price_limit_exact=price_limit_exact,
        )


class _NormalizedVenueOrderFields(BaseModel, frozen=True):
    quantity: float
    quantity_exact: str
    price_limit: float | None = None
    price_limit_exact: str | None = None
    error_detail: str | None = None
