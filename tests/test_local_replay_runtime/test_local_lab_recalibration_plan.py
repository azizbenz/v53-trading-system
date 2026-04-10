from __future__ import annotations

from interface_contracts import ArtifactProofSummary
from local_replay_runtime import (
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    build_local_lab_recalibration_plan,
)
from meta_learning.contracts import TradeLossAttribution, TradeLossAttributionReport


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


def test_build_local_lab_recalibration_plan_promotes_edge_gate_threshold_recalibration():
    report = TradeLossAttributionReport(
        correlation_id="corr-recalibration",
        total_records=3,
        executed_records=3,
        losing_trade_count=2,
        attribution_ready=True,
        attributions=(
            TradeLossAttribution(
                dtr_id="dtr-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state="executed",
                attribution_status="loss",
                primary_failure_mode="cost_drift",
                action_scope="engine_a:BTCUSDT",
                confidence=0.9,
                recommended_threshold_ids=("THR-E01", "THR-E02"),
            ),
            TradeLossAttribution(
                dtr_id="dtr-2",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state="executed",
                attribution_status="loss",
                primary_failure_mode="edge_degraded",
                action_scope="engine_a:BTCUSDT",
                confidence=0.8,
                recommended_threshold_ids=("THR-E01", "THR-E02"),
            ),
        ),
    )

    plan = build_local_lab_recalibration_plan(
        correlation_id="corr-recalibration",
        export_dir="E:/lab/export_dir",
        loss_reports=(report,),
    )

    assert plan.calibration_candidate_ready is True
    assert plan.blocking_reasons == ()
    assert plan.recommended_threshold_ids == ("THR-E01", "THR-E02")
    assert plan.action_count == 1
    assert plan.actions[0].action_type == "recalibrate_edge_gate"
    assert plan.actions[0].action_scope == "engine_a:BTCUSDT"
    assert plan.actions[0].blocking_reasons == ()
    assert plan.dominant_failure_modes[0].failure_mode == "cost_drift"
    assert plan.dominant_failure_modes[1].failure_mode == "edge_degraded"


def test_build_local_lab_recalibration_plan_blocks_when_trace_coverage_or_scope_matrix_is_not_ready():
    report = TradeLossAttributionReport(
        correlation_id="corr-trace",
        total_records=1,
        executed_records=1,
        losing_trade_count=1,
        attribution_ready=True,
        attributions=(
            TradeLossAttribution(
                dtr_id="dtr-trace",
                pair="ETHUSDT",
                engine_id="engine_b",
                decision_state="executed",
                attribution_status="loss",
                primary_failure_mode="trace_coverage",
                action_scope="engine_b:ETHUSDT",
                confidence=0.82,
            ),
        ),
    )
    scope_matrix = LocalLabScopeAnalysisMatrix(
        correlation_id="corr-trace",
        export_dir="E:/lab/export_dir",
        baseline_export_dir="E:/lab/baseline",
        scope_count=1,
        ready_scope_count=0,
        blocked_scope_count=1,
        scopes=(
            LocalLabScopeAnalysisRow(
                pair="ETHUSDT",
                engine_id="engine_b",
                scope_slug="ethusdt__engine_b",
                review_output_dir="E:/lab/scopes/ethusdt__engine_b/post_trade_review",
                review_bundle_path="E:/lab/scopes/ethusdt__engine_b/post_trade_review/meta_learning_review.bundle.json",
                trade_loss_attribution_path="E:/lab/scopes/ethusdt__engine_b/post_trade_review/trade_loss_attribution.json",
                artifact_ablation_study_path="E:/lab/scopes/ethusdt__engine_b/artifact_ablation_study.json",
                artifact_proof_summary_path="E:/lab/scopes/ethusdt__engine_b/artifact_proof_summary.json",
                artifact_proof_assessment_path="E:/lab/scopes/ethusdt__engine_b/artifact_proof_assessment.json",
                candidate_record_count=1,
                baseline_record_count=1,
                executed_records=1,
                losing_trade_count=1,
                artifact_ablation_ready=False,
                artifact_proof_ready=False,
                artifact_proof_validation_reasons=("PROOF_TRACE_COVERAGE_REQUIRED",),
                proof_summary=_proof_summary(),
            ),
        ),
    )

    plan = build_local_lab_recalibration_plan(
        correlation_id="corr-trace",
        export_dir="E:/lab/export_dir",
        loss_reports=(report,),
        scope_matrix=scope_matrix,
    )

    assert plan.calibration_candidate_ready is False
    assert plan.blocking_reasons == (
        "TRACE_COVERAGE_BLOCKS_RECALIBRATION",
        "SCOPE_MATRIX_NOT_FULLY_READY",
        "NO_THRESHOLD_RECOMMENDATION_FROM_LOSS_ATTRIBUTION",
    )
    assert plan.action_count == 1
    assert plan.actions[0].action_type == "improve_trace_capture"
    assert plan.actions[0].blocking_reasons == ("TRACE_COVERAGE_BLOCKS_RECALIBRATION",)
