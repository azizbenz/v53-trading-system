"""Minimal governed contracts for the Build-9X meta-learning layer."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    EngineId,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
    StrategyClassification,
)
from meta_learning.enums import (
    CandidateKind,
    DiagnosticSeverity,
    HypothesisStatus,
    LearningLifecycleState,
)


class TradeLearningInput(BaseModel, frozen=True):
    """Single governed input captured from Build-9 outputs."""

    correlation_id: str = Field(..., min_length=1)
    dtr_ids: tuple[str, ...] = ()
    pair: str = Field(..., min_length=1)
    engine_id: EngineId
    profile: ProfileId = ProfileId.LIGHT
    source_runtime_mode: RuntimeMode
    strategy_classification: StrategyClassification
    source_version: str = Field(..., min_length=1)
    backtest_profile: str | None = None
    live_mutation_requested: bool = False
    implicit_promotion_requested: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def validate_governance(self) -> "TradeLearningInput":
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.live_mutation_requested:
            raise ValueError("Build-9X must not mutate the live path")
        if self.implicit_promotion_requested:
            raise ValueError("Build-9X must not request implicit promotion")
        return self


class DiagnosticResult(BaseModel, frozen=True):
    """Governed diagnostic output from a Build-9X analysis pass."""

    diagnostic_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    category: str = Field(default="generic", min_length=1)
    summary: str = Field(..., min_length=1)
    severity: DiagnosticSeverity = DiagnosticSeverity.WARNING
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.DIAGNOSED
    evidence_refs: tuple[str, ...] = ()
    structured_log_key: str = Field(..., min_length=1)
    manual_review_required: bool = True


class LearningHypothesis(BaseModel, frozen=True):
    """Hypothesis queued for governed replay only."""

    hypothesis_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    category: str = Field(default="generic", min_length=1)
    title: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    diagnostic_ids: tuple[str, ...] = ()
    target_runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    status: HypothesisStatus = HypothesisStatus.OPEN
    review_state: ReviewState = ReviewState.PENDING
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.HYPOTHESIS_REGISTERED

    @model_validator(mode="after")
    def validate_target_mode(self) -> "LearningHypothesis":
        if self.target_runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("Learning hypotheses must target LOCAL_REPLAY first")
        return self


class ImprovementCandidate(BaseModel, frozen=True):
    """Governed candidate produced by Build-9X, never auto-promoted."""

    candidate_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    hypothesis_ids: tuple[str, ...] = ()
    classification: StrategyClassification
    kind: CandidateKind
    summary: str = Field(..., min_length=1)
    promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    review_state: ReviewState = ReviewState.PENDING
    requires_manual_review: bool = True
    auto_promotion_enabled: bool = False
    config_patch_preview: tuple[str, ...] = ()
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.CANDIDATE_READY

    @model_validator(mode="after")
    def validate_candidate_policy(self) -> "ImprovementCandidate":
        if self.auto_promotion_enabled:
            raise ValueError("Improvement candidates must not auto-promote")
        if self.promotion_state in {
            PromotionState.MICRO_LIVE_CANDIDATE,
            PromotionState.LIVE_CANDIDATE,
        }:
            raise ValueError("Improvement candidates must stop at replay/shadow candidacy")
        return self


class LearningChecklist(BaseModel, frozen=True):
    """Human checklist generated before any replay handoff."""

    checklist_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.CHECKLIST_READY
    items: tuple[str, ...] = Field(..., min_length=1)
    ready_for_local_replay: bool = False
    ready_for_shadow: bool = False

    @model_validator(mode="after")
    def validate_readiness(self) -> "LearningChecklist":
        if self.ready_for_shadow and not self.ready_for_local_replay:
            raise ValueError("Shadow readiness requires local replay readiness first")
        return self


class BreakdownReport(BaseModel, frozen=True):
    """Aggregated diagnostic report for governed review."""

    correlation_id: str = Field(..., min_length=1)
    diagnostics: tuple[DiagnosticResult, ...] = ()
    mistake_classes: tuple[str, ...] = ()
    near_miss_pairs: tuple[str, ...] = ()
    summary: str = Field(..., min_length=1)


class LearningMemoryRecord(BaseModel, frozen=True):
    """Append-only memory record for Build-9X review history."""

    correlation_id: str = Field(..., min_length=1)
    diagnostics_count: int = Field(..., ge=0)
    hypothesis_count: int = Field(..., ge=0)
    candidate_count: int = Field(..., ge=0)
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.EXPORTED
    summary: str = Field(..., min_length=1)


class LearningReviewExport(BaseModel, frozen=True):
    """Structured review export handed to human governance."""

    correlation_id: str = Field(..., min_length=1)
    markdown_body: str = Field(..., min_length=1)
    checklist: LearningChecklist
    candidates: tuple[ImprovementCandidate, ...] = ()


__all__ = [
    "TradeLearningInput",
    "DiagnosticResult",
    "LearningHypothesis",
    "ImprovementCandidate",
    "LearningChecklist",
    "BreakdownReport",
    "LearningMemoryRecord",
    "LearningReviewExport",
]
