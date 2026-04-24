from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil

from backtest_artifact_import import (
    ArtifactPayloadRefBundle,
    attach_regime_detector_transport_refs,
    build_regime_detector_artifact_summary,
    load_regime_detector_artifact,
    package_regime_detector_artifact_for_transport,
)
from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorWindow,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "backtest_artifact_import_regime_detector_transport_tests",
        label,
    )


def _artifact_path(label: str = "source") -> Path:
    scratch = _scratch_dir(label)
    path = scratch / "source_regime_detector_artifact.json"
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    artifact = RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=("spread_bps", "order_book_imbalance"),
        feature_hash="a" * 64,
        pair_universe=("BTCUSDT",),
        train_window=RegimeDetectorWindow(
            start_at=datetime(2026, 1, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 31, tzinfo=UTC),
        ),
        validation_window=RegimeDetectorWindow(
            start_at=datetime(2026, 4, 1, tzinfo=UTC),
            end_at=datetime(2026, 4, 22, tzinfo=UTC),
        ),
        regime_labels=("calm", "transition", "toxic"),
        oos_metrics={"transition_auc": 0.7},
        shadow_metrics={"shadow_diff_pct": 0.02},
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=17,
        created_at=created_at,
        calibration_version="lob-regime.v1",
        dataset_hash="b" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":[0.8,0.2,0.7,0.0]}').decode("ascii"),
        stale_after=created_at + timedelta(days=30),
    )
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def _payload_bundle(label: str) -> ArtifactPayloadRefBundle:
    scratch = _scratch_dir(label)
    refs = {
        "review_export_ref": scratch / "review.json",
        "feature_bridge_ref": scratch / "feature_bridge.json",
        "parity_diagnostics_ref": scratch / "parity.json",
        "replay_metrics_ref": scratch / "metrics.json",
        "replay_dtr_ref": scratch / "dtr.json",
    }
    for path in refs.values():
        path.write_text("{}", encoding="utf-8")
    return ArtifactPayloadRefBundle(
        review_export_ref=str(refs["review_export_ref"]),
        feature_bridge_ref=str(refs["feature_bridge_ref"]),
        parity_diagnostics_ref=str(refs["parity_diagnostics_ref"]),
        replay_metrics_ref=str(refs["replay_metrics_ref"]),
        replay_dtr_ref=str(refs["replay_dtr_ref"]),
    )


def test_regime_detector_artifact_summary_projects_transport_fields() -> None:
    source_path = _artifact_path("summary_source")
    try:
        artifact = load_regime_detector_artifact(str(source_path))
        summary = build_regime_detector_artifact_summary(str(source_path))

        assert summary.artifact_hash == artifact.artifact_hash
        assert summary.output_semantics == "lob_regime_detector.v1"
        assert summary.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
        assert summary.transport_artifact_ref == str(source_path.resolve())
    finally:
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_package_regime_detector_artifact_for_transport_materializes_refs() -> None:
    source_path = _artifact_path("package_source")
    export_dir = _scratch_dir("package_export")

    try:
        transport_package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        packaged_artifact = load_regime_detector_artifact(transport_package.transport_artifact_ref)

        assert Path(transport_package.transport_artifact_ref).name == "regime_detector_artifact.json"
        assert Path(transport_package.summary_ref).name == "regime_detector_artifact.summary.json"
        assert packaged_artifact.artifact_hash == transport_package.summary.artifact_hash
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_attach_regime_detector_transport_refs_uses_supplementary_refs() -> None:
    source_path = _artifact_path("attach_source")
    export_dir = _scratch_dir("attach_export")

    try:
        transport_package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        bundle = attach_regime_detector_transport_refs(
            _payload_bundle("attach_payload_bundle"),
            transport_package=transport_package,
        )

        assert bundle.supplementary_refs == (
            transport_package.transport_artifact_ref,
            transport_package.summary_ref,
        )
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(_scratch_dir("attach_payload_bundle"), ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)
