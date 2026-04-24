"""Governed Micro-live and Live-Light contracts for Build-12/13."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from protocols.contracts_validation_support import (
    validate_live_light_governance,
    validate_micro_live_governance,
)

from .contracts_shared import (
    InfoStressGovernanceSummary,
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
    OperatorSafingRequest,
    ProfileId,
    PromotionState,
    RegimeLiteGovernanceSummary,
    ReviewState,
    RuntimeMode,
    ShadowPortfolioJudgment,
    ShadowRunState,
    ShadowVerdict,
    _ACCEPTED_IMPORT_REVIEW_STATES,
    _ACCEPTED_IMPORT_STATUSES,
    _ACCEPTED_ONBOARDING_REVIEW_STATES,
    _EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION,
    _EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE,
    _EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE,
    _EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE,
    _EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE,
    _EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE,
    _EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL,
    _EXPECTED_IMPORT_SOURCE_PROFILE,
    _LIVE_LIGHT_ALLOWED_ENGINES,
    _MICRO_LIVE_ALLOWED_ENGINES,
    _REJECTED_IMPORT_COMPATIBILITY_STATUSES,
    _REJECTED_IMPORT_SIGNATURE_STATUSES,
)


class MicroLiveInput(BaseModel, frozen=True):
    """Single governed input entering the minimal Build-12 Micro-live gate."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.COMPLETE
    runtime_mode: RuntimeMode = RuntimeMode.MICRO_LIVE
    shadow_run_id: str = Field(..., min_length=1)
    shadow_truth_set_ref: str = Field(..., min_length=1)
    shadow_validation_set_ref: str = Field(..., min_length=1)
    shadow_verdict: ShadowVerdict
    shadow_run_state: ShadowRunState
    shadow_blocking_reasons: tuple[str, ...] = ()
    shadow_days_completed: int = Field(default=0, ge=0)
    shadow_required_days: int = Field(default=30, ge=1)
    shadow_report_ready: bool = False
    inter_engine_comparison_ready: bool = False
    build14_contribution_ready: bool = False
    shadow_validated_engines: tuple[str, ...] = ()
    shadow_dormant_components: tuple[str, ...] = ()
    shadow_promotable_engines: tuple[str, ...] = ()
    shadow_shadow_only_engines: tuple[str, ...] = ()
    shadow_rewrite_required_engines: tuple[str, ...] = ()
    shadow_portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()
    shadow_import_artifact_id: str = Field(..., min_length=1)
    shadow_import_lineage_version: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_exported_from: str = ""
    import_lineage_version: str = Field(..., min_length=1)
    import_validation_status: str = Field(..., min_length=1)
    import_source_profile: str = ""
    import_review_state: str = ""
    import_rejection_reasons: tuple[str, ...] = ()
    import_dataset_ref: str = ""
    import_clock_ref: str = ""
    import_activation_stage: str = ""
    import_health_state: str = ""
    import_compatibility_status: str = "not_evaluated"
    import_compatibility_reasons: tuple[str, ...] = ()
    import_feature_lineage_required: bool = False
    import_feature_lineage_present: bool = False
    import_feature_lineage_status: str = "not_required"
    import_feature_lineage_reasons: tuple[str, ...] = ()
    import_transform_whitelist_required: bool = False
    import_transform_whitelist_present: bool = False
    import_transform_whitelist_status: str = "not_required"
    import_transform_whitelist_reasons: tuple[str, ...] = ()
    import_signature_check_status: str = "not_provided"
    import_signature_check_reasons: tuple[str, ...] = ()
    import_conflict_resolution_mode: str = ""
    import_conflict_hard_veto_action: str = ""
    import_conflict_score_aggregation_mode: str = ""
    import_conflict_size_reduce_mode: str = ""
    import_conflict_rank_adjust_mode: str = ""
    import_conflict_additive_soft_boosts_allowed: bool = False
    import_conflict_additive_soft_reduces_allowed: bool = False
    import_registry_atomicity_mode: str = ""
    import_registry_concurrency_model: str = ""
    import_registry_publish_requires_atomic_replace: bool = False
    import_registry_publish_requires_fsync: bool = False
    import_registry_rollback_to_last_known_good: bool = False
    import_payload_ref_count: int = Field(default=5, ge=0)
    import_payload_bundle_present: bool = True
    import_review_export_ref: str = "exports/review.md"
    import_feature_bridge_ref: str = "exports/feature_bridge.json"
    import_parity_diagnostics_ref: str = "exports/parity.json"
    import_replay_metrics_ref: str = "exports/replay_metrics.json"
    import_replay_dtr_ref: str = "exports/replay_dtr.json"
    onboarding_accepted: bool = False
    onboarding_review_state: ReviewState = ReviewState.PENDING
    onboarding_reasons: tuple[str, ...] = ()
    review_export_ready: bool = False
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    regime_lite_governance: RegimeLiteGovernanceSummary = (
        RegimeLiteGovernanceSummary()
    )
    info_stress_governance: InfoStressGovernanceSummary = (
        InfoStressGovernanceSummary()
    )
    observability_ready: bool = False
    halt_ready: bool = False
    operator_safing_request: OperatorSafingRequest | None = None
    active_engines: tuple[str, ...] = ()
    probe_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., gt=0.0)
    requested_pair_notional_usdt: float = Field(..., gt=0.0)
    max_total_notional_usdt: float = Field(..., gt=0.0)
    max_pair_notional_usdt: float = Field(..., gt=0.0)
    order_probe_limit: int = Field(default=3, ge=1, le=10)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    automatic_live_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_governance(self) -> "MicroLiveInput":
        validate_micro_live_governance(
            self,
            accepted_import_statuses=_ACCEPTED_IMPORT_STATUSES,
            expected_import_source_profile=_EXPECTED_IMPORT_SOURCE_PROFILE,
            accepted_import_review_states=_ACCEPTED_IMPORT_REVIEW_STATES,
            accepted_onboarding_review_states=_ACCEPTED_ONBOARDING_REVIEW_STATES,
            rejected_import_compatibility_statuses=_REJECTED_IMPORT_COMPATIBILITY_STATUSES,
            rejected_import_signature_statuses=_REJECTED_IMPORT_SIGNATURE_STATUSES,
            expected_import_conflict_resolution_mode=_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE,
            expected_import_conflict_hard_veto_action=_EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION,
            expected_import_conflict_score_aggregation_mode=_EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE,
            expected_import_conflict_size_reduce_mode=_EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE,
            expected_import_conflict_rank_adjust_mode=_EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE,
            expected_import_registry_atomicity_mode=_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE,
            expected_import_registry_concurrency_model=_EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL,
            micro_live_allowed_engines=_MICRO_LIVE_ALLOWED_ENGINES,
        )
        return self


class MicroLiveDecision(BaseModel, frozen=True):
    """Governed Build-12 verdict for a micro-live candidate."""

    allowed_to_probe: bool
    verdict: MicroLiveVerdict
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    approved_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_pair_notional_usdt: float = Field(default=0.0, ge=0.0)
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True

    @model_validator(mode="after")
    def validate_decision(self) -> "MicroLiveDecision":
        if self.allowed_to_probe and self.verdict != MicroLiveVerdict.ALLOWED_TO_PROBE:
            raise ValueError(
                "allowed_to_probe=True requires verdict=ALLOWED_TO_PROBE"
            )
        if not self.allowed_to_probe and self.verdict == MicroLiveVerdict.ALLOWED_TO_PROBE:
            raise ValueError(
                "verdict=ALLOWED_TO_PROBE requires allowed_to_probe=True"
            )
        return self


class MicroLiveExecutionPlan(BaseModel, frozen=True):
    """Minimal micro-live plan produced by the governed Build-12 gate."""

    plan_id: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    planned_engines: tuple[str, ...] = ()
    planned_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., ge=0.0)
    approved_total_notional_usdt: float = Field(..., ge=0.0)
    approved_pair_notional_usdt: float = Field(..., ge=0.0)
    order_probe_limit: int = Field(..., ge=0)
    dry_run_only: bool = False
    halt_guard_required: bool = True

    @model_validator(mode="after")
    def validate_budgets(self) -> "MicroLiveExecutionPlan":
        if self.approved_total_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError("Approved total notional must stay within the requested budget")
        if self.approved_pair_notional_usdt > self.approved_total_notional_usdt:
            raise ValueError("Approved pair notional must stay within the approved total budget")
        return self


class MicroLiveRunSummary(BaseModel, frozen=True):
    """Deterministic output of the minimal Build-12 Micro-live gate."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: MicroLiveRunState
    shadow_run_id: str = Field(..., min_length=1)
    shadow_verdict: ShadowVerdict
    decision: MicroLiveDecision
    execution_plan: MicroLiveExecutionPlan
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    regime_lite_governance: RegimeLiteGovernanceSummary = (
        RegimeLiteGovernanceSummary()
    )
    info_stress_governance: InfoStressGovernanceSummary = (
        InfoStressGovernanceSummary()
    )
    observability_ready: bool = False
    halt_ready: bool = False
    onboarding_ready: bool = False
    operator_safing_request: OperatorSafingRequest | None = None
    shadow_validated_engines: tuple[str, ...] = ()
    shadow_dormant_components: tuple[str, ...] = ()
    shadow_promotable_engines: tuple[str, ...] = ()
    shadow_shadow_only_engines: tuple[str, ...] = ()
    shadow_rewrite_required_engines: tuple[str, ...] = ()
    shadow_portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()

    @property
    def blocking_reason_count(self) -> int:
        return len(self.decision.blocking_reasons)

    @property
    def planned_pair_count(self) -> int:
        return len(self.execution_plan.planned_pairs)

    @property
    def planned_engine_count(self) -> int:
        return len(self.execution_plan.planned_engines)


class LiveLightInput(BaseModel, frozen=True):
    """Single governed input entering the minimal Build-13 Live-Light gate."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.COMPLETE
    runtime_mode: RuntimeMode = RuntimeMode.LIVE
    micro_live_run_id: str = Field(..., min_length=1)
    shadow_run_id: str = Field(..., min_length=1)
    micro_live_verdict: MicroLiveVerdict
    micro_live_run_state: MicroLiveRunState
    micro_live_blocking_reasons: tuple[str, ...] = ()
    shadow_days_completed: int = Field(..., ge=0)
    shadow_required_days: int = Field(..., ge=1)
    component_verdicts_rendered: bool
    shadow_report_ready: bool
    shadow_promotable_engines: tuple[str, ...] = ()
    shadow_shadow_only_engines: tuple[str, ...] = ()
    shadow_rewrite_required_engines: tuple[str, ...] = ()
    shadow_portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()
    micro_live_planned_engines: tuple[str, ...] = ()
    micro_live_planned_pairs: tuple[str, ...] = ()
    micro_live_stable_days: int = Field(..., ge=0)
    micro_live_required_days: int = Field(..., ge=1)
    build14_live_eligible: bool = False
    micro_live_import_artifact_id: str = Field(..., min_length=1)
    micro_live_import_lineage_version: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_exported_from: str = ""
    import_lineage_version: str = Field(..., min_length=1)
    import_validation_status: str = Field(..., min_length=1)
    import_source_profile: str = ""
    import_review_state: str = ""
    import_rejection_reasons: tuple[str, ...] = ()
    import_dataset_ref: str = ""
    import_clock_ref: str = ""
    import_activation_stage: str = ""
    import_health_state: str = ""
    import_compatibility_status: str = "not_evaluated"
    import_compatibility_reasons: tuple[str, ...] = ()
    import_feature_lineage_required: bool = False
    import_feature_lineage_present: bool = False
    import_feature_lineage_status: str = "not_required"
    import_feature_lineage_reasons: tuple[str, ...] = ()
    import_transform_whitelist_required: bool = False
    import_transform_whitelist_present: bool = False
    import_transform_whitelist_status: str = "not_required"
    import_transform_whitelist_reasons: tuple[str, ...] = ()
    import_signature_check_status: str = "not_provided"
    import_signature_check_reasons: tuple[str, ...] = ()
    import_conflict_resolution_mode: str = ""
    import_conflict_hard_veto_action: str = ""
    import_conflict_score_aggregation_mode: str = ""
    import_conflict_size_reduce_mode: str = ""
    import_conflict_rank_adjust_mode: str = ""
    import_conflict_additive_soft_boosts_allowed: bool = False
    import_conflict_additive_soft_reduces_allowed: bool = False
    import_registry_atomicity_mode: str = ""
    import_registry_concurrency_model: str = ""
    import_registry_publish_requires_atomic_replace: bool = False
    import_registry_publish_requires_fsync: bool = False
    import_registry_rollback_to_last_known_good: bool = False
    import_payload_ref_count: int = Field(default=5, ge=0)
    import_payload_bundle_present: bool = True
    import_review_export_ref: str = "exports/review.md"
    import_feature_bridge_ref: str = "exports/feature_bridge.json"
    import_parity_diagnostics_ref: str = "exports/parity.json"
    import_replay_metrics_ref: str = "exports/replay_metrics.json"
    import_replay_dtr_ref: str = "exports/replay_dtr.json"
    onboarding_accepted: bool = False
    onboarding_review_state: ReviewState = ReviewState.PENDING
    onboarding_reasons: tuple[str, ...] = ()
    review_export_ready: bool = False
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    regime_lite_governance: RegimeLiteGovernanceSummary = (
        RegimeLiteGovernanceSummary()
    )
    info_stress_governance: InfoStressGovernanceSummary = (
        InfoStressGovernanceSummary()
    )
    observability_ready: bool = False
    halt_ready: bool = False
    operator_safing_request: OperatorSafingRequest | None = None
    execution_ready: bool = False
    broker_ready: bool = False
    exchange_ready: bool = False
    active_engines: tuple[str, ...] = ()
    live_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., gt=0.0)
    requested_pair_notional_usdt: float = Field(..., gt=0.0)
    max_total_notional_usdt: float = Field(..., gt=0.0)
    max_pair_notional_usdt: float = Field(..., gt=0.0)
    execution_order_limit: int = Field(default=3, ge=1, le=20)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    automatic_complete_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_governance(self) -> "LiveLightInput":
        validate_live_light_governance(
            self,
            accepted_import_statuses=_ACCEPTED_IMPORT_STATUSES,
            expected_import_source_profile=_EXPECTED_IMPORT_SOURCE_PROFILE,
            accepted_import_review_states=_ACCEPTED_IMPORT_REVIEW_STATES,
            accepted_onboarding_review_states=_ACCEPTED_ONBOARDING_REVIEW_STATES,
            rejected_import_compatibility_statuses=_REJECTED_IMPORT_COMPATIBILITY_STATUSES,
            rejected_import_signature_statuses=_REJECTED_IMPORT_SIGNATURE_STATUSES,
            expected_import_conflict_resolution_mode=_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE,
            expected_import_conflict_hard_veto_action=_EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION,
            expected_import_conflict_score_aggregation_mode=_EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE,
            expected_import_conflict_size_reduce_mode=_EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE,
            expected_import_conflict_rank_adjust_mode=_EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE,
            expected_import_registry_atomicity_mode=_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE,
            expected_import_registry_concurrency_model=_EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL,
            live_light_allowed_engines=_LIVE_LIGHT_ALLOWED_ENGINES,
        )
        return self


class LiveLightDecision(BaseModel, frozen=True):
    """Governed Build-13 verdict for a Live-Light candidate."""

    allowed_to_execute_small: bool
    verdict: LiveLightVerdict
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    approved_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_pair_notional_usdt: float = Field(default=0.0, ge=0.0)
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True

    @model_validator(mode="after")
    def validate_decision(self) -> "LiveLightDecision":
        if (
            self.allowed_to_execute_small
            and self.verdict != LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
        ):
            raise ValueError(
                "allowed_to_execute_small=True requires verdict=ALLOWED_TO_EXECUTE_SMALL"
            )
        if (
            not self.allowed_to_execute_small
            and self.verdict == LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
        ):
            raise ValueError(
                "verdict=ALLOWED_TO_EXECUTE_SMALL requires allowed_to_execute_small=True"
            )
        return self


class LiveLightExecutionIntent(BaseModel, frozen=True):
    """Minimal Live-Light execution intent produced by the governed Build-13 gate."""

    intent_id: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    planned_engines: tuple[str, ...] = ()
    planned_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., ge=0.0)
    approved_total_notional_usdt: float = Field(..., ge=0.0)
    approved_pair_notional_usdt: float = Field(..., ge=0.0)
    execution_order_limit: int = Field(..., ge=0)
    dry_run_only: bool = False
    halt_guard_required: bool = True
    broker_ready_required: bool = True
    exchange_ready_required: bool = True

    @model_validator(mode="after")
    def validate_budgets(self) -> "LiveLightExecutionIntent":
        if self.approved_total_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError("Approved total notional must stay within the requested cap")
        if self.approved_pair_notional_usdt > self.approved_total_notional_usdt:
            raise ValueError("Approved pair notional must stay within the approved total cap")
        return self


class LiveLightGateGroupSummary(BaseModel, frozen=True):
    """Audit-friendly status projection for the canonical Live-Light gate groups."""

    gate_id: Literal[
        "governance_envelope",
        "promotion_history",
        "import_replay_integrity",
        "operational_readiness",
        "build14_influence",
    ]
    status: Literal["passed", "blocked", "review_only"] = "passed"
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_status_consistency(self) -> "LiveLightGateGroupSummary":
        if self.status == "passed" and self.reasons:
            raise ValueError("Passed gate groups must not carry reasons")
        if self.status != "passed" and not self.reasons:
            raise ValueError("Blocked or review_only gate groups must carry reasons")
        return self


class LiveLightRunSummary(BaseModel, frozen=True):
    """Deterministic output of the minimal Build-13 Live-Light gate."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: LiveLightRunState
    micro_live_run_id: str = Field(..., min_length=1)
    shadow_run_id: str = Field(..., min_length=1)
    micro_live_verdict: MicroLiveVerdict
    decision: LiveLightDecision
    execution_intent: LiveLightExecutionIntent
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    regime_lite_governance: RegimeLiteGovernanceSummary = (
        RegimeLiteGovernanceSummary()
    )
    info_stress_governance: InfoStressGovernanceSummary = (
        InfoStressGovernanceSummary()
    )
    observability_ready: bool = False
    halt_ready: bool = False
    operator_safing_request: OperatorSafingRequest | None = None
    execution_ready: bool = False
    broker_ready: bool = False
    exchange_ready: bool = False
    onboarding_ready: bool = False
    build14_influence_mode: str = "read_only"
    build14_action: str = "observe"
    build14_severity: str = "nominal"
    build14_summary: str = ""
    build14_reason_codes: tuple[str, ...] = ()
    build14_confidence_penalty_weight: float = Field(default=0.0, ge=0.0, le=0.25)
    build14_recommended_budget_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    build14_live_eligible: bool = False
    shadow_portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()
    gate_groups: tuple[LiveLightGateGroupSummary, ...] = ()

    @property
    def blocking_reason_count(self) -> int:
        return len(self.decision.blocking_reasons)

    @property
    def planned_pair_count(self) -> int:
        return len(self.execution_intent.planned_pairs)

    @property
    def planned_engine_count(self) -> int:
        return len(self.execution_intent.planned_engines)

__all__ = [
    "LiveLightGateGroupSummary",
    "LiveLightDecision",
    "LiveLightExecutionIntent",
    "LiveLightInput",
    "LiveLightRunSummary",
    "MicroLiveDecision",
    "MicroLiveExecutionPlan",
    "MicroLiveInput",
    "MicroLiveRunSummary",
]
