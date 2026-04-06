from __future__ import annotations

from interface_contracts import ArtifactSignatureEnvelope, ProfileId, StrategyClassification
from backtest_artifact_import import (
    ArtifactSignatureCheckStatus,
    evaluate_artifact_signature_policy,
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


def test_signature_policy_allows_unsigned_manifest_without_forcing_rejection():
    result = evaluate_artifact_signature_policy(_manifest())

    assert result.status == ArtifactSignatureCheckStatus.NOT_PROVIDED
    assert result.accepted is True


def test_signature_policy_marks_trust_eligible_known_active_key():
    result = evaluate_artifact_signature_policy(
        _manifest(
            signature_envelope=ArtifactSignatureEnvelope(
                key_id="lab_ed25519_2026_q2_k1",
                public_key_author_sig="sig",
                payload_hash_sha256="hash",
            )
        )
    )

    assert result.status == ArtifactSignatureCheckStatus.TRUST_ELIGIBLE
    assert result.accepted is True
    assert result.trusted_key_status == "active"


def test_signature_policy_rejects_revoked_key():
    result = evaluate_artifact_signature_policy(
        _manifest(
            signature_envelope=ArtifactSignatureEnvelope(
                key_id="lab_ed25519_2025_q4_revoked",
                public_key_author_sig="sig",
                payload_hash_sha256="hash",
            )
        )
    )

    assert result.status == ArtifactSignatureCheckStatus.KEY_REVOKED
    assert result.accepted is False
    assert result.reasons == ("KEY_REVOKED",)
