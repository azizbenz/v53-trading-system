from __future__ import annotations

from datetime import date

from backtest_artifact_import import evaluate_artifact_compatibility_policy
from interface_contracts import (
    ArtifactCompatibilityEntry,
    ArtifactCompatibilityStatus,
    ProfileId,
    StrategyClassification,
)
from local_replay_runtime import ArtifactManifest


def _manifest(**overrides) -> ArtifactManifest:
    defaults = dict(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        source_profile=ProfileId.COMPLETE,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v1",
        lineage_version="a.v1.1",
        artifact_schema_version="1.0.0",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
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


def test_compatibility_policy_accepts_supported_exact_registry_match():
    result = evaluate_artifact_compatibility_policy(_manifest())

    assert result.accepted is True
    assert result.status == ArtifactCompatibilityStatus.SUPPORTED
    assert result.reasons == ()
    assert result.matched_entry is not None
    assert result.matched_entry.artifact_schema_version == "1.0.0"


def test_compatibility_policy_rejects_unknown_major_versions():
    result = evaluate_artifact_compatibility_policy(
        _manifest(
            artifact_schema_version="9.0.0",
            feature_set_version="9.0.0",
            transform_set_version="9.0.0",
        )
    )

    assert result.accepted is False
    assert result.status == ArtifactCompatibilityStatus.REJECTED
    assert "ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE" in result.reasons
    assert "FEATURE_SET_INCOMPATIBLE" in result.reasons
    assert "TRANSFORM_SET_INCOMPATIBLE" in result.reasons


def test_compatibility_policy_marks_exact_deprecated_entry_as_migration_required():
    result = evaluate_artifact_compatibility_policy(
        _manifest(),
        registry=(
            ArtifactCompatibilityEntry(
                artifact_schema_version="1.0.0",
                feature_set_version="1.0.0",
                transform_set_version="1.0.0",
                status=ArtifactCompatibilityStatus.DEPRECATED,
                activated_on=date(2026, 4, 5),
                support_end_on=date(2026, 6, 1),
                migration_note="migrate to 2.0.0",
            ),
        ),
    )

    assert result.accepted is False
    assert result.status == ArtifactCompatibilityStatus.DEPRECATED
    assert result.reasons == ("ARTIFACT_REQUIRES_MIGRATION",)
    assert result.matched_entry is not None
    assert result.matched_entry.status == ArtifactCompatibilityStatus.DEPRECATED
