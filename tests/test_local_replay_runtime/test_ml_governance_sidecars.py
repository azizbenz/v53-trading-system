from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import shutil

from local_replay_runtime.ml_governance_sidecars import (
    ML_ANTI_LEAKAGE_PROOF_FILENAME,
    ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
    build_ml_anti_leakage_proof_artifact,
    build_ml_live_drift_snapshot,
    discover_ml_governance_sidecar_refs,
    write_ml_governance_sidecars,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    build_fixture_expected_edge_artifact,
)
from meta_learning.model_risk_registry import (
    MlModelDriftSnapshot as RuntimeDriftSnapshot,
    MlModelRuntimeStage,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("ml_governance_sidecars_tests", label)


def test_build_ml_anti_leakage_proof_marks_ready_when_windows_are_causal() -> None:
    artifact = build_fixture_expected_edge_artifact()

    proof = build_ml_anti_leakage_proof_artifact(
        artifact,
        test_start=date(2025, 5, 1),
        test_end=date(2025, 5, 30),
    )

    assert proof.target_artifact_hash == artifact.artifact_hash
    assert proof.feature_timestamp_alignment_status == "FEATURE_TIMESTAMP_ALIGNED"
    assert proof.no_future_data_leak_status == "NO_FUTURE_DATA_LEAK_PROVEN"
    assert proof.promotion_ready_proof is True


def test_build_ml_live_drift_snapshot_stays_fail_closed_without_runtime_evidence() -> None:
    artifact = build_fixture_expected_edge_artifact()

    snapshot = build_ml_live_drift_snapshot(artifact)

    assert snapshot.stage == "SHADOW"
    assert snapshot.source_status == "LIVE_DRIFT_SOURCE_NOT_PROVEN"
    assert snapshot.promotion_ready_snapshot is False


def test_write_and_discover_ml_governance_sidecars_round_trip() -> None:
    scratch_dir = _scratch_dir("roundtrip")
    try:
        artifact = build_fixture_expected_edge_artifact()
        proof = build_ml_anti_leakage_proof_artifact(
            artifact,
            test_start=date(2025, 5, 1),
            test_end=date(2025, 5, 30),
        )
        runtime_snapshot = RuntimeDriftSnapshot(
            stage=MlModelRuntimeStage.LIVE,
            created_at=datetime(2025, 5, 1, 12, 0, tzinfo=UTC),
            feature_ks_pvalue=0.41,
            shadow_diff_pct=0.02,
            live_diff_pct=0.03,
            win_rate_delta=-0.01,
            ce_delta=-0.002,
        )
        drift_snapshot = build_ml_live_drift_snapshot(
            artifact,
            runtime_snapshot=runtime_snapshot,
            created_at=datetime(2025, 5, 1, 12, 0, tzinfo=UTC),
        )
        refs = write_ml_governance_sidecars(
            scratch_dir,
            anti_leakage_proof=proof,
            live_drift_snapshot=drift_snapshot,
        )
        artifact_ref = scratch_dir / "artifact.json"
        artifact_ref.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

        assert Path(refs.anti_leakage_proof_ref).name == ML_ANTI_LEAKAGE_PROOF_FILENAME
        assert Path(refs.live_drift_snapshot_ref).name == ML_LIVE_DRIFT_SNAPSHOT_FILENAME
        assert discover_ml_governance_sidecar_refs(artifact_ref) == refs.supplementary_refs
        assert drift_snapshot.source_status == "LIVE_DRIFT_SOURCE_GOVERNED"
        assert drift_snapshot.promotion_ready_snapshot is True
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
