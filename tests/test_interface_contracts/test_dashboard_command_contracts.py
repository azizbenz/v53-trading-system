from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    BinanceCredentialInventorySnapshot,
    BinanceCredentialValidationStatus,
    binance_credential_entry_from_manifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
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


def _secret_manifest() -> DashboardSecretTransferManifest:
    return DashboardSecretTransferManifest(
        secret_hash="b" * 64,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        profile_id="binance-live-001",
        environment=DashboardSecretEnvironment.LIVE,
        sealed_ref="secrets/binance-live-001.sealed.json",
        review_state="approved",
        validation_status="accepted",
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


def test_dashboard_secret_manifest_rejects_plaintext_secret_ref() -> None:
    with pytest.raises(ValidationError):
        DashboardSecretTransferManifest(
            secret_hash="b" * 64,
            secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
            profile_id="binance-live-001",
            environment=DashboardSecretEnvironment.LIVE,
            sealed_ref="secrets/binance-live-001.yml",
        )


def test_dashboard_secret_manifest_rejects_invalid_secret_hash() -> None:
    with pytest.raises(ValidationError):
        DashboardSecretTransferManifest(
            secret_hash="B" * 64,
            secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
            profile_id="binance-live-001",
            environment=DashboardSecretEnvironment.LIVE,
            sealed_ref="secrets/binance-live-001.sealed.json",
        )


def test_dashboard_secret_manifest_rejects_traversal_sealed_ref() -> None:
    with pytest.raises(ValidationError):
        DashboardSecretTransferManifest(
            secret_hash="b" * 64,
            secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
            profile_id="binance-live-001",
            environment=DashboardSecretEnvironment.LIVE,
            sealed_ref="../binance-live-001.sealed.json",
        )


def test_dashboard_binance_credential_upload_requires_secret_manifest() -> None:
    with pytest.raises(ValidationError):
        DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-5",
            request_id="req-5",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="upload sealed Binance profile",
        )


def test_dashboard_binance_credential_upload_idempotency_uses_secret_hash() -> None:
    request = DashboardGovernedCommandRequest(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-dashboard-6",
        request_id="req-6",
        command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
        source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
        target_runtime_mode=RuntimeMode.LIVE,
        operator_reason="upload sealed Binance profile",
        secret_manifest=_secret_manifest(),
    )

    assert request.idempotency_key == (
        "req-6:" + ("b" * 64) + ":request_upload_binance_credentials_bundle"
    )


def test_dashboard_binance_profile_activation_requires_target_and_reason() -> None:
    with pytest.raises(ValidationError):
        DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-7",
            request_id="req-7",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )


def test_binance_credential_inventory_snapshot_is_metadata_only_and_unique() -> None:
    entry = binance_credential_entry_from_manifest(
        _secret_manifest(),
        active=True,
        validation_status=BinanceCredentialValidationStatus.VALIDATED,
    )
    snapshot = BinanceCredentialInventorySnapshot(
        active_profile_id="binance-live-001",
        entries=(entry,),
        exported_at_ms=1_700_000_000_000,
    )

    dumped = snapshot.model_dump_json()
    assert snapshot.entries[0].profile.secret_hash == "b" * 64
    assert "api-key-value" not in dumped
    assert "secret-key-value" not in dumped
    assert "api_key" not in dumped
    assert "secret_key" not in dumped


def test_binance_credential_inventory_rejects_duplicate_profiles() -> None:
    entry = binance_credential_entry_from_manifest(_secret_manifest())

    with pytest.raises(ValidationError):
        BinanceCredentialInventorySnapshot(entries=(entry, entry))
