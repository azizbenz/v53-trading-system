"""Real Build-10 monitoring backend for the Light runtime."""

from monitoring.alert_manager import AlertLifecycleTracker, build_monitoring_alerts
from monitoring.contracts import (
    AlertHistoryEntry,
    AlertProjection,
    Build14ReaderProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    EngineMetrics,
    HealthDashboardPayload,
    InfraMetrics,
    LiveLightProjection,
    MetricSample,
    MicroLiveProjection,
    MetaMetrics,
    MonitoringSnapshot,
    ObservabilityExport,
    OperatorRuntimeEvent,
    OperatorRuntimeProjection,
    PairMetrics,
    PortfolioMetrics,
    ProjectionStatus,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload
from monitoring.metrics_collector import (
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from monitoring.observability import build_observability_export
from monitoring.technical_dashboard_backend import build_technical_dashboard_payload

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
    "ProjectionStatus",
    "SystemProjection",
    "Build9MetaProjection",
    "Build9XProjection",
    "Build14ReaderProjection",
    "Build14Projection",
    "MicroLiveProjection",
    "LiveLightProjection",
    "ShadowProjection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "MetricSample",
    "ObservabilityExport",
    "collect_portfolio_metrics",
    "collect_engine_metrics",
    "collect_pair_metrics",
    "collect_infra_metrics",
    "collect_meta_metrics",
    "collect_monitoring_snapshot",
    "MonitoringRuntime",
    "MonitoringRuntimeConfig",
    "MonitoringRuntimeResult",
    "MonitoringRuntimeState",
    "build_monitoring_alerts",
    "build_health_dashboard_payload",
    "build_technical_dashboard_payload",
    "build_observability_export",
    "AlertLifecycleTracker",
]


def __getattr__(name: str):
    if name in {"MonitoringRuntime", "MonitoringRuntimeConfig", "MonitoringRuntimeResult", "MonitoringRuntimeState"}:
        from monitoring.monitoring_runtime import (
            MonitoringRuntime,
            MonitoringRuntimeConfig,
            MonitoringRuntimeResult,
            MonitoringRuntimeState,
        )

        exports = {
            "MonitoringRuntime": MonitoringRuntime,
            "MonitoringRuntimeConfig": MonitoringRuntimeConfig,
            "MonitoringRuntimeResult": MonitoringRuntimeResult,
            "MonitoringRuntimeState": MonitoringRuntimeState,
        }
        return exports[name]
    raise AttributeError(f"module 'monitoring' has no attribute {name!r}")
