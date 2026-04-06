"""Thin monitoring projection adapters for governed LOCAL_REPLAY imports."""

from __future__ import annotations

from backtest_artifact_import.contracts import ArtifactImportSummary
from monitoring.contracts import ReplayImportProjection


def _status_from_summary(summary: ArtifactImportSummary) -> str:
    if summary.validation_status == "not_run":
        return "info"
    if summary.accepted:
        return "healthy"
    return "warning"


def build_replay_import_projection(summary: ArtifactImportSummary) -> ReplayImportProjection:
    """Project a governed import summary into the normalized replay/import surface."""

    return ReplayImportProjection(
        status=_status_from_summary(summary),
        artifact_id=summary.artifact_id,
        artifact_kind=summary.artifact_kind.value,
        exported_from=summary.exported_from,
        source_profile=summary.source_profile.value,
        lineage_version=summary.lineage_version,
        dataset_ref=summary.dataset_ref,
        clock_ref=summary.clock_ref,
        activation_stage=summary.activation_stage.value,
        health_state=summary.health_state.value,
        lifecycle_state=(
            f"activation={summary.activation_stage.value} / "
            f"health={summary.health_state.value} / "
            f"compat={summary.compatibility_status.value}"
        ),
        validation_status=summary.validation_status,
        review_state=summary.review_state.value,
        compatibility_status=summary.compatibility_status.value,
        compatibility_reasons=summary.compatibility_reasons,
        feature_lineage_required=summary.feature_lineage_required,
        feature_lineage_present=summary.feature_lineage_present,
        feature_lineage_status=summary.feature_lineage_status,
        feature_lineage_reasons=summary.feature_lineage_reasons,
        transform_whitelist_required=summary.transform_whitelist_required,
        transform_whitelist_present=summary.transform_whitelist_present,
        transform_whitelist_status=summary.transform_whitelist_status,
        transform_whitelist_reasons=summary.transform_whitelist_reasons,
        signature_check_status=summary.signature_check_status.value,
        signature_key_id=summary.signature_key_id,
        trusted_key_status=summary.trusted_key_status,
        signature_check_reasons=summary.signature_check_reasons,
        conflict_resolution_mode=summary.conflict_policy.resolution_mode.value,
        conflict_hard_veto_action=summary.conflict_policy.hard_veto_action.value,
        conflict_score_aggregation_mode=summary.conflict_policy.score_aggregation_mode.value,
        conflict_size_reduce_mode=summary.conflict_policy.size_reduce_mode.value,
        conflict_rank_adjust_mode=summary.conflict_policy.rank_adjust_mode.value,
        conflict_additive_soft_boosts_allowed=(
            summary.conflict_policy.additive_soft_boosts_allowed
        ),
        conflict_additive_soft_reduces_allowed=(
            summary.conflict_policy.additive_soft_reduces_allowed
        ),
        registry_atomicity_mode=summary.registry_policy.atomicity_mode.value,
        registry_concurrency_model=summary.registry_policy.concurrency_model.value,
        registry_publish_requires_atomic_replace=(
            summary.registry_policy.publish_requires_atomic_replace
        ),
        registry_publish_requires_fsync=summary.registry_policy.publish_requires_fsync,
        registry_rollback_to_last_known_good=(
            summary.registry_policy.rollback_to_last_known_good
        ),
        payload_ref_count=summary.payload_ref_count,
        payload_bundle_present=summary.payload_bundle_present,
        review_export_ref=summary.review_export_ref,
        feature_bridge_ref=summary.feature_bridge_ref,
        parity_diagnostics_ref=summary.parity_diagnostics_ref,
        replay_metrics_ref=summary.replay_metrics_ref,
        replay_dtr_ref=summary.replay_dtr_ref,
        rejection_reasons=summary.rejection_reasons,
    )


__all__ = ["build_replay_import_projection"]
