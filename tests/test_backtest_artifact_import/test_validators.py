"""Tests for controlled local->VPS artifact import."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from interface_contracts import (
    ActionUnit,
    ArtifactActivationStage,
    ArtifactActionKind,
    ArtifactHealthState,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    FeatureLineageLock,
    FeatureLineageRecord,
    HookId,
    PhysicsFeatureFamily,
    ProfileId,
    PromotionState,
    RuntimeMode,
    StrategyClassification,
    TransformWhitelistLock,
    TransformWhitelistId,
)
from backtest_artifact_import import (
    ArtifactImportRequest,
    ArtifactPayloadRefBundle,
    summarize_import_request,
    validate_import_request,
)
from local_replay_runtime import ArtifactManifest, ReplayArtifactKind


def _manifest(**overrides) -> ArtifactManifest:
    defaults = dict(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        source_profile=ProfileId.COMPLETE,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v1",
        lineage_version="a.v1.1",
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


def _request(**overrides) -> ArtifactImportRequest:
    payload_bundle = ArtifactPayloadRefBundle(
        review_export_ref="exports/review.md",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
        supplementary_refs=("exports/bundle.json",),
    )
    defaults = dict(
        manifest=_manifest(),
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
        payload_bundle=payload_bundle,
        payload_refs=payload_bundle.payload_refs,
        lifecycle_policy={"ttl_max_days": 30, "rule_half_life_days": 7},
        training_end=date(2026, 4, 1),
        governance_reference_date=date(2026, 4, 6),
        drift_score_threshold=0.85,
    )
    defaults.update(overrides)
    return ArtifactImportRequest(**defaults)


def test_import_request_accepts_shadow_entrypoint_only():
    decision = validate_import_request(_request())

    assert decision.accepted is True
    assert decision.normalized_promotion_state == PromotionState.SHADOW_CANDIDATE


def test_import_request_rejects_non_complete_source_profile():
    decision = validate_import_request(
        _request(manifest=_manifest(source_profile=ProfileId.LIGHT))
    )

    assert decision.accepted is False
    assert "governed import requires source_profile=COMPLETE" in decision.reasons


def test_import_request_can_derive_payload_refs_from_typed_bundle():
    request = ArtifactImportRequest(
        manifest=_manifest(),
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
        payload_bundle=ArtifactPayloadRefBundle(
            review_export_ref="exports/review.md",
            feature_bridge_ref="exports/feature_bridge.json",
            parity_diagnostics_ref="exports/parity.json",
            replay_metrics_ref="exports/replay_metrics.json",
            replay_dtr_ref="exports/replay_dtr.json",
            supplementary_refs=("exports/bundle.json",),
        ),
    )

    assert request.payload_refs == (
        "exports/review.md",
        "exports/feature_bridge.json",
        "exports/parity.json",
        "exports/replay_metrics.json",
        "exports/replay_dtr.json",
        "exports/bundle.json",
    )


def test_import_request_rejects_payload_refs_mismatch_with_typed_bundle():
    with pytest.raises(ValidationError):
        ArtifactImportRequest(
            manifest=_manifest(),
            artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
            payload_bundle=ArtifactPayloadRefBundle(
                review_export_ref="exports/review.md",
                feature_bridge_ref="exports/feature_bridge.json",
                parity_diagnostics_ref="exports/parity.json",
                replay_metrics_ref="exports/replay_metrics.json",
                replay_dtr_ref="exports/replay_dtr.json",
            ),
            payload_refs=("exports/review.md", "exports/feature_bridge.json"),
        )


def test_import_request_rejects_micro_live_target():
    decision = validate_import_request(
        _request(target_runtime_mode=RuntimeMode.MICRO_LIVE)
    )

    assert decision.accepted is False
    assert "import target must start at SHADOW" in decision.reasons


def test_import_request_rejects_live_candidate_jump():
    decision = validate_import_request(
        _request(requested_promotion_state=PromotionState.LIVE_CANDIDATE)
    )

    assert decision.accepted is False
    assert "implicit promotion beyond SHADOW is forbidden" in decision.reasons


def test_import_request_model_rejects_local_replay_target():
    with pytest.raises(ValidationError):
        _request(target_runtime_mode=RuntimeMode.LOCAL_REPLAY)


def test_import_request_rejects_multiple_policy_violations():
    decision = validate_import_request(
        _request(
            target_runtime_mode=RuntimeMode.LIVE,
            requested_promotion_state=PromotionState.LIVE_CANDIDATE,
            payload_bundle=None,
            payload_refs=(
                "exports/review.md",
                "exports/review.md",
                "exports/feature_bridge.json",
                "exports/parity.json",
                "exports/replay_metrics.json",
                "exports/replay_dtr.json",
            ),
        )
    )

    assert decision.accepted is False
    assert decision.review_state.value == "needs_revision"
    assert set(decision.reasons) == {
        "import target must start at SHADOW",
        "implicit promotion beyond SHADOW is forbidden",
        "payload refs must be unique",
    }


def test_import_request_rejects_missing_review_bundle_refs():
    decision = validate_import_request(
        _request(
            manifest=_manifest(review_export_ref=""),
            payload_bundle=None,
            payload_refs=("exports/bundle.json",),
        )
    )

    assert decision.accepted is False
    assert set(decision.reasons) == {
        "review packets require a review export ref",
        "feature bridge ref must be included in payload refs",
        "parity diagnostics ref must be included in payload refs",
        "replay metrics ref must be included in payload refs",
        "replay dtr ref must be included in payload refs",
    }


def test_import_request_rejects_incomplete_payload_and_origin_drift():
    decision = validate_import_request(
        _request(
            manifest=_manifest(exported_from="vps"),
            payload_bundle=None,
            payload_refs=(),
        )
    )

    assert decision.accepted is False
    assert set(decision.reasons) == {
        "unsupported artifact origin",
        "payload refs are required for governed import",
        "review export ref must be included in payload refs",
        "feature bridge ref must be included in payload refs",
        "parity diagnostics ref must be included in payload refs",
        "replay metrics ref must be included in payload refs",
        "replay dtr ref must be included in payload refs",
    }


def test_import_request_rejects_missing_dataset_or_clock_refs():
    decision = validate_import_request(
        _request(
            manifest=_manifest(dataset_ref="", clock_ref=""),
        )
    )

    assert decision.accepted is False
    assert "dataset and clock refs are required for governed import" in decision.reasons


def test_import_request_rejects_missing_replay_usefulness_refs():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                feature_bridge_ref="",
                parity_diagnostics_ref="",
                replay_metrics_ref="",
                replay_dtr_ref="",
            ),
            payload_bundle=None,
        )
    )

    assert decision.accepted is False
    assert set(decision.reasons) == {
        "feature bridge ref is required for governed import",
        "parity diagnostics ref is required for governed import",
        "replay metrics ref is required for governed import",
        "replay dtr ref is required for governed import",
    }


def test_import_request_rejects_non_active_artifact_health_state():
    decision = validate_import_request(
        _request(
            manifest=_manifest(health_state=ArtifactHealthState.DORMANT),
        )
    )

    assert decision.accepted is False
    assert "artifact health state blocks governed import" in decision.reasons


def test_import_request_rejects_governed_hook_without_explicit_action_kind():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                activation_stage=ArtifactActivationStage.SHADOW_READY,
                allowed_hook_ids=(HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,),
            ),
        )
    )

    assert decision.accepted is False
    assert "governed hook declarations require explicit action kinds" in decision.reasons


def test_import_request_rejects_action_kind_without_governed_hook():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                allowed_action_kinds=(ArtifactActionKind.NO_TRADE,),
            ),
        )
    )

    assert decision.accepted is False
    assert "explicit action kinds require governed hook declarations" in decision.reasons


def test_import_request_rejects_score_action_kind_without_action_unit():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                allowed_hook_ids=(HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,),
                allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            ),
        )
    )

    assert decision.accepted is False
    assert "governed action kinds require explicit action units" in decision.reasons


def test_import_request_rejects_unknown_schema_version():
    decision = validate_import_request(
        _request(
            manifest=_manifest(artifact_schema_version="artifact.v1"),
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_SCHEMA_UNKNOWN" in decision.reasons


def test_import_request_rejects_major_incompatible_versions():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                artifact_schema_version="9.0.0",
                feature_set_version="9.0.0",
                transform_set_version="9.0.0",
            ),
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE" in decision.reasons
    assert "FEATURE_SET_INCOMPATIBLE" in decision.reasons
    assert "TRANSFORM_SET_INCOMPATIBLE" in decision.reasons


def test_import_request_rejects_supported_major_but_unknown_minor_and_patch():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                artifact_schema_version="1.2.3",
                feature_set_version="1.2.3",
                transform_set_version="1.2.3",
            ),
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED" in decision.reasons
    assert "FEATURE_SET_UNKNOWN" in decision.reasons
    assert "TRANSFORM_SET_UNKNOWN" in decision.reasons


def test_import_request_acceptance_keeps_pending_review():
    decision = validate_import_request(_request())

    assert decision.accepted is True
    assert decision.review_state.value == "pending"


def test_import_request_rejects_unknown_signature_key_id():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                signature_envelope=ArtifactSignatureEnvelope(
                    key_id="lab_ed25519_unknown",
                    public_key_author_sig="sig",
                    payload_hash_sha256="hash",
                )
            )
        )
    )

    assert decision.accepted is False
    assert "KEY_ID_UNKNOWN" in decision.reasons


def test_import_request_rejects_payload_hash_mismatch_when_expected_hash_is_supplied():
    decision = validate_import_request(
        _request(
            manifest=_manifest(
                signature_envelope=ArtifactSignatureEnvelope(
                    key_id="lab_ed25519_2026_q2_k1",
                    public_key_author_sig="sig",
                    payload_hash_sha256="hash-a",
                )
            )
        ),
        expected_payload_hash_sha256="hash-b",
    )

    assert decision.accepted is False
    assert "PAYLOAD_HASH_MISMATCH" in decision.reasons


def test_import_summary_projects_clean_monitoring_facts():
    request = _request(
        manifest=_manifest(
            activation_stage=ArtifactActivationStage.SHADOW_READY,
            allowed_hook_ids=(HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,),
            allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
            signature_envelope=ArtifactSignatureEnvelope(
                key_id="lab_ed25519_2026_q2_k1",
                public_key_author_sig="sig",
                payload_hash_sha256="hash",
            ),
        )
    )
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.artifact_id == "artifact-1"
    assert summary.validation_status == "accepted"
    assert summary.payload_ref_count == 6
    assert summary.artifact_schema_version == "1.0.0"
    assert summary.feature_set_version == "1.0.0"
    assert summary.transform_set_version == "1.0.0"
    assert summary.compatibility_status.value == "supported"
    assert summary.compatibility_reasons == ()
    assert summary.activation_stage == ArtifactActivationStage.SHADOW_READY
    assert summary.health_state == ArtifactHealthState.ACTIVE
    assert summary.allowed_hook_ids == (HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,)
    assert summary.allowed_action_kinds == (ArtifactActionKind.SOFT_BOOST,)
    assert summary.allowed_action_units == (ActionUnit.RAW_SCORE_MULTIPLIER,)
    assert summary.signature_envelope is not None
    assert summary.signature_envelope.key_id == "lab_ed25519_2026_q2_k1"
    assert summary.signature_check_status.value == "trust_eligible"
    assert summary.signature_key_id == "lab_ed25519_2026_q2_k1"
    assert summary.trusted_key_status == "active"
    assert summary.conflict_policy.hard_veto_action == ArtifactActionKind.NO_TRADE
    assert summary.registry_policy.publish_requires_atomic_replace is True
    assert summary.feature_bridge_ref == "exports/feature_bridge.json"
    assert summary.parity_diagnostics_ref == "exports/parity.json"
    assert summary.review_export_ref == "exports/review.md"
    assert summary.payload_bundle_present is True
    assert summary.accepted is True


def test_import_request_rejects_manifest_refs_mismatch_with_payload_bundle():
    decision = validate_import_request(
        _request(
            manifest=_manifest(review_export_ref="exports/other_review.md"),
        )
    )

    assert decision.accepted is False
    assert "manifest review_export_ref must match payload bundle" in decision.reasons


def test_import_summary_projects_compatibility_reasons_for_unsupported_versions():
    request = _request(
        manifest=_manifest(
            artifact_schema_version="1.2.3",
            feature_set_version="1.2.3",
            transform_set_version="1.2.3",
        )
    )
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.compatibility_status.value == "rejected"
    assert "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED" in summary.compatibility_reasons
    assert "FEATURE_SET_UNKNOWN" in summary.compatibility_reasons
    assert "TRANSFORM_SET_UNKNOWN" in summary.compatibility_reasons


def test_import_request_rejects_required_feature_lineage_lock_when_missing():
    decision = validate_import_request(
        _request(
            feature_lineage_required=True,
            expected_feature_ids=("sweep_score_1m",),
        )
    )

    assert decision.accepted is False
    assert "feature lineage lock is required for governed artifact upload" in decision.reasons


def test_import_request_rejects_missing_lifecycle_policy_governance():
    decision = validate_import_request(
        _request(
            training_end=None,
            lifecycle_policy=None,
            governance_reference_date=None,
            drift_score_threshold=None,
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_LIFECYCLE_POLICY_REQUIRED" in decision.reasons
    assert "ARTIFACT_DRIFT_THRESHOLD_REQUIRED" in decision.reasons


def test_import_request_rejects_expired_ttl_governance():
    decision = validate_import_request(
        _request(
            training_end=date(2026, 1, 1),
            governance_reference_date=date(2026, 4, 6),
            lifecycle_policy={"ttl_max_days": 30, "rule_half_life_days": 7},
            drift_score_threshold=0.85,
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_TTL_EXPIRED" in decision.reasons


def test_import_request_rejects_observed_drift_above_threshold():
    decision = validate_import_request(
        _request(
            training_end=date(2026, 4, 1),
            governance_reference_date=date(2026, 4, 6),
            lifecycle_policy={"ttl_max_days": 30, "rule_half_life_days": 7},
            drift_score_threshold=0.85,
            observed_drift_score=0.90,
        )
    )

    assert decision.accepted is False
    assert "ARTIFACT_DRIFT_THRESHOLD_EXCEEDED" in decision.reasons


def test_import_request_rejects_incomplete_required_feature_lineage_lock():
    decision = validate_import_request(
        _request(
            feature_lineage_required=True,
            expected_feature_ids=("sweep_score_1m", "spread_regime"),
            feature_lineage_lock=FeatureLineageLock(
                records=(
                    FeatureLineageRecord(
                        feature_id="sweep_score_1m",
                        family=PhysicsFeatureFamily.SWEEP_SCORE,
                        source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
                        transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                    ),
                )
            ),
        )
    )

    assert decision.accepted is False
    assert (
        "feature lineage lock: missing lineage for feature_id=spread_regime"
        in decision.reasons
    )


def test_import_request_rejects_required_transform_whitelist_when_missing():
    decision = validate_import_request(
        _request(
            transform_whitelist_required=True,
            expected_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
        )
    )

    assert decision.accepted is False
    assert (
        "transform whitelist lock is required for governed artifact upload"
        in decision.reasons
    )


def test_import_request_rejects_missing_required_proof_summary():
    decision = validate_import_request(
        _request(
            proof_required=True,
        )
    )

    assert decision.accepted is False
    assert "PROOF_SUMMARY_REQUIRED" in decision.reasons


def test_import_request_rejects_weak_required_proof_summary():
    decision = validate_import_request(
        _request(
            proof_required=True,
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
            ),
        )
    )

    assert decision.accepted is False
    assert "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW" in decision.reasons


def test_import_request_rejects_incomplete_required_transform_whitelist():
    decision = validate_import_request(
        _request(
            transform_whitelist_required=True,
            expected_transform_ids=(
                TransformWhitelistId.SWEEP_SCORE_V1,
                TransformWhitelistId.ZPLUS,
            ),
            transform_whitelist_lock=TransformWhitelistLock(
                allowed_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,)
            ),
        )
    )

    assert decision.accepted is False
    assert (
        "transform whitelist lock: missing whitelist for transform_id=zplus"
        in decision.reasons
    )


def test_import_summary_projects_required_feature_lineage_status():
    request = _request(
        feature_lineage_required=True,
        expected_feature_ids=("sweep_score_1m",),
        feature_lineage_lock=FeatureLineageLock(
            records=(
                FeatureLineageRecord(
                    feature_id="sweep_score_1m",
                    family=PhysicsFeatureFamily.SWEEP_SCORE,
                    source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
                    transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                ),
            )
        ),
    )
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.accepted is True
    assert summary.feature_lineage_required is True
    assert summary.feature_lineage_present is True
    assert summary.feature_lineage_status == "ok"
    assert summary.feature_lineage_reasons == ()


def test_import_summary_projects_required_transform_whitelist_status():
    request = _request(
        transform_whitelist_required=True,
        expected_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
        transform_whitelist_lock=TransformWhitelistLock(
            allowed_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,)
        ),
    )
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.accepted is True
    assert summary.transform_whitelist_required is True
    assert summary.transform_whitelist_present is True
    assert summary.transform_whitelist_status == "ok"
    assert summary.transform_whitelist_reasons == ()


def test_import_summary_projects_ttl_and_drift_governance_status():
    request = _request(
        training_end=date(2026, 4, 1),
        governance_reference_date=date(2026, 4, 6),
        lifecycle_policy={"ttl_max_days": 30, "rule_half_life_days": 7},
        drift_score_threshold=0.85,
        observed_drift_score=0.20,
    )
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.accepted is True
    assert summary.ttl_status == "active"
    assert summary.ttl_reasons == ()
    assert summary.drift_status == "within_threshold"
    assert summary.drift_reasons == ()
