"""Dashboard and projection contracts for the real Build-10 backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import HookId, ProfileId, RuntimeMode, TimestampedModel

from .contracts_core import (
    Build14ReaderSeverity,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentVerdict,
    EngineMetrics,
    HeadlineStatus,
    InfraMetrics,
    OperatorRuntimeProjection,
    PairMetrics,
    PortfolioMetrics,
    ProjectionStatus,
    SystemProjection,
)
from .contracts_live_complete import (
    LiveCompleteGateGroupProjection,
    LiveCompleteProjection,
)


class EngineJudgmentCard(BaseModel, frozen=True):
    """Per-engine supervised judgment rendered for the current Shadow campaign."""

    engine_id: str = Field(..., min_length=1)
    component_verdict: str = Field(..., min_length=1)
    judgment_verdict: EngineJudgmentVerdict
    status: ProjectionStatus = "planned"
    useful_frequency: float = Field(default=0.0, ge=0.0)
    ce_expected: float = 0.0
    estimated_cost_bps: float = Field(default=0.0, ge=0.0)
    edge_net: float = 0.0
    economic_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    marginal_edge: float = 0.0
    redundancy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    portfolio_contribution: float = 0.0
    observations: int = Field(default=0, ge=0)
    rationale: str = Field(default="", min_length=0)
    evidence_summary: str = Field(default="", min_length=0)


class EngineJudgmentProjection(BaseModel, frozen=True):
    """Normalized engine-by-engine judgment surface for dashboard supervision."""

    status: ProjectionStatus = "planned"
    source_report_id: str = ""
    source_shadow_run_id: str = ""
    source_shadow_days_completed: int = Field(default=0, ge=0)
    source_shadow_required_days: int = Field(default=30, ge=1)
    portfolio_judgment_verdict: str = ""
    portfolio_physics_pressure: str = ""
    portfolio_redundancy_pressure: str = ""
    portfolio_cluster_pressure: str = ""
    portfolio_beta_pressure: str = ""
    portfolio_gross_capacity_pressure: str = ""
    portfolio_loss_capacity_pressure: str = ""
    portfolio_rejected_engine_count: int = Field(default=0, ge=0)
    ranking_rejected_engine_count: int = Field(default=0, ge=0)
    elevated_physics_engine_count: int = Field(default=0, ge=0)
    critical_physics_engine_count: int = Field(default=0, ge=0)
    phantom_trade_count: int = Field(default=0, ge=0)
    portfolio_rationale: str = ""
    cards: tuple[EngineJudgmentCard, ...] = ()


class ReplayImportProjection(BaseModel, frozen=True):
    """Normalized LOCAL_REPLAY / import projection consumed by Build-10."""

    status: ProjectionStatus
    artifact_id: str = "none"
    artifact_kind: str = "No replay bundle exported"
    exported_from: str = ""
    source_profile: str = ""
    lineage_version: str = "n/a"
    dataset_ref: str = ""
    clock_ref: str = ""
    activation_stage: str = ""
    health_state: str = ""
    lifecycle_state: str = "Awaiting LOCAL_REPLAY artifact"
    validation_status: str = "not_run"
    review_state: str = "No import review executed"
    compatibility_status: str = "not_evaluated"
    compatibility_reasons: tuple[str, ...] = ()
    feature_lineage_required: bool = False
    feature_lineage_present: bool = False
    feature_lineage_status: str = "not_required"
    feature_lineage_reasons: tuple[str, ...] = ()
    transform_whitelist_required: bool = False
    transform_whitelist_present: bool = False
    transform_whitelist_status: str = "not_required"
    transform_whitelist_reasons: tuple[str, ...] = ()
    signature_check_status: str = "not_provided"
    signature_key_id: str = ""
    trusted_key_status: str = ""
    signature_check_reasons: tuple[str, ...] = ()
    conflict_resolution_mode: str = ""
    conflict_hard_veto_action: str = ""
    conflict_score_aggregation_mode: str = ""
    conflict_size_reduce_mode: str = ""
    conflict_rank_adjust_mode: str = ""
    conflict_additive_soft_boosts_allowed: bool = False
    conflict_additive_soft_reduces_allowed: bool = False
    registry_atomicity_mode: str = ""
    registry_concurrency_model: str = ""
    registry_publish_requires_atomic_replace: bool = False
    registry_publish_requires_fsync: bool = False
    registry_rollback_to_last_known_good: bool = False
    payload_ref_count: int = Field(default=0, ge=0)
    payload_bundle_present: bool = False
    review_export_ref: str = ""
    feature_bridge_ref: str = ""
    parity_diagnostics_ref: str = ""
    replay_metrics_ref: str = ""
    replay_dtr_ref: str = ""
    rejection_reasons: tuple[str, ...] = ()


class RegimeLiteSafingProjection(BaseModel, frozen=True):
    """Normalized regime_lite safing recommendation exposed on the Shadow rail."""

    status: ProjectionStatus = "planned"
    severity: str = "not_configured"
    should_block_new_entries: bool = False
    should_exit_all: bool = False
    recommended_operator_action: str = ""
    operator_safing_request_action: str = ""
    operator_safing_request_source_runtime_mode: str = ""
    detail: str = ""
    reason_codes: tuple[str, ...] = ()


class ShadowProjection(BaseModel, frozen=True):
    """Normalized Build-11 Shadow summary consumed by Build-10 supervision."""

    status: ProjectionStatus = "planned"
    run_state: str = "not_run"
    verdict: str = "not_run"
    truth_set_ref: str = ""
    validation_set_ref: str = ""
    divergent_comparison_count: int = Field(default=0, ge=0)
    blocking_comparison_count: int = Field(default=0, ge=0)
    total_comparison_count: int = Field(default=0, ge=0)
    build9x_diagnostics_count: int = Field(default=0, ge=0)
    open_hypotheses: int = Field(default=0, ge=0)
    replay_candidate_count: int = Field(default=0, ge=0)
    review_export_ready: bool = False
    import_artifact_id: str = "none"
    import_lineage_version: str = "n/a"
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = False
    shadow_days_completed: int = Field(default=0, ge=0)
    shadow_required_days: int = Field(default=30, ge=1)
    shadow_report_ready: bool = False
    active_engine_count: int = Field(default=0, ge=0)
    build14_enabler_count: int = Field(default=0, ge=0)
    shadow_validated_component_count: int = Field(default=0, ge=0)
    dormant_component_count: int = Field(default=0, ge=0)
    execution_telemetry_ref: str = ""
    execution_telemetry_status: str = "not_configured"
    telegram_alert_delivery_status: str = "not_configured"
    telegram_alert_delivery_event_type: str = ""
    telegram_alert_delivery_error: str = ""
    telegram_alert_config_ref: str = ""
    telegram_alert_config_source: str = "not_configured"
    telegram_alert_key_ref: str = ""
    telegram_alert_key_source: str = "not_configured"
    execution_runtime_bootstrap_ref: str = ""
    execution_runtime_bootstrap_status: str = "not_configured"
    execution_runtime_bootstrap_source: str = "not_configured"
    execution_runtime_gatekeeper_audit_ref: str = ""
    execution_runtime_gatekeeper_audit_source: str = "not_configured"
    execution_runtime_bootstrap_user_data_stream_enabled: bool = False
    execution_runtime_bootstrap_reconciliation_boot_executed: bool = False
    execution_runtime_bootstrap_reconciliation_boot_trading_blocked: bool = False
    execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped: bool = False
    execution_runtime_bootstrap_reconciliation_boot_detail: str = ""
    execution_runtime_bootstrap_reconciliation_boot_recovery_action: str = ""
    execution_runtime_bootstrap_reconciliation_boot_divergence_count: int = Field(
        default=0,
        ge=0,
    )
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_source: str = "not_configured"
    regime_lite_assessment_ref: str = ""
    regime_lite_assessment_source: str = "not_configured"
    regime_lite_safing_recommendation_ref: str = ""
    regime_lite_safing_recommendation_source: str = "not_configured"
    info_stress_assessment_ref: str = ""
    info_stress_assessment_source: str = "not_configured"
    info_stress_governance_status: str = "not_configured"
    info_stress_level: str = "not_configured"
    info_stress_alert_count: int = Field(default=0, ge=0)
    info_stress_entries_blocked: bool = False
    info_stress_entries_blocked_until_ts: int = Field(default=0, ge=0)
    info_stress_reason_codes: tuple[str, ...] = ()
    info_stress_detail: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_bridge_status: str = "planned"
    execution_runtime_projection_bridge_loaded: bool = False
    execution_runtime_projection_rate_limit_model_loaded: bool = False
    execution_runtime_projection_spread_guard_model_loaded: bool = False
    execution_runtime_projection_slippage_model_loaded: bool = False
    regime_lite_safing: RegimeLiteSafingProjection = RegimeLiteSafingProjection()


class MicroLiveProjection(BaseModel, frozen=True):
    """Normalized Build-12 Micro-live summary consumed by Build-10 supervision."""

    status: ProjectionStatus = "planned"
    run_state: str = "not_run"
    verdict: str = "not_run"
    shadow_run_id: str = ""
    shadow_verdict: str = "not_run"
    allowed_to_probe: bool = False
    requested_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_pair_notional_usdt: float = Field(default=0.0, ge=0.0)
    order_probe_limit: int = Field(default=0, ge=0)
    planned_pairs: tuple[str, ...] = ()
    planned_engines: tuple[str, ...] = ()
    import_artifact_id: str = "none"
    import_lineage_version: str = "n/a"
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    observability_ready: bool = False
    halt_ready: bool = False
    onboarding_ready: bool = False
    operator_safing_action: str = ""
    operator_safing_target_runtime_mode: str = ""
    operator_safing_reason: str = ""
    blocking_reasons: tuple[str, ...] = ()

class LiveLightGateGroupProjection(BaseModel, frozen=True):
    """Normalized gate-group projection exposed to monitoring and dashboards."""

    gate_id: Literal[
        "governance_envelope",
        "promotion_history",
        "import_replay_integrity",
        "operational_readiness",
        "build14_influence",
    ]
    status: Literal["passed", "blocked", "review_only"] = "passed"
    reasons: tuple[str, ...] = ()


class LiveLightProjection(BaseModel, frozen=True):
    """Normalized Build-13 Live summary consumed by Build-10 supervision.

    `Live-Light` remains the historical label carried by the surrounding
    contract surface, but the governed rail represented here is the active
    Build-13 Live runtime on `profile=COMPLETE`.
    """

    status: ProjectionStatus = "planned"
    run_state: str = "not_run"
    verdict: str = "not_run"
    micro_live_run_id: str = ""
    micro_live_verdict: str = "not_run"
    allowed_to_execute_small: bool = False
    requested_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_pair_notional_usdt: float = Field(default=0.0, ge=0.0)
    execution_order_limit: int = Field(default=0, ge=0)
    planned_pairs: tuple[str, ...] = ()
    planned_engines: tuple[str, ...] = ()
    import_artifact_id: str = "none"
    import_lineage_version: str = "n/a"
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    observability_ready: bool = False
    halt_ready: bool = False
    execution_ready: bool = False
    broker_ready: bool = False
    exchange_ready: bool = False
    operator_safing_action: str = ""
    operator_safing_target_runtime_mode: str = ""
    operator_safing_reason: str = ""
    blocking_reasons: tuple[str, ...] = ()
    build14_influence_mode: str = "read_only"
    build14_action: str = "observe"
    build14_severity: str = "nominal"
    build14_summary: str = ""
    build14_reason_codes: tuple[str, ...] = ()
    build14_confidence_penalty_weight: float = Field(default=0.0, ge=0.0, le=0.25)
    build14_recommended_budget_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    gate_groups: tuple[LiveLightGateGroupProjection, ...] = ()


LiveProjection = LiveLightProjection


class Build14ReaderProjection(BaseModel, frozen=True):
    """Normalized per-reader Build-14 summary exposed to monitoring and UI."""

    reader_name: str = Field(..., min_length=1)
    signal_family: str = Field(..., min_length=1)
    observed_value: float = Field(default=0.0, ge=0.0)
    status: Build14ReaderSeverity = "nominal"
    detail: str = Field(..., min_length=1)
    evidence_refs: tuple[str, ...] = ()
    structured_log_key: str = Field(default="", min_length=0)


class Build14Projection(BaseModel, frozen=True):
    """Normalized Build-14 enabler status consumed by Build-10."""

    status: ProjectionStatus = "planned"
    hard_state: str = "coded"
    live_promotion_eligible: bool = False
    influence_mode: str = "read_only"
    action: str = "observe"
    severity: str = "nominal"
    summary: str = "No Build-14 evaluation materialized"
    market_toxicity_value: float = Field(default=0.0, ge=0.0)
    market_toxicity_status: str = "nominal"
    execution_fragility_value: float = Field(default=0.0, ge=0.0)
    execution_fragility_status: str = "nominal"
    confidence_penalty_weight: float = Field(default=0.0, ge=0.0, le=0.25)
    recommended_budget_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    requires_manual_review: bool = False
    candidate_effect: str = "observe_only"
    reason_codes: tuple[str, ...] = ()
    reader_projections: tuple[Build14ReaderProjection, ...] = ()

    @model_validator(mode="after")
    def validate_projection(self) -> "Build14Projection":
        if self.influence_mode == "shadow_enabled":
            if self.action != "shadow_apply":
                raise ValueError(
                    "Build-14 shadow_enabled projections must keep action=shadow_apply"
                )
            if self.candidate_effect != "shadow_enabled":
                raise ValueError(
                    "Build-14 shadow_enabled projections must keep candidate_effect=shadow_enabled"
                )
            if self.confidence_penalty_weight != 0.0:
                raise ValueError(
                    "Build-14 shadow_enabled projections must keep confidence_penalty_weight=0.0"
                )
            if self.recommended_budget_factor != 1.0:
                raise ValueError(
                    "Build-14 shadow_enabled projections must keep recommended_budget_factor=1.0"
                )
            if self.requires_manual_review:
                raise ValueError(
                    "Build-14 shadow_enabled projections must stay automated inside Shadow"
                )
        if self.influence_mode == "read_only":
            if self.action != "observe":
                raise ValueError(
                    "Build-14 read_only projections must keep action=observe"
                )
            if self.candidate_effect != "observe_only":
                raise ValueError(
                    "Build-14 read_only projections must keep candidate_effect=observe_only"
                )
        return self


class AccountUserDataProjection(BaseModel, frozen=True):
    """Normalized authenticated Binance account-stream summary for the dashboard."""

    status: ProjectionStatus = "planned"
    authenticated: bool = False
    session_date: str = ""
    acquisition_mode: str = ""
    endpoint: str = ""
    summary_ref: str = ""
    events_ref: str = ""
    subscription_id: int | None = Field(default=None, ge=0)
    event_count: int = Field(default=0, ge=0)
    event_types: tuple[str, ...] = ()
    pair_scope: tuple[str, ...] = ()
    detail: str = "No authenticated Binance user-data stream captured"


class RuntimeHookBridgeProjection(BaseModel, frozen=True):
    """Normalized monitoring projection for any bounded compiled runtime hook bridge."""

    hook_id: HookId
    label: str = Field(..., min_length=1)
    status: ProjectionStatus = "planned"
    configured: bool = False
    selection_status: str = "not_configured"
    current_snapshot_id: str = ""
    previous_snapshot_id: str = ""
    last_known_good_snapshot_id: str = ""
    binding_present: bool = False
    loaded: bool = False
    compiled_plan_ref: str = ""
    artifact_count: int = Field(default=0, ge=0)
    action_kinds: tuple[str, ...] = ()
    failure_mode: str = ""
    error_stage: str = ""
    error_type: str = ""
    detail: str = "Compiled runtime hook bridge not configured"


class ExecutionNoTradeBridgeProjection(BaseModel, frozen=True):
    """Governed monitoring projection of the bounded compiled no-trade bridge."""

    status: ProjectionStatus = "planned"
    configured: bool = False
    selection_status: str = "not_configured"
    current_snapshot_id: str = ""
    previous_snapshot_id: str = ""
    last_known_good_snapshot_id: str = ""
    binding_present: bool = False
    loaded: bool = False
    compiled_plan_ref: str = ""
    artifact_count: int = Field(default=0, ge=0)
    failure_mode: str = ""
    error_stage: str = ""
    error_type: str = ""
    detail: str = "Compiled execution no-trade bridge not configured"


class ExecutionRuntimeProjectionBridgeProjection(BaseModel, frozen=True):
    """Governed monitoring projection of the bounded Local IA Lab runtime projection bridge."""

    status: ProjectionStatus = "planned"
    configured: bool = False
    projection_found: bool = False
    projection_loaded: bool = False
    projection_status: str = ""
    projection_path: str = ""
    consumer_count: int = Field(default=0, ge=0)
    ready_consumer_count: int = Field(default=0, ge=0)
    partial_consumer_count: int = Field(default=0, ge=0)
    blocked_consumer_count: int = Field(default=0, ge=0)
    rate_limit_model_loaded: bool = False
    spread_guard_model_loaded: bool = False
    slippage_model_loaded: bool = False
    caution_flags: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    error_type: str = ""
    detail: str = "Execution runtime projection bridge not configured"


class AlertProjection(BaseModel, frozen=True):
    """Normalized alert and operability projection."""

    headline_status: HeadlineStatus
    active_alert_count: int = Field(..., ge=0)
    alert_ids: tuple[str, ...] = ()
    queue_backlog: int = Field(..., ge=0)
    backlog_high_water_mark: int = Field(default=0, ge=0)
    drop_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    stale_pair_count: int = Field(..., ge=0)
    stale_pairs: tuple[str, ...] = ()
    stale_spike_count: int = Field(default=0, ge=0)
    recovery_retry_count: int = Field(default=0, ge=0)
    kill_switch_active: bool = False
    kill_switch_timestamp_ms: int | None = Field(default=None, ge=0)
    persisted_metric_names: tuple[str, ...] = ()
    volatile_metric_names: tuple[str, ...] = ()
    backlog_stale_status: ProjectionStatus
    dtr_loss_count: int = Field(..., ge=0)
    log_loss_count: int = Field(..., ge=0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    loss_drift_status: ProjectionStatus
    operator_runtime: OperatorRuntimeProjection = OperatorRuntimeProjection()


class TechnicalDashboardPayload(TimestampedModel):
    """Normalized Build-10 technical supervision payload."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    system: SystemProjection
    portfolio: PortfolioMetrics
    engines: tuple[EngineMetrics, ...] = ()
    pairs: tuple[PairMetrics, ...] = ()
    infra: InfraMetrics = InfraMetrics()
    build9_meta: Build9MetaProjection
    build9x: Build9XProjection
    engine_judgment: EngineJudgmentProjection = EngineJudgmentProjection()
    shadow: ShadowProjection = ShadowProjection()
    micro_live: MicroLiveProjection = MicroLiveProjection()
    live_light: LiveLightProjection = LiveLightProjection()
    build14: Build14Projection = Build14Projection()
    account_user_data: AccountUserDataProjection = AccountUserDataProjection()
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection = ExecutionNoTradeBridgeProjection()
    execution_runtime_projection_bridge: ExecutionRuntimeProjectionBridgeProjection = (
        ExecutionRuntimeProjectionBridgeProjection()
    )
    runtime_hook_bridges: tuple[RuntimeHookBridgeProjection, ...] = ()
    replay_import: ReplayImportProjection
    alerts: AlertProjection
    future_panels: tuple[str, ...] = (
        "technical_supervision",
        "build9x_diagnostics",
        "shadow_supervision",
        "micro_live_supervision",
        "live_light_supervision",
        "build14_supervision",
        "artifact_import",
        "observability_export",
    )

    @property
    def live(self) -> LiveProjection:
        return self.live_light


class LocalLabMonitoringBackendPayload(TimestampedModel):
    """Descriptive backend payload for future Local IA Lab monitoring surfaces."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    status: ProjectionStatus
    detail: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    selected_pair: str = ""
    selected_engine_id: str = ""
    release_status: str = Field(..., min_length=1)
    bridge_status: str = Field(..., min_length=1)
    promotion_readiness_status: str = Field(..., min_length=1)
    activation_stage: str = Field(..., min_length=1)
    normalized_promotion_state: str = Field(..., min_length=1)
    review_state: str = Field(..., min_length=1)
    release_gate_status: str = Field(..., min_length=1)
    semantic_status: str = Field(..., min_length=1)
    review_ready: bool = False
    trade_loss_attribution_ready: bool = False
    walk_forward_review_ready: bool = False
    artifact_ablation_ready: bool = False
    artifact_proof_ready: bool = False
    edge_calibration_ready: bool = False
    release_ready_for_shadow: bool = False
    ready_for_shadow_import_dry_run: bool = False
    scope_count: int = Field(default=0, ge=0)
    scope_ready_count: int = Field(default=0, ge=0)
    scope_blocked_count: int = Field(default=0, ge=0)
    release_scope_ready_count: int = Field(default=0, ge=0)
    release_scope_blocked_count: int = Field(default=0, ge=0)
    loss_surrogate_status: str = Field(default="not_evaluated", min_length=1)
    loss_surrogate_ready: bool = False
    loss_surrogate_scope_count: int = Field(default=0, ge=0)
    loss_surrogate_top_scope_slug: str = ""
    loss_surrogate_top_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    calibration_methods_stationarity_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_stationarity_pass: bool | None = None
    execution_review_status: str = Field(default="not_evaluated", min_length=1)
    execution_review_ready: bool = False
    execution_ready_threshold_count: int = Field(default=0, ge=0)
    execution_partial_threshold_count: int = Field(default=0, ge=0)
    execution_blocked_threshold_count: int = Field(default=0, ge=0)
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_correction: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_family_count: int = Field(default=0, ge=0)
    calibration_normalized_report_status: str = Field(default="not_evaluated", min_length=1)
    calibration_normalized_report_ready: bool = False
    calibration_normalized_threshold_count: int = Field(default=0, ge=0)
    tail_risk_review_status: str = Field(default="not_evaluated", min_length=1)
    tail_risk_review_ready: bool = False
    tail_risk_ready_breaker_count: int = Field(default=0, ge=0)
    tail_risk_partial_breaker_count: int = Field(default=0, ge=0)
    tail_risk_blocked_breaker_count: int = Field(default=0, ge=0)
    research_priority_status: str = Field(default="not_evaluated", min_length=1)
    research_priority_scope_count: int = Field(default=0, ge=0)
    research_priority_top_scope_slug: str = ""
    research_priority_top_score: float = Field(default=0.0, ge=0.0, le=1.0)
    replay_candidate_queue_status: str = Field(default="not_evaluated", min_length=1)
    replay_candidate_count: int = Field(default=0, ge=0)
    replay_candidate_ready_count: int = Field(default=0, ge=0)
    replay_candidate_top_scope_slug: str = ""
    replay_ticket_index_status: str = Field(default="not_evaluated", min_length=1)
    replay_ticket_count: int = Field(default=0, ge=0)
    replay_ticket_ready_count: int = Field(default=0, ge=0)
    replay_ticket_top_scope_slug: str = ""
    replay_dispatch_plan_status: str = Field(default="not_evaluated", min_length=1)
    replay_dispatch_ready_count: int = Field(default=0, ge=0)
    replay_dispatch_blocked_count: int = Field(default=0, ge=0)
    replay_dispatch_top_ticket_id: str = ""
    observability_sample_count: int = Field(default=0, ge=0)
    blocking_reason_count: int = Field(default=0, ge=0)
    release_gate_reason_count: int = Field(default=0, ge=0)
    blocking_reasons: tuple[str, ...] = ()
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_reasons: tuple[str, ...] = ()
    bridge_blocking_reasons: tuple[str, ...] = ()
    observability_export_ref: str = ""
    scope_matrix_ref: str = ""
    artifact_release_candidate_ref: str = ""
    artifact_import_dry_run_bridge_ref: str = ""
    artifact_promotion_readiness_summary_ref: str = ""
    local_lab_loss_surrogate_ref: str = ""
    local_lab_calibration_methods_review_ref: str = ""
    local_lab_execution_review_ref: str = ""
    local_lab_multiple_testing_review_ref: str = ""
    local_lab_tail_risk_review_ref: str = ""
    local_lab_calibration_normalized_report_ref: str = ""
    local_lab_research_priority_ref: str = ""
    local_lab_replay_candidate_queue_ref: str = ""
    local_lab_replay_ticket_index_ref: str = ""
    local_lab_replay_dispatch_plan_ref: str = ""
    local_lab_replay_workflow_manifest_ref: str = ""
    local_lab_monitoring_bundle_manifest_ref: str = ""


class LocalLabMonitoringIngestionSummary(TimestampedModel):
    """Typed summary describing whether a Local IA Lab monitoring bundle is ingestion-ready."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    projection_status: ProjectionStatus
    selected_pair: str = ""
    selected_engine_id: str = ""
    release_status: str = Field(..., min_length=1)
    bridge_status: str = Field(..., min_length=1)
    promotion_readiness_status: str = Field(..., min_length=1)
    release_ready_for_shadow: bool = False
    ready_for_shadow_import_dry_run: bool = False
    sample_count: int = Field(default=0, ge=0)
    text_payload_present: bool = False
    text_payload_line_count: int = Field(default=0, ge=0)
    scope_count: int = Field(default=0, ge=0)
    release_scope_ready_count: int = Field(default=0, ge=0)
    release_scope_blocked_count: int = Field(default=0, ge=0)
    blocking_reason_count: int = Field(default=0, ge=0)
    release_gate_reason_count: int = Field(default=0, ge=0)
    ingestion_ready: bool = False
    ingestion_detail: str = Field(..., min_length=1)
    observability_export_ref: str = ""
    backend_payload_ref: str = ""
    monitoring_bundle_manifest_ref: str = ""


__all__ = [
    "AccountUserDataProjection",
    "AlertProjection",
    "Build14Projection",
    "Build14ReaderProjection",
    "EngineJudgmentCard",
    "EngineJudgmentProjection",
    "ExecutionNoTradeBridgeProjection",
    "ExecutionRuntimeProjectionBridgeProjection",
    "LiveCompleteGateGroupProjection",
    "LiveCompleteProjection",
    "LiveLightGateGroupProjection",
    "LiveLightProjection",
    "LiveProjection",
    "LocalLabMonitoringBackendPayload",
    "LocalLabMonitoringIngestionSummary",
    "MicroLiveProjection",
    "RegimeLiteSafingProjection",
    "ReplayImportProjection",
    "RuntimeHookBridgeProjection",
    "ShadowProjection",
    "TechnicalDashboardPayload",
]
