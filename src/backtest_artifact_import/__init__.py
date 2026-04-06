"""Controlled local->VPS artifact import scaffold."""

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
    evaluate_artifact_signature_policy,
)
from backtest_artifact_import.monitoring_projection import build_replay_import_projection
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
    "evaluate_artifact_signature_policy",
    "build_replay_import_projection",
    "build_import_request_from_upload_request",
    "build_artifact_upload_decision",
    "validate_artifact_manifest",
    "validate_import_request",
    "summarize_import_request",
    "validate_strategy_onboarding_request",
    "ArtifactImportError",
    "ImplicitPromotionForbiddenError",
]
