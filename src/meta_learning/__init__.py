"""Build-9X governed meta-learning layer.

This package remains strictly governed and must not alter the Build-1..9
decision path or create live mutation/promotion side effects.
"""

from __future__ import annotations

from meta_learning.contracts import (
    ArchiveEligibilityRecord,
    BreakdownReport,
    CandidateRecord,
    DiagnosticEvidence,
    DiagnosticResult,
    DiagnosticRecord,
    ExportBundleRecord,
    ImprovementCandidate,
    LearningCapacitySnapshot,
    LearningMemoryRecord,
    LearningEventRecord,
    LifecycleTransitionRecord,
    LearningReviewExport,
    LearningChecklist,
    LearningHypothesis,
    MetaLearningReviewBundle,
    ReviewQueueEntry,
    ReplayComparisonProtocol,
    ReplayExportBundle,
    ReviewDecisionRecord,
    ReviewRecord,
    TradeLearningInput,
    TradeLossAttribution,
    TradeLossAttributionReport,
    TradeLossEvidence,
    TradeLossFailureModeSummary,
    HypothesisRecord,
)
from meta_learning.enums import (
    CandidateGovernanceStage,
    CandidateKind,
    DiagnosticStatus,
    DiagnosticSeverity,
    EvidenceStrength,
    HypothesisGovernanceStage,
    HypothesisStatus,
    LearningBacklogState,
    LearningCaptureMode,
    LearningLifecycleState,
)
from meta_learning.capacity_guard import evaluate_learning_capacity
from meta_learning.errors import (
    ImplicitPromotionForbiddenError,
    LiveMutationForbiddenError,
    MetaLearningError,
)
from meta_learning.breakdown_report_builder import build_breakdown_report
from meta_learning.checklist_generator import build_learning_checklist
from meta_learning.hypothesis_registry import build_learning_hypotheses
from meta_learning.improvement_candidate_builder import build_improvement_candidates
from meta_learning.learning_memory_store import LearningMemoryStore
from meta_learning.persistence_store import AppendOnlyMetaLearningStore
from meta_learning.learning_review_exporter import export_learning_review
from meta_learning.merge_gate_contracts import (
    Build9XMergeGateName,
    Build9XMergeGateReport,
    Build9XMergeGateResult,
)
from meta_learning.review_queue import build_review_queue
from meta_learning.lifecycle_registry import (
    apply_candidate_path,
    apply_diagnostic_path,
    apply_hypothesis_path,
    transition_candidate,
    transition_diagnostic,
    transition_hypothesis,
)
from meta_learning.retention_policy import (
    diagnostic_or_hypothesis_retention,
    export_bundle_retention,
    review_or_promotion_retention,
)
from meta_learning.mistake_classifier import classify_mistakes
from meta_learning.near_miss_analyzer import analyze_near_misses
from meta_learning.post_trade_diagnostic_engine import build_post_trade_diagnostics
from meta_learning.monitoring_projection import build_build9x_projection
from meta_learning.merge_gates import evaluate_build9x_merge_gates
from meta_learning.trade_loss_attribution import build_trade_loss_attribution_report
from meta_learning.replay_bundle_builder import (
    build_replay_export_bundles,
    enrich_candidates_with_replay_refs,
)
from meta_learning.review_governance import (
    append_human_review_decision,
    build_archive_eligibility,
    build_system_review_decisions,
)
from meta_learning.review_resolution import (
    apply_candidate_replay_results,
    apply_human_review_resolution,
)
from meta_learning.model_risk_registry import (
    MlModelDriftSnapshot,
    MlModelRiskRecord,
    MlModelRiskRegistry,
    MlModelRiskSignal,
    MlModelRiskState,
    MlModelRuntimeStage,
    evaluate_model_risk_signal,
)
from meta_learning.strategy_drift_monitor import (
    StrategyDriftSignal,
    StrategyDriftSnapshot,
    StrategyDriftState,
    StrategyDriftThresholds,
    evaluate_strategy_drift,
)
from meta_learning.facade import MetaLearningFacade, MetaLearningFacadeProtocol
from meta_learning.review_orchestrator import run_meta_learning_review

__all__ = [
    "TradeLearningInput",
    "DiagnosticEvidence",
    "DiagnosticResult",
    "TradeLossEvidence",
    "TradeLossAttribution",
    "TradeLossFailureModeSummary",
    "TradeLossAttributionReport",
    "ReviewDecisionRecord",
    "ArchiveEligibilityRecord",
    "LearningCapacitySnapshot",
    "LearningHypothesis",
    "ImprovementCandidate",
    "LearningChecklist",
    "BreakdownReport",
    "LearningMemoryRecord",
    "LearningReviewExport",
    "ReviewQueueEntry",
    "MetaLearningReviewBundle",
    "ReplayComparisonProtocol",
    "ReplayExportBundle",
    "LifecycleTransitionRecord",
    "DiagnosticRecord",
    "HypothesisRecord",
    "CandidateRecord",
    "ReviewRecord",
    "ExportBundleRecord",
    "LearningEventRecord",
    "LearningLifecycleState",
    "DiagnosticStatus",
    "DiagnosticSeverity",
    "HypothesisStatus",
    "EvidenceStrength",
    "LearningCaptureMode",
    "LearningBacklogState",
    "HypothesisGovernanceStage",
    "CandidateGovernanceStage",
    "CandidateKind",
    "MetaLearningError",
    "LiveMutationForbiddenError",
    "ImplicitPromotionForbiddenError",
    "build_post_trade_diagnostics",
    "build_trade_loss_attribution_report",
    "classify_mistakes",
    "analyze_near_misses",
    "build_breakdown_report",
    "build_learning_checklist",
    "build_learning_hypotheses",
    "build_improvement_candidates",
    "evaluate_learning_capacity",
    "build_build9x_projection",
    "Build9XMergeGateName",
    "Build9XMergeGateResult",
    "Build9XMergeGateReport",
    "evaluate_build9x_merge_gates",
    "build_system_review_decisions",
    "append_human_review_decision",
    "build_archive_eligibility",
    "apply_candidate_replay_results",
    "apply_human_review_resolution",
    "MlModelRuntimeStage",
    "MlModelRiskState",
    "MlModelDriftSnapshot",
    "MlModelRiskSignal",
    "MlModelRiskRecord",
    "MlModelRiskRegistry",
    "evaluate_model_risk_signal",
    "StrategyDriftState",
    "StrategyDriftSnapshot",
    "StrategyDriftThresholds",
    "StrategyDriftSignal",
    "evaluate_strategy_drift",
    "build_review_queue",
    "MetaLearningFacadeProtocol",
    "MetaLearningFacade",
    "diagnostic_or_hypothesis_retention",
    "review_or_promotion_retention",
    "export_bundle_retention",
    "transition_diagnostic",
    "transition_hypothesis",
    "transition_candidate",
    "apply_diagnostic_path",
    "apply_hypothesis_path",
    "apply_candidate_path",
    "build_replay_export_bundles",
    "enrich_candidates_with_replay_refs",
    "LearningMemoryStore",
    "AppendOnlyMetaLearningStore",
    "export_learning_review",
    "run_meta_learning_review",
]
