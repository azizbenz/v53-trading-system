from __future__ import annotations

from backtest_artifact_import import (
    ArtifactImportSummary,
    ArtifactSignatureCheckStatus,
    build_replay_import_projection,
)
from interface_contracts import ProfileId, PromotionState, ReviewState, StrategyClassification
from local_replay_runtime.enums import ReplayArtifactKind


def _summary(**overrides) -> ArtifactImportSummary:
    defaults = dict(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
        strategy_classification=StrategyClassification.A_VARIANT,
        source_profile=ProfileId.COMPLETE,
        lineage_version="a.v1.1",
        exported_from="local",
        dataset_ref="dataset-1",
        clock_ref="clock-1",
        review_export_ref="exports/review.md",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
        payload_ref_count=5,
        payload_bundle_present=True,
        accepted=True,
        validation_status="accepted",
        normalized_promotion_state=PromotionState.REPLAY_ONLY,
        review_state=ReviewState.PENDING,
    )
    defaults.update(overrides)
    return ArtifactImportSummary(**defaults)


def test_build_replay_import_projection_maps_accepted_summary():
    projection = build_replay_import_projection(
        _summary(
            feature_lineage_required=True,
            feature_lineage_present=True,
            feature_lineage_status="ok",
            transform_whitelist_required=True,
            transform_whitelist_present=True,
            transform_whitelist_status="ok",
            signature_check_status=ArtifactSignatureCheckStatus.TRUST_ELIGIBLE,
            signature_key_id="lab_ed25519_2026_q2_k1",
            trusted_key_status="active",
        )
    )

    assert projection.status == "healthy"
    assert projection.artifact_kind == "review_packet"
    assert projection.validation_status == "accepted"
    assert projection.dataset_ref == "dataset-1"
    assert projection.clock_ref == "clock-1"
    assert projection.compatibility_status == "supported"
    assert projection.feature_lineage_required is True
    assert projection.feature_lineage_present is True
    assert projection.feature_lineage_status == "ok"
    assert projection.transform_whitelist_required is True
    assert projection.transform_whitelist_present is True
    assert projection.transform_whitelist_status == "ok"
    assert projection.signature_check_status == "trust_eligible"
    assert projection.signature_key_id == "lab_ed25519_2026_q2_k1"
    assert projection.trusted_key_status == "active"
    assert projection.conflict_resolution_mode == "no_trade_then_strictest"
    assert projection.conflict_hard_veto_action == "no_trade"
    assert projection.conflict_additive_soft_boosts_allowed is True
    assert projection.conflict_additive_soft_reduces_allowed is True
    assert projection.registry_atomicity_mode == "atomic_snapshot_swap"
    assert projection.registry_concurrency_model == "single_writer_multi_reader"
    assert projection.registry_publish_requires_atomic_replace is True
    assert projection.registry_publish_requires_fsync is True
    assert projection.registry_rollback_to_last_known_good is True
    assert projection.lifecycle_state == "activation=replay_only / health=active / compat=supported"


def test_build_replay_import_projection_maps_rejected_signature_state():
    projection = build_replay_import_projection(
        _summary(
            accepted=False,
            validation_status="needs_revision",
            review_state=ReviewState.NEEDS_REVISION,
            feature_lineage_required=True,
            feature_lineage_present=False,
            feature_lineage_status="missing",
            feature_lineage_reasons=("FEATURE_LINEAGE_LOCK_REQUIRED",),
            transform_whitelist_required=True,
            transform_whitelist_present=False,
            transform_whitelist_status="missing",
            transform_whitelist_reasons=("TRANSFORM_WHITELIST_LOCK_REQUIRED",),
            signature_check_status=ArtifactSignatureCheckStatus.KEY_ID_UNKNOWN,
            signature_key_id="lab_unknown",
            signature_check_reasons=("KEY_ID_UNKNOWN",),
            rejection_reasons=("import target must start at SHADOW",),
        )
    )

    assert projection.status == "warning"
    assert projection.review_state == "needs_revision"
    assert projection.compatibility_status == "supported"
    assert projection.feature_lineage_status == "missing"
    assert projection.feature_lineage_reasons == ("FEATURE_LINEAGE_LOCK_REQUIRED",)
    assert projection.transform_whitelist_status == "missing"
    assert projection.transform_whitelist_reasons == ("TRANSFORM_WHITELIST_LOCK_REQUIRED",)
    assert projection.signature_check_status == "key_id_unknown"
    assert projection.signature_check_reasons == ("KEY_ID_UNKNOWN",)
    assert projection.rejection_reasons == ("import target must start at SHADOW",)
