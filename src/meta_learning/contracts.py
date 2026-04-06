"""Minimal governed contracts for the Build-9X meta-learning layer."""

from __future__ import annotations

from datetime import datetime, timezone

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
    CandidateGovernanceStage,
    CandidateKind,
    LearningBacklogState,
    LearningCaptureMode,
    DiagnosticStatus,
    DiagnosticSeverity,
    EvidenceStrength,
    HypothesisGovernanceStage,
    HypothesisStatus,
    LearningLifecycleState,
)
from meta_learning.merge_gate_contracts import Build9XMergeGateReport


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


class DiagnosticEvidence(BaseModel, frozen=True):
    """Structured evidence attached to a Build-9X diagnostic."""

    source: str = Field(..., min_length=1)
    reference: str = Field(..., min_length=1)
    observation: str = Field(..., min_length=1)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class DiagnosticResult(BaseModel, frozen=True):
    """Governed diagnostic output from a Build-9X analysis pass."""

    diagnostic_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    status: DiagnosticStatus = DiagnosticStatus.OPEN
    category: str = Field(default="generic", min_length=1)
    secondary_categories: tuple[str, ...] = ()
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    summary: str = Field(..., min_length=1)
    severity: DiagnosticSeverity = DiagnosticSeverity.WARNING
    root_causes: tuple[str, ...] = ()
    evidence: tuple[DiagnosticEvidence, ...] = ()
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.DIAGNOSED
    evidence_refs: tuple[str, ...] = ()
    counterfactual_summary: str = ""
    economic_assessment: str = ""
    actionability_level: str = Field(default="review_required", min_length=1)
    structured_log_key: str = Field(..., min_length=1)
    manual_review_required: bool = True
    created_at: datetime = Field(default_factory=_utc_now)


class LearningCapacitySnapshot(BaseModel, frozen=True):
    """Observed Build-9X worker capacity and backpressure state."""

    queue_depth: int = Field(default=0, ge=0)
    queue_oldest_age_ms: int = Field(default=0, ge=0)
    worker_cpu_pct: float = Field(default=0.0, ge=0.0)
    worker_rss_mb: float = Field(default=0.0, ge=0.0)
    write_latency_ms: float = Field(default=0.0, ge=0.0)
    export_failures_total: int = Field(default=0, ge=0)
    log_loss_total: int = Field(default=0, ge=0)
    unprocessed_items_count: int = Field(default=0, ge=0)
    backlog_alert_threshold: int = Field(default=1000, ge=1)
    backlog_protection_threshold: int = Field(default=5000, ge=1)
    backlog_state: LearningBacklogState = LearningBacklogState.NORMAL
    capture_mode: LearningCaptureMode = LearningCaptureMode.FULL_CAPTURE
    observability_reduced: bool = False
    backpressure_active: bool = False
    backpressure_signal_key: str = ""
    review_blocked_due_to_incomplete_data: bool = False
    promotion_blocked_due_to_incomplete_data: bool = False
    blocking_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_capacity_state(self) -> "LearningCapacitySnapshot":
        if self.backlog_protection_threshold <= self.backlog_alert_threshold:
            raise ValueError("backlog_protection_threshold must be greater than backlog_alert_threshold")
        if (
            self.backlog_state == LearningBacklogState.PROTECTION
            and self.capture_mode != LearningCaptureMode.CAPTURE_MINIMALE
        ):
            raise ValueError("PROTECTION backlog_state requires capture_minimale mode")
        if self.capture_mode == LearningCaptureMode.CAPTURE_MINIMALE and not self.backpressure_active:
            raise ValueError("capture_minimale mode requires backpressure_active=True")
        if self.backpressure_active and not self.backpressure_signal_key:
            raise ValueError("backpressure_active=True requires backpressure_signal_key")
        if self.review_blocked_due_to_incomplete_data and not self.blocking_reasons:
            raise ValueError("Blocked review state requires at least one blocking reason")
        return self


class LearningHypothesis(BaseModel, frozen=True):
    """Hypothesis queued for governed replay only."""

    hypothesis_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    category: str = Field(default="generic", min_length=1)
    title: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    diagnostic_ids: tuple[str, ...] = ()
    target_module: str = ""
    target_component: str = ""
    signal_family: str = ""
    target_parameter_family: str = ""
    expected_effect: str = ""
    risk_of_regression: str = ""
    required_replay_scope: str = ""
    expected_replay_evidence: tuple[str, ...] = ()
    expected_shadow_evidence: tuple[str, ...] = ()
    monitoring_hooks: tuple[str, ...] = ()
    segmentation_used: tuple[str, ...] = ()
    comparison_metrics: tuple[str, ...] = ()
    rejection_criteria: tuple[str, ...] = ()
    evidence_strength: EvidenceStrength = EvidenceStrength.ANECDOTAL
    sample_size: int = Field(default=0, ge=0)
    shadow_candidate_allowed: bool = False
    target_runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    status: HypothesisStatus = HypothesisStatus.OPEN
    review_state: ReviewState = ReviewState.PENDING
    source_version: str = ""
    contracts_version: str = ""
    governance_stage: HypothesisGovernanceStage = HypothesisGovernanceStage.DRAFT
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.HYPOTHESIS_REGISTERED
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_target_mode(self) -> "LearningHypothesis":
        if self.target_runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("Learning hypotheses must target LOCAL_REPLAY first")
        if (
            self.governance_stage == HypothesisGovernanceStage.REPLAY_APPROVED
            and (
                not self.rationale
                or self.sample_size <= 0
                or not self.segmentation_used
                or not self.risk_of_regression
                or not self.comparison_metrics
                or not self.rejection_criteria
                or not self.target_component
                or not self.signal_family
                or not self.expected_replay_evidence
                or not self.expected_shadow_evidence
            )
        ):
            raise ValueError(
                "REPLAY_APPROVED hypotheses require rationale, sample_size, segmentation, regression risk, comparison metrics, rejection criteria, target_component, signal_family, expected_replay_evidence, and expected_shadow_evidence"
            )
        if (
            self.shadow_candidate_allowed
            and self.governance_stage
            not in {
                HypothesisGovernanceStage.REPLAY_APPROVED,
                HypothesisGovernanceStage.SHADOW_CANDIDATE,
            }
        ):
            raise ValueError(
                "shadow_candidate_allowed=True requires a replay-approved or shadow-candidate hypothesis"
            )
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
    candidate_version: str = "build9x.draft"
    config_patch_preview: tuple[str, ...] = ()
    tests_required: tuple[str, ...] = ()
    replay_scope: str = ""
    replay_bundle_reference: str = ""
    comparison_protocol_reference: str = ""
    shared_core_hash: str = ""
    governance_stage: CandidateGovernanceStage = CandidateGovernanceStage.PREPARED
    validation_notes: tuple[str, ...] = ()
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.CANDIDATE_READY
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_candidate_policy(self) -> "ImprovementCandidate":
        if self.auto_promotion_enabled:
            raise ValueError("Improvement candidates must not auto-promote")
        if self.promotion_state in {
            PromotionState.MICRO_LIVE_CANDIDATE,
            PromotionState.LIVE_CANDIDATE,
        }:
            raise ValueError("Improvement candidates must stop at replay/shadow candidacy")
        if (
            self.governance_stage
            in {
                CandidateGovernanceStage.READY_FOR_REPLAY,
                CandidateGovernanceStage.REPLAY_RUNNING,
                CandidateGovernanceStage.REPLAY_PASSED,
                CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
            }
            and (
                not self.tests_required
                or not self.replay_scope
                or not self.replay_bundle_reference
                or not self.comparison_protocol_reference
                or not self.shared_core_hash
            )
        ):
            raise ValueError(
                "Replay-ready candidate stages require tests, replay scope, replay bundle ref, comparison protocol ref, and shared_core_hash"
            )
        if (
            self.governance_stage == CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW
            and self.promotion_state != PromotionState.SHADOW_CANDIDATE
        ):
            raise ValueError(
                "READY_FOR_SHADOW_REVIEW candidates must stay on promotion_state=SHADOW_CANDIDATE"
            )
        return self


class LearningChecklist(BaseModel, frozen=True):
    """Human checklist generated before any replay handoff."""

    checklist_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.CHECKLIST_READY
    axes: tuple[str, ...] = ("OPERATIONS", "RESEARCH", "VALIDATION")
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
    primary_root_cause: str = ""
    expected_vs_realized_costs: str = ""
    break_even_reading: str = ""
    sterilization_reading: str = ""
    portfolio_reading: str = ""
    counterfactual_summary: str = ""
    main_lesson: str = ""
    verdict: str = ""


class LearningMemoryRecord(BaseModel, frozen=True):
    """Append-only memory record for Build-9X review history."""

    record_id: str = ""
    correlation_id: str = Field(..., min_length=1)
    diagnostic_id: str | None = None
    hypothesis_id: str | None = None
    candidate_id: str | None = None
    diagnostics_count: int = Field(..., ge=0)
    hypothesis_count: int = Field(..., ge=0)
    candidate_count: int = Field(..., ge=0)
    verdict: str = ""
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    archived: bool = False
    lifecycle_state: LearningLifecycleState = LearningLifecycleState.EXPORTED
    summary: str = Field(..., min_length=1)


class ReplayComparisonProtocol(BaseModel, frozen=True):
    """Governed comparison plan attached to a Build-9X replay bundle."""

    protocol_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    evaluation_scope: str = Field(..., min_length=1)
    target_components: tuple[str, ...] = ()
    signal_families: tuple[str, ...] = ()
    expected_replay_evidence: tuple[str, ...] = ()
    expected_shadow_evidence: tuple[str, ...] = ()
    comparison_metrics: tuple[str, ...] = ()
    rejection_criteria: tuple[str, ...] = ()


class ReplayExportBundle(BaseModel, frozen=True):
    """Replay handoff artifact produced by Build-9X before LOCAL_REPLAY."""

    bundle_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    hypothesis_ids: tuple[str, ...] = ()
    source_version: str = Field(..., min_length=1)
    contracts_version: str = Field(..., min_length=1)
    feature_schema_version: str = Field(..., min_length=1)
    formula_schema_version: str = Field(..., min_length=1)
    regime_logic_version: str = Field(..., min_length=1)
    cost_model_version: str = Field(..., min_length=1)
    replay_scope: str = Field(..., min_length=1)
    tests_required: tuple[str, ...] = ()
    comparison_protocol: ReplayComparisonProtocol
    execution_plan: BaseModel
    shared_core_hash: str = Field(..., min_length=1)
    bundle_checksum: str = Field(..., min_length=1)
    exported_at: datetime = Field(default_factory=_utc_now)


class ReviewDecisionRecord(BaseModel, frozen=True):
    """Explicit review decision attached to a governed Build-9X review."""

    decision_id: str = Field(..., min_length=1)
    review_entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    is_human_review: bool = False
    review_state: ReviewState = ReviewState.PENDING
    verdict: str = Field(..., min_length=1)
    rationale: str = ""
    final_verdict_recorded: bool = False
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_review_decision(self) -> "ReviewDecisionRecord":
        if self.is_human_review and self.actor == "system_build9x":
            raise ValueError("Human review decisions require an explicit non-system actor")
        if self.final_verdict_recorded and self.review_state in {
            ReviewState.PENDING,
            ReviewState.IN_REVIEW,
        }:
            raise ValueError("Final verdicts cannot stay pending/in_review")
        return self


class ArchiveEligibilityRecord(BaseModel, frozen=True):
    """Audit-ready archive eligibility evaluation for diagnostics and hypotheses."""

    entity_kind: str = Field(..., min_length=1)
    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    eligible: bool = False
    final_verdict_recorded: bool = False
    replay_active: bool = False
    review_open: bool = True
    pending_promotion: bool = False
    blocking_reasons: tuple[str, ...] = ()
    archived_at: datetime | None = Field(default=None)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""

    @model_validator(mode="after")
    def validate_archive_eligibility(self) -> "ArchiveEligibilityRecord":
        if self.eligible and self.blocking_reasons:
            raise ValueError("Archive-eligible records must not keep blocking reasons")
        if self.archived_at is not None and not self.eligible:
            raise ValueError("archived_at requires eligible=True")
        return self


class LifecycleTransitionRecord(BaseModel, frozen=True):
    """Historized Build-9X state transition emitted into the append-only ledger."""

    transition_id: str = Field(..., min_length=1)
    entity_kind: str = Field(..., min_length=1)
    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    from_state: str = Field(..., min_length=1)
    to_state: str = Field(..., min_length=1)
    actor: str = Field(default="system_build9x", min_length=1)
    reason: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_transition(self) -> "LifecycleTransitionRecord":
        if self.from_state == self.to_state:
            raise ValueError("Lifecycle transitions must change state")
        return self


class LearningReviewExport(BaseModel, frozen=True):
    """Structured review export handed to human governance."""

    correlation_id: str = Field(..., min_length=1)
    export_ref: str = ""
    markdown_body: str = Field(..., min_length=1)
    checklist: LearningChecklist
    candidates: tuple[ImprovementCandidate, ...] = ()
    replay_bundles: tuple[ReplayExportBundle, ...] = ()
    review_decisions: tuple[ReviewDecisionRecord, ...] = ()
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...] = ()
    lifecycle_transitions: tuple[LifecycleTransitionRecord, ...] = ()
    merge_gate_report: Build9XMergeGateReport | None = None
    capture_mode: LearningCaptureMode = LearningCaptureMode.FULL_CAPTURE
    review_blocked_due_to_incomplete_data: bool = False
    blocking_reasons: tuple[str, ...] = ()


class ReviewQueueEntry(BaseModel, frozen=True):
    """Canonical review-queue entry for hypotheses awaiting human governance."""

    hypothesis_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    diagnostic_ids: tuple[str, ...] = ()
    diagnostic_severities: tuple[DiagnosticSeverity, ...] = ()
    priority: str = Field(default="normal", min_length=1)
    review_state: ReviewState = ReviewState.PENDING
    governance_stage: HypothesisGovernanceStage = HypothesisGovernanceStage.UNDER_REVIEW
    evidence_strength: EvidenceStrength = EvidenceStrength.ANECDOTAL
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_priority(self) -> "ReviewQueueEntry":
        if self.priority not in {"critical", "normal"}:
            raise ValueError("Review queue priority must be critical or normal")
        if self.governance_stage != HypothesisGovernanceStage.UNDER_REVIEW:
            raise ValueError("Review queue entries must remain in UNDER_REVIEW stage")
        return self


class MetaLearningReviewBundle(BaseModel, frozen=True):
    """Single governed Build-9X review bundle for downstream consumers."""

    correlation_id: str = Field(..., min_length=1)
    diagnostics: tuple[DiagnosticResult, ...] = ()
    mistake_classes: tuple[str, ...] = ()
    breakdown_report: BreakdownReport
    checklist: LearningChecklist
    hypotheses: tuple[LearningHypothesis, ...] = ()
    candidates: tuple[ImprovementCandidate, ...] = ()
    replay_bundles: tuple[ReplayExportBundle, ...] = ()
    memory_record: LearningMemoryRecord
    review_export: LearningReviewExport
    capacity_snapshot: LearningCapacitySnapshot | None = None
    review_decisions: tuple[ReviewDecisionRecord, ...] = ()
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...] = ()
    lifecycle_transitions: tuple[LifecycleTransitionRecord, ...] = ()
    merge_gate_report: Build9XMergeGateReport | None = None

    @model_validator(mode="after")
    def validate_bundle_coherence(self) -> "MetaLearningReviewBundle":
        if self.breakdown_report.correlation_id != self.correlation_id:
            raise ValueError("Breakdown report correlation_id must match bundle correlation_id")
        if self.checklist.correlation_id != self.correlation_id:
            raise ValueError("Checklist correlation_id must match bundle correlation_id")
        if self.memory_record.correlation_id != self.correlation_id:
            raise ValueError("Memory record correlation_id must match bundle correlation_id")
        if self.review_export.correlation_id != self.correlation_id:
            raise ValueError("Review export correlation_id must match bundle correlation_id")
        if any(diagnostic.correlation_id != self.correlation_id for diagnostic in self.diagnostics):
            raise ValueError("All diagnostics must share the bundle correlation_id")
        if any(hypothesis.correlation_id != self.correlation_id for hypothesis in self.hypotheses):
            raise ValueError("All hypotheses must share the bundle correlation_id")
        if any(candidate.correlation_id != self.correlation_id for candidate in self.candidates):
            raise ValueError("All candidates must share the bundle correlation_id")
        if self.review_export.replay_bundles and self.review_export.replay_bundles != self.replay_bundles:
            raise ValueError("Review export replay bundles must match bundle replay bundles")
        if self.review_export.review_decisions and self.review_export.review_decisions != self.review_decisions:
            raise ValueError("Review export review decisions must match bundle review decisions")
        if self.review_export.archive_eligibility and self.review_export.archive_eligibility != self.archive_eligibility:
            raise ValueError("Review export archive eligibility must match bundle archive eligibility")
        if self.review_export.lifecycle_transitions and self.review_export.lifecycle_transitions != self.lifecycle_transitions:
            raise ValueError("Review export lifecycle transitions must match bundle lifecycle transitions")
        if self.review_export.merge_gate_report and self.review_export.merge_gate_report != self.merge_gate_report:
            raise ValueError("Review export merge_gate_report must match bundle merge_gate_report")
        if self.capacity_snapshot is not None:
            if (
                self.review_export.review_blocked_due_to_incomplete_data
                != self.capacity_snapshot.review_blocked_due_to_incomplete_data
            ):
                raise ValueError("Review export blocked flag must match capacity snapshot blocked flag")
            if self.review_export.capture_mode != self.capacity_snapshot.capture_mode:
                raise ValueError("Review export capture_mode must match capacity snapshot capture_mode")
        return self


class DiagnosticRecord(BaseModel, frozen=True):
    """Persisted diagnostic record used by the append-only Build-9X ledger."""

    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    diagnostic: DiagnosticResult


class HypothesisRecord(BaseModel, frozen=True):
    """Persisted hypothesis record used by the append-only Build-9X ledger."""

    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    hypothesis: LearningHypothesis


class CandidateRecord(BaseModel, frozen=True):
    """Persisted candidate record used by the append-only Build-9X ledger."""

    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    candidate: ImprovementCandidate


class ReviewRecord(BaseModel, frozen=True):
    """Persisted review record used by the append-only Build-9X ledger."""

    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    actor: str = Field(default="system_build9x", min_length=1)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    review_export: LearningReviewExport
    capacity_snapshot: LearningCapacitySnapshot | None = None
    review_decisions: tuple[ReviewDecisionRecord, ...] = ()
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...] = ()
    lifecycle_transitions: tuple[LifecycleTransitionRecord, ...] = ()


class ExportBundleRecord(BaseModel, frozen=True):
    """Persisted replay export bundle record."""

    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    retention_locked: bool = False
    replay_bundle: ReplayExportBundle


class LearningEventRecord(BaseModel, frozen=True):
    """Append-only event emitted for governed Build-9X state transitions."""

    event_id: str = Field(..., min_length=1)
    entity_kind: str = Field(..., min_length=1)
    entity_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    actor: str = Field(default="system_build9x", min_length=1)
    payload_ref: str = ""
    payload_checksum: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    retention_until: datetime | None = Field(default=None)
    retention_policy: str = ""
    created_at: datetime = Field(default_factory=_utc_now)


__all__ = [
    "TradeLearningInput",
    "DiagnosticEvidence",
    "DiagnosticResult",
    "LearningCapacitySnapshot",
    "LearningHypothesis",
    "ImprovementCandidate",
    "LearningChecklist",
    "BreakdownReport",
    "LearningMemoryRecord",
    "ReplayComparisonProtocol",
    "ReplayExportBundle",
    "ReviewDecisionRecord",
    "ArchiveEligibilityRecord",
    "LifecycleTransitionRecord",
    "LearningReviewExport",
    "ReviewQueueEntry",
    "MetaLearningReviewBundle",
    "DiagnosticRecord",
    "HypothesisRecord",
    "CandidateRecord",
    "ReviewRecord",
    "ExportBundleRecord",
    "LearningEventRecord",
]
