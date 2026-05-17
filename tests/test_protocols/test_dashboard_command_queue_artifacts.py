from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import (
    DashboardArtifactKind,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandStatus,
    RuntimeMode,
)
from protocols import (
    DashboardGovernedCommandExecutionContext,
    ShadowVpsServiceStore,
    initialize_dashboard_command_queue,
    load_dashboard_command_results,
    process_dashboard_command_queue_once,
    write_dashboard_command_request,
)
from tests.support_paths import make_repo_scratch_dir


def _queue_root(label: str) -> Path:
    return make_repo_scratch_dir("dashboard_command_queue_tests", label)


def _service_dir(label: str) -> Path:
    return make_repo_scratch_dir("dashboard_command_queue_service_tests", label)


def _manifest(*, kind: DashboardArtifactKind, source_ref: str):
    from interface_contracts import DashboardArtifactTransferManifest

    return DashboardArtifactTransferManifest(
        artifact_hash="a" * 64,
        artifact_kind=kind,
        artifact_id="artifact-1",
        feature_set_version="lob_regime_feature_set.v2",
        feature_profile="extended_v2",
        lineage_version="a.v1.0.r1",
        source_ref=source_ref,
    )


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


def test_upload_shadow_ml_challenger_persists_only_challenger_manifest() -> None:
    queue_root = _queue_root("upload_shadow_ml_challenger")
    service_dir = _service_dir("upload_shadow_ml_challenger")
    try:
        initialize_dashboard_command_queue(queue_root)
        store = ShadowVpsServiceStore(service_dir)
        store.update_state(
            active_ml_artifact=_manifest(
                kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                source_ref="exports/active_ml_artifact.json",
            )
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-shadow-ml-challenger",
            request_id="req-shadow-ml-challenger",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.SHADOW,
            artifact_manifest=_manifest(
                kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                source_ref="exports/shadow_ml_challenger_artifact.json",
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
        assert persisted.shadow_ml_challenger_artifact is not None
        assert (
            persisted.shadow_ml_challenger_artifact.source_ref
            == "exports/shadow_ml_challenger_artifact.json"
        )
        assert persisted.last_shadow_ml_artifact_comparison_status == "shadow_pending_evidence"
        assert persisted.last_shadow_challenger_verdict_bundle_status == "shadow_pending_evidence"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_shadow_regime_challenger_clear_only_resets_challenger_slot() -> None:
    queue_root = _queue_root("clear_shadow_regime_challenger")
    service_dir = _service_dir("clear_shadow_regime_challenger")
    try:
        initialize_dashboard_command_queue(queue_root)
        store = ShadowVpsServiceStore(service_dir)
        store.update_state(
            active_regime_detector_artifact=_manifest(
                kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
                source_ref="exports/active_regime_detector_artifact.json",
            ),
            shadow_regime_detector_challenger_artifact=_manifest(
                kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
                source_ref="exports/shadow_regime_detector_challenger.json",
            ),
            last_shadow_regime_detector_artifact_comparison_ref="exports/compare_regime.json",
            last_shadow_regime_detector_artifact_comparison_status="shadow_ready",
            last_shadow_challenger_verdict_bundle_ref="exports/verdict_bundle.json",
            last_shadow_challenger_verdict_bundle_status="shadow_validated",
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-clear-shadow-regime",
            request_id="req-clear-shadow-regime",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_CLEAR_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT
            ),
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.SHADOW,
            operator_reason="clear stale challenger",
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
        assert persisted.active_regime_detector_artifact is not None
        assert (
            persisted.active_regime_detector_artifact.source_ref
            == "exports/active_regime_detector_artifact.json"
        )
        assert persisted.shadow_regime_detector_challenger_artifact is None
        assert persisted.last_shadow_regime_detector_artifact_comparison_ref == ""
        assert persisted.last_shadow_regime_detector_artifact_comparison_status == "not_available"
        assert persisted.last_shadow_challenger_verdict_bundle_ref == ""
        assert persisted.last_shadow_challenger_verdict_bundle_status == "not_available"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_export_shadow_ml_artifact_comparison_reads_persisted_state() -> None:
    queue_root = _queue_root("export_shadow_ml_comparison")
    service_dir = _service_dir("export_shadow_ml_comparison")
    try:
        initialize_dashboard_command_queue(queue_root)
        ShadowVpsServiceStore(service_dir).update_state(
            shadow_ml_challenger_artifact=_manifest(
                kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                source_ref="exports/shadow_ml_challenger_artifact.json",
            ),
            last_shadow_ml_artifact_comparison_ref="exports/shadow_ml_comparison.json",
            last_shadow_ml_artifact_comparison_status="shadow_ready",
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-export-shadow-ml-comparison",
            request_id="req-export-shadow-ml-comparison",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_ML_ARTIFACT_COMPARISON_EVIDENCE
            ),
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
        assert results[0].export_ref == "exports/shadow_ml_comparison.json"
        assert results[0].artifact_manifest is not None
        assert results[0].artifact_manifest.artifact_kind == DashboardArtifactKind.GENERIC_EXPORT_BUNDLE
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_export_shadow_regime_artifact_comparison_reads_persisted_state() -> None:
    queue_root = _queue_root("export_shadow_regime_comparison")
    service_dir = _service_dir("export_shadow_regime_comparison")
    try:
        initialize_dashboard_command_queue(queue_root)
        ShadowVpsServiceStore(service_dir).update_state(
            shadow_regime_detector_challenger_artifact=_manifest(
                kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
                source_ref="exports/shadow_regime_detector_challenger.json",
            ),
            last_shadow_regime_detector_artifact_comparison_ref=(
                "exports/shadow_regime_comparison.json"
            ),
            last_shadow_regime_detector_artifact_comparison_status="shadow_runtime_inputs_missing",
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-export-shadow-regime-comparison",
            request_id="req-export-shadow-regime-comparison",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_REGIME_DETECTOR_ARTIFACT_COMPARISON_EVIDENCE
            ),
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
        assert results[0].export_ref == "exports/shadow_regime_comparison.json"
        assert results[0].artifact_manifest is not None
        assert (
            results[0].artifact_manifest.artifact_id
            == "shadow_regime_detector_artifact_comparison_evidence"
        )
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)


def test_export_shadow_challenger_verdict_bundle_reads_persisted_state() -> None:
    queue_root = _queue_root("export_shadow_verdict_bundle")
    service_dir = _service_dir("export_shadow_verdict_bundle")
    try:
        initialize_dashboard_command_queue(queue_root)
        ShadowVpsServiceStore(service_dir).update_state(
            last_shadow_challenger_verdict_bundle_ref="exports/shadow_verdict_bundle.json",
            last_shadow_challenger_verdict_bundle_status="shadow_validated",
        )
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-export-shadow-verdict-bundle",
            request_id="req-export-shadow-verdict-bundle",
            command_kind=(
                DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE
            ),
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
        assert results[0].export_ref == "exports/shadow_verdict_bundle.json"
        assert results[0].artifact_manifest is not None
        assert results[0].artifact_manifest.artifact_id == "shadow_challenger_verdict_bundle"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
        shutil.rmtree(service_dir, ignore_errors=True)
