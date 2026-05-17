from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from interface_contracts import DashboardArtifactKind, DashboardArtifactTransferManifest
from local_replay_runtime.ml_governance_sidecars import (
    ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
    build_ml_anti_leakage_proof_artifact,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    build_fixture_expected_edge_artifact,
)
from monitoring.contracts_artifacts import ArtifactShadowComparisonEvidence
from protocols import ShadowVpsServiceStore


def _scratch_dir(label: str) -> Path:
    from tests.test_protocols.test_shadow_vps_service_launcher import _scratch_dir

    return _scratch_dir(label)


def _load_governance_snapshot_support_module():
    from tests.test_protocols.test_shadow_vps_service_launcher import _load_service_module

    _load_service_module()
    import shadow_vps_service_governance_snapshot_support as support

    return support


def test_refresh_shadow_vps_governance_snapshots_writes_service_sidecars(
    monkeypatch,
) -> None:
    support = _load_governance_snapshot_support_module()
    output_dir = _scratch_dir("governance_snapshot_support")

    try:
        service_dir = output_dir / "campaign" / "service"
        auto_exports_root = output_dir / "campaign" / "auto_exports"
        service_dir.mkdir(parents=True, exist_ok=True)
        auto_exports_root.mkdir(parents=True, exist_ok=True)
        context = SimpleNamespace(
            service_dir=service_dir,
            resolved_auto_exports_root=auto_exports_root,
        )
        seen: list[tuple[Path, Path]] = []

        monkeypatch.setattr(
            support,
            "synthesise_refusal_journal",
            lambda *, auto_exports_root, build_root: seen.append((auto_exports_root, build_root)) or {
                "top_motifs": [{"motif": "rank_cutoff", "count": 2, "last_observed_at": "2026-04-28T00:00:00+00:00"}],
                "tail_risk_meter": 0.25,
                "quadruple_filter": {"tail_risk_audit": True},
                "anti_survivorship": False,
            },
        )
        store = ShadowVpsServiceStore(service_dir)
        context = SimpleNamespace(
            service_dir=service_dir,
            resolved_auto_exports_root=auto_exports_root,
            store=store,
        )

        refusal_path, model_risk_path = support._refresh_shadow_vps_governance_snapshots(context)

        assert seen == [(auto_exports_root, output_dir)]
        assert refusal_path == service_dir / "refusal_journal.snapshot.json"
        assert model_risk_path == service_dir / "model_risk_register.snapshot.json"
        refusal_payload = json.loads(refusal_path.read_text(encoding="utf-8"))
        model_risk_payload = json.loads(model_risk_path.read_text(encoding="utf-8"))
        assert refusal_payload["top_motifs"][0]["motif"] == "rank_cutoff"
        assert model_risk_payload["source_status"] == "ok"
        assert model_risk_payload["active_ml"] is None
        assert model_risk_payload["promotion_eligible"] is False
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_refresh_shadow_vps_governance_snapshots_derives_ml_model_risk_and_persists_shadow_drift() -> None:
    support = _load_governance_snapshot_support_module()
    output_dir = _scratch_dir("governance_snapshot_ml_risk")

    try:
        service_dir = output_dir / "campaign" / "service"
        auto_exports_root = output_dir / "campaign" / "auto_exports"
        artifact_dir = output_dir / "artifacts"
        service_dir.mkdir(parents=True, exist_ok=True)
        auto_exports_root.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        challenger_artifact = build_fixture_expected_edge_artifact()
        challenger_artifact_path = artifact_dir / "shadow_ml_challenger.json"
        challenger_artifact_path.write_text(
            challenger_artifact.model_dump_json(indent=2),
            encoding="utf-8",
        )
        anti_leakage_proof = build_ml_anti_leakage_proof_artifact(
            challenger_artifact,
            test_start=challenger_artifact.stale_after.date(),
            test_end=challenger_artifact.stale_after.date(),
        )
        (artifact_dir / "ml_anti_leakage_proof_artifact.json").write_text(
            anti_leakage_proof.model_dump_json(indent=2),
            encoding="utf-8",
        )
        comparison_evidence = ArtifactShadowComparisonEvidence(
            artifact_family="ml",
            champion_artifact_id="ml-active",
            challenger_artifact_id="ml-shadow",
            event_count=12,
            decision_diff_rate=0.08,
            expected_ce_delta_mean=0.012,
            comparison_status="shadow_ready",
        )
        comparison_ref = service_dir / "2026-05-14.ml.shadow_artifact_comparison.json"
        comparison_ref.write_text(comparison_evidence.model_dump_json(indent=2), encoding="utf-8")

        store = ShadowVpsServiceStore(service_dir)
        store.update_state(
            shadow_ml_challenger_artifact=DashboardArtifactTransferManifest(
                artifact_hash=challenger_artifact.artifact_hash,
                artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
                artifact_id="ml-shadow",
                feature_set_version="ml_feature_set.v1",
                lineage_version="a.v1.0.r1",
                review_state="pending",
                source_ref=str(challenger_artifact_path.resolve()),
            ),
            last_shadow_ml_artifact_comparison_ref=str(comparison_ref.resolve()),
            last_shadow_ml_artifact_comparison_status="shadow_ready",
        )
        context = SimpleNamespace(
            service_dir=service_dir,
            resolved_auto_exports_root=auto_exports_root,
            store=store,
        )

        _, model_risk_path = support._refresh_shadow_vps_governance_snapshots(context)

        payload = json.loads(model_risk_path.read_text(encoding="utf-8"))
        drift_path = artifact_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME
        drift_payload = json.loads(drift_path.read_text(encoding="utf-8"))
        persisted_manifest = store.state.shadow_ml_challenger_artifact

        assert payload["source_status"] == "ok"
        assert payload["shadow_ml_challenger"]["profile_id"] == "ml-shadow"
        assert payload["shadow_ml_challenger"]["drift_score"] == 0.08
        assert payload["promotion_eligible"] is False
        assert "ml.formalism.unresolved" in payload["promotion_blocking_reasons"]
        assert drift_payload["source_status"] == "LIVE_DRIFT_SOURCE_GOVERNED"
        assert drift_payload["stage"] == "SHADOW"
        assert drift_payload["shadow_diff_pct"] == 0.08
        assert persisted_manifest is not None
        assert str(drift_path.resolve()) in persisted_manifest.payload_refs
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
