"""Governed contracts for the minimal real Build-11/12/13 runtimes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    ALL_PAIRS,
    OperatorSafingAction,
    OperatorSafingRequest,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
)
from protocols.enums import (
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)


_ACCEPTED_IMPORT_STATUSES = frozenset({"accepted"})
_ACCEPTED_IMPORT_REVIEW_STATES = frozenset({"pending", "approved"})
_EXPECTED_IMPORT_SOURCE_PROFILE = ProfileId.COMPLETE.value
_ACCEPTED_ONBOARDING_REVIEW_STATES = frozenset(
    {ReviewState.PENDING, ReviewState.APPROVED}
)
_REJECTED_IMPORT_COMPATIBILITY_STATUSES = frozenset({"rejected"})
_REJECTED_IMPORT_SIGNATURE_STATUSES = frozenset(
    {
        "signature_invalid",
        "trust_store_unavailable",
        "key_id_unknown",
        "key_revoked",
        "payload_hash_mismatch",
    }
)
_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE = "no_trade_then_strictest"
_EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION = "no_trade"
_EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE = "bounded_sum_with_global_cap"
_EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE = "min_factor_wins"
_EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE = "bounded_sum"
_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE = "atomic_snapshot_swap"
_EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL = "single_writer_multi_reader"
_REQUIRED_SHADOW_ENGINE_IDS = frozenset(
    {"engine_a", "engine_b", "engine_c", "engine_d"}
)
_REQUIRED_SHADOW_BUILD14_COMPONENT_IDS = frozenset(
    {
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    }
)
_KNOWN_SHADOW_BUILD14_READER_IDS = frozenset(
    {
        "market_toxicity_snapshot",
        "execution_fragility_score",
        "lob_deep_filter_vwa",
        "order_book_imbalance",
        "false_breakout_model",
        "hurst_regime_classifier",
        "competition_monitor",
    }
)
_MICRO_LIVE_ALLOWED_ENGINES = _REQUIRED_SHADOW_ENGINE_IDS
_LIVE_LIGHT_ALLOWED_ENGINES = _REQUIRED_SHADOW_ENGINE_IDS
ShadowEngineJudgmentVerdict = Literal[
    "promotable",
    "shadow-only",
    "rewrite-required",
    "dormant",
]
ShadowPortfolioJudgmentVerdict = Literal[
    "promotable",
    "shadow-only",
    "rewrite-required",
]
ShadowPressureLevel = Literal["nominal", "elevated", "critical"]


class ShadowTruthSet(BaseModel, frozen=True):
    """Baseline truth set used by Shadow for candidate comparison."""

    truth_ref: str = Field(..., min_length=1)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    ce_net: float = 0.0
    active_alert_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)


class ShadowRuntimeEvidence(BaseModel, frozen=True):
    """Typed Build-11 runtime evidence combined from replay and shadow execution."""

    data_source: Literal["unknown", "live_websocket", "recorded_replay"] = "unknown"
    feature_bridge_ready: bool = False
    parity_diagnostics_ready: bool = False
    replay_metrics_ready: bool = False
    replay_dtr_ready: bool = False
    event_loop_ready: bool = False
    config_loaded: bool = False
    shadow_dtr_persisted: bool = False
    continuous_hours: float = Field(default=0.0, ge=0.0)
    evidence_summary: str = "No real runtime evidence recorded"


class ShadowValidationSet(BaseModel, frozen=True):
    """Candidate validation set measured in Shadow conditions."""

    validation_ref: str = Field(..., min_length=1)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    ce_net: float = 0.0
    active_alert_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)
    accepted_import: bool = False
    import_validation_status: str = Field(..., min_length=1)
    import_artifact_id: str = ""
    import_exported_from: str = ""
    import_lineage_version: str = ""
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
    runtime_data_source: Literal["unknown", "live_websocket", "recorded_replay"] = "unknown"
    runtime_feature_bridge_ready: bool = False
    runtime_parity_diagnostics_ready: bool = False
    runtime_replay_metrics_ready: bool = False
    runtime_replay_dtr_ready: bool = False
    runtime_event_loop_ready: bool = False
    runtime_config_loaded: bool = False
    runtime_shadow_dtr_persisted: bool = False
    runtime_continuous_hours: float = Field(default=0.0, ge=0.0)
    runtime_evidence_summary: str = "No real runtime evidence recorded"
    build9x_diagnostics_count: int = Field(default=0, ge=0)
    open_hypotheses: int = Field(default=0, ge=0)
    replay_candidate_count: int = Field(default=0, ge=0)
    review_export_ready: bool = False
    active_engines: tuple[str, ...] = ()
    build14_status: str = "planned"
    shadow_days_completed: int = Field(default=0, ge=0)
    shadow_required_days: int = Field(default=30, ge=1)
    shadow_report_ready: bool = False
    inter_engine_comparison_ready: bool = False
    build14_contribution_ready: bool = False
    component_assessments: tuple["ShadowComponentAssessment", ...] = ()

    @model_validator(mode="after")
    def validate_import_consistency(self) -> "ShadowValidationSet":
        normalized_status = self.import_validation_status.strip().casefold()

        if self.accepted_import:
            if normalized_status not in _ACCEPTED_IMPORT_STATUSES:
                raise ValueError(
                    "accepted_import=True requires an acceptance import_validation_status"
                )
            if self.import_rejection_reasons:
                raise ValueError(
                    "accepted_import=True requires empty import_rejection_reasons"
                )

        if normalized_status in _ACCEPTED_IMPORT_STATUSES and not self.accepted_import:
            raise ValueError(
                "accepted import_validation_status requires accepted_import=True"
            )
        if (
            self.accepted_import
            and self.import_exported_from != "local"
        ):
            raise ValueError(
                "accepted_import=True requires import_exported_from=local"
            )
        if (
            self.accepted_import
            and self.import_source_profile != _EXPECTED_IMPORT_SOURCE_PROFILE
        ):
            raise ValueError(
                "accepted_import=True requires import_source_profile=complete"
            )
        if (
            self.accepted_import
            and self.import_review_state not in _ACCEPTED_IMPORT_REVIEW_STATES
        ):
            raise ValueError(
                "accepted_import=True requires import_review_state to stay pending or approved"
            )
        if self.accepted_import and not self.import_dataset_ref:
            raise ValueError(
                "accepted_import=True requires import_dataset_ref"
            )
        if self.accepted_import and not self.import_clock_ref:
            raise ValueError(
                "accepted_import=True requires import_clock_ref"
            )
        if (
            self.accepted_import
            and self.import_compatibility_status in _REJECTED_IMPORT_COMPATIBILITY_STATUSES
        ):
            raise ValueError(
                "accepted_import=True requires a non-rejected import_compatibility_status"
            )
        if self.accepted_import and not self.import_feature_lineage_required:
            raise ValueError(
                "accepted_import=True requires import_feature_lineage_required=True"
            )
        if self.accepted_import and not self.import_feature_lineage_present:
            raise ValueError(
                "accepted_import=True requires import_feature_lineage_present=True"
            )
        if self.accepted_import and self.import_feature_lineage_status != "ok":
            raise ValueError(
                "accepted_import=True requires import_feature_lineage_status=ok"
            )
        if self.accepted_import and not self.import_transform_whitelist_required:
            raise ValueError(
                "accepted_import=True requires import_transform_whitelist_required=True"
            )
        if self.accepted_import and not self.import_transform_whitelist_present:
            raise ValueError(
                "accepted_import=True requires import_transform_whitelist_present=True"
            )
        if self.accepted_import and self.import_transform_whitelist_status != "ok":
            raise ValueError(
                "accepted_import=True requires import_transform_whitelist_status=ok"
            )
        if (
            self.accepted_import
            and self.import_signature_check_status in _REJECTED_IMPORT_SIGNATURE_STATUSES
        ):
            raise ValueError(
                "accepted_import=True requires a non-rejected import_signature_check_status"
            )
        if self.accepted_import and self.import_activation_stage != "shadow_ready":
            raise ValueError(
                "accepted_import=True requires import_activation_stage=shadow_ready"
            )
        if self.accepted_import and self.import_health_state != "active":
            raise ValueError(
                "accepted_import=True requires import_health_state=active"
            )
        if (
            self.accepted_import
            and self.import_conflict_resolution_mode
            != _EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_conflict_resolution_mode"
            )
        if (
            self.accepted_import
            and self.import_conflict_hard_veto_action
            != _EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_conflict_hard_veto_action"
            )
        if (
            self.accepted_import
            and self.import_conflict_score_aggregation_mode
            != _EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_conflict_score_aggregation_mode"
            )
        if (
            self.accepted_import
            and self.import_conflict_size_reduce_mode
            != _EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_conflict_size_reduce_mode"
            )
        if (
            self.accepted_import
            and self.import_conflict_rank_adjust_mode
            != _EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_conflict_rank_adjust_mode"
            )
        if self.accepted_import and not self.import_conflict_additive_soft_boosts_allowed:
            raise ValueError(
                "accepted_import=True requires import_conflict_additive_soft_boosts_allowed=True"
            )
        if self.accepted_import and not self.import_conflict_additive_soft_reduces_allowed:
            raise ValueError(
                "accepted_import=True requires import_conflict_additive_soft_reduces_allowed=True"
            )
        if (
            self.accepted_import
            and self.import_registry_atomicity_mode
            != _EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_registry_atomicity_mode"
            )
        if (
            self.accepted_import
            and self.import_registry_concurrency_model
            != _EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL
        ):
            raise ValueError(
                "accepted_import=True requires canonical import_registry_concurrency_model"
            )
        if self.accepted_import and not self.import_registry_publish_requires_atomic_replace:
            raise ValueError(
                "accepted_import=True requires import_registry_publish_requires_atomic_replace=True"
            )
        if self.accepted_import and not self.import_registry_publish_requires_fsync:
            raise ValueError(
                "accepted_import=True requires import_registry_publish_requires_fsync=True"
            )
        if self.accepted_import and not self.import_registry_rollback_to_last_known_good:
            raise ValueError(
                "accepted_import=True requires import_registry_rollback_to_last_known_good=True"
            )
        if self.accepted_import and self.import_payload_ref_count < 5:
            raise ValueError(
                "accepted_import=True requires import_payload_ref_count>=5"
            )
        if self.accepted_import and not self.import_payload_bundle_present:
            raise ValueError(
                "accepted_import=True requires import_payload_bundle_present=True"
            )
        if self.accepted_import and not self.import_review_export_ref:
            raise ValueError(
                "accepted_import=True requires import_review_export_ref"
            )
        if self.accepted_import and not self.import_feature_bridge_ref:
            raise ValueError(
                "accepted_import=True requires import_feature_bridge_ref"
            )
        if self.accepted_import and not self.import_parity_diagnostics_ref:
            raise ValueError(
                "accepted_import=True requires import_parity_diagnostics_ref"
            )
        if self.accepted_import and not self.import_replay_metrics_ref:
            raise ValueError(
                "accepted_import=True requires import_replay_metrics_ref"
            )
        if self.accepted_import and not self.import_replay_dtr_ref:
            raise ValueError(
                "accepted_import=True requires import_replay_dtr_ref"
            )

        if self.shadow_required_days != 30:
            raise ValueError("Build-11 Shadow requires shadow_required_days=30")

        if len(self.active_engines) != len(set(self.active_engines)):
            raise ValueError("Build-11 Shadow active_engines must be unique")

        component_ids = tuple(
            assessment.component_id for assessment in self.component_assessments
        )
        if len(component_ids) != len(set(component_ids)):
            raise ValueError(
                "Build-11 Shadow component assessments must be unique per component"
            )

        return self


class ShadowComponentAssessment(BaseModel, frozen=True):
    """Per-component Shadow activation + verdict evidence for Build-11."""

    component_id: str = Field(..., min_length=1)
    component_kind: ShadowComponentKind
    hard_state: ShadowComponentHardState = ShadowComponentHardState.SHADOW_ENABLED
    verdict: ShadowComponentVerdict
    evidence_summary: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_component_identity(self) -> "ShadowComponentAssessment":
        if self.component_kind == ShadowComponentKind.ENGINE:
            if self.component_id not in _REQUIRED_SHADOW_ENGINE_IDS:
                raise ValueError("Build-11 Shadow engine assessment is out of scope")
        elif self.component_id not in _REQUIRED_SHADOW_BUILD14_COMPONENT_IDS:
            raise ValueError(
                "Build-11 Shadow Build-14 assessment is out of scope"
            )
        return self


class ShadowInput(BaseModel, frozen=True):
    """Single governed input entering the Build-11 Shadow runtime."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.COMPLETE
    runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    truth_set: ShadowTruthSet
    validation_set: ShadowValidationSet
    max_allowed_dtr_coverage_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_allowed_cra_increase: float = Field(default=0.10, ge=0.0, le=1.0)
    max_allowed_break_even_drift_scope_increase: int = Field(default=0, ge=0)
    max_allowed_edge_degraded_delta: int = Field(default=0, ge=0)
    max_allowed_ce_net_drop: float = Field(default=0.0005, ge=0.0)
    max_allowed_alert_count_increase: int = Field(default=1, ge=0)
    max_allowed_queue_backlog_increase: int = Field(default=25, ge=0)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    automatic_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_governance(self) -> "ShadowInput":
        if self.profile != ProfileId.COMPLETE:
            raise ValueError("Build-11 Shadow opens in COMPLETE profile only")
        if self.runtime_mode != RuntimeMode.SHADOW:
            raise ValueError("Build-11 Shadow requires runtime_mode=SHADOW")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.automatic_promotion_requested:
            raise ValueError("Shadow must not request automatic promotion")
        return self


class ShadowComparison(BaseModel, frozen=True):
    """Single baseline-vs-candidate Shadow comparison."""

    comparison_id: str = Field(..., min_length=1)
    metric_name: str = Field(..., min_length=1)
    baseline_value: float
    candidate_value: float
    delta: float = Field(..., ge=0.0)
    threshold: float = Field(..., ge=0.0)
    status: ShadowComparisonStatus
    severity: ShadowDivergenceSeverity
    blocking: bool = False
    summary: str = Field(..., min_length=1)


class ShadowDecision(BaseModel, frozen=True):
    """Governed Shadow verdict for a candidate."""

    accepted: bool
    verdict: ShadowVerdict
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True


class RegimeLiteGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit regime_lite governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
        "recommendation_only",
        "ready",
    ] = "not_configured"
    state: str = "not_configured"
    candidate_state: str = "not_configured"
    state_changed: bool = False
    entries_blocked: bool = False
    sudden_event: bool = False
    safing_severity: str = "not_configured"
    should_block_new_entries: bool = False
    should_exit_all: bool = False
    recommended_operator_action: str = ""
    operator_safing_request_action: str = ""
    operator_safing_request_source_runtime_mode: str = ""
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class InfoStressGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit info_stress governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
    ] = "not_configured"
    level: str = "not_configured"
    alert_count: int = Field(default=0, ge=0)
    entries_blocked: bool = False
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class DailyPnlBreakerGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit daily PnL breaker governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
    ] = "not_configured"
    verdict: str = "not_configured"
    should_force_shadow: bool = False
    circuit_breaker_tripped: bool = False
    circuit_breaker_reason: str = ""
    drawdown_pct: float = Field(default=0.0, ge=0.0)
    threshold_pct: float = Field(default=0.0, ge=0.0)
    shadow_locked_session_date: str = ""
    state_corrupted: bool = False
    state_last_reason: str = ""
    detail: str = ""
    reason_codes: tuple[str, ...] = ()


class ShadowRunSummary(BaseModel, frozen=True):
    """Deterministic output of the minimal Build-11 Shadow runtime."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: ShadowRunState
    truth_set_ref: str = Field(..., min_length=1)
    validation_set_ref: str = Field(..., min_length=1)
    comparisons: tuple[ShadowComparison, ...] = ()
    decision: ShadowDecision
    import_artifact_id: str = ""
    import_lineage_version: str = ""
    runtime_data_source: Literal["unknown", "live_websocket", "recorded_replay"] = "unknown"
    runtime_feature_bridge_ready: bool = False
    runtime_parity_diagnostics_ready: bool = False
    runtime_replay_metrics_ready: bool = False
    runtime_replay_dtr_ready: bool = False
    runtime_event_loop_ready: bool = False
    runtime_config_loaded: bool = False
    runtime_shadow_dtr_persisted: bool = False
    runtime_continuous_hours: float = Field(default=0.0, ge=0.0)
    runtime_evidence_ready: bool = False
    runtime_evidence_summary: str = "No real runtime evidence recorded"
    build9x_diagnostics_count: int = Field(default=0, ge=0)
    open_hypotheses: int = Field(default=0, ge=0)
    replay_candidate_count: int = Field(default=0, ge=0)
    review_export_ready: bool = False
    active_engines: tuple[str, ...] = ()
    build14_status: str = "planned"
    shadow_days_completed: int = Field(default=0, ge=0)
    shadow_required_days: int = Field(default=30, ge=1)
    shadow_report_ready: bool = False
    inter_engine_comparison_ready: bool = False
    build14_contribution_ready: bool = False
    component_assessments: tuple[ShadowComponentAssessment, ...] = ()
    regime_lite_governance: RegimeLiteGovernanceSummary = (
        RegimeLiteGovernanceSummary()
    )
    info_stress_governance: InfoStressGovernanceSummary = (
        InfoStressGovernanceSummary()
    )
    daily_pnl_breaker_governance: DailyPnlBreakerGovernanceSummary = (
        DailyPnlBreakerGovernanceSummary()
    )

    @property
    def blocking_comparison_count(self) -> int:
        return sum(1 for comparison in self.comparisons if comparison.blocking)

    @property
    def divergent_comparison_count(self) -> int:
        return sum(
            1
            for comparison in self.comparisons
            if comparison.status == ShadowComparisonStatus.DIVERGENT
        )

    @property
    def shadow_validated_component_count(self) -> int:
        return sum(
            1
            for assessment in self.component_assessments
            if assessment.verdict == ShadowComponentVerdict.SHADOW_VALIDATED
        )

    @property
    def dormant_component_count(self) -> int:
        return sum(
            1
            for assessment in self.component_assessments
            if assessment.verdict == ShadowComponentVerdict.DORMANT
        )

    @property
    def build14_component_count(self) -> int:
        return sum(
            1
            for assessment in self.component_assessments
            if assessment.component_kind == ShadowComponentKind.BUILD14_ENABLER
        )

    @property
    def remaining_shadow_days(self) -> int:
        return max(0, self.shadow_required_days - self.shadow_days_completed)


class ShadowEngineReport(BaseModel, frozen=True):
    """Aggregated per-engine evidence rendered by the Build-11 shadow report."""

    engine_id: str = Field(..., min_length=1)
    gross_frequency: float = Field(..., ge=0.0)
    useful_frequency: float = Field(..., ge=0.0)
    estimated_cost_bps: float = Field(..., ge=0.0)
    edge_net: float
    economic_pass_rate: float = Field(..., ge=0.0, le=1.0)
    conflict_rate: float = Field(..., ge=0.0, le=1.0)
    marginal_edge: float = 0.0
    observations: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_engine_scope(self) -> "ShadowEngineReport":
        if self.engine_id not in _REQUIRED_SHADOW_ENGINE_IDS:
            raise ValueError("Build-11 shadow report engine is out of canonical scope")
        if self.useful_frequency > self.gross_frequency:
            raise ValueError(
                "Build-11 shadow report useful_frequency must stay within gross_frequency"
            )
        return self


class ShadowBuild14Contribution(BaseModel, frozen=True):
    """Aggregated Build-14 evidence rendered by the Build-11 shadow report."""

    component_id: str = Field(..., min_length=1)
    contribution_score: float
    interaction_score: float = 0.0
    observations: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_component_scope(self) -> "ShadowBuild14Contribution":
        if self.component_id not in _REQUIRED_SHADOW_BUILD14_COMPONENT_IDS:
            raise ValueError(
                "Build-11 shadow report Build-14 contribution is out of canonical scope"
        )
        return self


class ShadowBuild14ReaderContribution(BaseModel, frozen=True):
    """Optional reader-level Build-14 evidence rendered by the Build-11 shadow report."""

    reader_name: str = Field(..., min_length=1)
    signal_family: str = Field(..., min_length=1)
    average_observed_value: float = Field(..., ge=0.0)
    average_severity_score: float = Field(..., ge=0.0, le=1.0)
    latest_status: Literal["nominal", "elevated", "critical"]
    latest_detail: str = ""
    structured_log_key: str = ""
    observations: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_reader_scope(self) -> "ShadowBuild14ReaderContribution":
        if self.reader_name not in _KNOWN_SHADOW_BUILD14_READER_IDS:
            raise ValueError(
                "Build-11 shadow report Build-14 reader contribution is out of canonical scope"
            )
        return self


class ShadowReportSection(BaseModel, frozen=True):
    """Audit-ready section rendered inside the final Build-11 shadow report."""

    section_id: Literal[
        "data_infra_report",
        "decisions_dtr_report",
        "costs_break_even_report",
        "engine_comparison_report",
        "portfolio_report",
        "ui_alerting_report",
        "go_no_go_report",
    ]
    title: str = Field(..., min_length=1)
    ready: bool = False
    summary: str = Field(..., min_length=1)


class ShadowReportArtifact(BaseModel, frozen=True):
    """Persisted Build-11 shadow report required before promotion."""

    report_id: str = Field(..., min_length=1)
    report_version: str = "build11.shadow.v1"
    profile: str = Field(..., min_length=1)
    report_generated_at: float
    consecutive_days: int = Field(..., ge=0)
    required_days: int = Field(default=30, ge=1)
    remaining_days: int = Field(..., ge=0)
    is_complete: bool = False
    started_at: float | None = None
    last_shadow_timestamp: float | None = None
    total_resets: int = Field(default=0, ge=0)
    daily_records_count: int = Field(default=0, ge=0)
    dtr_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    dtr_complete: bool = False
    ce_net: float | None = None
    estimated_cost_bps: float | None = Field(default=None, ge=0.0)
    edge_net: float | None = None
    drawdown_pct: float | None = None
    stale_rate: float | None = Field(default=None, ge=0.0)
    economic_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    pair_health_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    backlog_avg: float | None = Field(default=None, ge=0.0)
    capital_simulated_usdt: float | None = Field(default=None, ge=0.0)
    gross_exposure_shadow_pct: float | None = Field(default=None, ge=0.0)
    loss_budget_shadow_pct: float | None = Field(default=None, ge=0.0)
    capital_free_usdt: float | None = None
    beta_btc_shadow: float | None = None
    dominant_cluster: str = ""
    pnl_shadow: float | None = None
    dtr_loss_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    log_loss_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    event_latency_ms: float | None = Field(default=None, ge=0.0)
    hard_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    phantom_trade_count: int | None = Field(default=None, ge=0)
    decisions_reproducible: bool = False
    infra_stable: bool = False
    costs_plausible: bool = False
    break_even_visible: bool = False
    critical_alerts_visible: bool = False
    operator_actions_logged: bool = False
    ui_locked: bool = False
    shadow_report_ready: bool = False
    data_infra_report_ready: bool = False
    decisions_dtr_report_ready: bool = False
    costs_break_even_report_ready: bool = False
    inter_engine_comparison_ready: bool = False
    build14_contribution_ready: bool = False
    portfolio_report_ready: bool = False
    ui_alerting_report_ready: bool = False
    go_no_go_report_ready: bool = False
    inter_engine_comparison: tuple[ShadowEngineReport, ...] = ()
    build14_contribution: tuple[ShadowBuild14Contribution, ...] = ()
    build14_reader_contribution: tuple[ShadowBuild14ReaderContribution, ...] = ()
    rendered_sections: tuple[ShadowReportSection, ...] = ()
    missing_sections: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_report(self) -> "ShadowReportArtifact":
        if self.required_days != 30:
            raise ValueError("Build-11 shadow report requires required_days=30")
        if self.remaining_days != max(0, self.required_days - self.consecutive_days):
            raise ValueError(
                "Build-11 shadow report remaining_days must reflect the 30-day counter"
            )

        engine_ids = tuple(
            entry.engine_id for entry in self.inter_engine_comparison
        )
        if len(engine_ids) != len(set(engine_ids)):
            raise ValueError(
                "Build-11 shadow report inter_engine_comparison must stay unique per engine"
            )
        build14_ids = tuple(
            entry.component_id for entry in self.build14_contribution
        )
        if len(build14_ids) != len(set(build14_ids)):
            raise ValueError(
                "Build-11 shadow report build14_contribution must stay unique per component"
            )
        build14_reader_ids = tuple(
            entry.reader_name for entry in self.build14_reader_contribution
        )
        if len(build14_reader_ids) != len(set(build14_reader_ids)):
            raise ValueError(
                "Build-11 shadow report build14_reader_contribution must stay unique per reader"
            )
        section_ids = tuple(section.section_id for section in self.rendered_sections)
        if len(section_ids) != len(set(section_ids)):
            raise ValueError(
                "Build-11 shadow report rendered_sections must stay unique per section"
            )

        if self.inter_engine_comparison_ready and set(engine_ids) != _REQUIRED_SHADOW_ENGINE_IDS:
            raise ValueError(
                "Build-11 shadow report inter_engine_comparison_ready=True requires A/B/C/D evidence"
            )
        if (
            self.build14_contribution_ready
            and set(build14_ids) != _REQUIRED_SHADOW_BUILD14_COMPONENT_IDS
        ):
            raise ValueError(
                "Build-11 shadow report build14_contribution_ready=True requires all Build-14 enablers"
            )

        if self.shadow_report_ready:
            missing: list[str] = []
            for field_name in (
                "dtr_coverage",
                "ce_net",
                "estimated_cost_bps",
                "edge_net",
                "drawdown_pct",
                "stale_rate",
                "economic_pass_rate",
                "pair_health_ratio",
                "backlog_avg",
                "capital_simulated_usdt",
                "gross_exposure_shadow_pct",
                "loss_budget_shadow_pct",
                "capital_free_usdt",
                "beta_btc_shadow",
                "pnl_shadow",
                "dtr_loss_rate",
                "log_loss_rate",
                "event_latency_ms",
                "hard_block_rate",
                "phantom_trade_count",
            ):
                if getattr(self, field_name) is None:
                    missing.append(field_name)
            if not self.dominant_cluster:
                missing.append("dominant_cluster")
            if not self.is_complete:
                missing.append("30_day_counter")
            if not self.dtr_complete:
                missing.append("dtr_complete")
            if not self.decisions_reproducible:
                missing.append("decisions_reproducible")
            if not self.infra_stable:
                missing.append("infra_stable")
            if not self.costs_plausible:
                missing.append("costs_plausible")
            if not self.break_even_visible:
                missing.append("break_even_visible")
            if not self.critical_alerts_visible:
                missing.append("critical_alerts_visible")
            if not self.operator_actions_logged:
                missing.append("operator_actions_logged")
            if not self.ui_locked:
                missing.append("ui_locked")
            if not self.data_infra_report_ready:
                missing.append("data_infra_report")
            if not self.decisions_dtr_report_ready:
                missing.append("decisions_dtr_report")
            if not self.costs_break_even_report_ready:
                missing.append("costs_break_even_report")
            if not self.inter_engine_comparison_ready:
                missing.append("inter_engine_comparison")
            if not self.build14_contribution_ready:
                missing.append("build14_contribution")
            if not self.portfolio_report_ready:
                missing.append("portfolio_report")
            if not self.ui_alerting_report_ready:
                missing.append("ui_alerting_report")
            if not self.go_no_go_report_ready:
                missing.append("go_no_go_report")
            if missing:
                raise ValueError(
                    "Build-11 shadow report cannot be ready while required sections are missing: "
                    + ", ".join(missing)
                )

        return self


class ShadowEngineJudgment(BaseModel, frozen=True):
    """Engine-by-engine supervised judgment derived from the Build-11 shadow report."""

    engine_id: str = Field(..., min_length=1)
    component_verdict: str = Field(..., min_length=1)
    judgment_verdict: ShadowEngineJudgmentVerdict
    useful_frequency: float = Field(default=0.0, ge=0.0)
    ce_expected: float | None = None
    estimated_cost_bps: float = Field(default=0.0, ge=0.0)
    edge_net: float = 0.0
    economic_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    marginal_edge: float = 0.0
    redundancy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    portfolio_contribution: float = 0.0
    final_size_multiplier: float | None = None
    selection_outcome_code: str = ""
    portfolio_verdict_code: str = ""
    phantom_trade: bool = False
    hard_blocked: bool = False
    risk_decision_severity: str = ""
    physics_pressure_state: ShadowPressureLevel = "nominal"
    fragility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    toxicity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    execution_survivability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    micro_friction_score: float | None = Field(default=None, ge=0.0, le=1.0)
    observations: int = Field(default=0, ge=0)
    rationale: str = ""
    evidence_summary: str = ""


class ShadowPortfolioJudgment(BaseModel, frozen=True):
    """Portfolio-level supervised judgment derived from the governed Shadow payload."""

    judgment_verdict: ShadowPortfolioJudgmentVerdict = "shadow-only"
    physics_pressure: ShadowPressureLevel = "nominal"
    redundancy_pressure: ShadowPressureLevel = "nominal"
    cluster_pressure: ShadowPressureLevel = "nominal"
    beta_pressure: ShadowPressureLevel = "nominal"
    gross_capacity_pressure: ShadowPressureLevel = "nominal"
    loss_capacity_pressure: ShadowPressureLevel = "nominal"
    dominant_cluster: str = ""
    beta_utilization: float | None = Field(default=None, ge=0.0)
    gross_capacity_used_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    loss_capacity_used_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    hard_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    phantom_trade_count: int | None = Field(default=None, ge=0)
    promotable_engine_count: int = Field(default=0, ge=0)
    shadow_only_engine_count: int = Field(default=0, ge=0)
    rewrite_required_engine_count: int = Field(default=0, ge=0)
    dormant_engine_count: int = Field(default=0, ge=0)
    elevated_physics_engine_count: int = Field(default=0, ge=0)
    critical_physics_engine_count: int = Field(default=0, ge=0)
    portfolio_rejected_engine_count: int = Field(default=0, ge=0)
    ranking_rejected_engine_count: int = Field(default=0, ge=0)
    cluster_rejected_engine_count: int = Field(default=0, ge=0)
    beta_rejected_engine_count: int = Field(default=0, ge=0)
    exposure_rejected_engine_count: int = Field(default=0, ge=0)
    loss_budget_rejected_engine_count: int = Field(default=0, ge=0)
    rationale: str = ""


class ShadowEngineJudgmentSummary(BaseModel, frozen=True):
    """Normalized judgment bundle used to decide engine promotion readiness after Shadow."""

    source_report_id: str = ""
    source_shadow_run_id: str = ""
    source_shadow_days_completed: int = Field(default=0, ge=0)
    source_shadow_required_days: int = Field(default=30, ge=1)
    portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()
    judgments: tuple[ShadowEngineJudgment, ...] = ()


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
        if self.profile != ProfileId.COMPLETE:
            raise ValueError("Build-12 Micro-live opens in COMPLETE profile only")
        if self.runtime_mode != RuntimeMode.MICRO_LIVE:
            raise ValueError("Build-12 Micro-live requires runtime_mode=MICRO_LIVE")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.automatic_live_promotion_requested:
            raise ValueError("Micro-live must not request automatic promotion to LIVE")
        if (
            self.operator_safing_request is not None
            and self.operator_safing_request.source_runtime_mode != self.runtime_mode
        ):
            raise ValueError(
                "Build-12 Micro-live operator_safing_request must match source_runtime_mode=MICRO_LIVE"
            )
        if self.shadow_required_days != 30:
            raise ValueError("Build-12 Micro-live requires shadow_required_days=30")
        if self.shadow_days_completed < self.shadow_required_days:
            raise ValueError(
                "Build-12 Micro-live requires a completed 30-day Shadow"
            )
        if not self.shadow_report_ready:
            raise ValueError(
                "Build-12 Micro-live requires shadow_report_ready=True"
            )
        if not self.inter_engine_comparison_ready:
            raise ValueError(
                "Build-12 Micro-live requires inter_engine_comparison_ready=True"
            )
        if not self.build14_contribution_ready:
            raise ValueError(
                "Build-12 Micro-live requires build14_contribution_ready=True"
            )

        normalized_status = self.import_validation_status.strip().casefold()
        if normalized_status not in _ACCEPTED_IMPORT_STATUSES:
            raise ValueError(
                "Build-12 Micro-live requires an accepted import_validation_status"
            )
        if self.import_exported_from != "local":
            raise ValueError(
                "Build-12 Micro-live requires import_exported_from=local"
            )
        if self.import_source_profile != _EXPECTED_IMPORT_SOURCE_PROFILE:
            raise ValueError(
                "Build-12 Micro-live requires import_source_profile=complete"
            )
        if self.import_rejection_reasons:
            raise ValueError(
                "Build-12 Micro-live requires empty import_rejection_reasons"
            )
        if self.import_review_state not in _ACCEPTED_IMPORT_REVIEW_STATES:
            raise ValueError(
                "Build-12 Micro-live requires import_review_state to stay pending or approved"
            )
        if not self.import_dataset_ref:
            raise ValueError("Build-12 Micro-live requires import_dataset_ref")
        if not self.import_clock_ref:
            raise ValueError("Build-12 Micro-live requires import_clock_ref")
        if self.import_activation_stage != "shadow_ready":
            raise ValueError(
                "Build-12 Micro-live requires import_activation_stage=shadow_ready"
            )
        if self.import_health_state != "active":
            raise ValueError(
                "Build-12 Micro-live requires import_health_state=active"
            )
        if self.import_compatibility_status in _REJECTED_IMPORT_COMPATIBILITY_STATUSES:
            raise ValueError(
                "Build-12 Micro-live requires a non-rejected import_compatibility_status"
            )
        if not self.import_feature_lineage_required:
            raise ValueError(
                "Build-12 Micro-live requires import_feature_lineage_required=True"
            )
        if not self.import_feature_lineage_present:
            raise ValueError(
                "Build-12 Micro-live requires import_feature_lineage_present=True"
            )
        if self.import_feature_lineage_status != "ok":
            raise ValueError(
                "Build-12 Micro-live requires import_feature_lineage_status=ok"
            )
        if not self.import_transform_whitelist_required:
            raise ValueError(
                "Build-12 Micro-live requires import_transform_whitelist_required=True"
            )
        if not self.import_transform_whitelist_present:
            raise ValueError(
                "Build-12 Micro-live requires import_transform_whitelist_present=True"
            )
        if self.import_transform_whitelist_status != "ok":
            raise ValueError(
                "Build-12 Micro-live requires import_transform_whitelist_status=ok"
            )
        if self.import_signature_check_status in _REJECTED_IMPORT_SIGNATURE_STATUSES:
            raise ValueError(
                "Build-12 Micro-live requires a non-rejected import_signature_check_status"
            )
        if self.import_conflict_resolution_mode != _EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE:
            raise ValueError(
                "Build-12 Micro-live requires canonical import_conflict_resolution_mode"
            )
        if self.import_conflict_hard_veto_action != _EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION:
            raise ValueError(
                "Build-12 Micro-live requires canonical import_conflict_hard_veto_action"
            )
        if (
            self.import_conflict_score_aggregation_mode
            != _EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE
        ):
            raise ValueError(
                "Build-12 Micro-live requires canonical import_conflict_score_aggregation_mode"
            )
        if self.import_conflict_size_reduce_mode != _EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE:
            raise ValueError(
                "Build-12 Micro-live requires canonical import_conflict_size_reduce_mode"
            )
        if self.import_conflict_rank_adjust_mode != _EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE:
            raise ValueError(
                "Build-12 Micro-live requires canonical import_conflict_rank_adjust_mode"
            )
        if not self.import_conflict_additive_soft_boosts_allowed:
            raise ValueError(
                "Build-12 Micro-live requires import_conflict_additive_soft_boosts_allowed=True"
            )
        if not self.import_conflict_additive_soft_reduces_allowed:
            raise ValueError(
                "Build-12 Micro-live requires import_conflict_additive_soft_reduces_allowed=True"
            )
        if self.import_registry_atomicity_mode != _EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE:
            raise ValueError(
                "Build-12 Micro-live requires canonical import_registry_atomicity_mode"
            )
        if (
            self.import_registry_concurrency_model
            != _EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL
        ):
            raise ValueError(
                "Build-12 Micro-live requires canonical import_registry_concurrency_model"
            )
        if not self.import_registry_publish_requires_atomic_replace:
            raise ValueError(
                "Build-12 Micro-live requires import_registry_publish_requires_atomic_replace=True"
            )
        if not self.import_registry_publish_requires_fsync:
            raise ValueError(
                "Build-12 Micro-live requires import_registry_publish_requires_fsync=True"
            )
        if not self.import_registry_rollback_to_last_known_good:
            raise ValueError(
                "Build-12 Micro-live requires import_registry_rollback_to_last_known_good=True"
            )
        if self.import_payload_ref_count < 5:
            raise ValueError(
                "Build-12 Micro-live requires import_payload_ref_count>=5"
            )
        if not self.import_payload_bundle_present:
            raise ValueError(
                "Build-12 Micro-live requires import_payload_bundle_present=True"
            )
        if not self.import_review_export_ref:
            raise ValueError(
                "Build-12 Micro-live requires import_review_export_ref"
            )
        if not self.import_feature_bridge_ref:
            raise ValueError(
                "Build-12 Micro-live requires import_feature_bridge_ref"
            )
        if not self.import_parity_diagnostics_ref:
            raise ValueError(
                "Build-12 Micro-live requires import_parity_diagnostics_ref"
            )
        if not self.import_replay_metrics_ref:
            raise ValueError(
                "Build-12 Micro-live requires import_replay_metrics_ref"
            )
        if not self.import_replay_dtr_ref:
            raise ValueError(
                "Build-12 Micro-live requires import_replay_dtr_ref"
            )
        if self.shadow_import_artifact_id == "none":
            raise ValueError(
                "Build-12 Micro-live requires a concrete shadow_import_artifact_id"
            )
        if self.shadow_import_lineage_version == "n/a":
            raise ValueError(
                "Build-12 Micro-live requires a concrete shadow_import_lineage_version"
            )
        if self.import_artifact_id == "none":
            raise ValueError("Build-12 Micro-live requires a concrete import_artifact_id")
        if self.import_lineage_version == "n/a":
            raise ValueError("Build-12 Micro-live requires a concrete lineage_version")
        if self.shadow_import_artifact_id != self.import_artifact_id:
            raise ValueError(
                "Build-12 Micro-live requires matching Shadow/import artifact_id"
            )
        if self.shadow_import_lineage_version != self.import_lineage_version:
            raise ValueError(
                "Build-12 Micro-live requires matching Shadow/import lineage_version"
            )

        if self.onboarding_accepted:
            if self.onboarding_review_state not in _ACCEPTED_ONBOARDING_REVIEW_STATES:
                raise ValueError(
                    "onboarding_accepted=True requires a pending or approved onboarding_review_state"
                )
            if self.onboarding_reasons:
                raise ValueError(
                    "onboarding_accepted=True requires empty onboarding_reasons"
                )

        if not self.active_engines:
            raise ValueError("Build-12 Micro-live requires at least one governed engine")
        unknown_engines = set(self.active_engines) - _MICRO_LIVE_ALLOWED_ENGINES
        if unknown_engines:
            raise ValueError(
                "Build-12 Micro-live allows only governed engines from the Full Shadow perimeter"
            )
        if not self.shadow_validated_engines:
            raise ValueError(
                "Build-12 Micro-live requires at least one SHADOW_VALIDATED engine"
            )
        unknown_shadow_validated = (
            set(self.shadow_validated_engines) - _MICRO_LIVE_ALLOWED_ENGINES
        )
        if unknown_shadow_validated:
            raise ValueError(
                "Build-12 Micro-live shadow_validated_engines must stay within the governed engine perimeter"
            )
        if not set(self.active_engines).issubset(set(self.shadow_validated_engines)):
            raise ValueError(
                "Build-12 Micro-live active_engines must be SHADOW_VALIDATED in Shadow"
            )
        if self.shadow_promotable_engines:
            unknown_shadow_promotable = (
                set(self.shadow_promotable_engines) - _MICRO_LIVE_ALLOWED_ENGINES
            )
            if unknown_shadow_promotable:
                raise ValueError(
                    "Build-12 Micro-live shadow_promotable_engines must stay within the governed engine perimeter"
                )
            if not set(self.active_engines).issubset(set(self.shadow_promotable_engines)):
                raise ValueError(
                    "Build-12 Micro-live active_engines must be PROMOTABLE in Shadow judgment"
                )
        elif self.shadow_shadow_only_engines or self.shadow_rewrite_required_engines:
            raise ValueError(
                "Build-12 Micro-live requires at least one PROMOTABLE engine in Shadow judgment"
            )
        if set(self.active_engines) & set(self.shadow_shadow_only_engines):
            raise ValueError(
                "Build-12 Micro-live must not activate engines marked SHADOW_ONLY in Shadow judgment"
            )
        if set(self.active_engines) & set(self.shadow_rewrite_required_engines):
            raise ValueError(
                "Build-12 Micro-live must not activate engines marked REWRITE_REQUIRED in Shadow judgment"
            )
        if set(self.active_engines) & set(self.shadow_dormant_components):
            raise ValueError(
                "Build-12 Micro-live must not activate components marked DORMANT in Shadow"
            )

        if not self.probe_pairs:
            raise ValueError("Build-12 Micro-live requires at least one probe pair")
        if len(self.probe_pairs) > len(ALL_PAIRS):
            raise ValueError("Build-12 Micro-live must stay within the Complete pair scope")
        invalid_pairs = tuple(pair for pair in self.probe_pairs if pair not in ALL_PAIRS)
        if invalid_pairs:
            raise ValueError(
                "Build-12 Micro-live probe_pairs must stay within the Complete pair scope"
            )

        if self.max_pair_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Micro-live max_pair_notional_usdt must stay within total budget")
        if self.requested_pair_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError(
                "Micro-live requested_pair_notional_usdt must stay within total request"
            )
        if self.requested_total_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Micro-live requested_total_notional_usdt exceeds max budget")
        if self.requested_pair_notional_usdt > self.max_pair_notional_usdt:
            raise ValueError("Micro-live requested_pair_notional_usdt exceeds max pair budget")

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
        if self.profile != ProfileId.COMPLETE:
            raise ValueError("Build-13 Live-Light opens in COMPLETE profile only")
        if self.runtime_mode != RuntimeMode.LIVE:
            raise ValueError("Build-13 Live-Light requires runtime_mode=LIVE")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.automatic_complete_promotion_requested:
            raise ValueError(
                "Build-13 Live-Light must not request automatic promotion to Complete"
            )
        if (
            self.operator_safing_request is not None
            and self.operator_safing_request.source_runtime_mode != self.runtime_mode
        ):
            raise ValueError(
                "Build-13 Live-Light operator_safing_request must match source_runtime_mode=LIVE"
            )
        if self.shadow_required_days != 30:
            raise ValueError("Build-13 Live-Light requires shadow_required_days=30")
        if self.shadow_days_completed < self.shadow_required_days:
            raise ValueError(
                "Build-13 Live-Light requires a completed 30-day Shadow"
            )
        if not self.component_verdicts_rendered:
            raise ValueError(
                "Build-13 Live-Light requires rendered post-Shadow component verdicts"
            )
        if not self.shadow_report_ready:
            raise ValueError(
                "Build-13 Live-Light requires shadow_report_ready=True"
            )
        if self.micro_live_required_days != 7:
            raise ValueError(
                "Build-13 Live-Light requires micro_live_required_days=7"
            )
        if self.micro_live_stable_days < self.micro_live_required_days:
            raise ValueError(
                "Build-13 Live-Light requires 7 stable Micro-live days"
            )

        normalized_status = self.import_validation_status.strip().casefold()
        if normalized_status not in _ACCEPTED_IMPORT_STATUSES:
            raise ValueError(
                "Build-13 Live-Light requires an accepted import_validation_status"
            )
        if self.import_exported_from != "local":
            raise ValueError(
                "Build-13 Live-Light requires import_exported_from=local"
            )
        if self.import_source_profile != _EXPECTED_IMPORT_SOURCE_PROFILE:
            raise ValueError(
                "Build-13 Live-Light requires import_source_profile=complete"
            )
        if self.import_rejection_reasons:
            raise ValueError(
                "Build-13 Live-Light requires empty import_rejection_reasons"
            )
        if self.import_review_state not in _ACCEPTED_IMPORT_REVIEW_STATES:
            raise ValueError(
                "Build-13 Live-Light requires import_review_state to stay pending or approved"
            )
        if not self.import_dataset_ref:
            raise ValueError("Build-13 Live-Light requires import_dataset_ref")
        if not self.import_clock_ref:
            raise ValueError("Build-13 Live-Light requires import_clock_ref")
        if self.import_activation_stage != "shadow_ready":
            raise ValueError(
                "Build-13 Live-Light requires import_activation_stage=shadow_ready"
            )
        if self.import_health_state != "active":
            raise ValueError(
                "Build-13 Live-Light requires import_health_state=active"
            )
        if self.import_compatibility_status in _REJECTED_IMPORT_COMPATIBILITY_STATUSES:
            raise ValueError(
                "Build-13 Live-Light requires a non-rejected import_compatibility_status"
            )
        if not self.import_feature_lineage_required:
            raise ValueError(
                "Build-13 Live-Light requires import_feature_lineage_required=True"
            )
        if not self.import_feature_lineage_present:
            raise ValueError(
                "Build-13 Live-Light requires import_feature_lineage_present=True"
            )
        if self.import_feature_lineage_status != "ok":
            raise ValueError(
                "Build-13 Live-Light requires import_feature_lineage_status=ok"
            )
        if not self.import_transform_whitelist_required:
            raise ValueError(
                "Build-13 Live-Light requires import_transform_whitelist_required=True"
            )
        if not self.import_transform_whitelist_present:
            raise ValueError(
                "Build-13 Live-Light requires import_transform_whitelist_present=True"
            )
        if self.import_transform_whitelist_status != "ok":
            raise ValueError(
                "Build-13 Live-Light requires import_transform_whitelist_status=ok"
            )
        if self.import_signature_check_status in _REJECTED_IMPORT_SIGNATURE_STATUSES:
            raise ValueError(
                "Build-13 Live-Light requires a non-rejected import_signature_check_status"
            )
        if self.import_conflict_resolution_mode != _EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE:
            raise ValueError(
                "Build-13 Live-Light requires canonical import_conflict_resolution_mode"
            )
        if self.import_conflict_hard_veto_action != _EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION:
            raise ValueError(
                "Build-13 Live-Light requires canonical import_conflict_hard_veto_action"
            )
        if (
            self.import_conflict_score_aggregation_mode
            != _EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE
        ):
            raise ValueError(
                "Build-13 Live-Light requires canonical import_conflict_score_aggregation_mode"
            )
        if self.import_conflict_size_reduce_mode != _EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE:
            raise ValueError(
                "Build-13 Live-Light requires canonical import_conflict_size_reduce_mode"
            )
        if self.import_conflict_rank_adjust_mode != _EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE:
            raise ValueError(
                "Build-13 Live-Light requires canonical import_conflict_rank_adjust_mode"
            )
        if not self.import_conflict_additive_soft_boosts_allowed:
            raise ValueError(
                "Build-13 Live-Light requires import_conflict_additive_soft_boosts_allowed=True"
            )
        if not self.import_conflict_additive_soft_reduces_allowed:
            raise ValueError(
                "Build-13 Live-Light requires import_conflict_additive_soft_reduces_allowed=True"
            )
        if self.import_registry_atomicity_mode != _EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE:
            raise ValueError(
                "Build-13 Live-Light requires canonical import_registry_atomicity_mode"
            )
        if (
            self.import_registry_concurrency_model
            != _EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL
        ):
            raise ValueError(
                "Build-13 Live-Light requires canonical import_registry_concurrency_model"
            )
        if not self.import_registry_publish_requires_atomic_replace:
            raise ValueError(
                "Build-13 Live-Light requires import_registry_publish_requires_atomic_replace=True"
            )
        if not self.import_registry_publish_requires_fsync:
            raise ValueError(
                "Build-13 Live-Light requires import_registry_publish_requires_fsync=True"
            )
        if not self.import_registry_rollback_to_last_known_good:
            raise ValueError(
                "Build-13 Live-Light requires import_registry_rollback_to_last_known_good=True"
            )
        if self.import_payload_ref_count < 5:
            raise ValueError(
                "Build-13 Live-Light requires import_payload_ref_count>=5"
            )
        if not self.import_payload_bundle_present:
            raise ValueError(
                "Build-13 Live-Light requires import_payload_bundle_present=True"
            )
        if not self.import_review_export_ref:
            raise ValueError(
                "Build-13 Live-Light requires import_review_export_ref"
            )
        if not self.import_feature_bridge_ref:
            raise ValueError(
                "Build-13 Live-Light requires import_feature_bridge_ref"
            )
        if not self.import_parity_diagnostics_ref:
            raise ValueError(
                "Build-13 Live-Light requires import_parity_diagnostics_ref"
            )
        if not self.import_replay_metrics_ref:
            raise ValueError(
                "Build-13 Live-Light requires import_replay_metrics_ref"
            )
        if not self.import_replay_dtr_ref:
            raise ValueError(
                "Build-13 Live-Light requires import_replay_dtr_ref"
            )
        if self.micro_live_import_artifact_id == "none":
            raise ValueError(
                "Build-13 Live-Light requires a concrete micro_live_import_artifact_id"
            )
        if self.micro_live_import_lineage_version == "n/a":
            raise ValueError(
                "Build-13 Live-Light requires a concrete micro_live_import_lineage_version"
            )
        if self.import_artifact_id == "none":
            raise ValueError("Build-13 Live-Light requires a concrete import_artifact_id")
        if self.import_lineage_version == "n/a":
            raise ValueError("Build-13 Live-Light requires a concrete lineage_version")
        if self.micro_live_import_artifact_id != self.import_artifact_id:
            raise ValueError(
                "Build-13 Live-Light requires matching Micro-live/import artifact_id"
            )
        if self.micro_live_import_lineage_version != self.import_lineage_version:
            raise ValueError(
                "Build-13 Live-Light requires matching Micro-live/import lineage_version"
            )

        if self.onboarding_accepted:
            if self.onboarding_review_state not in _ACCEPTED_ONBOARDING_REVIEW_STATES:
                raise ValueError(
                    "onboarding_accepted=True requires a pending or approved onboarding_review_state"
                )
            if self.onboarding_reasons:
                raise ValueError(
                    "onboarding_accepted=True requires empty onboarding_reasons"
                )

        if not self.active_engines:
            raise ValueError("Build-13 Live-Light requires at least one governed engine")
        unknown_engines = set(self.active_engines) - _LIVE_LIGHT_ALLOWED_ENGINES
        if unknown_engines:
            raise ValueError(
                "Build-13 Live-Light allows only governed engines from the Full Shadow perimeter"
            )
        if self.shadow_promotable_engines:
            unknown_shadow_promotable = (
                set(self.shadow_promotable_engines) - _LIVE_LIGHT_ALLOWED_ENGINES
            )
            if unknown_shadow_promotable:
                raise ValueError(
                    "Build-13 Live-Light shadow_promotable_engines must stay within the governed engine perimeter"
                )
            if not set(self.active_engines).issubset(set(self.shadow_promotable_engines)):
                raise ValueError(
                    "Build-13 Live-Light active_engines must be PROMOTABLE in Shadow judgment"
                )
        elif self.shadow_shadow_only_engines or self.shadow_rewrite_required_engines:
            raise ValueError(
                "Build-13 Live-Light requires at least one PROMOTABLE engine in Shadow judgment"
            )
        if set(self.active_engines) & set(self.shadow_shadow_only_engines):
            raise ValueError(
                "Build-13 Live-Light must not activate engines marked SHADOW_ONLY in Shadow judgment"
            )
        if set(self.active_engines) & set(self.shadow_rewrite_required_engines):
            raise ValueError(
                "Build-13 Live-Light must not activate engines marked REWRITE_REQUIRED in Shadow judgment"
            )
        if not self.micro_live_planned_engines:
            raise ValueError(
                "Build-13 Live-Light requires governed micro_live_planned_engines"
            )
        unknown_planned_engines = (
            set(self.micro_live_planned_engines) - _LIVE_LIGHT_ALLOWED_ENGINES
        )
        if unknown_planned_engines:
            raise ValueError(
                "Build-13 Live-Light micro_live_planned_engines must stay within the governed engine perimeter"
            )
        if not set(self.active_engines).issubset(set(self.micro_live_planned_engines)):
            raise ValueError(
                "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines"
            )

        if not self.live_pairs:
            raise ValueError("Build-13 Live-Light requires at least one live pair")
        if len(self.live_pairs) > len(ALL_PAIRS):
            raise ValueError("Build-13 Live-Light must stay within the Complete pair scope")
        invalid_pairs = tuple(pair for pair in self.live_pairs if pair not in ALL_PAIRS)
        if invalid_pairs:
            raise ValueError(
                "Build-13 Live-Light live_pairs must stay within the Complete pair scope"
            )
        if not self.micro_live_planned_pairs:
            raise ValueError(
                "Build-13 Live-Light requires governed micro_live_planned_pairs"
            )
        invalid_planned_pairs = tuple(
            pair for pair in self.micro_live_planned_pairs if pair not in ALL_PAIRS
        )
        if invalid_planned_pairs:
            raise ValueError(
                "Build-13 Live-Light micro_live_planned_pairs must stay within the Complete pair scope"
            )
        if not set(self.live_pairs).issubset(set(self.micro_live_planned_pairs)):
            raise ValueError(
                "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs"
            )

        if self.max_pair_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Live-Light max_pair_notional_usdt must stay within total cap")
        if self.requested_pair_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError(
                "Live-Light requested_pair_notional_usdt must stay within total request"
            )
        if self.requested_total_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Live-Light requested_total_notional_usdt exceeds max cap")
        if self.requested_pair_notional_usdt > self.max_pair_notional_usdt:
            raise ValueError("Live-Light requested_pair_notional_usdt exceeds max pair cap")

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

    @property
    def blocking_reason_count(self) -> int:
        return len(self.decision.blocking_reasons)

    @property
    def planned_pair_count(self) -> int:
        return len(self.execution_intent.planned_pairs)

    @property
    def planned_engine_count(self) -> int:
        return len(self.execution_intent.planned_engines)


ShadowValidationSet.model_rebuild()

LiveInput = LiveLightInput
LiveDecision = LiveLightDecision
LiveExecutionIntent = LiveLightExecutionIntent
LiveRunSummary = LiveLightRunSummary


__all__ = [
    "ShadowTruthSet",
    "ShadowRuntimeEvidence",
    "ShadowValidationSet",
    "OperatorSafingAction",
    "OperatorSafingRequest",
    "ShadowInput",
    "ShadowComparison",
    "ShadowDecision",
    "RegimeLiteGovernanceSummary",
    "InfoStressGovernanceSummary",
    "DailyPnlBreakerGovernanceSummary",
    "ShadowRunSummary",
    "ShadowEngineReport",
    "ShadowBuild14Contribution",
    "ShadowBuild14ReaderContribution",
    "ShadowReportSection",
    "ShadowReportArtifact",
    "ShadowEngineJudgmentVerdict",
    "ShadowEngineJudgment",
    "ShadowPortfolioJudgmentVerdict",
    "ShadowPressureLevel",
    "ShadowPortfolioJudgment",
    "ShadowEngineJudgmentSummary",
    "MicroLiveInput",
    "MicroLiveDecision",
    "MicroLiveExecutionPlan",
    "MicroLiveRunSummary",
    "LiveInput",
    "LiveDecision",
    "LiveExecutionIntent",
    "LiveRunSummary",
    "LiveLightInput",
    "LiveLightDecision",
    "LiveLightExecutionIntent",
    "LiveLightRunSummary",
]
