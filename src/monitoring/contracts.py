"""Contracts for the real Build-10 monitoring backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    AlertCategory,
    AlertRecord,
    AlertSeverity,
    DeploymentState,
    PairHealthLevel,
    ProfileId,
    RuntimeMode,
    TimestampedModel,
)


HeadlineStatus = Literal["healthy", "warning", "critical"]
ProjectionStatus = Literal["healthy", "warning", "critical", "info", "planned"]
MetricKind = Literal["counter", "gauge", "state"]
AlertHistoryState = Literal["open", "resolved"]


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
    """Short Build-10 alert lifecycle history exposed to the locked Light UI."""

    alert_id: str = Field(..., min_length=1)
    severity: AlertSeverity
    category: AlertCategory
    message: str = Field(..., min_length=1)
    status: AlertHistoryState = "open"
    opened_ms: int = Field(..., ge=0)
    last_seen_ms: int = Field(..., ge=0)
    resolved_ms: int | None = Field(default=None, ge=0)


class OperatorRuntimeEvent(BaseModel, frozen=True):
    """Audit-ready operator log event projected from the locked Light UI into monitoring."""

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
    """Stable backend payload structured for the locked Light UI."""

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


class ReplayImportProjection(BaseModel, frozen=True):
    """Normalized LOCAL_REPLAY / import projection consumed by Build-10."""

    status: ProjectionStatus
    artifact_id: str = "none"
    artifact_kind: str = "No replay bundle exported"
    lineage_version: str = "n/a"
    lifecycle_state: str = "Awaiting LOCAL_REPLAY artifact"
    validation_status: str = "not_run"
    review_state: str = "No import review executed"
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
    """Normalized Build-13 Live-Light summary consumed by Build-10 supervision."""

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
    shadow: ShadowProjection = ShadowProjection()
    micro_live: MicroLiveProjection = MicroLiveProjection()
    live_light: LiveLightProjection = LiveLightProjection()
    build14: Build14Projection = Build14Projection()
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
    "ShadowProjection",
    "MicroLiveProjection",
    "LiveLightProjection",
    "Build14Projection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "MetricKind",
    "MetricSample",
    "ObservabilityExport",
]
