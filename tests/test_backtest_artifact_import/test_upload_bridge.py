from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backtest_artifact_import import (
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    ArtifactUploadRequest,
    build_artifact_upload_decision,
    build_import_request_from_upload_request,
    validate_import_request,
)
from interface_contracts import (
    ActionUnit,
    ArtifactActionKind,
    ArtifactActivationStage,
    ArtifactClass,
    ArtifactExportBundle,
    ArtifactLifecyclePolicy,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    FeatureLineageLock,
    FeatureLineageRecord,
    HookId,
    PhysicsFeatureFamily,
    ProfileId,
    StrategyClassification,
    TransformWhitelistLock,
    TransformWhitelistId,
)
from local_replay_runtime import ArtifactManifest


def _payload_bundle() -> ArtifactPayloadRefBundle:
    return ArtifactPayloadRefBundle(
        review_export_ref="exports/review.md",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
    )


def _manifest(**overrides) -> ArtifactManifest:
    defaults = dict(
        artifact_id="ART_B_SWEEP_FADE_V1",
        correlation_id="corr-upload-1",
        source_profile=ProfileId.COMPLETE,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v1",
        lineage_version="a.v1.1",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        activation_stage=ArtifactActivationStage.SHADOW_READY,
        allowed_hook_ids=(HookId.ENGINE_B_SWEEP_VALIDATION,),
        allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
        allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
        signature_envelope=ArtifactSignatureEnvelope(
            key_id="lab_ed25519_2026_q2_k1",
            public_key_author_sig="sig",
            payload_hash_sha256="hash",
        ),
        dataset_ref="dataset-1",
        clock_ref="clock-1",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
        review_export_ref="exports/review.md",
        diagnostic_ids=("diag-1",),
        candidate_ids=("cand-1",),
    )
    defaults.update(overrides)
    return ArtifactManifest(**defaults)


def _bundle(**overrides) -> ArtifactExportBundle:
    feature_set_version = overrides.get("feature_set_version", "1.0.0")
    transform_set_version = overrides.get("transform_set_version", "1.0.0")
    defaults = dict(
        artifact_id="ART_B_SWEEP_FADE_V1",
        artifact_version="1.0.0",
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_b:sweep_fade",
        allowed_hook_ids=(HookId.ENGINE_B_SWEEP_VALIDATION,),
        allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
        allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
        distilled_logic_format="rule_ast_json",
        rules=(
            {
                "rule_id": "rule_1",
                "conditions": (
                    {
                        "condition_id": "SWEEP_GT",
                        "feature_id": "sweep_score_1m",
                        "operator": ">",
                        "threshold": 0.82,
                    },
                ),
                "action": {
                    "action": "soft_boost",
                    "action_value": 0.15,
                    "action_unit": "raw_score_multiplier",
                    "max_raw_score_cap": 2.5,
                    "reason_code": "PHYSICS_B_SWEEP_FADE_BOOST",
                },
                "support_count": 12,
                "fragility_score": 0.15,
            },
        ),
        payload_hash_sha256="hash",
        public_key_author_sig="sig",
        dataset_id="dataset-1",
        feature_set_version=feature_set_version,
        transform_set_version=transform_set_version,
        feature_lineage_lock=FeatureLineageLock(
            feature_set_version=feature_set_version,
            transform_set_version=transform_set_version,
            records=(
                FeatureLineageRecord(
                    feature_id="sweep_score_1m",
                    family=PhysicsFeatureFamily.SWEEP_SCORE,
                    source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
                    transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                    feature_set_version=feature_set_version,
                    transform_set_version=transform_set_version,
                ),
            )
        ),
        transform_whitelist_lock=TransformWhitelistLock(
            transform_set_version=transform_set_version,
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
    defaults.update(overrides)
    return ArtifactExportBundle(**defaults)


def _upload_request(**overrides) -> ArtifactUploadRequest:
    defaults = dict(
        bundle=_bundle(),
        manifest=_manifest(),
        payload_bundle=_payload_bundle(),
        uploaded_by="lab-user",
        upload_context=ArtifactUploadContext.LOCAL_LAB,
    )
    defaults.update(overrides)
    return ArtifactUploadRequest(**defaults)


def test_upload_request_requires_bundle_manifest_alignment():
    with pytest.raises(ValidationError):
        _upload_request(bundle=_bundle(feature_set_version="2.0.0"))


def test_build_import_request_from_upload_request_keeps_governed_payload_bundle():
    upload_request = _upload_request()

    import_request = build_import_request_from_upload_request(upload_request)

    assert import_request.manifest.artifact_id == "ART_B_SWEEP_FADE_V1"
    assert import_request.payload_bundle is not None
    assert import_request.payload_refs == upload_request.payload_bundle.payload_refs
    assert import_request.feature_lineage_required is True
    assert import_request.feature_lineage_lock is not None
    assert import_request.expected_feature_ids == ("sweep_score_1m",)
    assert import_request.transform_whitelist_required is True
    assert import_request.transform_whitelist_lock is not None
    assert import_request.expected_transform_ids == (TransformWhitelistId.SWEEP_SCORE_V1,)
    assert import_request.lifecycle_policy == upload_request.bundle.lifecycle_policy
    assert import_request.training_end == upload_request.bundle.training_end
    assert import_request.governance_reference_date == date.today()
    assert import_request.drift_score_threshold == upload_request.bundle.drift_score_threshold
    assert import_request.proof_required is True
    assert import_request.proof_summary == upload_request.bundle.proof_summary


def test_build_artifact_upload_decision_maps_accepted_dry_run():
    upload_request = _upload_request()
    import_request = build_import_request_from_upload_request(upload_request)
    import_decision = validate_import_request(import_request)

    decision = build_artifact_upload_decision(upload_request, import_decision)

    assert decision.accepted is True
    assert decision.status.value == "DRY_RUN_OK"


def test_build_artifact_upload_decision_maps_signature_rejection():
    upload_request = _upload_request(
        manifest=_manifest(
            signature_envelope=ArtifactSignatureEnvelope(
                key_id="lab_unknown",
                public_key_author_sig="sig",
                payload_hash_sha256="hash",
            )
        )
    )
    import_request = build_import_request_from_upload_request(upload_request)
    import_decision = validate_import_request(import_request)

    decision = build_artifact_upload_decision(upload_request, import_decision)

    assert decision.accepted is False
    assert decision.status.value == "REJECTED_SIGNATURE"
    assert "KEY_ID_UNKNOWN" in decision.rejection_reasons


def test_build_artifact_upload_decision_maps_schema_rejection():
    upload_request = _upload_request(
        manifest=_manifest(
            artifact_schema_version="9.0.0",
            feature_set_version="9.0.0",
            transform_set_version="9.0.0",
        ),
        bundle=_bundle(
            feature_set_version="9.0.0",
            transform_set_version="9.0.0",
        ),
    )
    import_request = build_import_request_from_upload_request(upload_request)
    import_decision = validate_import_request(import_request)

    decision = build_artifact_upload_decision(upload_request, import_decision)

    assert decision.accepted is False
    assert decision.status.value == "REJECTED_SCHEMA"


def test_build_artifact_upload_decision_maps_scope_rejection():
    upload_request = _upload_request(target_runtime_mode="live")
    import_request = build_import_request_from_upload_request(upload_request)
    import_decision = validate_import_request(import_request)

    decision = build_artifact_upload_decision(upload_request, import_decision)

    assert decision.accepted is False
    assert decision.status.value == "REJECTED_SCOPE"
    assert "import target must start at SHADOW" in decision.rejection_reasons


def test_build_artifact_upload_decision_maps_proof_rejection():
    upload_request = _upload_request(
        bundle=_bundle(
            proof_summary=ArtifactProofSummary(
                anti_cowardice_pass=True,
                friction_regret_pass=True,
                walk_forward_pass=True,
                regime_segmentation_pass=True,
                operational_burden_pass=True,
                capital_efficiency_pass=True,
                ablation_delta_net_pnl=0.0,
                ablation_delta_ce=0.03,
                friction_regret_value=0.01,
                block_rate_delta=0.02,
            )
        )
    )
    import_request = build_import_request_from_upload_request(upload_request)
    import_decision = validate_import_request(import_request)

    decision = build_artifact_upload_decision(upload_request, import_decision)

    assert decision.accepted is False
    assert decision.status.value == "REJECTED_PROOF"
    assert "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW" in decision.rejection_reasons


def test_upload_request_rejects_missing_lineage_coverage():
    with pytest.raises(ValidationError, match="feature_lineage_lock is incomplete"):
        _upload_request(
            bundle=_bundle(
                feature_lineage_lock=FeatureLineageLock(records=()),
            )
        )


def test_upload_request_rejects_missing_transform_whitelist_coverage():
    with pytest.raises(ValidationError, match="transform_whitelist_lock is incomplete"):
        _upload_request(
            bundle=_bundle(
                transform_whitelist_lock=TransformWhitelistLock(
                    allowed_transform_ids=(TransformWhitelistId.CLIP01,)
                ),
            )
        )
