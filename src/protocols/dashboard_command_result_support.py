"""Result builders for the governed dashboard command queue."""

from __future__ import annotations

from interface_contracts import (
    BinanceCredentialInventoryEntry,
    BinanceCredentialInventorySnapshot,
    BinanceCredentialValidationStatus,
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    DashboardSecretTransferManifest,
    binance_credential_entry_from_manifest,
)


def completed_command_result(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    artifact_manifest: DashboardArtifactTransferManifest | None = None,
    secret_manifest: DashboardSecretTransferManifest | None = None,
    credential_inventory: BinanceCredentialInventorySnapshot | None = None,
    export_ref: str = "",
) -> DashboardGovernedCommandResult:
    return DashboardGovernedCommandResult(
        timestamp_ms=timestamp_ms,
        correlation_id=request.correlation_id,
        result_id=result_id,
        request_id=request.request_id,
        command_kind=request.command_kind,
        status=DashboardGovernedCommandStatus.COMPLETED,
        idempotency_key=request.idempotency_key,
        reason_codes=(f"dashboard.command.{request.command_kind.value}.completed",),
        detail=f"{request.command_kind.value} completed",
        artifact_manifest=artifact_manifest,
        secret_manifest=secret_manifest,
        credential_inventory=credential_inventory,
        export_ref=export_ref,
    )


def result_for_active_export(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    manifest: DashboardArtifactTransferManifest | None,
) -> DashboardGovernedCommandResult:
    if manifest is None:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.FAILED,
            idempotency_key=request.idempotency_key,
            reason_codes=("dashboard.command.active_artifact_missing",),
            detail=(
                f"{request.command_kind.value} could not find an active governed "
                "artifact"
            ),
            failure_stage="lookup_active_artifact",
        )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        artifact_manifest=manifest,
        export_ref=manifest.source_ref,
    )


def result_for_upload_request(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
) -> DashboardGovernedCommandResult:
    export_ref = (
        "" if request.artifact_manifest is None else request.artifact_manifest.source_ref
    )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        artifact_manifest=request.artifact_manifest,
        export_ref=export_ref,
    )


def result_for_secret_upload_request(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
) -> DashboardGovernedCommandResult:
    export_ref = "" if request.secret_manifest is None else request.secret_manifest.sealed_ref
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        secret_manifest=request.secret_manifest,
        export_ref=export_ref,
    )


def result_for_shadow_audit_export(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    shadow_audit_bundle_ref: str,
) -> DashboardGovernedCommandResult:
    if not shadow_audit_bundle_ref:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.FAILED,
            idempotency_key=request.idempotency_key,
            reason_codes=("dashboard.command.regime_detector_shadow_audit_missing",),
            detail="No VPS RegimeDetector shadow audit bundle is available for export",
            failure_stage="resolve_shadow_audit_bundle",
        )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        artifact_manifest=DashboardArtifactTransferManifest(
            artifact_hash="shadow_audit_bundle",
            artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
            source_ref=shadow_audit_bundle_ref,
        ),
        export_ref=shadow_audit_bundle_ref,
    )


def result_for_shadow_artifact_comparison_export(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    comparison_ref: str,
    artifact_id: str,
) -> DashboardGovernedCommandResult:
    return result_for_generic_export_bundle(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        export_ref=comparison_ref,
        artifact_id=artifact_id,
        missing_reason_code="dashboard.command.shadow_artifact_comparison_missing",
        missing_detail="No Shadow challenger comparison evidence is available for export",
        missing_failure_stage="resolve_shadow_artifact_comparison_evidence",
        artifact_hash="shadow_artifact_comparison_evidence",
    )


def result_for_generic_export_bundle(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    export_ref: str,
    artifact_id: str,
    missing_reason_code: str,
    missing_detail: str,
    missing_failure_stage: str,
    artifact_hash: str = "generic_export_bundle",
) -> DashboardGovernedCommandResult:
    if not export_ref:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.FAILED,
            idempotency_key=request.idempotency_key,
            reason_codes=(missing_reason_code,),
            detail=missing_detail,
            failure_stage=missing_failure_stage,
        )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        artifact_manifest=DashboardArtifactTransferManifest(
            artifact_hash=artifact_hash,
            artifact_kind=DashboardArtifactKind.GENERIC_EXPORT_BUNDLE,
            artifact_id=artifact_id,
            source_ref=export_ref,
        ),
        export_ref=export_ref,
    )


def find_credential_profile_entry(
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    *,
    profile_id: str,
) -> BinanceCredentialInventoryEntry | None:
    for entry in inventory:
        if entry.profile.profile_id == profile_id:
            return entry
    return None


def result_for_credential_profile_request(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    profile_change_allowed: bool,
) -> DashboardGovernedCommandResult:
    if not profile_change_allowed:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.REJECTED,
            idempotency_key=request.idempotency_key,
            reason_codes=("dashboard.command.binance_credentials_state_forbidden",),
            detail="Binance credential profile changes require halted or blocked VPS state",
            failure_stage="credential_profile_governance",
        )
    entry = find_credential_profile_entry(
        inventory,
        profile_id=request.target_secret_profile,
    )
    if entry is None:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.FAILED,
            idempotency_key=request.idempotency_key,
            reason_codes=("dashboard.command.binance_credentials_profile_missing",),
            detail="Binance credential profile is not present in the governed inventory",
            failure_stage="lookup_binance_credential_profile",
        )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        export_ref=entry.profile.sealed_ref,
    )


def result_for_credential_inventory_export(
    request: DashboardGovernedCommandRequest,
    *,
    result_id: str,
    timestamp_ms: int,
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    active_profile_id: str,
    export_ref: str,
) -> DashboardGovernedCommandResult:
    inventory_snapshot = BinanceCredentialInventorySnapshot(
        active_profile_id=active_profile_id,
        entries=inventory,
        exported_at_ms=timestamp_ms,
    )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
        credential_inventory=inventory_snapshot,
        export_ref=export_ref,
    )


def replace_credential_entry(
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    manifest: DashboardSecretTransferManifest,
) -> tuple[BinanceCredentialInventoryEntry, ...]:
    by_profile = {item.profile.profile_id: item for item in inventory}
    by_profile[manifest.profile_id] = binance_credential_entry_from_manifest(manifest)
    return tuple(by_profile[key] for key in sorted(by_profile))


def set_active_credential_entry(
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    *,
    profile_id: str,
) -> tuple[BinanceCredentialInventoryEntry, ...]:
    return tuple(
        entry.model_copy(
            update={
                "active": entry.profile.profile_id == profile_id,
                "validation_status": (
                    BinanceCredentialValidationStatus.PENDING
                    if entry.profile.profile_id == profile_id
                    else entry.validation_status
                ),
            }
        )
        for entry in inventory
    )


def deactivate_credential_entry(
    inventory: tuple[BinanceCredentialInventoryEntry, ...],
    *,
    profile_id: str,
) -> tuple[BinanceCredentialInventoryEntry, ...]:
    return tuple(
        entry.model_copy(
            update={
                "active": False,
                "validation_status": (
                    BinanceCredentialValidationStatus.DEACTIVATED
                    if entry.profile.profile_id == profile_id
                    else entry.validation_status
                ),
            }
        )
        for entry in inventory
    )
