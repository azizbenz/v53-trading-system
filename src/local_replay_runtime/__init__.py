"""Minimal LOCAL_REPLAY scaffold for the unified V5.3 plan."""

from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    ReplayArtifactExportResult,
    export_local_replay_artifact,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest, SHARED_CORE_ID
from local_replay_runtime.contracts import (
    LocalReplayRequest,
    LocalReplayRuntimeEvidence,
    ReplayBundle,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
)
from local_replay_runtime.enums import ReplayArtifactKind, ReplayLifecycleState
from local_replay_runtime.errors import (
    BacktestProfileForbiddenError,
    LocalReplayRuntimeError,
    ProfileForkForbiddenError,
    RuntimeModeViolationError,
)
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    build_feature_bridge_payload,
    load_historical_replay_dataset,
)
from local_replay_runtime.historical_snapshot_loader import (
    HistoricalMarketEventEnvelope,
    HistoricalSnapshotBatch,
    ReplayRouteHint,
    load_historical_snapshot_batch,
)
from local_replay_runtime.orchestrator import LocalReplayOrchestrator
from local_replay_runtime.performance_mode_guard import (
    PerformanceModeGuardReport,
    build_performance_mode_guard_report,
)
from local_replay_runtime.replay_event_router import (
    ReplayEventRouterConfig,
    route_snapshot_batch_to_dataset,
)
from local_replay_runtime.replay_clock import (
    HistoricalReplayClock,
    ReplayClockTick,
    build_replay_clock,
)
from local_replay_runtime.replay_dtr_exporter import export_replay_dtr_records
from local_replay_runtime.replay_executor import (
    ReplayExecutionInput,
    ReplayExecutionResult,
    execute_local_replay_export,
)
from local_replay_runtime.replay_metrics_collector import (
    ReplayEngineAggregate,
    ReplayMetricsSummary,
    ReplayPairAggregate,
    build_replay_metrics_summary,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_orchestrator import (
    ReplayChunkArtifact,
    ReplayChunkSessionSummary,
    ReplayOrchestratorRequest,
    ReplayOrchestratorResult,
    build_execution_input_from_dataset,
    orchestrate_local_replay_export,
)
from local_replay_runtime.replay_session_config import (
    ReplayDetailLevel,
    ReplayInputKind,
    ReplaySessionConfig,
    build_replay_session_config,
)
from local_replay_runtime.replay_state_store import (
    ReplaySessionLifecycle,
    ReplaySessionState,
    ReplaySessionStateStore,
    ReplaySessionStoreConfig,
)
from local_replay_runtime.run_consistency_guard import (
    RunConsistencyGuardReport,
    compare_replay_runs,
)
from local_replay_runtime.runtime_evidence import (
    LocalReplayEvidenceRecorder,
    LocalReplayEvidenceRecorderConfig,
    LocalReplayEvidenceRecorderState,
)
from local_replay_runtime.shadow_execution_simulator import (
    ShadowExecutionSimulatorConfig,
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)

__all__ = [
    "ArtifactManifest",
    "SHARED_CORE_ID",
    "ReplayArtifactExportRequest",
    "ReplayArtifactExportResult",
    "export_local_replay_artifact",
    "ReplayPairAggregate",
    "ReplayEngineAggregate",
    "ReplayMetricsSummary",
    "build_replay_metrics_summary",
    "export_replay_dtr_records",
    "ReplayExecutionInput",
    "ReplayExecutionResult",
    "execute_local_replay_export",
    "ReplayChunkArtifact",
    "ReplayChunkSessionSummary",
    "ReplayOrchestratorRequest",
    "ReplayOrchestratorResult",
    "build_execution_input_from_dataset",
    "orchestrate_local_replay_export",
    "ReplayDatasetRef",
    "ReplayClockRef",
    "LocalReplayRequest",
    "ReplayBundle",
    "ReplayExecutionPlan",
    "LocalReplayRuntimeEvidence",
    "LocalReplayOrchestrator",
    "PerformanceModeGuardReport",
    "build_performance_mode_guard_report",
    "ReplayRunManifest",
    "ReplayInputKind",
    "ReplayDetailLevel",
    "ReplaySessionConfig",
    "build_replay_session_config",
    "ReplaySessionLifecycle",
    "ReplaySessionState",
    "ReplaySessionStoreConfig",
    "ReplaySessionStateStore",
    "RunConsistencyGuardReport",
    "compare_replay_runs",
    "LocalReplayEvidenceRecorderConfig",
    "LocalReplayEvidenceRecorderState",
    "LocalReplayEvidenceRecorder",
    "HistoricalReplayOpportunity",
    "HistoricalReplayDataset",
    "load_historical_replay_dataset",
    "build_feature_bridge_payload",
    "ReplayRouteHint",
    "HistoricalMarketEventEnvelope",
    "HistoricalSnapshotBatch",
    "load_historical_snapshot_batch",
    "ReplayEventRouterConfig",
    "route_snapshot_batch_to_dataset",
    "ReplayClockTick",
    "HistoricalReplayClock",
    "build_replay_clock",
    "ShadowExecutionSimulatorConfig",
    "simulate_shadow_compatible_dtrs",
    "build_parity_diagnostics_payload",
    "ReplayArtifactKind",
    "ReplayLifecycleState",
    "LocalReplayRuntimeError",
    "RuntimeModeViolationError",
    "BacktestProfileForbiddenError",
    "ProfileForkForbiddenError",
]
