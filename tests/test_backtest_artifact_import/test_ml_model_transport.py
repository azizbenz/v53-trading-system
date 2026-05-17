from __future__ import annotations

import backtest_artifact_import.ml_model_transport as import_ml_model_transport
from datetime import UTC, date, datetime
import local_replay_runtime.ml_model_transport as replay_ml_model_transport
from pathlib import Path
import shutil

from backtest_artifact_import import (
    ArtifactUploadContext,
    build_import_request_from_upload_request,
    build_lab_fixture_signature_envelope,
    build_ml_supplementary_refs_source_summary,
    build_replay_plan_from_export_dir,
    build_upload_request_from_replay_plan_with_ml_model_artifact,
    build_ml_model_source_artifact_summary,
    load_ml_model_artifact,
    package_ml_model_artifact_for_transport,
    validate_import_request,
)
from interface_contracts import (
    ArtifactClass,
    ArtifactExportBundle,
    ArtifactLifecyclePolicy,
    ArtifactLogicFormat,
    ArtifactProofSummary,
    FeatureLineageLock,
    FeatureLineageRecord,
    MlModelArtifact,
    MlModelWindow,
    PhysicsFeatureFamily,
    ProfileId,
    PromotionState,
    StrategyClassification,
    TransformWhitelistId,
    TransformWhitelistLock,
)
from local_replay_runtime import ReplayExecutionInput, ReplayRunManifest, execute_local_replay_export
from local_replay_runtime.ml_governance_sidecars import (
    ML_ANTI_LEAKAGE_PROOF_FILENAME,
    ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
    build_ml_anti_leakage_proof_artifact,
    build_ml_live_drift_snapshot,
    write_ml_governance_sidecars,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "backtest_artifact_import_ml_model_transport_tests",
        label,
    )


def _export_dir(*, profile_scope: ProfileId = ProfileId.COMPLETE) -> Path:
    export_dir = _scratch_dir(f"export_{profile_scope.value}")
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id=f"run-export-{profile_scope.value}-ml",
                strategy_id="strategy-a-ml-bridge-1",
                strategy_version="a.v2.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v2.0.r4",
                profile_scope=profile_scope,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id="dataset-export-20260422",
                timeframe_scope="2026-03-01/2026-03-31",
                feature_set_version="1.0.0",
                transform_set_version="1.0.0",
                formula_set_version="formula.v2",
                scoring_version="score.v2",
                regime_version="regime.v2",
                risk_policy_version="risk.v2",
                cost_model_version="cost.v2",
                performance_mode="research_fast_mode",
                artifact_schema_version="1.0.0",
                artifact_hash=f"artifact-hash-{profile_scope.value}-ml",
                clock_id="clock-local-export-ml",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=2048,
            ),
            total_opportunities=3,
            dtr_records=(
                build_dtr(
                    dtr_id=f"run-export-{profile_scope.value}-ml:dtr:1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.SELECTED,
                    expected_cost=0.0010,
                    realized_cost=0.0011,
                    gross_return=0.0020,
                    ce_expected=0.0006,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_000.0,
                ),
            ),
            feature_bridge_payload={
                "bridge": "ok",
                "dataset_id": "dataset-export-20260422",
                "feature_set_version": "1.0.0",
                "transform_set_version": "1.0.0",
                "pairs": ["BTCUSDT", "ETHUSDT"],
                "engines": ["engine_a", "engine_b"],
                "recognized_feature_keys": ["sweep_score_1m"],
            },
            parity_diagnostics_payload={
                "parity_status": "ok",
                "dataset_id": "dataset-export-20260422",
                "decision_match_rate": 1.0,
            },
            review_notes=("ml transport export",),
        ),
    )
    return export_dir


def _upload_bundle(*, artifact_id: str) -> ArtifactExportBundle:
    signature_envelope = build_lab_fixture_signature_envelope()
    return ArtifactExportBundle(
        artifact_id=artifact_id,
        artifact_version="1.0.0",
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_a:ml_confidence",
        distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
        payload_hash_sha256=signature_envelope.payload_hash_sha256,
        public_key_author_sig=signature_envelope.public_key_author_sig,
        dataset_id="dataset-export-20260422",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        feature_lineage_lock=FeatureLineageLock(
            feature_set_version="1.0.0",
            transform_set_version="1.0.0",
            records=(
                FeatureLineageRecord(
                    feature_id="sweep_score_1m",
                    family=PhysicsFeatureFamily.SWEEP_SCORE,
                    source_inputs=("historical_prices",),
                    transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                    feature_set_version="1.0.0",
                    transform_set_version="1.0.0",
                ),
            ),
        ),
        transform_whitelist_lock=TransformWhitelistLock(
            transform_set_version="1.0.0",
            allowed_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
        ),
        training_start=date(2026, 1, 1),
        training_end=date(2026, 4, 22),
        lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
        covariance_shrinkage_matrix_ref="matrix_ref",
        drift_score_threshold=0.85,
        proof_summary=ArtifactProofSummary(
            anti_cowardice_pass=True,
            friction_regret_pass=True,
            walk_forward_pass=True,
            regime_segmentation_pass=True,
            operational_burden_pass=True,
            capital_efficiency_pass=True,
            ablation_delta_net_pnl=0.12,
            ablation_delta_ce=0.03,
            friction_regret_value=0.01,
            block_rate_delta=0.02,
        ),
    )


def _ml_artifact_path() -> Path:
    scratch = _scratch_dir("ml_artifact")
    path = scratch / "source_ml_model_artifact.json"
    artifact = MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="a" * 64,
        pair_universe=("BTCUSDT", "ETHUSDT"),
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
    )
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def _write_governance_sidecars(source_path: Path) -> None:
    artifact = load_ml_model_artifact(str(source_path))
    proof = build_ml_anti_leakage_proof_artifact(
        artifact,
        test_start=date(2026, 4, 29),
        test_end=date(2026, 5, 6),
    )
    snapshot = build_ml_live_drift_snapshot(artifact)
    write_ml_governance_sidecars(
        source_path.parent,
        anti_leakage_proof=proof,
        live_drift_snapshot=snapshot,
    )


def test_build_ml_model_source_artifact_summary_projects_typed_fields() -> None:
    source_path = _ml_artifact_path()
    try:
        artifact = load_ml_model_artifact(str(source_path))
        summary = build_ml_model_source_artifact_summary(str(source_path))

        assert summary.artifact_hash == artifact.artifact_hash
        assert summary.model_family == "lightgbm"
        assert summary.calibration_version == "cal.v1"
        assert summary.transport_artifact_ref == str(source_path.resolve())
    finally:
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_build_ml_supplementary_refs_source_summary_projects_fresh_governed_refs() -> None:
    source_path = _ml_artifact_path()
    try:
        artifact = load_ml_model_artifact(str(source_path))
        summary = build_ml_model_source_artifact_summary(str(source_path))
        source_summary = build_ml_supplementary_refs_source_summary(
            artifact=artifact,
            transport_artifact_ref=str(source_path.resolve()),
            summary_ref=str(source_path.with_name("ml_model_artifact.summary.json").resolve()),
        )

        assert source_summary.target_artifact_hash == artifact.artifact_hash
        assert source_summary.source_status == "SUPPLEMENTARY_REFS_SOURCE_GOVERNED"
        assert source_summary.non_empty_refs_status == "NON_EMPTY_SUPPLEMENTARY_REFS_PROVEN"
        assert source_summary.summary_ref.endswith("ml_model_artifact.summary.json")
        assert source_summary.target_artifact_hash == summary.artifact_hash
    finally:
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_package_ml_model_artifact_for_transport_materializes_packaged_refs() -> None:
    export_dir = _export_dir()
    source_path = _ml_artifact_path()

    try:
        _write_governance_sidecars(source_path)
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        packaged_artifact = load_ml_model_artifact(transport_package.transport_artifact_ref)

        assert Path(transport_package.transport_artifact_ref).parent == export_dir.resolve()
        assert Path(transport_package.summary_ref).parent == export_dir.resolve()
        assert Path(transport_package.source_summary_ref).parent == export_dir.resolve()
        assert Path(export_dir / ML_ANTI_LEAKAGE_PROOF_FILENAME).is_file()
        assert Path(export_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).is_file()
        assert packaged_artifact.artifact_hash == transport_package.summary.artifact_hash
        assert transport_package.summary.source_artifact_ref == str(source_path.resolve())
        assert transport_package.source_summary.target_artifact_hash == packaged_artifact.artifact_hash
        assert transport_package.source_summary.supplementary_refs_count == 5
        assert len(transport_package.supplementary_refs) == 5
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_build_upload_request_from_replay_plan_with_ml_model_artifact_preserves_governed_transport() -> None:
    export_dir = _export_dir()
    source_path = _ml_artifact_path()

    try:
        discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
        _write_governance_sidecars(source_path)
        transport_package = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        upload_request = build_upload_request_from_replay_plan_with_ml_model_artifact(
            replay_plan,
            payload_bundle=discovery.payload_bundle,
            bundle=_upload_bundle(artifact_id=discovery.run_manifest.artifact_hash),
            signature_envelope=build_lab_fixture_signature_envelope(),
            uploaded_by="lab-user",
            upload_context=ArtifactUploadContext.LOCAL_LAB,
            governance_reference_date=date(2026, 4, 22),
            transport_package=transport_package,
        )
        import_request = build_import_request_from_upload_request(upload_request)
        decision = validate_import_request(import_request)

        assert transport_package.transport_artifact_ref in upload_request.payload_bundle.supplementary_refs
        assert transport_package.summary_ref in upload_request.payload_bundle.supplementary_refs
        assert transport_package.source_summary_ref in upload_request.payload_bundle.supplementary_refs
        assert str((export_dir / ML_ANTI_LEAKAGE_PROOF_FILENAME).resolve()) in upload_request.payload_bundle.supplementary_refs
        assert str((export_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).resolve()) in upload_request.payload_bundle.supplementary_refs
        assert transport_package.transport_artifact_ref in import_request.payload_refs
        assert transport_package.summary_ref in import_request.payload_refs
        assert transport_package.source_summary_ref in import_request.payload_refs
        assert str((export_dir / ML_ANTI_LEAKAGE_PROOF_FILENAME).resolve()) in import_request.payload_refs
        assert str((export_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).resolve()) in import_request.payload_refs
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_backtest_artifact_import_ml_transport_reuses_local_replay_packaging_ownership() -> None:
    assert (
        import_ml_model_transport.MlModelTransportPackage
        is replay_ml_model_transport.MlModelTransportPackage
    )
    assert (
        import_ml_model_transport.load_ml_model_artifact
        is replay_ml_model_transport.load_ml_model_artifact
    )
    assert (
        import_ml_model_transport.build_ml_model_source_artifact_summary
        is replay_ml_model_transport.build_ml_model_source_artifact_summary
    )
    assert (
        import_ml_model_transport.build_ml_supplementary_refs_source_summary
        is replay_ml_model_transport.build_ml_supplementary_refs_source_summary
    )
    assert (
        import_ml_model_transport.package_ml_model_artifact_for_transport
        is replay_ml_model_transport.package_ml_model_artifact_for_transport
    )
