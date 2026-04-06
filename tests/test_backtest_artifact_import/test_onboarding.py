"""Tests for the minimal governed strategy onboarding flow."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from interface_contracts import ProfileId, PromotionState, StrategyClassification
from backtest_artifact_import import (
    ArtifactImportRequest,
    ArtifactPayloadRefBundle,
    StrategyLineageRecord,
    StrategyOnboardingRequest,
    validate_strategy_onboarding_request,
)
from local_replay_runtime import ArtifactManifest, ReplayArtifactKind


def _manifest(**overrides) -> ArtifactManifest:
    defaults = dict(
        artifact_id="artifact-onb",
        correlation_id="corr-onb",
        source_profile=ProfileId.COMPLETE,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v3",
        lineage_version="a.v3.1",
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


def _import_request(**overrides) -> ArtifactImportRequest:
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


def _lineage(**overrides) -> StrategyLineageRecord:
    defaults = dict(
        proposal_id="proposal-1",
        classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v3",
        lineage_version="a.v3.1",
        source_version="5.3.0-build10",
        artifact_id="artifact-onb",
    )
    defaults.update(overrides)
    return StrategyLineageRecord(**defaults)


def _request(**overrides) -> StrategyOnboardingRequest:
    defaults = dict(
        proposal_id="proposal-1",
        proposal_name="A Variant Tightening",
        classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v3",
        source_version="5.3.0-build10",
        economic_hypothesis="Improve spread capture under replay.",
        portfolio_hypothesis="Reduce adverse fill clusters.",
        lineage=_lineage(),
        import_request=_import_request(),
    )
    defaults.update(overrides)
    return StrategyOnboardingRequest(**defaults)


def test_onboarding_accepts_a_variant_after_import_gate():
    decision = validate_strategy_onboarding_request(_request())

    assert decision.accepted is True
    assert decision.normalized_promotion_state == PromotionState.SHADOW_CANDIDATE


def test_onboarding_keeps_build14_enabler_replay_only():
    request = _request(
        classification=StrategyClassification.BUILD14_ENABLER,
        lineage=_lineage(classification=StrategyClassification.BUILD14_ENABLER),
        import_request=_import_request(
            manifest=_manifest(strategy_classification=StrategyClassification.BUILD14_ENABLER)
        ),
    )

    decision = validate_strategy_onboarding_request(request)

    assert decision.accepted is True
    assert decision.normalized_promotion_state == PromotionState.REPLAY_ONLY


def test_onboarding_rejects_out_of_scope_category():
    request = _request(
        classification=StrategyClassification.OUT_OF_SCOPE_FOR_V5_3,
        lineage=_lineage(classification=StrategyClassification.OUT_OF_SCOPE_FOR_V5_3),
        import_request=_import_request(
            manifest=_manifest(strategy_classification=StrategyClassification.OUT_OF_SCOPE_FOR_V5_3)
        ),
    )

    decision = validate_strategy_onboarding_request(request)

    assert decision.accepted is False
    assert "classification is out_of_scope_for_V5_3" in decision.reasons


def test_onboarding_rejects_c_and_d_candidates_until_later_builds():
    request = _request(
        classification=StrategyClassification.C_CANDIDATE,
        lineage=_lineage(classification=StrategyClassification.C_CANDIDATE),
        import_request=_import_request(
            manifest=_manifest(strategy_classification=StrategyClassification.C_CANDIDATE)
        ),
    )

    decision = validate_strategy_onboarding_request(request)

    assert decision.accepted is False
    assert "C/D candidates stay documented only until later builds are opened" in decision.reasons


def test_onboarding_rejects_automatic_promotion_and_gate_bypass():
    decision = validate_strategy_onboarding_request(
        _request(
            automatic_promotion_requested=True,
            bypass_runtime_gates_requested=True,
        )
    )

    assert decision.accepted is False
    assert set(decision.reasons) == {
        "automatic promotion is forbidden",
        "bypassing SHADOW/MICRO_LIVE/LIVE gates is forbidden",
    }


def test_onboarding_propagates_import_gate_failures():
    decision = validate_strategy_onboarding_request(
        _request(
            import_request=_import_request(payload_bundle=None, payload_refs=()),
        )
    )

    assert decision.accepted is False
    assert "import gate: payload refs are required for governed import" in decision.reasons
    assert "import gate: review export ref must be included in payload refs" in decision.reasons
    assert "import gate: feature bridge ref must be included in payload refs" in decision.reasons


def test_onboarding_request_rejects_manifest_classification_mismatch():
    with pytest.raises(ValidationError):
        _request(
            import_request=_import_request(
                manifest=_manifest(strategy_classification=StrategyClassification.B_VARIANT)
            )
        )
