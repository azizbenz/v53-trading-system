"""Build-9X governed meta-learning scaffold.

This package intentionally ships only governed contracts and guards in the
minimal phase. It must not alter the Build-1..9 decision path.
"""

from meta_learning.contracts import (
    BreakdownReport,
    DiagnosticResult,
    ImprovementCandidate,
    LearningMemoryRecord,
    LearningReviewExport,
    LearningChecklist,
    LearningHypothesis,
    TradeLearningInput,
)
from meta_learning.enums import (
    CandidateKind,
    DiagnosticSeverity,
    HypothesisStatus,
    LearningLifecycleState,
)
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
from meta_learning.learning_review_exporter import export_learning_review
from meta_learning.mistake_classifier import classify_mistakes
from meta_learning.near_miss_analyzer import analyze_near_misses
from meta_learning.post_trade_diagnostic_engine import build_post_trade_diagnostics

__all__ = [
    "TradeLearningInput",
    "DiagnosticResult",
    "LearningHypothesis",
    "ImprovementCandidate",
    "LearningChecklist",
    "BreakdownReport",
    "LearningMemoryRecord",
    "LearningReviewExport",
    "LearningLifecycleState",
    "DiagnosticSeverity",
    "HypothesisStatus",
    "CandidateKind",
    "MetaLearningError",
    "LiveMutationForbiddenError",
    "ImplicitPromotionForbiddenError",
    "build_post_trade_diagnostics",
    "classify_mistakes",
    "analyze_near_misses",
    "build_breakdown_report",
    "build_learning_checklist",
    "build_learning_hypotheses",
    "build_improvement_candidates",
    "LearningMemoryStore",
    "export_learning_review",
]
