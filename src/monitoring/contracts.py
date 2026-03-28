"""Contracts for the real Build-10 monitoring backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts import AlertRecord, PairHealthLevel, ProfileId, RuntimeMode, TimestampedModel


HeadlineStatus = Literal["healthy", "warning", "critical"]


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


__all__ = [
    "PortfolioMetrics",
    "EngineMetrics",
    "PairMetrics",
    "InfraMetrics",
    "MetaMetrics",
    "MonitoringSnapshot",
    "HealthDashboardPayload",
    "HeadlineStatus",
]
