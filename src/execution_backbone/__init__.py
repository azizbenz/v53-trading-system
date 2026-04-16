"""
V5.3 - Execution Backbone: real, measurable, reconcilable execution.

Sub-modules (in build order):
1. order_decider - intent, order type selection, execution guards, timeout, reporting
2. fill_tracker - order lifecycle, fill aggregation, latency, terminal states
3. execution_cost_meter - fees, ELW, adverse selection, partial fill costs, aggregation
4. reconciliation_layer - order/fill/position reconciliation, divergence, recovery
"""

from __future__ import annotations

from .execution_runtime import (
    ExecutionNoTradeFilter,
    ExecutionNoTradeFilterInput,
    ExecutionNoTradeFilterOutcome,
    ExecutionRefusalSink,
    ExecutionOpportunity,
    ExecutionRuntime,
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
)
from .gatekeeper import (
    ExecutionGatekeeperAuditDecision,
    ExecutionGatekeeperAuditEvent,
    ExecutionGateName,
    ExecutionGateRefusalDisposition,
    ExecutionGateTrace,
    ExecutionGateTraceVerdict,
    ExecutionGatekeeper,
    GatekeeperAuditLogger,
    ExecutionPermit,
    ExecutionRefusal,
    ExecutionVenueNormalizationResult,
)
from .rate_limiter import (
    ExecutionRateLimitDecision,
    ExecutionRateLimitModel,
    evaluate_execution_rate_limit,
)
from .spread_guard import (
    ExecutionSpreadGuardDecision,
    ExecutionSpreadGuardModel,
    evaluate_execution_spread_guard,
)
from .slippage_model import (
    ExecutionSlippageEstimate,
    ExecutionSlippageModel,
    predict_execution_slippage,
)
from .venue_constraints_provider import (
    BinanceExchangeInfoVenueConstraintProvider,
    VenueConstraintProvider,
    parse_binance_exchange_info_payload,
)

__all__ = [
    "ExecutionNoTradeFilter",
    "ExecutionNoTradeFilterInput",
    "ExecutionNoTradeFilterOutcome",
    "ExecutionRefusalSink",
    "ExecutionGatekeeper",
    "ExecutionGatekeeperAuditDecision",
    "ExecutionGatekeeperAuditEvent",
    "ExecutionGateName",
    "ExecutionGateRefusalDisposition",
    "ExecutionGateTrace",
    "ExecutionGateTraceVerdict",
    "GatekeeperAuditLogger",
    "ExecutionPermit",
    "ExecutionRefusal",
    "ExecutionVenueNormalizationResult",
    "ExecutionOpportunity",
    "ExecutionRateLimitDecision",
    "ExecutionRateLimitModel",
    "ExecutionRuntime",
    "ExecutionSpreadGuardDecision",
    "ExecutionSpreadGuardModel",
    "ExecutionSlippageEstimate",
    "ExecutionSlippageModel",
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
    "evaluate_execution_rate_limit",
    "evaluate_execution_spread_guard",
    "BinanceExchangeInfoVenueConstraintProvider",
    "predict_execution_slippage",
    "VenueConstraintProvider",
    "parse_binance_exchange_info_payload",
]
