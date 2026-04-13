from __future__ import annotations

from datetime import date

from interface_contracts import ArtifactClass, ArtifactProofSummary
from local_replay_runtime import build_local_lab_artifact_release_candidate
from backtest_artifact_import.local_lab_upload_bridge_candidate import (
    build_local_lab_artifact_upload_dry_run_bridge,
)


def _proof_summary() -> ArtifactProofSummary:
    return ArtifactProofSummary(
        anti_cowardice_pass=True,
        friction_regret_pass=True,
        walk_forward_pass=True,
        regime_segmentation_pass=True,
        operational_burden_pass=True,
        capital_efficiency_pass=True,
        ablation_delta_net_pnl=0.02,
        ablation_delta_ce=0.01,
        friction_regret_value=0.01,
        block_rate_delta=0.0,
    )


def _release_candidate(*, ready_for_shadow_import: bool):
    return build_local_lab_artifact_release_candidate(
        correlation_id="corr-bridge",
        export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        run_id="run-bridge",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=ready_for_shadow_import,
        artifact_proof_validation_reasons=(
            () if ready_for_shadow_import else ("PROOF_WALK_FORWARD_REQUIRED",)
        ),
        local_lab_calibration_methods_review_path="E:/lab/local_lab_calibration_methods_review.json",
        calibration_methods_review_status="ready" if ready_for_shadow_import else "partial",
        calibration_methods_review_ready=ready_for_shadow_import,
        calibration_methods_dsr_pass=True if ready_for_shadow_import else None,
        calibration_methods_walk_forward_plan_ready=ready_for_shadow_import,
    )


def test_artifact_upload_bridge_candidate_blocks_without_ready_release_candidate():
    bridge, upload_context = build_local_lab_artifact_upload_dry_run_bridge(
        release_candidate=_release_candidate(ready_for_shadow_import=False),
        proof_summary=_proof_summary(),
        governance_reference_date=date(2026, 4, 10),
        training_end=date(2026, 4, 9),
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_a:edge_gate",
        lifecycle_ttl_days=30,
        rule_half_life_days=7,
        drift_score_threshold=0.85,
        uploaded_by="operator.aziz",
        source_artifact_summary_ref="E:/lab/artifact_source_summary.json",
        release_gate_summary_ref="E:/lab/artifact_release_gate_summary.json",
    )

    assert upload_context is None
    assert bridge.bridge_status == "blocked_release_candidate"
    assert bridge.ready_for_shadow_import_dry_run is False
    assert bridge.release_gate_status == "proof_gate_blocked"
    assert bridge.release_gate_reasons == ("PROOF_WALK_FORWARD_REQUIRED", "RECALIBRATION_NOT_REQUIRED")
    assert bridge.release_calibration_methods_review_status == "partial"
    assert bridge.release_calibration_methods_review_ready is False
    assert bridge.release_calibration_methods_dsr_pass is None
    assert bridge.release_calibration_methods_walk_forward_plan_ready is False
    assert bridge.release_calibration_methods_review_ref.endswith(
        "local_lab_calibration_methods_review.json"
    )
    assert bridge.blocking_reasons == ("PROOF_WALK_FORWARD_REQUIRED",)


def test_artifact_upload_bridge_candidate_requires_explicit_governance_inputs():
    bridge, upload_context = build_local_lab_artifact_upload_dry_run_bridge(
        release_candidate=_release_candidate(ready_for_shadow_import=True),
        proof_summary=None,
        governance_reference_date=None,
        training_end=None,
        artifact_class=None,
        artifact_scope="",
        lifecycle_ttl_days=None,
        rule_half_life_days=None,
        drift_score_threshold=None,
        uploaded_by="operator.aziz",
    )

    assert upload_context is None
    assert bridge.bridge_status == "blocked_missing_governance_inputs"
    assert bridge.ready_for_shadow_import_dry_run is False
    assert bridge.release_calibration_methods_review_status == "ready"
    assert bridge.release_calibration_methods_review_ready is True
    assert bridge.release_calibration_methods_dsr_pass is True
    assert bridge.release_calibration_methods_walk_forward_plan_ready is True
    assert set(bridge.blocking_reasons) == {
        "PROOF_SUMMARY_REQUIRED_FOR_DRY_RUN_BRIDGE",
        "GOVERNANCE_REFERENCE_DATE_REQUIRED",
        "TRAINING_END_REQUIRED",
        "ARTIFACT_CLASS_REQUIRED",
        "ARTIFACT_SCOPE_REQUIRED",
        "LIFECYCLE_TTL_DAYS_REQUIRED",
        "RULE_HALF_LIFE_DAYS_REQUIRED",
        "DRIFT_SCORE_THRESHOLD_REQUIRED",
        "SOURCE_ARTIFACT_SUMMARY_REQUIRED",
        "RELEASE_GATE_SUMMARY_REQUIRED",
    }


def test_artifact_upload_bridge_candidate_blocks_when_source_artifact_is_unreadable():
    bridge, upload_context = build_local_lab_artifact_upload_dry_run_bridge(
        release_candidate=_release_candidate(ready_for_shadow_import=True),
        proof_summary=_proof_summary(),
        governance_reference_date=date(2026, 4, 10),
        training_end=date(2026, 4, 9),
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_a:edge_gate",
        lifecycle_ttl_days=30,
        rule_half_life_days=7,
        drift_score_threshold=0.85,
        uploaded_by="operator.aziz",
        source_artifact_summary_ref="E:/lab/artifact_source_summary.json",
        release_gate_summary_ref="E:/lab/artifact_release_gate_summary.json",
    )

    assert upload_context is None
    assert bridge.bridge_status == "blocked_source_artifact"
    assert bridge.release_calibration_methods_review_status == "ready"
    assert bridge.release_calibration_methods_review_ready is True
    assert bridge.release_calibration_methods_dsr_pass is True
    assert bridge.release_calibration_methods_walk_forward_plan_ready is True
    assert bridge.blocking_reasons == ("SOURCE_ARTIFACT_UNREADABLE",)
