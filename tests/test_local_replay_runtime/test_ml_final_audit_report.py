from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    MlModelArtifact,
)
from local_replay_runtime import (
    LocalLabMlArtifactTrainingReport,
    build_local_lab_ml_final_audit_report_from_vps_command_result,
)


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("ml_final_audit_report_tests", label)


def _artifact(
    feature_seed: str,
    *,
    dataset_seed: str = "d",
    model_seed: bytes = b"ml-model",
) -> MlModelArtifact:
    return MlModelArtifact.create(
        feature_names=("spread_bps", "depth_imbalance"),
        feature_hash=feature_seed * 64,
        pair_universe=("BTCUSDT",),
        train_window={
            "start_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "end_at": datetime(2026, 1, 31, tzinfo=timezone.utc),
        },
        validation_window={
            "start_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
            "end_at": datetime(2026, 2, 28, tzinfo=timezone.utc),
        },
        oos_sharpe=1.2,
        backtest_sharpe=1.5,
        shadow_diff_pct=1.0,
        training_seed=17,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        calibration_version="ml.v1",
        dataset_hash=dataset_seed * 64,
        model_bytes_b64=base64.b64encode(model_seed).decode("ascii"),
    )


def _training_report(artifact: MlModelArtifact) -> LocalLabMlArtifactTrainingReport:
    return LocalLabMlArtifactTrainingReport(
        correlation_id="corr-ml-final-audit",
        export_dir="build/ml",
        status="ready",
        ready=True,
        replay_sample_count=32,
        training_row_count=32,
        recognized_feature_key_count=2,
        pair_scope=("BTCUSDT",),
        engine_scope=("engine_a",),
        artifact=artifact,
        artifact_hash=artifact.artifact_hash,
        oos_sharpe=artifact.oos_sharpe,
        backtest_sharpe=artifact.backtest_sharpe,
    )


def _command_result(export_ref: Path, artifact: MlModelArtifact) -> DashboardGovernedCommandResult:
    manifest = DashboardArtifactTransferManifest(
        artifact_hash=artifact.artifact_hash,
        artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
        artifact_id="ml-active",
        feature_set_version="ml_feature_set.v1",
        lineage_version="a.v1.0.r1",
        source_ref=str(export_ref.resolve()),
    )
    return DashboardGovernedCommandResult(
        timestamp_ms=1_800_000_000_000,
        correlation_id="corr-ml-final-audit",
        result_id="req-ml-export.result",
        request_id="req-ml-export",
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
        status=DashboardGovernedCommandStatus.COMPLETED,
        idempotency_key="req-ml-export:no_artifact:request_export_active_ml_artifact",
        artifact_manifest=manifest,
        export_ref=str(export_ref.resolve()),
    )


def test_build_local_lab_ml_final_audit_report_blocks_when_formalism_is_unresolved() -> None:
    scratch_dir = _scratch_dir("ready")
    try:
        artifact = _artifact("a")
        artifact_path = scratch_dir / "active_ml_artifact.json"
        artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

        report = build_local_lab_ml_final_audit_report_from_vps_command_result(
            correlation_id="corr-ml-final-audit",
            training_report=_training_report(artifact),
            command_result=_command_result(artifact_path, artifact),
        )

        assert report.status == "blocked"
        assert report.audit_ready is False
        assert report.feature_set_compatible is True
        assert report.artifact_matches_lab_recommendation is True
        assert report.final_recommendation == "resolve_ml_final_audit_blockers"
        assert "ml.formalism.unresolved" in report.blocking_reasons
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_build_local_lab_ml_final_audit_report_stays_blocked_when_hash_differs() -> None:
    scratch_dir = _scratch_dir("partial")
    try:
        recommended = _artifact("a")
        uploaded = _artifact("a", dataset_seed="e", model_seed=b"ml-model-variant")
        artifact_path = scratch_dir / "active_ml_artifact.json"
        artifact_path.write_text(uploaded.model_dump_json(indent=2), encoding="utf-8")

        report = build_local_lab_ml_final_audit_report_from_vps_command_result(
            correlation_id="corr-ml-final-audit",
            training_report=_training_report(recommended),
            command_result=_command_result(artifact_path, uploaded),
        )

        assert report.status == "blocked"
        assert report.audit_ready is False
        assert report.feature_set_compatible is True
        assert report.final_recommendation == "resolve_ml_final_audit_blockers"
        assert "ml.final_audit.upload_differs_from_lab_recommendation" in report.caution_flags
        assert "ml.formalism.unresolved" in report.blocking_reasons
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_build_local_lab_ml_final_audit_report_rejects_non_ml_export_command() -> None:
    artifact = _artifact("a")
    result = DashboardGovernedCommandResult(
        timestamp_ms=1_800_000_000_000,
        correlation_id="corr-ml-final-audit",
        result_id="req-regime-export.result",
        request_id="req-regime-export",
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
        status=DashboardGovernedCommandStatus.COMPLETED,
        idempotency_key="req-regime-export:no_artifact:request_export_active_regime_detector_artifact",
        export_ref="build/regime_detector.json",
    )

    with pytest.raises(
        ValueError,
        match="request_export_active_ml_artifact",
    ):
        build_local_lab_ml_final_audit_report_from_vps_command_result(
            correlation_id="corr-ml-final-audit",
            training_report=_training_report(artifact),
            command_result=result,
        )
