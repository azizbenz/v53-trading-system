"""Core monitoring contracts for the real Build-10 backend."""

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
Build14ReaderSeverity = Literal["nominal", "elevated", "critical"]
MetricKind = Literal["counter", "gauge", "state"]
AlertHistoryState = Literal["open", "resolved"]
EngineJudgmentVerdict = Literal["promotable", "shadow-only", "rewrite-required", "dormant"]
ShadowVpsLogScanMode = Literal["full_scan", "tail_recent"]


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


__all__ = [
    "AlertHistoryEntry",
    "AlertHistoryState",
    "Build14ReaderSeverity",
    "Build9MetaProjection",
    "Build9XProjection",
    "EngineJudgmentVerdict",
    "EngineMetrics",
    "EnginePhysicsMetrics",
    "FleetNodeProjection",
    "FleetOverviewProjection",
    "HealthDashboardPayload",
    "HeadlineStatus",
    "InfraMetrics",
    "MetaMetrics",
    "MetricKind",
    "MonitoringSnapshot",
    "OperatorRuntimeEvent",
    "OperatorRuntimeProjection",
    "PairMetrics",
    "PortfolioMetrics",
    "ProjectionStatus",
    "ShadowVpsLogScanMode",
    "SystemProjection",
]
