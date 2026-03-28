"""Contracts for the real Build-10 monitoring backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts import AlertRecord, PairHealthLevel, ProfileId, RuntimeMode, TimestampedModel


HeadlineStatus = Literal["healthy", "warning", "critical"]
ProjectionStatus = Literal["healthy", "warning", "critical", "info", "planned"]
MetricKind = Literal["counter", "gauge", "state"]


class PortfolioMetrics(BaseModel, frozen=True):
    """Portfolio-level health and risk metrics for the Light dashboard."""

    allocated_opportunities: int = Field(..., ge=0)
    gross_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    loss_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    beta_utilization: float = Field(..., ge=0.0)
    capital_deployed_usdt: float = Field(..., ge=0.0)
    ce_net: float = 0.0


class EngineMetrics(BaseModel, frozen=True):
    """Per-engine summary projected to monitoring."""

    engine_id: str = Field(..., min_length=1)
    emitted_signals: int = Field(..., ge=0)
    net_edge_bps: float = 0.0
    expected_cost_bps: float = Field(default=0.0, ge=0.0)
    ce_expected: float = 0.0
    stale: bool = False


class PairMetrics(BaseModel, frozen=True):
    """Per-pair quality metrics."""

    pair: str = Field(..., min_length=1)
    health: PairHealthLevel
    freshness_ms: int = Field(..., ge=0)
    backlog_depth: int = Field(default=0, ge=0)
    is_active: bool = True


class InfraMetrics(BaseModel, frozen=True):
    """Infrastructure and operability metrics for Build-10."""

    queue_backlog: int = Field(default=0, ge=0)
    reconnect_count: int = Field(default=0, ge=0)
    stale_pairs: tuple[str, ...] = ()
    dtr_loss_count: int = Field(default=0, ge=0)
    log_loss_count: int = Field(default=0, ge=0)
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


class HealthDashboardPayload(TimestampedModel):
    """Stable backend payload structured for the locked Light UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    headline_status: HeadlineStatus
    active_alert_count: int = Field(..., ge=0)
    stale_pair_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)
    capital_deployed_usdt: float = Field(..., ge=0.0)
    gross_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    loss_capacity_used_pct: float = Field(..., ge=0.0, le=100.0)
    ce_net: float = 0.0
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    break_even_drift_scopes: tuple[str, ...] = ()
    edge_credible_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    edge_surveillance_count: int = Field(..., ge=0)
    future_learning_diagnostics: int = Field(default=0, ge=0)
    future_learning_hypotheses: int = Field(default=0, ge=0)
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
    blocking_reasons: tuple[str, ...] = ()


class AlertProjection(BaseModel, frozen=True):
    """Normalized alert and operability projection."""

    headline_status: HeadlineStatus
    active_alert_count: int = Field(..., ge=0)
    alert_ids: tuple[str, ...] = ()
    queue_backlog: int = Field(..., ge=0)
    stale_pair_count: int = Field(..., ge=0)
    stale_pairs: tuple[str, ...] = ()
    backlog_stale_status: ProjectionStatus
    dtr_loss_count: int = Field(..., ge=0)
    log_loss_count: int = Field(..., ge=0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    loss_drift_status: ProjectionStatus


class TechnicalDashboardPayload(TimestampedModel):
    """Normalized Build-10 technical supervision payload."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    system: SystemProjection
    portfolio: PortfolioMetrics
    build9_meta: Build9MetaProjection
    build9x: Build9XProjection
    shadow: ShadowProjection = ShadowProjection()
    micro_live: MicroLiveProjection = MicroLiveProjection()
    replay_import: ReplayImportProjection
    alerts: AlertProjection
    future_panels: tuple[str, ...] = (
        "technical_supervision",
        "build9x_diagnostics",
        "shadow_supervision",
        "micro_live_supervision",
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
    "HealthDashboardPayload",
    "HeadlineStatus",
    "ProjectionStatus",
    "SystemProjection",
    "Build9MetaProjection",
    "Build9XProjection",
    "ShadowProjection",
    "MicroLiveProjection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "MetricKind",
    "MetricSample",
    "ObservabilityExport",
]
