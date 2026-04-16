"""Governed Shadow contracts for the minimal real Build-11 runtime."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from protocols.contracts_validation_support import (
    validate_shadow_validation_import_consistency,
)

from .contracts_shared import (
    DailyPnlBreakerGovernanceSummary,
    InfoStressGovernanceSummary,
    ProfileId,
    PromotionState,
    RegimeLiteGovernanceSummary,
    ReviewState,
    RuntimeMode,
    ShadowComparisonStatus,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
    _ACCEPTED_IMPORT_REVIEW_STATES,
    _ACCEPTED_IMPORT_STATUSES,
    _EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION,
    _EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE,
    _EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE,
    _EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE,
    _EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE,
    _EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE,
    _EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL,
    _EXPECTED_IMPORT_SOURCE_PROFILE,
    _KNOWN_SHADOW_BUILD14_READER_IDS,
    _REJECTED_IMPORT_COMPATIBILITY_STATUSES,
    _REJECTED_IMPORT_SIGNATURE_STATUSES,
    _REQUIRED_SHADOW_BUILD14_COMPONENT_IDS,
    _REQUIRED_SHADOW_ENGINE_IDS,
)


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
        validate_shadow_validation_import_consistency(
            self,
            accepted_import_statuses=_ACCEPTED_IMPORT_STATUSES,
            expected_import_source_profile=_EXPECTED_IMPORT_SOURCE_PROFILE,
            accepted_import_review_states=_ACCEPTED_IMPORT_REVIEW_STATES,
            rejected_import_compatibility_statuses=_REJECTED_IMPORT_COMPATIBILITY_STATUSES,
            rejected_import_signature_statuses=_REJECTED_IMPORT_SIGNATURE_STATUSES,
            expected_import_conflict_resolution_mode=_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE,
            expected_import_conflict_hard_veto_action=_EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION,
            expected_import_conflict_score_aggregation_mode=_EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE,
            expected_import_conflict_size_reduce_mode=_EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE,
            expected_import_conflict_rank_adjust_mode=_EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE,
            expected_import_registry_atomicity_mode=_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE,
            expected_import_registry_concurrency_model=_EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL,
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


ShadowValidationSet.model_rebuild()


__all__ = [
    "ShadowBuild14Contribution",
    "ShadowBuild14ReaderContribution",
    "ShadowComparison",
    "ShadowComponentAssessment",
    "ShadowDecision",
    "ShadowEngineReport",
    "ShadowInput",
    "ShadowReportArtifact",
    "ShadowReportSection",
    "ShadowRunSummary",
    "ShadowRuntimeEvidence",
    "ShadowTruthSet",
    "ShadowValidationSet",
]
