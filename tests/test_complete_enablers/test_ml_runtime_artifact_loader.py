from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from complete_enablers import (
    MlRuntimeArtifactLoadStatus,
    load_ml_runtime_artifact,
)
from backtest_artifact_import import package_ml_model_artifact_for_transport
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "complete_enablers_ml_runtime_artifact_loader_tests",
        label,
    )


def _write_ml_artifact(
    *,
    label: str,
    stale_after: datetime | None = None,
) -> Path:
    scratch = _scratch_dir(label)
    path = scratch / "source_ml_model_artifact.json"
    artifact = MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="a" * 64,
        pair_universe=("BTCUSDT",),
        train_window=MlModelWindow(
            start_at=datetime(2025, 10, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 29, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 30, tzinfo=UTC),
            end_at=datetime(2026, 4, 28, tzinfo=UTC),
        ),
        oos_sharpe=1.0,
        backtest_sharpe=1.2,
        ks_test_features_pvalue=0.42,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=17,
        created_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
        calibration_version="cal.v1",
        dataset_hash="b" * 64,
        model_bytes_b64="eyJwcmVkaWN0aW9uIjowLjd9",
        stale_after=stale_after,
    )
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_runtime_loader_loads_packaged_ml_artifact() -> None:
    export_dir = _scratch_dir("load_ok_export")
    source_path = _write_ml_artifact(label="load_ok_source")

    try:
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )

        selection = load_ml_runtime_artifact(
            (
                transport_package.transport_artifact_ref,
                transport_package.summary_ref,
            )
        )

        assert selection.status == MlRuntimeArtifactLoadStatus.LOADED
        assert selection.artifact_ready is True
        assert selection.artifact is not None
        assert selection.summary is not None
        assert selection.artifact.artifact_hash == selection.summary.artifact_hash
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_runtime_loader_fails_closed_when_summary_missing() -> None:
    selection = load_ml_runtime_artifact(())

    assert selection.status == MlRuntimeArtifactLoadStatus.MISSING_SUPPLEMENTARY_REFS
    assert selection.artifact_ready is False


def test_runtime_loader_fails_closed_when_summary_not_found_in_refs() -> None:
    export_dir = _scratch_dir("summary_not_found_export")
    source_path = _write_ml_artifact(label="summary_not_found_source")

    try:
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )

        selection = load_ml_runtime_artifact((transport_package.transport_artifact_ref,))

        assert selection.status == MlRuntimeArtifactLoadStatus.SUMMARY_NOT_FOUND
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_runtime_loader_requires_transport_artifact_to_be_declared() -> None:
    export_dir = _scratch_dir("transport_not_declared_export")
    source_path = _write_ml_artifact(label="transport_not_declared_source")

    try:
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )

        selection = load_ml_runtime_artifact((transport_package.summary_ref,))

        assert selection.status == MlRuntimeArtifactLoadStatus.TRANSPORT_ARTIFACT_NOT_DECLARED
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_runtime_loader_detects_hash_mismatch() -> None:
    export_dir = _scratch_dir("hash_mismatch_export")
    source_path = _write_ml_artifact(label="hash_mismatch_source")

    try:
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        summary_payload = json.loads(
            Path(transport_package.summary_ref).read_text(encoding="utf-8")
        )
        summary_payload["artifact_hash"] = "f" * 64
        Path(transport_package.summary_ref).write_text(
            json.dumps(summary_payload, indent=2),
            encoding="utf-8",
        )

        selection = load_ml_runtime_artifact(
            (
                transport_package.transport_artifact_ref,
                transport_package.summary_ref,
            )
        )

        assert selection.status == MlRuntimeArtifactLoadStatus.HASH_MISMATCH
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_runtime_loader_marks_stale_artifact() -> None:
    source_path = _write_ml_artifact(
        label="stale_source",
        stale_after=datetime(2026, 4, 28, 12, 5, tzinfo=UTC),
    )
    export_dir = _scratch_dir("stale_export")

    try:
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )

        selection = load_ml_runtime_artifact(
            (
                transport_package.transport_artifact_ref,
                transport_package.summary_ref,
            ),
            as_of=datetime(2026, 4, 28, 12, 6, tzinfo=UTC),
        )

        assert selection.status == MlRuntimeArtifactLoadStatus.STALE
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)
