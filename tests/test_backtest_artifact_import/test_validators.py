"""Tests for controlled local->VPS artifact import."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import ProfileId, PromotionState, RuntimeMode, StrategyClassification
from backtest_artifact_import import (
    ArtifactImportRequest,
    summarize_import_request,
    validate_import_request,
)
from local_replay_runtime import ArtifactManifest, ReplayArtifactKind


def _manifest(**overrides) -> ArtifactManifest:
    defaults = dict(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        source_profile=ProfileId.LIGHT,
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
    defaults = dict(
        manifest=_manifest(),
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
        payload_refs=(
            "exports/review.md",
            "exports/feature_bridge.json",
            "exports/parity.json",
            "exports/replay_metrics.json",
            "exports/replay_dtr.json",
            "exports/bundle.json",
        ),
    )
    defaults.update(overrides)
    return ArtifactImportRequest(**defaults)


def test_import_request_accepts_shadow_entrypoint_only():
    decision = validate_import_request(_request())

    assert decision.accepted is True
    assert decision.normalized_promotion_state == PromotionState.SHADOW_CANDIDATE


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
        )
    )

    assert decision.accepted is False
    assert set(decision.reasons) == {
        "feature bridge ref is required for governed import",
        "parity diagnostics ref is required for governed import",
        "replay metrics ref is required for governed import",
        "replay dtr ref is required for governed import",
    }


def test_import_request_acceptance_keeps_pending_review():
    decision = validate_import_request(_request())

    assert decision.accepted is True
    assert decision.review_state.value == "pending"


def test_import_summary_projects_clean_monitoring_facts():
    request = _request()
    decision = validate_import_request(request)
    summary = summarize_import_request(request, decision)

    assert summary.artifact_id == "artifact-1"
    assert summary.validation_status == "accepted"
    assert summary.payload_ref_count == 6
    assert summary.feature_bridge_ref == "exports/feature_bridge.json"
    assert summary.parity_diagnostics_ref == "exports/parity.json"
    assert summary.review_export_ref == "exports/review.md"
    assert summary.accepted is True
