from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    RuntimeMode,
)


def _artifact_manifest() -> DashboardArtifactTransferManifest:
    return DashboardArtifactTransferManifest(
        artifact_hash="a" * 64,
        artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
        artifact_id="regime-artifact-1",
        feature_set_version="lob_regime_feature_set.v2",
        feature_profile="extended_v2",
        lineage_version="a.v1.0.r1",
        review_state="pending",
        validation_status="accepted",
        source_ref="exports/regime_detector_artifact.json",
    )


def test_dashboard_governed_command_request_rejects_missing_upload_manifest() -> None:
    with pytest.raises(ValidationError):
        DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-1",
            request_id="req-1",
            command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )


def test_dashboard_governed_command_request_requires_pair_target_and_reason() -> None:
    with pytest.raises(ValidationError):
        DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-2",
            request_id="req-2",
            command_kind=DashboardGovernedCommandKind.SUSPEND_PAIR,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )


def test_dashboard_governed_command_request_exposes_stable_idempotency_key() -> None:
    request = DashboardGovernedCommandRequest(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-dashboard-3",
        request_id="req-3",
        command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
        source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
        target_runtime_mode=RuntimeMode.LIVE,
        artifact_manifest=_artifact_manifest(),
    )

    assert request.idempotency_key == (
        "req-3:" + ("a" * 64) + ":request_upload_regime_detector_artifact"
    )


def test_dashboard_governed_command_result_rejects_failed_outcome_without_reason_codes() -> None:
    with pytest.raises(ValidationError):
        DashboardGovernedCommandResult(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-4",
            result_id="res-4",
            request_id="req-4",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
            status=DashboardGovernedCommandStatus.FAILED,
            idempotency_key="req-4:no_artifact:request_export_active_ml_artifact",
        )
