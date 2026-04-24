from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import shutil

import pytest

import backtest_artifact_import.export_dir_bridge as export_dir_bridge_module
from backtest_artifact_import import (
    ArtifactUploadContext,
    build_lab_fixture_signature_envelope,
    build_artifact_export_bundle_from_replay_import_context,
    build_import_context_from_replay_plan,
    build_import_context_from_export_dir,
    build_import_request_from_upload_request,
    build_replay_plan_from_export_dir,
    build_upload_context_from_replay_import_context,
    build_upload_request_from_replay_plan,
    build_upload_request_from_export_dir,
    discover_local_replay_export,
    validate_import_request,
)
from interface_contracts import (
    ArtifactClass,
    ArtifactExportBundle,
    ArtifactLifecyclePolicy,
    ArtifactLogicFormat,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    FeatureLineageLock,
    FeatureLineageRecord,
    PhysicsFeatureFamily,
    ProfileId,
    StrategyClassification,
    TransformWhitelistId,
    TransformWhitelistLock,
)
from local_replay_runtime import (
    LocalReplayRuntimeEvidence,
    ReplayExecutionInput,
    ReplayRunManifest,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "backtest_artifact_import_export_dir_bridge_tests",
        label,
    )


def _export_dir(*, profile_scope: ProfileId = ProfileId.COMPLETE) -> Path:
    export_dir = _scratch_dir(f"export_{profile_scope.value}")
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id=f"run-export-{profile_scope.value}-1",
                strategy_id="strategy-a-bridge-1",
                strategy_version="a.v2.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v2.0.r3",
                profile_scope=profile_scope,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id="dataset-export-20260401",
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
                artifact_hash=f"artifact-hash-{profile_scope.value}-1",
                clock_id="clock-local-export-1",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=2048,
            ),
            total_opportunities=3,
            dtr_records=(
                build_dtr(
                    dtr_id=f"run-export-{profile_scope.value}-1:dtr:1",
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
                "dataset_id": "dataset-export-20260401",
                "feature_set_version": "1.0.0",
                "transform_set_version": "1.0.0",
                "pairs": ["BTCUSDT", "ETHUSDT"],
                "engines": ["engine_a", "engine_b"],
                "recognized_feature_keys": ["sweep_score_1m"],
            },
            parity_diagnostics_payload={
                "parity_status": "ok",
                "dataset_id": "dataset-export-20260401",
                "decision_match_rate": 1.0,
            },
            review_notes=("bridge integration export",),
        ),
    )
    return export_dir


def _upload_bundle(*, artifact_id: str) -> ArtifactExportBundle:
    signature_envelope = build_lab_fixture_signature_envelope()
    return ArtifactExportBundle(
        artifact_id=artifact_id,
        artifact_version="1.0.0",
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_a:bridge_test",
        distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
        payload_hash_sha256=signature_envelope.payload_hash_sha256,
        public_key_author_sig=signature_envelope.public_key_author_sig,
        dataset_id="dataset-export-20260401",
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
        training_end=date(2026, 4, 1),
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


def _local_replay_evidence() -> LocalReplayRuntimeEvidence:
    return LocalReplayRuntimeEvidence(
        artifact_id="artifact-hash-complete-1",
        lineage_version="a.v2.0.r3",
        data_source="recorded_replay",
        feature_bridge_ready=True,
        parity_diagnostics_ready=True,
        replay_metrics_ready=True,
        replay_dtr_ready=True,
        replay_useful_ready=True,
        evidence_summary="source=recorded_replay / feature_bridge=yes / parity=yes / metrics=yes / replay_dtr=yes",
    )


def test_build_import_context_from_export_dir_builds_typed_import_request():
    export_dir = _export_dir()

    try:
        context = build_import_context_from_export_dir(
            export_dir,
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            training_end=date(2026, 4, 6),
            governance_reference_date=date(2026, 4, 6),
            drift_score_threshold=0.85,
        )
        decision = validate_import_request(context.import_request)

        assert context.export_discovery.run_manifest.profile_scope == ProfileId.COMPLETE
        assert context.replay_plan.request.profile == ProfileId.COMPLETE
        assert context.import_request.manifest.source_profile == ProfileId.COMPLETE
        assert context.import_request.payload_bundle is not None
        assert context.expected_feature_ids == ("sweep_score_1m",)
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_import_context_from_replay_plan_builds_typed_import_request():
    export_dir = _export_dir()

    try:
        discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
        context = build_import_context_from_replay_plan(
            replay_plan,
            payload_bundle=discovery.payload_bundle,
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            training_end=date(2026, 4, 6),
            governance_reference_date=date(2026, 4, 6),
            drift_score_threshold=0.85,
        )
        decision = validate_import_request(context.import_request)

        assert context.replay_plan.request.profile == ProfileId.COMPLETE
        assert context.import_request.manifest.source_profile == ProfileId.COMPLETE
        assert context.import_request.payload_bundle is not None
        assert context.expected_feature_ids == ("sweep_score_1m",)
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_artifact_export_bundle_from_replay_import_context_materializes_bundle():
    export_dir = _export_dir()

    try:
        discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
        import_context = build_import_context_from_replay_plan(
            replay_plan,
            payload_bundle=discovery.payload_bundle,
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            training_end=date(2026, 4, 6),
            governance_reference_date=date(2026, 4, 6),
            drift_score_threshold=0.85,
        )
        bundle = build_artifact_export_bundle_from_replay_import_context(
            import_context,
            local_replay_evidence=_local_replay_evidence(),
            signature_envelope=build_lab_fixture_signature_envelope(),
            artifact_class=ArtifactClass.DAMAGE_REDUCER,
            artifact_scope="bridge:test",
            governance_reference_date=date(2026, 4, 6),
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
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
            distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
            covariance_shrinkage_matrix_ref="matrix_ref",
        )

        assert bundle.artifact_id == replay_plan.bundle.manifest.artifact_id
        assert bundle.dataset_id == discovery.run_manifest.dataset_manifest_id
        assert bundle.feature_lineage_lock == import_context.feature_lineage_lock
        assert bundle.transform_whitelist_lock == import_context.transform_whitelist_lock
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_import_context_from_export_dir_preserves_light_profile_and_fails_closed():
    export_dir = _export_dir(profile_scope=ProfileId.LIGHT)

    try:
        context = build_import_context_from_export_dir(
            export_dir,
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            training_end=date(2026, 4, 6),
            governance_reference_date=date(2026, 4, 6),
            drift_score_threshold=0.85,
        )
        decision = validate_import_request(context.import_request)

        assert context.export_discovery.run_manifest.profile_scope == ProfileId.LIGHT
        assert context.replay_plan.request.profile == ProfileId.LIGHT
        assert context.import_request.manifest.source_profile == ProfileId.LIGHT
        assert decision.accepted is False
        assert "governed import requires source_profile=COMPLETE" in decision.reasons
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_requires_run_manifest():
    export_dir = _export_dir()

    try:
        (export_dir / "replay_run_manifest.json").unlink()

        with pytest.raises(FileNotFoundError, match="Missing governed export file for replay_run_manifest"):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_sidecar_resolving_outside_export_dir(
    monkeypatch: pytest.MonkeyPatch,
):
    export_dir = _export_dir()
    external_dir = _scratch_dir("outside_sidecar")

    try:
        outside_review_export = external_dir / "review_export.md"
        outside_review_export.write_text(
            (export_dir / "review_export.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original_discover = export_dir_bridge_module._discover_export_file

        def _fake_discover(export_root: Path, **kwargs) -> Path:
            if kwargs.get("label") == "review_export":
                return outside_review_export.resolve()
            return original_discover(export_root, **kwargs)

        monkeypatch.setattr(
            export_dir_bridge_module,
            "_discover_export_file",
            _fake_discover,
        )

        with pytest.raises(
            ValueError,
            match="governed export review_export must resolve inside export_dir",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(external_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_multiple_review_export_candidates():
    export_dir = _export_dir()

    try:
        (export_dir / "learning_review_export.md").write_text(
            (export_dir / "review_export.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Multiple governed export files found for review_export",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_corrupted_run_manifest():
    export_dir = _export_dir()

    try:
        run_manifest_path = export_dir / "replay_run_manifest.json"
        run_manifest_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for replay_run_manifest",
        ):
            discover_local_replay_export(export_dir)

        assert run_manifest_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_import_context_from_export_dir_backs_up_corrupted_feature_bridge():
    export_dir = _export_dir()

    try:
        feature_bridge_path = export_dir / "feature_bridge.json"
        feature_bridge_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for feature_bridge",
        ):
            build_import_context_from_export_dir(
                export_dir,
                lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
                training_end=date(2026, 4, 6),
                governance_reference_date=date(2026, 4, 6),
                drift_score_threshold=0.85,
            )

        assert feature_bridge_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_corrupted_parity_diagnostics():
    export_dir = _export_dir()

    try:
        parity_path = export_dir / "parity_diagnostics.json"
        parity_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for parity_diagnostics",
        ):
            discover_local_replay_export(export_dir)

        assert parity_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_invalid_parity_diagnostics_schema():
    export_dir = _export_dir()

    try:
        parity_path = export_dir / "parity_diagnostics.json"
        parity_path.write_text('{"dataset_id":"broken"}', encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for parity_diagnostics",
        ):
            discover_local_replay_export(export_dir)

        assert parity_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_corrupted_replay_metrics():
    export_dir = _export_dir()

    try:
        replay_metrics_path = export_dir / "replay_metrics.json"
        replay_metrics_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for replay_metrics",
        ):
            discover_local_replay_export(export_dir)

        assert replay_metrics_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_invalid_replay_metrics_schema():
    export_dir = _export_dir()

    try:
        replay_metrics_path = export_dir / "replay_metrics.json"
        replay_metrics_path.write_text('{"total_records":"oops"}', encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for replay_metrics",
        ):
            discover_local_replay_export(export_dir)

        assert replay_metrics_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_corrupted_replay_dtr():
    export_dir = _export_dir()

    try:
        replay_dtr_path = export_dir / "replay_dtr.jsonl"
        replay_dtr_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for replay_dtr",
        ):
            discover_local_replay_export(export_dir)

        assert replay_dtr_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_backs_up_invalid_replay_dtr_schema():
    export_dir = _export_dir()

    try:
        replay_dtr_path = export_dir / "replay_dtr.jsonl"
        replay_dtr_path.write_text('{"foo":"bar"}\n', encoding="utf-8")

        with pytest.raises(
            ValueError,
            match="governed export sidecar is corrupted for replay_dtr",
        ):
            discover_local_replay_export(export_dir)

        assert replay_dtr_path.with_suffix(".corrupted").exists()
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_parity_dataset_id_mismatch():
    export_dir = _export_dir()

    try:
        parity_path = export_dir / "parity_diagnostics.json"
        parity_path.write_text(
            (
                '{"parity_status":"ok","dataset_id":"other-dataset",'
                '"decision_match_rate":1.0,"score_match_rate":1.0}'
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export parity_diagnostics dataset_id must match replay_run_manifest dataset_manifest_id",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_feature_bridge_dataset_id_mismatch():
    export_dir = _export_dir()

    try:
        feature_bridge_path = export_dir / "feature_bridge.json"
        feature_bridge = json.loads(feature_bridge_path.read_text(encoding="utf-8"))
        feature_bridge["dataset_id"] = "other-dataset"
        feature_bridge_path.write_text(
            json.dumps(feature_bridge, indent=2),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export feature_bridge dataset_id must match replay_run_manifest dataset_manifest_id",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_review_export_run_id_mismatch():
    export_dir = _export_dir()

    try:
        review_export_path = export_dir / "review_export.md"
        review_text = review_export_path.read_text(encoding="utf-8")
        review_export_path.write_text(
            review_text.replace(
                "- run_id: run-export-complete-1",
                "- run_id: run-export-other",
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export review_export run_id must match replay_run_manifest run_id",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_metrics_dtr_count_mismatch():
    export_dir = _export_dir()

    try:
        replay_metrics_path = export_dir / "replay_metrics.json"
        replay_metrics_path.write_text(
            (
                '{"total_records":2,"total_opportunities":3,"dtr_coverage":0.333333,'
                '"selected_count":1,"executed_count":0,"hard_blocked_count":0,'
                '"rejected_ranking_count":0,"phantom_count":0,"ce_net":0.0006,'
                '"expected_cost_mean":0.001,"realized_cost_mean":0.0011,'
                '"gross_return_mean":0.002,"gross_return_total":0.002,'
                '"drawdown_proxy":0.0,'
                '"pair_aggregates":[{"pair":"BTCUSDT","record_count":2,"selected_count":1,'
                '"ce_net":0.0006,"expected_cost_mean":0.001,"realized_cost_mean":0.0011,'
                '"gross_return_mean":0.002}],'
                '"engine_aggregates":[{"engine_id":"engine_a","record_count":2,"selected_count":1,'
                '"hard_blocked_count":0,"ce_net":0.0006,"expected_cost_mean":0.001,'
                '"realized_cost_mean":0.0011,"gross_return_mean":0.002}]}'
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export replay_metrics total_records must match replay_dtr count",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_metrics_summary_drift_from_dtr():
    export_dir = _export_dir()

    try:
        replay_metrics_path = export_dir / "replay_metrics.json"
        replay_metrics = json.loads(replay_metrics_path.read_text(encoding="utf-8"))
        replay_metrics["selected_count"] = 0
        replay_metrics_path.write_text(
            json.dumps(replay_metrics, indent=2),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export replay_metrics must stay consistent with replay_dtr records",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_review_export_metrics_drift():
    export_dir = _export_dir()

    try:
        review_export_path = export_dir / "review_export.md"
        review_text = review_export_path.read_text(encoding="utf-8")
        review_export_path.write_text(
            review_text.replace("- total_records: 1", "- total_records: 9"),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export review_export total_records must match replay_metrics total_records",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_discover_local_replay_export_rejects_metrics_pair_outside_manifest_scope():
    export_dir = _export_dir()

    try:
        replay_metrics_path = export_dir / "replay_metrics.json"
        replay_metrics = json.loads(replay_metrics_path.read_text(encoding="utf-8"))
        replay_metrics["pair_aggregates"][0]["pair"] = "DOGEUSDT"
        replay_metrics_path.write_text(
            json.dumps(replay_metrics, indent=2),
            encoding="utf-8",
        )
        replay_dtr_path = export_dir / "replay_dtr.jsonl"
        replay_dtr_path.write_text(
            (
                '{"dtr_id":"run-export-complete-1:dtr:1","timestamp":1700000000.0,'
                '"pair":"DOGEUSDT","engine_id":"engine_a","regime":"","schema_version":"1.0",'
                '"runtime_mode":"local_replay","input_source":"local_replay",'
                '"path_complete":true,"path_warnings":[],"raw_score":0.0,'
                '"penalized_score":0.0,"final_score":0.0,"hard_blocked":false,'
                '"hard_block_reasons":[],"ranking_position":0,"candidate_size":0.0,'
                '"final_size":0.0,"tier":"","expected_cost":0.001,"realized_cost":0.0011,'
                '"gross_return":0.002,"ce_expected":0.0006,"decision_state":"selected",'
                '"primary_reason":"","cause_chain":[]}\n'
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="governed export replay_metrics pair_aggregates must stay within replay_run_manifest tested_pairs",
        ):
            discover_local_replay_export(export_dir)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_upload_request_from_export_dir_materializes_typed_upload_request():
    export_dir = _export_dir()

    try:
        discovery = discover_local_replay_export(export_dir)
        upload_request = build_upload_request_from_export_dir(
            export_dir,
            bundle=_upload_bundle(artifact_id=discovery.run_manifest.artifact_hash),
            signature_envelope=build_lab_fixture_signature_envelope(),
            uploaded_by="lab-user",
            upload_context=ArtifactUploadContext.LOCAL_LAB,
            governance_reference_date=date(2026, 4, 6),
        )
        import_request = build_import_request_from_upload_request(upload_request)
        decision = validate_import_request(import_request)

        assert upload_request.manifest.artifact_id == discovery.run_manifest.artifact_hash
        assert upload_request.payload_bundle.review_export_ref.endswith("review_export.md")
        assert upload_request.governance_reference_date == date(2026, 4, 6)
        assert import_request.governance_reference_date == date(2026, 4, 6)
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_upload_request_from_replay_plan_materializes_typed_upload_request():
    export_dir = _export_dir()

    try:
        discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
        upload_request = build_upload_request_from_replay_plan(
            replay_plan,
            payload_bundle=discovery.payload_bundle,
            bundle=_upload_bundle(artifact_id=discovery.run_manifest.artifact_hash),
            signature_envelope=build_lab_fixture_signature_envelope(),
            uploaded_by="lab-user",
            upload_context=ArtifactUploadContext.LOCAL_LAB,
            governance_reference_date=date(2026, 4, 6),
        )
        import_request = build_import_request_from_upload_request(upload_request)
        decision = validate_import_request(import_request)

        assert upload_request.manifest.artifact_id == discovery.run_manifest.artifact_hash
        assert upload_request.payload_bundle.review_export_ref.endswith("review_export.md")
        assert upload_request.governance_reference_date == date(2026, 4, 6)
        assert import_request.governance_reference_date == date(2026, 4, 6)
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def test_build_upload_context_from_replay_import_context_materializes_governed_chain():
    export_dir = _export_dir()

    try:
        discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
        import_context = build_import_context_from_replay_plan(
            replay_plan,
            payload_bundle=discovery.payload_bundle,
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            training_end=date(2026, 4, 6),
            governance_reference_date=date(2026, 4, 6),
            drift_score_threshold=0.85,
        )
        upload_context = build_upload_context_from_replay_import_context(
            import_context,
            local_replay_evidence=_local_replay_evidence(),
            signature_envelope=build_lab_fixture_signature_envelope(),
            uploaded_by="lab-user",
            upload_context=ArtifactUploadContext.LOCAL_LAB,
            governance_reference_date=date(2026, 4, 6),
            artifact_class=ArtifactClass.DAMAGE_REDUCER,
            artifact_scope="bridge:test",
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
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
            distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
            covariance_shrinkage_matrix_ref="matrix_ref",
        )
        decision = validate_import_request(upload_context.import_request)

        assert upload_context.upload_request.manifest.signature_envelope is not None
        assert upload_context.import_request.proof_summary is not None
        assert upload_context.artifact_bundle.artifact_scope == "bridge:test"
        assert decision.accepted is True
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
