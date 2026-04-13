"""Minimal LOCAL_REPLAY scaffold for the unified V5.3 plan."""

from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    ReplayArtifactExportResult,
    export_local_replay_artifact,
)
from local_replay_runtime.edge_gate_calibration import (
    EdgeGateCalibrationConfig,
    EdgeGateCalibrationError,
    EdgeGateCalibrationInsufficientDataError,
    EdgeGateCalibrationReport,
    EdgeGateCalibrationValidationError,
    EdgeGateThresholdCalibration,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
    write_edge_gate_calibration_artifact,
)
from local_replay_runtime.artifact_proof_summary_builder import (
    LocalLabArtifactProofAssessment,
    build_local_lab_artifact_proof_assessment,
)
from local_replay_runtime.artifact_ablation_study import (
    LocalLabAblationStudy,
    build_local_lab_ablation_study,
    build_pending_local_lab_ablation_study,
)
from local_replay_runtime.artifact_release_candidate import (
    LocalLabArtifactReleaseCandidate,
    LocalLabArtifactReleaseScope,
    LocalLabArtifactReleaseScopeSummary,
    build_local_lab_artifact_release_candidate,
    build_local_lab_artifact_release_scope_summary,
)
from local_replay_runtime.local_lab_scope_matrix import (
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    LocalLabScopeKey,
    build_local_lab_scope_matrix,
    build_local_lab_scope_slug,
    discover_local_lab_scope_keys,
)
from local_replay_runtime.local_lab_recalibration_plan import (
    LocalLabFailureModeAggregate,
    LocalLabRecalibrationAction,
    LocalLabRecalibrationPlan,
    build_local_lab_recalibration_plan,
)
from local_replay_runtime.local_lab_calibration_methods_review import (
    LocalLabCalibrationMethodsReview,
    LocalLabCalibrationMethodsStatus,
    build_local_lab_calibration_methods_review,
)
from local_replay_runtime.local_lab_execution_review import (
    LocalLabExecutionReview,
    LocalLabExecutionReviewStatus,
    LocalLabExecutionTelemetry,
    LocalLabExecutionThresholdReview,
    build_local_lab_execution_review,
)
from local_replay_runtime.local_lab_execution_runtime_projection import (
    LocalLabExecutionRuntimeConsumerProjection,
    LocalLabExecutionRuntimeProjection,
    LocalLabExecutionRuntimeProjectionStatus,
    build_local_lab_execution_runtime_projection,
)
from local_replay_runtime.local_lab_multiple_testing_review import (
    LocalLabMultipleTestingFamilyReview,
    LocalLabMultipleTestingReview,
    LocalLabMultipleTestingStatus,
    build_hypothesis_test_family_review,
    build_local_lab_multiple_testing_review,
)
from local_replay_runtime.local_lab_tail_risk_review import (
    LocalLabTailRiskBreakerEstimate,
    LocalLabTailRiskReview,
    LocalLabTailRiskStatus,
    build_local_lab_tail_risk_review,
)
from local_replay_runtime.local_lab_calibration_normalized_report import (
    LocalLabCalibrationDataWindow,
    LocalLabCalibrationOosReservation,
    LocalLabCalibrationReproducibility,
    LocalLabCalibrationThresholdReport,
    LocalLabNormalizedCalibrationReport,
    build_local_lab_calibration_normalized_report,
)
from local_replay_runtime.local_lab_loss_surrogate import (
    LocalLabLossSurrogateModel,
    LocalLabLossSurrogateRecordScore,
    LocalLabLossSurrogateReport,
    LocalLabLossSurrogateScopeScore,
    build_local_lab_loss_surrogate_report,
)
from local_replay_runtime.local_lab_research_priority import (
    LocalLabResearchPriorityFeatures,
    LocalLabResearchPriorityReport,
    LocalLabResearchPriorityScope,
    LocalLabResearchPriorityWeights,
    build_local_lab_research_priority_report,
)
from local_replay_runtime.local_lab_replay_candidate_queue import (
    LocalLabReplayCandidate,
    LocalLabReplayCandidateQueue,
    build_local_lab_replay_candidate_queue,
)
from local_replay_runtime.local_lab_replay_ticket_index import (
    LocalLabReplayTicket,
    LocalLabReplayTicketIndex,
    build_local_lab_replay_ticket_index,
)
from local_replay_runtime.local_lab_replay_dispatch_plan import (
    LocalLabReplayDispatchItem,
    LocalLabReplayDispatchPlan,
    build_local_lab_replay_dispatch_plan,
)
from local_replay_runtime.local_lab_replay_workflow_manifest import (
    LocalLabReplayWorkflowManifest,
    build_local_lab_replay_workflow_manifest,
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
from interface_contracts import (
    ActionUnit,
    ArtifactActivationStage,
    ArtifactActionKind,
    ArtifactHealthState,
    ArtifactLogicFormat,
    HookId,
    HOOK_MODULE_BY_ID,
)
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
from local_replay_runtime.replay_dtr_exporter import export_replay_dtr_records, load_replay_dtr_records
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
    ParityTolerancePolicy,
    ReplayParityDiagnosticsSummary,
    ShadowExecutionSimulatorConfig,
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)
from local_replay_runtime.walk_forward_review import (
    WalkForwardHumanReview,
    WalkForwardReviewStatus,
    WalkForwardReviewSummary,
    build_walk_forward_review_template,
    summarize_walk_forward_review,
)

__all__ = [
    "ArtifactManifest",
    "SHARED_CORE_ID",
    "ReplayArtifactExportRequest",
    "ReplayArtifactExportResult",
    "export_local_replay_artifact",
    "EdgeGateCalibrationConfig",
    "EdgeGateCalibrationError",
    "EdgeGateCalibrationInsufficientDataError",
    "EdgeGateCalibrationReport",
    "EdgeGateCalibrationValidationError",
    "EdgeGateThresholdCalibration",
    "build_edge_gate_calibration_artifact",
    "calibrate_edge_gate_thresholds",
    "write_edge_gate_calibration_artifact",
    "LocalLabArtifactProofAssessment",
    "build_local_lab_artifact_proof_assessment",
    "LocalLabAblationStudy",
    "build_local_lab_ablation_study",
    "build_pending_local_lab_ablation_study",
    "LocalLabArtifactReleaseCandidate",
    "LocalLabArtifactReleaseScope",
    "LocalLabArtifactReleaseScopeSummary",
    "build_local_lab_artifact_release_candidate",
    "build_local_lab_artifact_release_scope_summary",
    "LocalLabScopeAnalysisMatrix",
    "LocalLabScopeAnalysisRow",
    "LocalLabScopeKey",
    "build_local_lab_scope_matrix",
    "build_local_lab_scope_slug",
    "discover_local_lab_scope_keys",
    "LocalLabFailureModeAggregate",
    "LocalLabRecalibrationAction",
    "LocalLabRecalibrationPlan",
    "build_local_lab_recalibration_plan",
    "LocalLabCalibrationMethodsReview",
    "LocalLabCalibrationMethodsStatus",
    "build_local_lab_calibration_methods_review",
    "LocalLabExecutionReview",
    "LocalLabExecutionReviewStatus",
    "LocalLabExecutionTelemetry",
    "LocalLabExecutionThresholdReview",
    "LocalLabExecutionRuntimeConsumerProjection",
    "LocalLabExecutionRuntimeProjection",
    "LocalLabExecutionRuntimeProjectionStatus",
    "build_local_lab_execution_review",
    "build_local_lab_execution_runtime_projection",
    "LocalLabMultipleTestingFamilyReview",
    "LocalLabMultipleTestingReview",
    "LocalLabMultipleTestingStatus",
    "build_hypothesis_test_family_review",
    "build_local_lab_multiple_testing_review",
    "LocalLabTailRiskBreakerEstimate",
    "LocalLabTailRiskReview",
    "LocalLabTailRiskStatus",
    "build_local_lab_tail_risk_review",
    "LocalLabCalibrationDataWindow",
    "LocalLabCalibrationOosReservation",
    "LocalLabCalibrationReproducibility",
    "LocalLabCalibrationThresholdReport",
    "LocalLabNormalizedCalibrationReport",
    "build_local_lab_calibration_normalized_report",
    "LocalLabLossSurrogateModel",
    "LocalLabLossSurrogateRecordScore",
    "LocalLabLossSurrogateReport",
    "LocalLabLossSurrogateScopeScore",
    "build_local_lab_loss_surrogate_report",
    "LocalLabResearchPriorityFeatures",
    "LocalLabResearchPriorityReport",
    "LocalLabResearchPriorityScope",
    "LocalLabResearchPriorityWeights",
    "build_local_lab_research_priority_report",
    "LocalLabReplayCandidate",
    "LocalLabReplayCandidateQueue",
    "build_local_lab_replay_candidate_queue",
    "LocalLabReplayTicket",
    "LocalLabReplayTicketIndex",
    "build_local_lab_replay_ticket_index",
    "LocalLabReplayDispatchItem",
    "LocalLabReplayDispatchPlan",
    "build_local_lab_replay_dispatch_plan",
    "LocalLabReplayWorkflowManifest",
    "build_local_lab_replay_workflow_manifest",
    "ReplayPairAggregate",
    "ReplayEngineAggregate",
    "ReplayMetricsSummary",
    "build_replay_metrics_summary",
    "export_replay_dtr_records",
    "load_replay_dtr_records",
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
    "ParityTolerancePolicy",
    "ReplayParityDiagnosticsSummary",
    "ShadowExecutionSimulatorConfig",
    "simulate_shadow_compatible_dtrs",
    "build_parity_diagnostics_payload",
    "WalkForwardHumanReview",
    "WalkForwardReviewStatus",
    "WalkForwardReviewSummary",
    "build_walk_forward_review_template",
    "summarize_walk_forward_review",
    "ReplayArtifactKind",
    "ReplayLifecycleState",
    "ArtifactActivationStage",
    "ArtifactHealthState",
    "ArtifactLogicFormat",
    "ArtifactActionKind",
    "ActionUnit",
    "HookId",
    "HOOK_MODULE_BY_ID",
    "LocalReplayRuntimeError",
    "RuntimeModeViolationError",
    "BacktestProfileForbiddenError",
    "ProfileForkForbiddenError",
]
