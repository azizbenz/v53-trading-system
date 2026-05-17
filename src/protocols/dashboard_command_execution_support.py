"""Execution and state helpers for the governed dashboard command queue."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from interface_contracts import (
    BinanceCredentialInventoryEntry,
    BinanceCredentialValidationStatus,
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    DeploymentState,
    ProfileId,
)
from .dashboard_command_result_support import (
    completed_command_result,
    deactivate_credential_entry,
    find_credential_profile_entry,
    replace_credential_entry,
    result_for_active_export,
    result_for_credential_inventory_export,
    result_for_credential_profile_request,
    result_for_generic_export_bundle,
    result_for_secret_upload_request,
    result_for_shadow_artifact_comparison_export,
    result_for_shadow_audit_export,
    result_for_upload_request,
    set_active_credential_entry,
)
from .shadow_vps_service import ShadowVpsServiceStore

if TYPE_CHECKING:
    from .dashboard_command_queue import DashboardGovernedCommandExecutionContext


def _load_shadow_vps_service_store(
    context: DashboardGovernedCommandExecutionContext,
) -> ShadowVpsServiceStore | None:
    if context.shadow_vps_service_state_dir is None:
        return None
    return ShadowVpsServiceStore(Path(context.shadow_vps_service_state_dir))


def _resolve_active_manifest(
    context: DashboardGovernedCommandExecutionContext,
    *,
    artifact_kind: DashboardArtifactKind,
) -> DashboardArtifactTransferManifest | None:
    store = _load_shadow_vps_service_store(context)
    if artifact_kind == DashboardArtifactKind.ML_MODEL_ARTIFACT:
        persisted = None if store is None else store.state.active_ml_artifact
        return persisted or context.active_ml_artifact
    persisted = None if store is None else store.state.active_regime_detector_artifact
    return persisted or context.active_regime_detector_artifact


def _resolve_shadow_challenger_manifest(
    context: DashboardGovernedCommandExecutionContext,
    *,
    artifact_kind: DashboardArtifactKind,
) -> DashboardArtifactTransferManifest | None:
    store = _load_shadow_vps_service_store(context)
    if artifact_kind == DashboardArtifactKind.ML_MODEL_ARTIFACT:
        persisted = None if store is None else store.state.shadow_ml_challenger_artifact
        return persisted or context.shadow_ml_challenger_artifact
    persisted = (
        None if store is None else store.state.shadow_regime_detector_challenger_artifact
    )
    return persisted or context.shadow_regime_detector_challenger_artifact


def _resolve_shadow_audit_bundle_ref(
    context: DashboardGovernedCommandExecutionContext,
) -> str:
    store = _load_shadow_vps_service_store(context)
    persisted = (
        ""
        if store is None
        else store.state.active_regime_detector_shadow_audit_bundle_ref
    )
    return persisted or context.regime_detector_shadow_audit_bundle_ref


def _resolve_shadow_artifact_comparison_ref(
    context: DashboardGovernedCommandExecutionContext,
    *,
    artifact_kind: DashboardArtifactKind,
) -> str:
    store = _load_shadow_vps_service_store(context)
    if artifact_kind == DashboardArtifactKind.ML_MODEL_ARTIFACT:
        persisted = (
            ""
            if store is None
            else store.state.last_shadow_ml_artifact_comparison_ref
        )
        return persisted or context.shadow_ml_artifact_comparison_ref
    persisted = (
        ""
        if store is None
        else store.state.last_shadow_regime_detector_artifact_comparison_ref
    )
    return persisted or context.shadow_regime_detector_artifact_comparison_ref


def _resolve_shadow_challenger_verdict_bundle_ref(
    context: DashboardGovernedCommandExecutionContext,
) -> str:
    store = _load_shadow_vps_service_store(context)
    persisted = (
        ""
        if store is None
        else store.state.last_shadow_challenger_verdict_bundle_ref
    )
    return persisted or context.shadow_challenger_verdict_bundle_ref


def _credential_inventory(
    context: DashboardGovernedCommandExecutionContext,
) -> tuple[BinanceCredentialInventoryEntry, ...]:
    store = _load_shadow_vps_service_store(context)
    persisted = () if store is None else store.state.binance_credential_inventory
    return persisted or context.binance_credential_inventory


def _credential_state_allows_profile_change(
    context: DashboardGovernedCommandExecutionContext,
) -> bool:
    store = _load_shadow_vps_service_store(context)
    if store is None:
        return False
    state = store.state
    return (
        state.dashboard_control_halted
        or state.dashboard_control_target_deployment_state == DeploymentState.HALTED.value
        or state.last_vps_warmup_final_state == "blocked"
        or state.last_vps_recovery_status == "blocked"
    )


def _sorted_unique(values: tuple[str, ...], new_value: str) -> tuple[str, ...]:
    if not new_value:
        return values
    return tuple(sorted(set(values) | {new_value}))


def _without_value(values: tuple[str, ...], removed_value: str) -> tuple[str, ...]:
    if not removed_value:
        return values
    return tuple(value for value in values if value != removed_value)


def _comparison_reset_status(
    challenger_manifest: DashboardArtifactTransferManifest | None,
) -> str:
    return "shadow_pending_evidence" if challenger_manifest is not None else "not_available"


def _verdict_reset_status(
    *,
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None,
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None,
) -> str:
    if (
        shadow_ml_challenger_artifact is not None
        or shadow_regime_detector_challenger_artifact is not None
    ):
        return "shadow_pending_evidence"
    return "not_available"


def _build_state_updates(
    store: ShadowVpsServiceStore,
    request: DashboardGovernedCommandRequest,
    result: DashboardGovernedCommandResult,
) -> dict[str, object]:
    state = store.state
    updates: dict[str, object] = {
        "dashboard_control_last_request_id": request.request_id,
        "dashboard_control_last_command_kind": request.command_kind.value,
        "dashboard_control_last_operator_reason": request.operator_reason,
        "dashboard_control_last_result_status": result.status.value,
        "dashboard_control_last_command_timestamp_ms": request.timestamp_ms,
    }
    if result.status != DashboardGovernedCommandStatus.COMPLETED:
        return updates

    ml_challenger = state.shadow_ml_challenger_artifact
    regime_challenger = state.shadow_regime_detector_challenger_artifact

    if request.command_kind == DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT:
        updates["active_ml_artifact"] = request.artifact_manifest
        updates["last_shadow_ml_artifact_comparison_ref"] = ""
        updates["last_shadow_ml_artifact_comparison_status"] = _comparison_reset_status(
            ml_challenger
        )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT
    ):
        updates["active_regime_detector_artifact"] = request.artifact_manifest
        updates["last_shadow_regime_detector_artifact_comparison_ref"] = ""
        updates["last_shadow_regime_detector_artifact_comparison_status"] = (
            _comparison_reset_status(regime_challenger)
        )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT
    ):
        ml_challenger = request.artifact_manifest
        updates["shadow_ml_challenger_artifact"] = ml_challenger
        updates["last_shadow_ml_artifact_comparison_ref"] = ""
        updates["last_shadow_ml_artifact_comparison_status"] = _comparison_reset_status(
            ml_challenger
        )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT
    ):
        regime_challenger = request.artifact_manifest
        updates["shadow_regime_detector_challenger_artifact"] = regime_challenger
        updates["last_shadow_regime_detector_artifact_comparison_ref"] = ""
        updates["last_shadow_regime_detector_artifact_comparison_status"] = (
            _comparison_reset_status(regime_challenger)
        )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_CLEAR_SHADOW_ML_CHALLENGER_ARTIFACT
    ):
        ml_challenger = None
        updates["shadow_ml_challenger_artifact"] = None
        updates["last_shadow_ml_artifact_comparison_ref"] = ""
        updates["last_shadow_ml_artifact_comparison_status"] = "not_available"
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_CLEAR_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT
    ):
        regime_challenger = None
        updates["shadow_regime_detector_challenger_artifact"] = None
        updates["last_shadow_regime_detector_artifact_comparison_ref"] = ""
        updates["last_shadow_regime_detector_artifact_comparison_status"] = "not_available"
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
    ):
        if request.secret_manifest is not None:
            updates["binance_credential_inventory"] = replace_credential_entry(
                state.binance_credential_inventory,
                request.secret_manifest,
            )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE
    ):
        entry = find_credential_profile_entry(
            state.binance_credential_inventory,
            profile_id=request.target_secret_profile,
        )
        if entry is not None:
            updates["binance_credential_inventory"] = set_active_credential_entry(
                state.binance_credential_inventory,
                profile_id=request.target_secret_profile,
            )
            updates["active_binance_credential_profile_id"] = request.target_secret_profile
            updates["active_binance_credential_environment"] = (
                entry.profile.environment.value
            )
            updates["binance_credential_validation_status"] = (
                BinanceCredentialValidationStatus.PENDING.value
            )
            updates["binance_credential_last_failure_reason_codes"] = ()
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE
    ):
        if state.active_binance_credential_profile_id == request.target_secret_profile:
            updates["binance_credential_inventory"] = deactivate_credential_entry(
                state.binance_credential_inventory,
                profile_id=request.target_secret_profile,
            )
            updates["active_binance_credential_profile_id"] = ""
            updates["active_binance_credential_environment"] = ""
            updates["binance_credential_validation_status"] = (
                BinanceCredentialValidationStatus.DEACTIVATED.value
            )
            updates["binance_credential_last_failure_reason_codes"] = ()
    elif request.command_kind == DashboardGovernedCommandKind.SET_HALTED:
        updates["dashboard_control_halted"] = True
        updates["dashboard_control_target_deployment_state"] = (
            DeploymentState.HALTED.value
        )
    elif request.command_kind == DashboardGovernedCommandKind.ROLLBACK_TO_LIGHT:
        updates["dashboard_control_halted"] = False
        updates["dashboard_control_target_profile"] = ProfileId.LIGHT.value
        updates["dashboard_control_target_deployment_state"] = (
            DeploymentState.ROLLBACK.value
        )
    elif request.command_kind == DashboardGovernedCommandKind.SUSPEND_PAIR:
        updates["dashboard_control_suspended_pairs"] = _sorted_unique(
            state.dashboard_control_suspended_pairs,
            request.target_pair,
        )
    elif request.command_kind == DashboardGovernedCommandKind.REQUEST_PAIR_RESUME:
        updates["dashboard_control_suspended_pairs"] = _without_value(
            state.dashboard_control_suspended_pairs,
            request.target_pair,
        )
    elif request.command_kind == DashboardGovernedCommandKind.SUSPEND_ENGINE:
        updates["dashboard_control_suspended_engines"] = _sorted_unique(
            state.dashboard_control_suspended_engines,
            request.target_engine,
        )
    elif request.command_kind == DashboardGovernedCommandKind.REQUEST_ENGINE_RESUME:
        updates["dashboard_control_suspended_engines"] = _without_value(
            state.dashboard_control_suspended_engines,
            request.target_engine,
        )
    elif (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE
        and result.export_ref
    ):
        updates["active_regime_detector_shadow_audit_bundle_ref"] = result.export_ref

    if request.command_kind in {
        DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_CLEAR_SHADOW_ML_CHALLENGER_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_CLEAR_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT,
    }:
        updates["last_shadow_challenger_verdict_bundle_ref"] = ""
        updates["last_shadow_challenger_verdict_bundle_status"] = _verdict_reset_status(
            shadow_ml_challenger_artifact=ml_challenger,
            shadow_regime_detector_challenger_artifact=regime_challenger,
        )
    return updates


def _persist_command_result_state(
    context: DashboardGovernedCommandExecutionContext,
    request: DashboardGovernedCommandRequest,
    result: DashboardGovernedCommandResult,
) -> None:
    store = _load_shadow_vps_service_store(context)
    if store is None:
        return
    store.update_state(**_build_state_updates(store, request, result))


def execute_dashboard_governed_command(
    request: DashboardGovernedCommandRequest,
    *,
    context: DashboardGovernedCommandExecutionContext,
    timestamp_ms: int,
) -> DashboardGovernedCommandResult:
    """Execute one governed dashboard command against the bounded VPS context."""

    result_id = f"{request.request_id}.result"
    if request.command_kind not in context.allowed_commands:
        return DashboardGovernedCommandResult(
            timestamp_ms=timestamp_ms,
            correlation_id=request.correlation_id,
            result_id=result_id,
            request_id=request.request_id,
            command_kind=request.command_kind,
            status=DashboardGovernedCommandStatus.REJECTED,
            idempotency_key=request.idempotency_key,
            reason_codes=("dashboard.command.kind_not_allowed",),
            detail=f"{request.command_kind.value} is outside the governed VPS command surface",
            failure_stage="governance_surface",
        )
    if request.command_kind in {
        DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT,
    }:
        return result_for_upload_request(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
    ):
        return result_for_secret_upload_request(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
        )
    if request.command_kind in {
        DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        DashboardGovernedCommandKind.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
    }:
        return result_for_credential_profile_request(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            inventory=_credential_inventory(context),
            profile_change_allowed=_credential_state_allows_profile_change(context),
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY
    ):
        store = _load_shadow_vps_service_store(context)
        active_profile_id = (
            "" if store is None else store.state.active_binance_credential_profile_id
        )
        return result_for_credential_inventory_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            inventory=_credential_inventory(context),
            active_profile_id=active_profile_id,
            export_ref=context.binance_credential_inventory_export_ref,
        )
    if request.command_kind == DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT:
        return result_for_active_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            manifest=_resolve_active_manifest(
                context,
                artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
            ),
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT
    ):
        return result_for_active_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            manifest=_resolve_active_manifest(
                context,
                artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            ),
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_ML_ARTIFACT_COMPARISON_EVIDENCE
    ):
        return result_for_shadow_artifact_comparison_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            comparison_ref=_resolve_shadow_artifact_comparison_ref(
                context,
                artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
            ),
            artifact_id="shadow_ml_artifact_comparison_evidence",
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_REGIME_DETECTOR_ARTIFACT_COMPARISON_EVIDENCE
    ):
        return result_for_shadow_artifact_comparison_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            comparison_ref=_resolve_shadow_artifact_comparison_ref(
                context,
                artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            ),
            artifact_id="shadow_regime_detector_artifact_comparison_evidence",
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE
    ):
        return result_for_generic_export_bundle(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            export_ref=_resolve_shadow_challenger_verdict_bundle_ref(context),
            artifact_id="shadow_challenger_verdict_bundle",
            missing_reason_code="dashboard.command.shadow_challenger_verdict_missing",
            missing_detail="No Shadow challenger verdict bundle is available for export",
            missing_failure_stage="resolve_shadow_challenger_verdict_bundle",
            artifact_hash="shadow_challenger_verdict_bundle",
        )
    if (
        request.command_kind
        == DashboardGovernedCommandKind.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE
    ):
        return result_for_shadow_audit_export(
            request,
            result_id=result_id,
            timestamp_ms=timestamp_ms,
            shadow_audit_bundle_ref=_resolve_shadow_audit_bundle_ref(context),
        )
    return completed_command_result(
        request,
        result_id=result_id,
        timestamp_ms=timestamp_ms,
    )


__all__ = [
    "_persist_command_result_state",
    "execute_dashboard_governed_command",
]
