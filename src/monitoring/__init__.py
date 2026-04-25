"""Real Build-10 monitoring backend for the Light runtime."""

from __future__ import annotations

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
    DiskUsageSample,
    FleetNodeProjection,
    FleetOverviewProjection,
    HybridRouterMetricsProjection,
    ExecutionNoTradeBridgeProjection,
    ExecutionRuntimeProjectionBridgeProjection,
    RuntimeHookBridgeProjection,
    HealthDashboardPayload,
    InfraMetrics,
    LiveCompleteGateGroupProjection,
    LiveCompleteProjection,
    LiveProjection,
    LiveLightGateGroupProjection,
    LiveLightProjection,
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
    MetricSample,
    MicroLiveProjection,
    MetaMetrics,
    MonitoringSnapshot,
    ObservabilityExport,
    ProcessMetricsSample,
    PrometheusFileSdEntry,
    OperatorRuntimeEvent,
    OperatorRuntimeProjection,
    PairMetrics,
    PortfolioMetrics,
    ProjectionStatus,
    RegimeLiteSafingProjection,
    ReplayImportProjection,
    ShadowVpsLogScanMode,
    ShadowVpsServiceLogEventProjection,
    ShadowVpsServiceLogQuery,
    ShadowVpsServiceLogQueryResult,
    ShadowVpsServiceMonitoringPayload,
    ShadowVpsServiceScrapeManifest,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload
from monitoring.hybrid_router_metrics import (
    HybridRouterCalibrationMetricProjection,
    HybridRouterDistributionSummary,
    HybridRouterMetricsProjection,
    HybridRouterMetricsSink,
    HybridRouterTraceProjection,
)
from monitoring.metrics_collector import (
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from monitoring.observability import build_observability_export
from monitoring.observability_io import (
    write_node_exporter_textfile_payload,
    write_observability_text_payload,
)
from monitoring.disk_monitor import sample_disk_usage
from monitoring.log_rotation import LogRotationResult, rotate_log_file
from monitoring.process_metrics import ProcessMetricsSampler
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary
from monitoring.local_lab_monitoring_bundle_manifest import (
    LocalLabMonitoringBundleManifest,
    build_local_lab_monitoring_bundle_manifest,
)
from monitoring.local_lab_bundle_loader import (
    LocalLabMonitoringBundle,
    load_local_lab_monitoring_bundle,
)
from monitoring.local_lab_bundle_discovery import (
    LocalLabMonitoringBundleDiscovery,
    LocalLabMonitoringBundleDiscoveryItem,
    discover_local_lab_monitoring_bundles,
    load_latest_local_lab_monitoring_bundle,
)
from monitoring.local_lab_monitoring_projection import (
    LocalLabMonitoringProjection,
    build_local_lab_monitoring_projection,
)
from monitoring.local_lab_observability import build_local_lab_observability_export
from monitoring.logging_config import build_rotating_file_handler
from monitoring.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from monitoring.local_lab_monitoring_feed import (
    LocalLabMonitoringFeed,
    LocalLabMonitoringFeedItem,
    build_local_lab_monitoring_feed,
    build_local_lab_monitoring_feed_from_root,
)
from monitoring.shadow_vps_service_monitoring import (
    build_shadow_vps_service_monitoring_payload,
    build_shadow_vps_service_observability_export,
)
from monitoring.shadow_vps_service_log_retrieval import (
    build_shadow_vps_service_recent_events_summary,
    query_shadow_vps_service_events,
)
from monitoring.shadow_vps_service_scrape_manifest import (
    build_shadow_vps_service_prometheus_file_sd,
    build_shadow_vps_service_scrape_manifest,
)
from monitoring.regime_detector_shadow_projection import (
    RegimeDetectorShadowProjection,
    build_regime_detector_shadow_projection,
)
from monitoring.regime_detector_shadow_audit_bundle import (
    build_regime_detector_shadow_audit_bundle,
    build_regime_detector_shadow_audit_sample,
)
from monitoring.shadow_vps_scrape_discovery import (
    ShadowVpsScrapeDiscovery,
    ShadowVpsScrapeDiscoveryItem,
    build_shadow_vps_prometheus_file_sd_from_root,
    discover_shadow_vps_service_scrape_manifests,
)
from monitoring.local_prometheus_config import (
    LocalPrometheusConfigSummary,
    build_local_prometheus_config_summary,
    build_local_prometheus_config_text,
)
from monitoring.local_prometheus_metrics_bridge import (
    LocalPrometheusMetricsBridgeSummary,
    build_local_prometheus_metrics_bridge_server,
    build_local_prometheus_metrics_bridge_summary,
    load_local_prometheus_text_payload,
    resolve_local_prometheus_text_source,
)
from monitoring.local_grafana_dashboard import (
    LocalGrafanaDashboardSummary,
    build_local_shadow_vps_grafana_dashboard,
    build_local_shadow_vps_grafana_dashboard_summary,
    extract_prometheus_metric_names,
)
from monitoring.local_lab_grafana_dashboard import (
    LocalLabGrafanaDashboardSummary,
    build_local_lab_grafana_dashboard,
    build_local_lab_grafana_dashboard_summary,
)
from monitoring.local_grafana_api import (
    LocalGrafanaBootstrapSummary,
    bootstrap_local_grafana,
    build_prometheus_datasource_payload,
    load_dashboard_payload,
)
from monitoring.technical_dashboard_backend import build_technical_dashboard_payload

__all__ = [
    "PortfolioMetrics",
    "EnginePhysicsMetrics",
    "EngineMetrics",
    "DiskUsageSample",
    "FleetNodeProjection",
    "FleetOverviewProjection",
    "HybridRouterCalibrationMetricProjection",
    "HybridRouterDistributionSummary",
    "HybridRouterMetricsProjection",
    "HybridRouterMetricsSink",
    "HybridRouterTraceProjection",
    "RuntimeHookBridgeProjection",
    "ExecutionNoTradeBridgeProjection",
    "ExecutionRuntimeProjectionBridgeProjection",
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
    "LiveCompleteGateGroupProjection",
    "LiveCompleteProjection",
    "MicroLiveProjection",
    "LiveProjection",
    "LiveLightGateGroupProjection",
    "LiveLightProjection",
    "RegimeLiteSafingProjection",
    "ShadowProjection",
    "ReplayImportProjection",
    "AlertProjection",
    "TechnicalDashboardPayload",
    "LocalLabMonitoringBackendPayload",
    "LocalLabMonitoringIngestionSummary",
    "MetricSample",
    "ObservabilityExport",
    "ProcessMetricsSample",
    "PrometheusFileSdEntry",
    "ShadowVpsLogScanMode",
    "ShadowVpsServiceLogEventProjection",
    "ShadowVpsServiceLogQuery",
    "ShadowVpsServiceLogQueryResult",
    "ShadowVpsServiceMonitoringPayload",
    "ShadowVpsServiceScrapeManifest",
    "RegimeDetectorShadowProjection",
    "ShadowVpsScrapeDiscoveryItem",
    "ShadowVpsScrapeDiscovery",
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
    "write_node_exporter_textfile_payload",
    "sample_disk_usage",
    "LogRotationResult",
    "rotate_log_file",
    "build_rotating_file_handler",
    "ProcessMetricsSampler",
    "build_shadow_vps_service_monitoring_payload",
    "build_shadow_vps_service_observability_export",
    "query_shadow_vps_service_events",
    "build_shadow_vps_service_recent_events_summary",
    "build_shadow_vps_service_scrape_manifest",
    "build_shadow_vps_service_prometheus_file_sd",
    "build_regime_detector_shadow_projection",
    "build_regime_detector_shadow_audit_sample",
    "build_regime_detector_shadow_audit_bundle",
    "discover_shadow_vps_service_scrape_manifests",
    "build_shadow_vps_prometheus_file_sd_from_root",
    "build_local_lab_monitoring_ingestion_summary",
    "LocalLabMonitoringBundleManifest",
    "build_local_lab_monitoring_bundle_manifest",
    "LocalLabMonitoringBundle",
    "load_local_lab_monitoring_bundle",
    "LocalLabMonitoringBundleDiscoveryItem",
    "LocalLabMonitoringBundleDiscovery",
    "discover_local_lab_monitoring_bundles",
    "load_latest_local_lab_monitoring_bundle",
    "LocalLabMonitoringProjection",
    "build_local_lab_monitoring_projection",
    "build_local_lab_observability_export",
    "build_local_lab_monitoring_backend_payload",
    "LocalLabMonitoringFeedItem",
    "LocalLabMonitoringFeed",
    "build_local_lab_monitoring_feed",
    "build_local_lab_monitoring_feed_from_root",
    "LocalPrometheusConfigSummary",
    "build_local_prometheus_config_text",
    "build_local_prometheus_config_summary",
    "LocalPrometheusMetricsBridgeSummary",
    "build_local_prometheus_metrics_bridge_server",
    "build_local_prometheus_metrics_bridge_summary",
    "load_local_prometheus_text_payload",
    "resolve_local_prometheus_text_source",
    "LocalGrafanaDashboardSummary",
    "LocalLabGrafanaDashboardSummary",
    "LocalGrafanaBootstrapSummary",
    "bootstrap_local_grafana",
    "build_prometheus_datasource_payload",
    "build_local_shadow_vps_grafana_dashboard",
    "build_local_shadow_vps_grafana_dashboard_summary",
    "build_local_lab_grafana_dashboard",
    "build_local_lab_grafana_dashboard_summary",
    "extract_prometheus_metric_names",
    "load_dashboard_payload",
    "derive_build14_observation_from_snapshot",
    "derive_build14_observation_from_payload",
    "AlertLifecycleTracker",
]


def __getattr__(name: str) -> object:
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
