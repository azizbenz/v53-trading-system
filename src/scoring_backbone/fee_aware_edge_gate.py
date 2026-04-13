"""Compatibility surface for the canonical execution-owned fee-aware edge gate."""

from execution_backbone.fee_aware_edge_gate import (
    FeeAwareEdgeDecision,
    FeeAwareEdgeGateConfig,
    FeeAwareEdgeThresholds,
    evaluate_fee_aware_edge,
    resolve_fee_aware_edge_thresholds,
)

__all__ = [
    "FeeAwareEdgeDecision",
    "FeeAwareEdgeGateConfig",
    "FeeAwareEdgeThresholds",
    "evaluate_fee_aware_edge",
    "resolve_fee_aware_edge_thresholds",
]
