from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueStatus,
    BinanceCredentialValidationStatus,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandStatus,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
    RuntimeMode,
    binance_credential_entry_from_manifest,
)
from protocols import (
    DashboardGovernedCommandExecutionContext,
    ShadowVpsServiceStore,
    initialize_dashboard_command_queue,
    load_dashboard_command_acks,
    load_dashboard_command_requests,
    load_dashboard_command_results,
    process_dashboard_command_queue_once,
    write_dashboard_command_request,
)
from tests.support_paths import make_repo_scratch_dir


def _queue_root(label: str) -> Path:
    return make_repo_scratch_dir("dashboard_command_queue_tests", label)


def _service_dir(label: str) -> Path:
    return make_repo_scratch_dir("dashboard_command_queue_service_tests", label)


def _manifest(*, kind: DashboardArtifactKind, source_ref: str) -> DashboardArtifactTransferManifest:
    return DashboardArtifactTransferManifest(
        artifact_hash="a" * 64,
        artifact_kind=kind,
        artifact_id="artifact-1",
        feature_set_version="lob_regime_feature_set.v2",
        feature_profile="extended_v2",
        lineage_version="a.v1.0.r1",
        source_ref=source_ref,
    )


def _secret_manifest() -> DashboardSecretTransferManifest:
    return DashboardSecretTransferManifest(
        secret_hash="b" * 64,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        profile_id="binance-live-001",
        environment=DashboardSecretEnvironment.LIVE,
        sealed_ref="secrets/binance-live-001.sealed.json",
        backend="dpapi",
        review_state="approved",
        validation_status="accepted",
    )


def test_process_dashboard_command_queue_once_round_trips_request_ack_and_result() -> None:
    queue_root = _queue_root("round_trip")
    try:
        initialize_dashboard_command_queue(queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-1",
            request_id="req-1",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )
        write_dashboard_command_request(queue_root, request)

        snapshot = process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset({request.command_kind}),
                regime_detector_shadow_audit_bundle_ref=(
                    "exports/regime_detector_shadow_audit_bundle.json"
                ),
            ),
        )

        requests = load_dashboard_command_requests(queue_root)
        acks = load_dashboard_command_acks(queue_root)
        results = load_dashboard_command_results(queue_root)
        assert len(requests) == 1
        assert len(acks) == 1
        assert len(results) == 1
        assert acks[0].status == DashboardGovernedCommandStatus.ACCEPTED
        assert results[0].status == DashboardGovernedCommandStatus.COMPLETED
        assert results[0].export_ref.endswith("regime_detector_shadow_audit_bundle.json")
        assert snapshot.queue_status == DashboardCommandQueueStatus.HEALTHY
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)


def test_write_dashboard_command_request_uses_atomic_json_publication() -> None:
    queue_root = _queue_root("atomic_request_write")
    try:
        initialize_dashboard_command_queue(queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-atomic",
            request_id="req-atomic",
            command_kind=DashboardGovernedCommandKind.SET_HALTED,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="operator halt",
        )

        request_path = write_dashboard_command_request(queue_root, request)

        assert request_path.read_text(encoding="utf-8").strip().startswith("{")
        assert not tuple(request_path.parent.glob("*.tmp_*"))
        requests = load_dashboard_command_requests(queue_root)
        assert len(requests) == 1
        assert requests[0].request_id == "req-atomic"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)


def test_process_dashboard_command_queue_once_is_idempotent_for_duplicate_request() -> None:
    queue_root = _queue_root("idempotent")
    try:
        initialize_dashboard_command_queue(queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-2",
            request_id="req-2",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )
        write_dashboard_command_request(queue_root, request)
        context = DashboardGovernedCommandExecutionContext(
            allowed_commands=frozenset({request.command_kind}),
            active_regime_detector_artifact=_manifest(
                kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
                source_ref="exports/regime_detector_artifact.json",
            ),
        )

        process_dashboard_command_queue_once(queue_root, context=context)
        process_dashboard_command_queue_once(queue_root, context=context)

        assert len(load_dashboard_command_acks(queue_root)) == 1
        assert len(load_dashboard_command_results(queue_root)) == 1
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)


def test_upload_ml_artifact_persists_active_manifest_in_shadow_vps_state() -> None:
    queue_root = _queue_root("upload_ml_persist")
    service_dir = _service_dir("upload_ml_persist")
    try:
        initialize_dashboard_command_queue(queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-4",
            request_id="req-4",
            command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            artifact_manifest=_manifest(
                kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                source_ref="exports/active_ml_artifact.json",
            ),
        )
        write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset({request.command_kind}),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        persisted = ShadowVpsServiceStore(service_dir).state
        assert persisted.active_ml_artifact is not None
        assert persisted.active_ml_artifact.source_ref == "exports/active_ml_artifact.json"
        assert persisted.dashboard_control_last_request_id == "req-4"
        assert persisted.dashboard_control_last_result_status == "completed"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_export_active_ml_artifact_reads_persisted_shadow_vps_state() -> None:
    queue_root = _queue_root("export_active_ml_persisted")
    service_dir = _service_dir("export_active_ml_persisted")
    try:
        initialize_dashboard_command_queue(queue_root)
        store = ShadowVpsServiceStore(service_dir)
        store.update_state(
            active_ml_artifact=_manifest(
                kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                source_ref="exports/persisted_ml_artifact.json",
            )
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-5",
            request_id="req-5",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )
        write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset({request.command_kind}),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        results = load_dashboard_command_results(queue_root)
        assert len(results) == 1
        assert results[0].status == DashboardGovernedCommandStatus.COMPLETED
        assert results[0].export_ref == "exports/persisted_ml_artifact.json"
        assert results[0].artifact_manifest is not None
        assert results[0].artifact_manifest.source_ref == "exports/persisted_ml_artifact.json"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_upload_and_export_regime_detector_artifact_use_persisted_state() -> None:
    queue_root = _queue_root("upload_export_regime")
    service_dir = _service_dir("upload_export_regime")
    try:
        initialize_dashboard_command_queue(queue_root)
        upload_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-5b",
            request_id="req-5b",
            command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            artifact_manifest=_manifest(
                kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
                source_ref="exports/persisted_regime_detector_artifact.json",
            ),
        )
        export_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_100,
            correlation_id="corr-queue-5c",
            request_id="req-5c",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )
        write_dashboard_command_request(queue_root, upload_request)
        write_dashboard_command_request(queue_root, export_request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset(
                    {upload_request.command_kind, export_request.command_kind}
                ),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        persisted = ShadowVpsServiceStore(service_dir).state
        assert persisted.active_regime_detector_artifact is not None
        assert (
            persisted.active_regime_detector_artifact.source_ref
            == "exports/persisted_regime_detector_artifact.json"
        )
        results = load_dashboard_command_results(queue_root)
        assert len(results) == 2
        assert results[-1].status == DashboardGovernedCommandStatus.COMPLETED
        assert results[-1].export_ref == "exports/persisted_regime_detector_artifact.json"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_binance_credential_upload_activate_export_and_deactivate_use_persisted_state() -> None:
    queue_root = _queue_root("binance_credentials_lifecycle")
    service_dir = _service_dir("binance_credentials_lifecycle")
    try:
        initialize_dashboard_command_queue(queue_root)
        ShadowVpsServiceStore(service_dir).update_state(
            dashboard_control_halted=True,
            dashboard_control_target_deployment_state="halted",
        )
        upload_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-credentials-upload",
            request_id="req-credentials-upload",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="upload reviewed sealed credentials",
            secret_manifest=_secret_manifest(),
        )
        activate_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_100,
            correlation_id="corr-queue-credentials-activate",
            request_id="req-credentials-activate",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="activate reviewed sealed credentials",
            target_secret_profile="binance-live-001",
        )
        export_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_200,
            correlation_id="corr-queue-credentials-export",
            request_id="req-credentials-export",
            command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
        )
        deactivate_request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_300,
            correlation_id="corr-queue-credentials-deactivate",
            request_id="req-credentials-deactivate",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="deactivate reviewed sealed credentials",
            target_secret_profile="binance-live-001",
        )
        for request in (
            upload_request,
            activate_request,
            export_request,
            deactivate_request,
        ):
            write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset(
                    {
                        upload_request.command_kind,
                        activate_request.command_kind,
                        export_request.command_kind,
                        deactivate_request.command_kind,
                    }
                ),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        persisted = ShadowVpsServiceStore(service_dir).state
        assert len(persisted.binance_credential_inventory) == 1
        assert persisted.binance_credential_inventory[0].profile.secret_hash == "b" * 64
        assert (
            persisted.binance_credential_inventory[0].validation_status
            == BinanceCredentialValidationStatus.DEACTIVATED
        )
        assert persisted.active_binance_credential_profile_id == ""
        assert persisted.active_binance_credential_environment == ""
        assert persisted.binance_credential_validation_status == "deactivated"
        results = load_dashboard_command_results(queue_root)
        assert len(results) == 4
        assert results[1].status == DashboardGovernedCommandStatus.COMPLETED
        assert results[2].credential_inventory is not None
        assert results[2].credential_inventory.active_profile_id == "binance-live-001"
        assert results[2].export_ref.endswith("binance_credential_inventory.json")
        for result in results:
            dumped = result.model_dump_json()
            assert "api-key" not in dumped
            assert "secret-key" not in dumped
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_binance_credential_activation_fails_when_profile_missing() -> None:
    queue_root = _queue_root("binance_credentials_missing")
    service_dir = _service_dir("binance_credentials_missing")
    try:
        initialize_dashboard_command_queue(queue_root)
        ShadowVpsServiceStore(service_dir).update_state(
            dashboard_control_halted=True,
            dashboard_control_target_deployment_state="halted",
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-credentials-missing",
            request_id="req-credentials-missing",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="activate missing profile",
            target_secret_profile="missing-profile",
        )
        write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset({request.command_kind}),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        results = load_dashboard_command_results(queue_root)
        assert len(results) == 1
        assert results[0].status == DashboardGovernedCommandStatus.FAILED
        assert results[0].reason_codes == (
            "dashboard.command.binance_credentials_profile_missing",
        )
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_binance_credential_activation_rejected_when_vps_not_halted_or_blocked() -> None:
    queue_root = _queue_root("binance_credentials_state_forbidden")
    service_dir = _service_dir("binance_credentials_state_forbidden")
    try:
        initialize_dashboard_command_queue(queue_root)
        store = ShadowVpsServiceStore(service_dir)
        store.update_state(
            binance_credential_inventory=(
                binance_credential_entry_from_manifest(_secret_manifest()),
            )
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-credentials-state-forbidden",
            request_id="req-credentials-state-forbidden",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="activate while running",
            target_secret_profile="binance-live-001",
        )
        write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset({request.command_kind}),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        results = load_dashboard_command_results(queue_root)
        assert len(results) == 1
        assert results[0].status == DashboardGovernedCommandStatus.REJECTED
        assert results[0].reason_codes == (
            "dashboard.command.binance_credentials_state_forbidden",
        )
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_control_commands_persist_halt_rollback_and_pair_engine_suspensions() -> None:
    queue_root = _queue_root("control_state")
    service_dir = _service_dir("control_state")
    try:
        initialize_dashboard_command_queue(queue_root)
        requests = (
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_000,
                correlation_id="corr-queue-6",
                request_id="req-6",
                command_kind=DashboardGovernedCommandKind.SET_HALTED,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="manual stop",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_100,
                correlation_id="corr-queue-7",
                request_id="req-7",
                command_kind=DashboardGovernedCommandKind.SUSPEND_PAIR,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="suspend pair",
                target_pair="BTCUSDT",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_200,
                correlation_id="corr-queue-8",
                request_id="req-8",
                command_kind=DashboardGovernedCommandKind.SUSPEND_ENGINE,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="suspend engine",
                target_engine="engine_c",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_300,
                correlation_id="corr-queue-9",
                request_id="req-9",
                command_kind=DashboardGovernedCommandKind.ROLLBACK_TO_LIGHT,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="rollback to governed light",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_400,
                correlation_id="corr-queue-10",
                request_id="req-10",
                command_kind=DashboardGovernedCommandKind.REQUEST_PAIR_RESUME,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="resume pair",
                target_pair="BTCUSDT",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_500,
                correlation_id="corr-queue-11",
                request_id="req-11",
                command_kind=DashboardGovernedCommandKind.REQUEST_ENGINE_RESUME,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="resume engine",
                target_engine="engine_c",
            ),
        )
        for request in requests:
            write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset(request.command_kind for request in requests),
                shadow_vps_service_state_dir=service_dir,
            ),
        )

        persisted = ShadowVpsServiceStore(service_dir).state
        assert persisted.dashboard_control_halted is False
        assert persisted.dashboard_control_target_profile == "light"
        assert persisted.dashboard_control_target_deployment_state == "rollback"
        assert persisted.dashboard_control_suspended_pairs == ()
        assert persisted.dashboard_control_suspended_engines == ()
        assert persisted.dashboard_control_last_request_id == "req-11"
        assert persisted.dashboard_control_last_command_kind == "request_engine_resume"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_process_dashboard_command_queue_once_rejects_forbidden_command() -> None:
    queue_root = _queue_root("forbidden")
    try:
        initialize_dashboard_command_queue(queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-queue-3",
            request_id="req-3",
            command_kind=DashboardGovernedCommandKind.SET_HALTED,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="manual stop",
        )
        write_dashboard_command_request(queue_root, request)

        process_dashboard_command_queue_once(
            queue_root,
            context=DashboardGovernedCommandExecutionContext(
                allowed_commands=frozenset(),
            ),
        )

        results = load_dashboard_command_results(queue_root)
        assert len(results) == 1
        assert results[0].status == DashboardGovernedCommandStatus.REJECTED
        assert results[0].reason_codes == ("dashboard.command.kind_not_allowed",)
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
