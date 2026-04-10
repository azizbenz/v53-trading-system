"""Contracts for the real Build-10 monitoring backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    AlertCategory,
    AlertRecord,
    AlertSeverity,
    DeploymentState,
    HookId,
    PairHealthLevel,
    ProfileId,
    RuntimeMode,
    TimestampedModel,
)


HeadlineStatus = Literal["healthy", "warning", "critical"]
ProjectionStatus = Literal["healthy", "warning", "critical", "info", "planned"]
Build14ReaderSeverity = Literal["nominal", "elevated", "critical"]
MetricKind = Literal["counter", "gauge", "state"]
AlertHistoryState = Literal["open", "resolved"]
EngineJudgmentVerdict = Literal["promotable", "shadow-only", "rewrite-required", "dormant"]


class PortfolioMetrics(BaseModel, frozen=True):
    """Portfolio-level health and risk metrics for the Light dashboard."""

    allocated_opportunities: int = Field(..., ge=0)
    gross_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    loss_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    beta_utilization: float = Field(..., ge=0.0)
    capital_deployed_usdt: float = Field(..., ge=0.0)
    ce_net: float = 0.0
    pnl_net_usdt: float = 0.0
    dominant_cluster: str = ""
    breaches: tuple[str, ...] = ()


class EnginePhysicsMetrics(BaseModel, frozen=True):
    """Optional market-physics metrics surfaced for engine supervision."""

    physics_pressure_state: str = ""
    delta_confirmation: float | None = Field(default=None, ge=0.0, le=1.0)
    execution_fragility: float | None = Field(default=None, ge=0.0, le=1.0)
    market_toxicity: float | None = Field(default=None, ge=0.0, le=1.0)
    spread_regime_penalty: float | None = Field(default=None, ge=0.0, le=1.0)
    competition_support: float | None = Field(default=None, ge=0.0, le=1.0)
    sweep_score: float | None = Field(default=None, ge=0.0, le=1.0)
    absorption_score: float | None = Field(default=None, ge=0.0, le=1.0)
    poc_reversion_score: float | None = Field(default=None, ge=0.0, le=1.0)
    false_breakout_score: float | None = Field(default=None, ge=0.0, le=1.0)
    fragility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    toxicity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    execution_survivability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    micro_friction_score: float | None = Field(default=None, ge=0.0, le=1.0)


class EngineMetrics(BaseModel, frozen=True):
    """Per-engine summary projected to monitoring."""

    engine_id: str = Field(..., min_length=1)
    emitted_signals: int = Field(..., ge=0)
    net_edge_bps: float = 0.0
    expected_cost_bps: float = Field(default=0.0, ge=0.0)
    ce_expected: float = 0.0
    useful_frequency: float = Field(default=0.0, ge=0.0)
    sharpe_per_trade: float = 0.0
    drawdown_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    suspension_reason: str = ""
    stale: bool = False
    scoring_summary: str = ""
    risk_summary: str = ""
    scoring_reason_codes: tuple[str, ...] = ()
    risk_reason_codes: tuple[str, ...] = ()
    scoring_penalized_score: float = 0.0
    scoring_ranking_score: float | None = None
    scoring_final_size_multiplier: float = Field(default=1.0, ge=0.0)
    selection_outcome_code: str = ""
    portfolio_verdict_code: str = ""
    phantom_trade: bool = False
    phantom_reason_code: str = ""
    hard_blocked: bool = False
    risk_decision_severity: str = ""
    drawdown_state_code: str = ""
    blocked_guard_count: int = Field(default=0, ge=0)
    physics: EnginePhysicsMetrics = Field(default_factory=EnginePhysicsMetrics)


class PairMetrics(BaseModel, frozen=True):
    """Per-pair quality metrics."""

    pair: str = Field(..., min_length=1)
    health: PairHealthLevel
    freshness_ms: int = Field(..., ge=0)
    backlog_depth: int = Field(default=0, ge=0)
    is_active: bool = True
    average_cost_bps: float = Field(default=0.0, ge=0.0)
    cost_p90_bps: float = Field(default=0.0, ge=0.0)
    ce_expected: float = 0.0
    useful_frequency: float = Field(default=0.0, ge=0.0)
    suspension_reason: str = ""


class InfraMetrics(BaseModel, frozen=True):
    """Infrastructure and operability metrics for Build-10."""

    queue_backlog: int = Field(default=0, ge=0)
    backlog_high_water_mark: int = Field(default=0, ge=0)
    reconnect_count: int = Field(default=0, ge=0)
    stale_pairs: tuple[str, ...] = ()
    stale_spike_count: int = Field(default=0, ge=0)
    recovery_retry_count: int = Field(default=0, ge=0)
    dtr_loss_count: int = Field(default=0, ge=0)
    log_loss_count: int = Field(default=0, ge=0)
    total_enqueued: int = Field(default=0, ge=0)
    total_dropped: int = Field(default=0, ge=0)
    drop_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    elw_bps: float = Field(default=0.0, ge=0.0)
    expected_cost_bps: float = Field(default=0.0, ge=0.0)
    realized_cost_bps: float = Field(default=0.0, ge=0.0)
    partial_fill_count: int = Field(default=0, ge=0)
    fill_latency_ms_p95: int = Field(default=0, ge=0)
    reconciliation_alert_count: int = Field(default=0, ge=0)
    kill_switch_active: bool = False
    kill_switch_timestamp_ms: int | None = Field(default=None, ge=0)
    persisted_metric_names: tuple[str, ...] = ()
    volatile_metric_names: tuple[str, ...] = ()
    cpu_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class MetaMetrics(BaseModel, frozen=True):
    """Projected Build-9 meta outputs made visible by Build-10."""

    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    cra_alert_count: int = Field(..., ge=0)
    break_even_drift_alert: bool = False
    break_even_drift_scopes: tuple[str, ...] = ()
    edge_credible_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    edge_surveillance_count: int = Field(..., ge=0)
    future_learning_diagnostics: int = Field(default=0, ge=0)
    future_learning_hypotheses: int = Field(default=0, ge=0)


class MonitoringSnapshot(TimestampedModel):
    """Coherent monitoring snapshot consumed by alerting and UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    portfolio: PortfolioMetrics
    engines: tuple[EngineMetrics, ...] = ()
    pairs: tuple[PairMetrics, ...] = ()
    infra: InfraMetrics
    meta: MetaMetrics
    alerts: tuple[AlertRecord, ...] = ()
    backlog_warning: bool = False
    stale_warning: bool = False
    loss_warning: bool = False

    @property
    def active_alert_count(self) -> int:
        return len(self.alerts)

    @property
    def stale_pair_count(self) -> int:
        return len(self.infra.stale_pairs)


class AlertHistoryEntry(BaseModel, frozen=True):
    """Short Build-10 alert lifecycle history exposed to the locked operator UI."""

    alert_id: str = Field(..., min_length=1)
    severity: AlertSeverity
    category: AlertCategory
    message: str = Field(..., min_length=1)
    status: AlertHistoryState = "open"
    opened_ms: int = Field(..., ge=0)
    last_seen_ms: int = Field(..., ge=0)
    resolved_ms: int | None = Field(default=None, ge=0)


class OperatorRuntimeEvent(BaseModel, frozen=True):
    """Audit-ready operator log event projected from the locked operator UI into monitoring."""

    timestamp_ms: int = Field(..., ge=0)
    correlation_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    source_runtime_mode: str = ""
    target_runtime_mode: str = ""
    target: str = ""
    accepted: bool = False
    message: str = Field(..., min_length=1)
    operator_reason: str = ""
    rejection_reason: str = ""


class OperatorRuntimeProjection(BaseModel, frozen=True):
    """Typed operator-governance surface projected through Build-10 monitoring."""

    event_count: int = Field(default=0, ge=0)
    latest_event_type: str = ""
    latest_event_message: str = ""
    last_error: str = ""
    recent_event_log: tuple[OperatorRuntimeEvent, ...] = ()
    rejection_event_count: int = Field(default=0, ge=0)
    latest_rejection_reason: str = ""
    pending_notification_count: int = Field(default=0, ge=0)
    pending_notification_alert_ids: tuple[str, ...] = ()
    acknowledged_notification_count: int = Field(default=0, ge=0)
    latest_acknowledged_alert_id: str = ""
    latest_safing_action: str = ""
    latest_safing_source_runtime_mode: str = ""
    latest_safing_target_runtime_mode: str = ""
    latest_safing_reason: str = ""


class HealthDashboardPayload(TimestampedModel):
    """Stable backend payload structured for the locked Build-10 operator UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    headline_status: HeadlineStatus
    active_alert_count: int = Field(..., ge=0)
    active_alert_ids: tuple[str, ...] = ()
    alert_history: tuple[AlertHistoryEntry, ...] = ()
    stale_pair_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)
    backlog_high_water_mark: int = Field(default=0, ge=0)
    drop_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    stale_spike_count: int = Field(default=0, ge=0)
    recovery_retry_count: int = Field(default=0, ge=0)
    kill_switch_active: bool = False
    kill_switch_timestamp_ms: int | None = Field(default=None, ge=0)
    persisted_metric_names: tuple[str, ...] = ()
    volatile_metric_names: tuple[str, ...] = ()
    capital_deployed_usdt: float = Field(..., ge=0.0)
    pnl_net_usdt: float = 0.0
    gross_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    loss_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    beta_utilization: float = Field(default=0.0, ge=0.0)
    ce_net: float = 0.0
    dominant_cluster: str = ""
    risk_breaches: tuple[str, ...] = ()
    pairs: tuple[PairMetrics, ...] = ()
    engines: tuple[EngineMetrics, ...] = ()
    reconnect_count: int = Field(default=0, ge=0)
    dtr_loss_count: int = Field(default=0, ge=0)
    log_loss_count: int = Field(default=0, ge=0)
    elw_bps: float = Field(default=0.0, ge=0.0)
    expected_cost_bps: float = Field(default=0.0, ge=0.0)
    realized_cost_bps: float = Field(default=0.0, ge=0.0)
    partial_fill_count: int = Field(default=0, ge=0)
    fill_latency_ms_p95: int = Field(default=0, ge=0)
    reconciliation_alert_count: int = Field(default=0, ge=0)
    cpu_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    cra_alert_count: int = Field(default=0, ge=0)
    break_even_drift_scopes: tuple[str, ...] = ()
    edge_credible_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    edge_surveillance_count: int = Field(..., ge=0)
    future_learning_diagnostics: int = Field(default=0, ge=0)
    future_learning_hypotheses: int = Field(default=0, ge=0)
    deployment_state: DeploymentState = DeploymentState.SHADOW
    last_transition_summary: str = ""
    shadow_status: ProjectionStatus = "planned"
    micro_live_status: ProjectionStatus = "planned"
    live_light_status: ProjectionStatus = "planned"
    operator_runtime: OperatorRuntimeProjection = OperatorRuntimeProjection()
    controls_locked: bool = True

    @property
    def live_status(self) -> ProjectionStatus:
        return self.live_light_status


class SystemProjection(BaseModel, frozen=True):
    """Normalized system-level projection used by the technical dashboard."""

    headline_status: HeadlineStatus
    active_modules: tuple[str, ...] = ()
    active_engines: tuple[str, ...] = ()
    stale_engines: tuple[str, ...] = ()
    build9x_status: ProjectionStatus = "planned"
    shadow_status: ProjectionStatus = "planned"
    micro_live_status: ProjectionStatus = "planned"
    live_light_status: ProjectionStatus = "planned"
    build14_status: ProjectionStatus = "planned"
    replay_import_status: ProjectionStatus = "planned"
    governed_extensions_detail: str = ""

    @property
    def live_status(self) -> ProjectionStatus:
        return self.live_light_status


class FleetNodeProjection(BaseModel, frozen=True):
    """Read-only synthetic summary for one VPS in a future fleet overview."""

    vps_id: str = Field(..., min_length=1)
    health_status: ProjectionStatus
    runtime_mode: RuntimeMode | None = None
    artifact_version: str = ""
    heartbeat_age_ms: int | None = Field(default=None, ge=0)
    alert_state: HeadlineStatus = "healthy"


class FleetOverviewProjection(TimestampedModel):
    """Read-only fleet summary. Deep diagnostics still live on the selected VPS."""

    nodes: tuple[FleetNodeProjection, ...] = ()
    active_vps_id: str = ""

    @model_validator(mode="after")
    def validate_fleet(self) -> "FleetOverviewProjection":
        vps_ids = tuple(node.vps_id for node in self.nodes)
        if len(set(vps_ids)) != len(vps_ids):
            raise ValueError("FleetOverviewProjection nodes must have unique vps_id values")
        if self.active_vps_id and self.active_vps_id not in set(vps_ids):
            raise ValueError("FleetOverviewProjection active_vps_id must reference a node in nodes")
        return self


class Build9MetaProjection(BaseModel, frozen=True):
    """Normalized Build-9 projection for technical supervision."""

    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    dtr_status: ProjectionStatus
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    cra_alert_count: int = Field(..., ge=0)
    cra_status: ProjectionStatus
    break_even_state: str = Field(..., min_length=1)
    break_even_status: ProjectionStatus
    break_even_drift_scopes: tuple[str, ...] = ()
    edge_credible_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    edge_surveillance_count: int = Field(..., ge=0)
    edge_status: ProjectionStatus


class Build9XProjection(BaseModel, frozen=True):
    """Normalized Build-9X summary consumed by Build-10."""

    status: ProjectionStatus
    diagnostics_count: int = Field(..., ge=0)
    diagnostics_summary: str = "No diagnostic report"
    open_hypotheses: int = Field(..., ge=0)
    total_hypotheses: int = Field(..., ge=0)
    near_miss_count: int = Field(..., ge=0)
    replay_candidate_count: int = Field(..., ge=0)
    memory_record_count: int = Field(..., ge=0)
    latest_memory_summary: str = "No memory records"
    enrichment_hypothesis_count: int = Field(default=0, ge=0)
    latest_enrichment_target: str = ""
    latest_enrichment_signal_family: str = ""
    expected_replay_evidence_count: int = Field(default=0, ge=0)
    expected_shadow_evidence_count: int = Field(default=0, ge=0)
    enrichment_summary: str = "No enrichment hypothesis mapped"
    review_export_ready: bool = False
    review_export_ref: str = ""
    learning_queue_depth: int = Field(default=0, ge=0)
    learning_queue_oldest_age_ms: int = Field(default=0, ge=0)
    learning_worker_cpu_pct: float = Field(default=0.0, ge=0.0)
    learning_worker_rss_mb: float = Field(default=0.0, ge=0.0)
    learning_write_latency_ms: float = Field(default=0.0, ge=0.0)
    learning_export_failures_total: int = Field(default=0, ge=0)
    learning_log_loss_total: int = Field(default=0, ge=0)
    learning_unprocessed_items_count: int = Field(default=0, ge=0)
    learning_backlog_state: Literal["normal", "alert", "protection"] = "normal"
    learning_capture_mode: Literal["full_capture", "capture_minimale"] = "full_capture"
    learning_observability_reduced: bool = False
    learning_backpressure_active: bool = False
    review_blocked_due_to_incomplete_data: bool = False
    promotion_blocked_due_to_incomplete_data: bool = False
    learning_capacity_summary: str = "queue=0 / backlog=normal / mode=full_capture"


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
    observability_ready: bool = False
    halt_ready: bool = False
    onboarding_ready: bool = False
    operator_safing_action: str = ""
    operator_safing_target_runtime_mode: str = ""
    operator_safing_reason: str = ""
    blocking_reasons: tuple[str, ...] = ()


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


class MetricSample(BaseModel, frozen=True):
    """Single structured metric emitted by the minimal observability layer."""

    name: str = Field(..., min_length=1)
    kind: MetricKind
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    unit: str = ""


class ObservabilityExport(TimestampedModel):
    """Structured and text-exportable monitoring snapshot."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    samples: tuple[MetricSample, ...] = ()
    text_payload: str = Field(..., min_length=1)


__all__ = [
    "PortfolioMetrics",
    "EngineMetrics",
    "EnginePhysicsMetrics",
    "PairMetrics",
    "InfraMetrics",
    "MetaMetrics",
    "MonitoringSnapshot",
    "AlertHistoryEntry",
    "OperatorRuntimeEvent",
    "OperatorRuntimeProjection",
    "HealthDashboardPayload",
    "HeadlineStatus",
    "ProjectionStatus",
    "SystemProjection",
    "Build9MetaProjection",
    "Build9XProjection",
    "EngineJudgmentVerdict",
    "EngineJudgmentCard",
    "EngineJudgmentProjection",
    "ShadowProjection",
    "MicroLiveProjection",
    "LiveProjection",
    "LiveLightProjection",
    "Build14ReaderProjection",
    "Build14Projection",
    "AccountUserDataProjection",
    "RuntimeHookBridgeProjection",
    "ExecutionNoTradeBridgeProjection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "LocalLabMonitoringBackendPayload",
    "LocalLabMonitoringIngestionSummary",
    "MetricKind",
    "MetricSample",
    "ObservabilityExport",
]
