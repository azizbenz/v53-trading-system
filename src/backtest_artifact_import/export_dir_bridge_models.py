"""Typed models shared by the governed LOCAL_REPLAY export-dir bridge."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactExportBundle,
    ArtifactPayloadRefBundle,
    ArtifactSignatureEnvelope,
    ArtifactUploadDecision,
    ArtifactUploadRequest,
)
from interface_contracts import FeatureLineageLock, RuntimeMode, TransformWhitelistId, TransformWhitelistLock
from local_replay_runtime import LocalReplayRuntimeEvidence, ReplayExecutionPlan, ReplayRunManifest


class LocalReplayExportDiscovery(BaseModel, frozen=True):
    """Stable discovery result for a governed LOCAL_REPLAY export directory."""

    export_dir: Path
    run_manifest: ReplayRunManifest
    payload_bundle: ArtifactPayloadRefBundle


class ReplayPlanImportBuildContext(BaseModel, frozen=True):
    """Typed materialization of a governed replay plan into an import handshake."""

    replay_plan: ReplayExecutionPlan
    feature_lineage_lock: FeatureLineageLock
    transform_whitelist_lock: TransformWhitelistLock
    expected_feature_ids: tuple[str, ...] = ()
    expected_transform_ids: tuple[TransformWhitelistId, ...] = ()
    import_request: ArtifactImportRequest


class LocalReplayImportBuildContext(ReplayPlanImportBuildContext, frozen=True):
    """Typed materialization of the governed export -> import handshake."""

    export_discovery: LocalReplayExportDiscovery


class ReplayPlanUploadBuildContext(BaseModel, frozen=True):
    """Typed materialization of replay evidence into governed upload/import contracts."""

    import_context: ReplayPlanImportBuildContext
    local_replay_evidence: LocalReplayRuntimeEvidence
    artifact_bundle: ArtifactExportBundle
    signature_envelope: ArtifactSignatureEnvelope
    upload_request: ArtifactUploadRequest
    import_request: ArtifactImportRequest
    import_decision: ArtifactImportDecision | None = None
    upload_decision: ArtifactUploadDecision | None = None


__all__ = [
    "LocalReplayExportDiscovery",
    "LocalReplayImportBuildContext",
    "ReplayPlanImportBuildContext",
    "ReplayPlanUploadBuildContext",
]
