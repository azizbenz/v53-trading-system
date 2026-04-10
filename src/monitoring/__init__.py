"""Real Build-10 monitoring backend for the Light runtime."""

from monitoring.alert_manager import AlertLifecycleTracker, build_monitoring_alerts
from monitoring.build14_observation import (
    derive_build14_observation_from_payload,
    derive_build14_observation_from_snapshot,
)
from monitoring.contracts import (
    AccountUserDataProjection,
    AlertHistoryEntry,
    AlertProjection,
    Build14ReaderProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentCard,
    EngineJudgmentProjection,
    EngineJudgmentVerdict,
    EnginePhysicsMetrics,
    EngineMetrics,
    FleetNodeProjection,
    FleetOverviewProjection,
    ExecutionNoTradeBridgeProjection,
    RuntimeHookBridgeProjection,
    HealthDashboardPayload,
    InfraMetrics,
    LiveProjection,
    LiveLightProjection,
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
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
from monitoring.observability_io import write_observability_text_payload
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary
from monitoring.local_lab_bundle_loader import (
    LocalLabMonitoringBundle,
    load_local_lab_monitoring_bundle,
)
from monitoring.technical_dashboard_backend import build_technical_dashboard_payload

__all__ = [
    "PortfolioMetrics",
    "EnginePhysicsMetrics",
    "EngineMetrics",
    "FleetNodeProjection",
    "FleetOverviewProjection",
    "RuntimeHookBridgeProjection",
    "ExecutionNoTradeBridgeProjection",
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
    "EngineJudgmentVerdict",
    "EngineJudgmentCard",
    "EngineJudgmentProjection",
    "Build14ReaderProjection",
    "Build14Projection",
    "AccountUserDataProjection",
    "MicroLiveProjection",
    "LiveProjection",
    "LiveLightProjection",
    "ShadowProjection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "LocalLabMonitoringBackendPayload",
    "LocalLabMonitoringIngestionSummary",
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
    "write_observability_text_payload",
    "build_local_lab_monitoring_ingestion_summary",
    "LocalLabMonitoringBundle",
    "load_local_lab_monitoring_bundle",
    "derive_build14_observation_from_snapshot",
    "derive_build14_observation_from_payload",
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
