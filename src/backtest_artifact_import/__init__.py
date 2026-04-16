"""Controlled local->VPS artifact import scaffold."""

from __future__ import annotations

from backtest_artifact_import.contracts import (
    ArtifactCompatibilityCheckResult,
    ArtifactImportDecision,
    ArtifactPayloadRefBundle,
    ArtifactImportRequest,
    ArtifactImportSummary,
    ArtifactSignatureCheckResult,
    ArtifactSignatureCheckStatus,
    ArtifactUploadContext,
    ArtifactUploadDecision,
    ArtifactUploadRequest,
    ArtifactUploadStatus,
    StrategyLineageRecord,
    StrategyOnboardingDecision,
    StrategyOnboardingRequest,
)
from backtest_artifact_import.compatibility_policy import (
    DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY,
    evaluate_artifact_compatibility_policy,
)
from backtest_artifact_import.errors import ArtifactImportError, ImplicitPromotionForbiddenError
from backtest_artifact_import.signature_policy import (
    DEFAULT_ARTIFACT_TRUST_STORE,
    LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID,
    LAB_ARTIFACT_SIGNING_ACTIVE_PAYLOAD_HASH_SHA256,
    LAB_ARTIFACT_SIGNING_ACTIVE_SIGNATURE_B64,
    build_lab_fixture_signature_envelope,
    evaluate_artifact_signature_policy,
    verify_default_artifact_signature,
)
from backtest_artifact_import.monitoring_projection import build_replay_import_projection
from backtest_artifact_import.export_dir_bridge import (
    LocalReplayExportDiscovery,
    ReplayPlanImportBuildContext,
    ReplayPlanUploadBuildContext,
    LocalReplayImportBuildContext,
    build_feature_locks_from_feature_bridge,
    discover_local_replay_export,
    build_replay_plan_from_export_dir,
    build_import_context_from_replay_plan,
    build_artifact_export_bundle_from_replay_import_context,
    build_upload_request_from_replay_plan,
    build_upload_context_from_replay_import_context,
    build_import_context_from_export_dir,
    build_upload_request_from_export_dir,
)
from backtest_artifact_import.upload_bridge import (
    build_artifact_upload_decision,
    build_import_request_from_upload_request,
)
from backtest_artifact_import.validators import (
    summarize_import_request,
    validate_artifact_manifest,
    validate_import_request,
    validate_strategy_onboarding_request,
)

__all__ = [
    "ArtifactCompatibilityCheckResult",
    "ArtifactPayloadRefBundle",
    "ArtifactImportRequest",
    "ArtifactImportDecision",
    "ArtifactImportSummary",
    "ArtifactSignatureCheckStatus",
    "ArtifactSignatureCheckResult",
    "ArtifactUploadContext",
    "ArtifactUploadStatus",
    "ArtifactUploadRequest",
    "ArtifactUploadDecision",
    "StrategyLineageRecord",
    "StrategyOnboardingRequest",
    "StrategyOnboardingDecision",
    "DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY",
    "evaluate_artifact_compatibility_policy",
    "DEFAULT_ARTIFACT_TRUST_STORE",
    "LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID",
    "LAB_ARTIFACT_SIGNING_ACTIVE_PAYLOAD_HASH_SHA256",
    "LAB_ARTIFACT_SIGNING_ACTIVE_SIGNATURE_B64",
    "build_lab_fixture_signature_envelope",
    "evaluate_artifact_signature_policy",
    "verify_default_artifact_signature",
    "build_replay_import_projection",
    "LocalReplayExportDiscovery",
    "ReplayPlanImportBuildContext",
    "ReplayPlanUploadBuildContext",
    "LocalReplayImportBuildContext",
    "build_feature_locks_from_feature_bridge",
    "discover_local_replay_export",
    "build_replay_plan_from_export_dir",
    "build_import_context_from_replay_plan",
    "build_artifact_export_bundle_from_replay_import_context",
    "build_upload_request_from_replay_plan",
    "build_upload_context_from_replay_import_context",
    "build_import_context_from_export_dir",
    "build_upload_request_from_export_dir",
    "build_import_request_from_upload_request",
    "build_artifact_upload_decision",
    "validate_artifact_manifest",
    "validate_import_request",
    "summarize_import_request",
    "validate_strategy_onboarding_request",
    "ArtifactImportError",
    "ImplicitPromotionForbiddenError",
]
