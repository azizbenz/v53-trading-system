from __future__ import annotations

from local_replay_runtime import (
    LocalLabScopeAnalysisRow,
    build_local_lab_artifact_release_candidate,
    build_local_lab_scope_matrix,
    build_local_lab_scope_slug,
)
from interface_contracts import ArtifactProofSummary


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


def test_local_lab_artifact_release_candidate_blocks_without_ready_proof():
    candidate = build_local_lab_artifact_release_candidate(
        correlation_id="corr-release",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-release",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=False,
        artifact_proof_validation_reasons=("PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",),
    )

    assert candidate.ready_for_shadow_import is False
    assert candidate.release_status == "local_only"
    assert candidate.artifact_proof_ready is False
    assert candidate.recalibration_candidate_ready is False
    assert candidate.blocking_reasons == ("PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",)


def test_local_lab_artifact_release_candidate_projects_scope_matrix():
    scope_matrix = build_local_lab_scope_matrix(
        correlation_id="corr-release",
        export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        scopes=(
            LocalLabScopeAnalysisRow(
                pair="BTCUSDT",
                engine_id="engine_a",
                scope_slug=build_local_lab_scope_slug("BTCUSDT", "engine_a"),
                review_output_dir="E:/lab/scopes/btcusdt__engine_a/post_trade_review",
                review_bundle_path="E:/lab/scopes/btcusdt__engine_a/post_trade_review/meta_learning_review.bundle.json",
                trade_loss_attribution_path="E:/lab/scopes/btcusdt__engine_a/post_trade_review/trade_loss_attribution.json",
                artifact_ablation_study_path="E:/lab/scopes/btcusdt__engine_a/artifact_ablation_study.json",
                artifact_proof_summary_path="E:/lab/scopes/btcusdt__engine_a/artifact_proof_summary.json",
                artifact_proof_assessment_path="E:/lab/scopes/btcusdt__engine_a/artifact_proof_assessment.json",
                artifact_ablation_ready=True,
                artifact_proof_ready=True,
                proof_summary=_proof_summary(),
            ),
        ),
    )

    candidate = build_local_lab_artifact_release_candidate(
        correlation_id="corr-release",
        export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        run_id="run-release",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        artifact_proof_summary_path="E:/lab/artifact_proof_summary.json",
        artifact_proof_assessment_path="E:/lab/artifact_proof_assessment.json",
        scope_matrix_path="E:/lab/local_lab_scope_matrix.json",
        scope_matrix=scope_matrix,
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=True,
        artifact_proof_validation_reasons=(),
    )

    assert candidate.ready_for_shadow_import is True
    assert candidate.release_status == "shadow_candidate"
    assert candidate.artifact_proof_ready is True
    assert candidate.recalibration_candidate_ready is False
    assert candidate.scope_count == 1
    assert candidate.ready_scope_count == 1
    assert candidate.blocked_scope_count == 0
    assert candidate.release_scopes[0].release_ready is True
    assert candidate.release_scopes[0].review_bundle_path.endswith("meta_learning_review.bundle.json")
    assert candidate.release_scopes[0].trade_loss_attribution_path.endswith(
        "trade_loss_attribution.json"
    )
    assert candidate.release_scopes[0].artifact_proof_summary_path.endswith(
        "artifact_proof_summary.json"
    )
    assert candidate.release_scopes[0].artifact_proof_assessment_path.endswith(
        "artifact_proof_assessment.json"
    )


def test_local_lab_artifact_release_candidate_blocks_without_recalibration_plan():
    candidate = build_local_lab_artifact_release_candidate(
        correlation_id="corr-release",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-release",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path=None,
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=True,
        artifact_proof_validation_reasons=(),
    )

    assert candidate.ready_for_shadow_import is False
    assert candidate.release_status == "local_only"
    assert candidate.blocking_reasons == ("RECALIBRATION_PLAN_REQUIRED",)


def test_local_lab_artifact_release_candidate_blocks_on_non_benign_recalibration_reason():
    candidate = build_local_lab_artifact_release_candidate(
        correlation_id="corr-release",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-release",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("TRACE_COVERAGE_BLOCKS_RECALIBRATION",),
        artifact_proof_ready=True,
        artifact_proof_validation_reasons=(),
    )

    assert candidate.ready_for_shadow_import is False
    assert candidate.release_status == "local_only"
    assert candidate.blocking_reasons == ("TRACE_COVERAGE_BLOCKS_RECALIBRATION",)
