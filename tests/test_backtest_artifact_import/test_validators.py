"""Tests for controlled local->VPS artifact import."""

from __future__ import annotations

from interface_contracts import ProfileId, PromotionState, RuntimeMode, StrategyClassification
from backtest_artifact_import import ArtifactImportRequest, validate_import_request
from local_replay_runtime import ArtifactManifest


def _manifest() -> ArtifactManifest:
    return ArtifactManifest(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        source_profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v1",
        lineage_version="a.v1.1",
    )


def test_import_request_accepts_shadow_entrypoint_only():
    decision = validate_import_request(ArtifactImportRequest(manifest=_manifest()))

    assert decision.accepted is True
    assert decision.normalized_promotion_state == PromotionState.SHADOW_CANDIDATE


def test_import_request_rejects_micro_live_target():
    decision = validate_import_request(
        ArtifactImportRequest(
            manifest=_manifest(),
            target_runtime_mode=RuntimeMode.MICRO_LIVE,
        )
    )

    assert decision.accepted is False
    assert "import target must start at SHADOW" in decision.reasons


def test_import_request_rejects_live_candidate_jump():
    decision = validate_import_request(
        ArtifactImportRequest(
            manifest=_manifest(),
            requested_promotion_state=PromotionState.LIVE_CANDIDATE,
        )
    )

    assert decision.accepted is False
    assert "implicit promotion beyond SHADOW is forbidden" in decision.reasons
