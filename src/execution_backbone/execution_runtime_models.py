"""Models and protocols for the canonical Build-3 execution runtime."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field
from interface_contracts import RefusalRecord
from sharia_compliance.contracts import ShariaPermit, ShariaRejection, ShariaTradeRequest

from .execution_routing_features import (
    ExecutionRoutingFeatureSnapshot,
    ExecutionRoutingTopOfBookSnapshot,
    ExecutionRoutingVenueFees,
)
from .execution_cost_meter.cost_aggregator import CostAggregate
from .fill_tracker.fill_reporter import FillStats
from .fill_tracker.latency_meter import LatencyStats
from .fill_tracker.order_terminal_state_resolver import TerminalResolution
from .gatekeeper import ExecutionGateTrace
from .order_decider.decision_reporter import DecisionStats
from .order_decider.execution_guard import GuardResult
from .order_decider.intent_builder import ExecutionIntent, NoTradeDecision, VenueConstraintSnapshot
from .reconciliation_layer.divergence_classifier import DivergenceClassification
from .reconciliation_layer.fill_reconciler import FillReconciliationResult
from .reconciliation_layer.order_reconciler import OrderReconciliationResult
from .reconciliation_layer.position_reconciler import PositionReconciliationResult
from .reconciliation_layer.recovery_trigger import RecoveryDecision


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
    profile: str = "COMPLETE"  # BS-49: LIGHT removed; COMPLETE is the governed profile
    venue_constraints: VenueConstraintSnapshot | None = None
    signal_arrival_monotonic_s: float | None = Field(default=None, ge=0.0)
    scoring_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    risk_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    portfolio_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    routing_features: ExecutionRoutingFeatureSnapshot | None = None
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
    signal_to_submit_s: float | None = None
    signal_to_scoring_s: float | None = None
    scoring_to_risk_s: float | None = None
    risk_to_portfolio_s: float | None = None
    portfolio_to_submit_s: float | None = None
    detail: str = ""
    gate_trace: tuple[ExecutionGateTrace, ...] = ()
    routing_trace: dict[str, object] = Field(default_factory=dict)


class TimeoutSweepResult(BaseModel, frozen=True):
    """Result of a timeout sweep across open orders."""

    cancelled_order_ids: tuple[str, ...] = ()
    converted_order_ids: tuple[str, ...] = ()


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


class ExecutionRoutingLobSnapshotResolver(Protocol):
    def __call__(self, pair: str) -> object | None:
        ...


class ExecutionRoutingRegimeSignalResolver(Protocol):
    def __call__(self, pair: str) -> object | None:
        ...


class ExecutionRoutingTopOfBookResolver(Protocol):
    def __call__(self, pair: str) -> ExecutionRoutingTopOfBookSnapshot | None:
        ...


class ExecutionRoutingVenueFeesResolver(Protocol):
    def __call__(self, pair: str) -> ExecutionRoutingVenueFees | None:
        ...


class ExecutionRefusalSink(Protocol):
    """Typed sink for governed refusal journaling."""

    def record_refusal(self, record: RefusalRecord) -> None:
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


__all__ = [
    "ExecutionNoTradeFilter",
    "ExecutionNoTradeFilterInput",
    "ExecutionNoTradeFilterOutcome",
    "ExecutionRefusalSink",
    "ExecutionOpportunity",
    "ExecutionSubmission",
    "ExecutionSubmissionStatus",
    "ExecutionVenueAdapter",
    "RemoteExecutionState",
    "ReplaceReceipt",
    "RuntimeProcessingSummary",
    "RuntimeReconciliationResult",
    "ShariaTradeAuthorizer",
    "SubmitReceipt",
    "TimeoutSweepResult",
    "VenueOrderEvent",
    "VenueOrderEventType",
    "_OrderCostContext",
    "_TerminalOrderSnapshot",
]
