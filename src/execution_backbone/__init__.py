"""
V5.3 - Execution Backbone: real, measurable, reconcilable execution.

Sub-modules (in build order):
1. order_decider - intent, order type selection, execution guards, timeout, reporting
2. fill_tracker - order lifecycle, fill aggregation, latency, terminal states
3. execution_cost_meter - fees, ELW, adverse selection, partial fill costs, aggregation
4. reconciliation_layer - order/fill/position reconciliation, divergence, recovery
"""

from .execution_runtime import (
    ExecutionOpportunity,
    ExecutionRuntime,
    ExecutionSubmission,
    ExecutionSubmissionStatus,
    ExecutionVenueAdapter,
    RemoteExecutionState,
    ReplaceReceipt,
    RuntimeProcessingSummary,
    RuntimeReconciliationResult,
    SubmitReceipt,
    TimeoutSweepResult,
    VenueOrderEvent,
    VenueOrderEventType,
)

__all__ = [
    "ExecutionOpportunity",
    "ExecutionRuntime",
    "ExecutionSubmission",
    "ExecutionSubmissionStatus",
    "ExecutionVenueAdapter",
    "RemoteExecutionState",
    "ReplaceReceipt",
    "RuntimeProcessingSummary",
    "RuntimeReconciliationResult",
    "SubmitReceipt",
    "TimeoutSweepResult",
    "VenueOrderEvent",
    "VenueOrderEventType",
]
