from __future__ import annotations

from datetime import UTC, datetime

import pytest

from interface_contracts import (
    MlAntiLeakageProofArtifact,
    MlLiveDriftSnapshot,
    MlModelWindow,
    MlSupplementaryRefsSourceSummary,
)


def test_anti_leakage_proof_contract_hashes_and_marks_ready() -> None:
    proof = MlAntiLeakageProofArtifact.create(
        artifact_id="anti-leakage-proof-1",
        target_artifact_hash="a" * 64,
        dataset_hash="b" * 64,
        feature_hash="c" * 64,
        label_policy="ml_backtest_realized_target_policy.v1",
        train_window=MlModelWindow(
            start_at=datetime(2025, 10, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 29, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 30, tzinfo=UTC),
            end_at=datetime(2026, 4, 28, tzinfo=UTC),
        ),
        test_window=MlModelWindow(
            start_at=datetime(2026, 4, 29, tzinfo=UTC),
            end_at=datetime(2026, 5, 6, tzinfo=UTC),
        ),
        purge_size=48,
        embargo_size=24,
        label_horizon="30m",
        max_feature_timestamp=datetime(2026, 4, 28, 23, 30, tzinfo=UTC),
        min_label_timestamp=datetime(2026, 4, 28, 23, 30, tzinfo=UTC),
        feature_timestamp_alignment_status="FEATURE_TIMESTAMP_ALIGNED",
        no_future_data_leak_status="NO_FUTURE_DATA_LEAK_PROVEN",
        reviewer_signature="quant-reviewer",
        method_version_hash="anti_leakage.v1",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )

    assert proof.artifact_hash == proof.artifact_hash_sha256()
    assert proof.promotion_ready_proof is True


def test_anti_leakage_proof_contract_rejects_future_leak_timestamps() -> None:
    with pytest.raises(ValueError, match="max_feature_timestamp <= min_label_timestamp"):
        MlAntiLeakageProofArtifact.create(
            artifact_id="anti-leakage-proof-bad",
            target_artifact_hash="a" * 64,
            dataset_hash="b" * 64,
            feature_hash="c" * 64,
            label_policy="ml_backtest_realized_target_policy.v1",
            train_window=MlModelWindow(
                start_at=datetime(2025, 10, 1, tzinfo=UTC),
                end_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            validation_window=MlModelWindow(
                start_at=datetime(2026, 3, 30, tzinfo=UTC),
                end_at=datetime(2026, 4, 28, tzinfo=UTC),
            ),
            purge_size=48,
            embargo_size=24,
            label_horizon="30m",
            max_feature_timestamp=datetime(2026, 4, 29, 0, 0, tzinfo=UTC),
            min_label_timestamp=datetime(2026, 4, 28, 23, 30, tzinfo=UTC),
            feature_timestamp_alignment_status="FEATURE_TIMESTAMP_ALIGNED",
            no_future_data_leak_status="NO_FUTURE_DATA_LEAK_PROVEN",
            reviewer_signature="quant-reviewer",
            method_version_hash="anti_leakage.v1",
            created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        )


def test_live_drift_snapshot_and_source_summary_expose_freshness() -> None:
    drift = MlLiveDriftSnapshot.create(
        artifact_id="live-drift-1",
        target_artifact_hash="a" * 64,
        feature_hash="b" * 64,
        stage="LIVE",
        feature_ks_pvalue=0.42,
        shadow_diff_pct=0.02,
        live_diff_pct=0.03,
        win_rate_delta=-0.01,
        ce_delta=-0.002,
        source_status="LIVE_DRIFT_SOURCE_GOVERNED",
        input_data_hash="d" * 64,
        method_version_hash="live_drift.v1",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    source_summary = MlSupplementaryRefsSourceSummary.create(
        artifact_id="supplementary-source-1",
        target_artifact_hash="a" * 64,
        feature_hash="b" * 64,
        dataset_hash="c" * 64,
        transport_artifact_ref="E:/exports/ml_model_artifact.json",
        summary_ref="E:/exports/ml_model_artifact.summary.json",
        supplementary_refs_count=3,
        source_component="LOCAL_REPLAY_ML_MODEL_TRANSPORT",
        source_stage="LOCAL_REPLAY",
        source_status="SUPPLEMENTARY_REFS_SOURCE_GOVERNED",
        non_empty_refs_status="NON_EMPTY_SUPPLEMENTARY_REFS_PROVEN",
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        source_stale_after=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        method_version_hash="source_summary.v1",
    )

    assert drift.promotion_ready_snapshot is True
    assert drift.is_stale(as_of=datetime(2026, 5, 7, 12, 0, tzinfo=UTC)) is True
    assert source_summary.runtime_active_ready is True
    assert source_summary.is_stale(as_of=datetime(2026, 4, 30, 12, 1, tzinfo=UTC)) is True
