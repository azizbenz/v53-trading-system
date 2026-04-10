"""Build-5 - scoring_backbone: auditable hard/soft/rank runtime."""

from .fee_aware_edge_gate import (
    FeeAwareEdgeDecision,
    FeeAwareEdgeGateConfig,
    FeeAwareEdgeThresholds,
    evaluate_fee_aware_edge,
    resolve_fee_aware_edge_thresholds,
)
from .scoring_runtime import (
    ScoringCandidateInput,
    ScoringCandidateAudit,
    ScoringRoundResult,
    ScoringSoftPenaltyLayerHook,
    ScoringSoftPenaltyLayerInput,
    ScoringSoftPenaltyLayerOutcome,
    ScoringRuntime,
)

__all__ = [
    "FeeAwareEdgeDecision",
    "FeeAwareEdgeGateConfig",
    "FeeAwareEdgeThresholds",
    "ScoringCandidateAudit",
    "ScoringCandidateInput",
    "ScoringRoundResult",
    "ScoringSoftPenaltyLayerHook",
    "ScoringSoftPenaltyLayerInput",
    "ScoringSoftPenaltyLayerOutcome",
    "ScoringRuntime",
    "evaluate_fee_aware_edge",
    "resolve_fee_aware_edge_thresholds",
]
