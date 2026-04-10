from __future__ import annotations

from datetime import datetime, timezone

from local_replay_runtime import (
    WalkForwardHumanReview,
    build_local_lab_ablation_study,
    build_local_lab_artifact_proof_assessment,
    summarize_walk_forward_review,
)
from meta_learning import build_trade_loss_attribution_report
from meta_minimal import build_meta_runtime_result_from_records
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _good_records():
    return (
        build_dtr(
            dtr_id="dtr-proof-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0080,
            ce_expected=0.0030,
            regime="trend",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=1.0,
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-proof-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0011,
            gross_return=0.0084,
            ce_expected=0.0033,
            regime="range",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=0.95,
            timestamp=1_700_000_060.0,
        ),
    )


def _baseline_records():
    return (
        build_dtr(
            dtr_id="dtr-proof-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0020,
            ce_expected=0.0015,
            regime="trend",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=1.0,
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-proof-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0011,
            gross_return=0.0022,
            ce_expected=0.0016,
            regime="range",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=0.95,
            timestamp=1_700_000_060.0,
        ),
    )


def _walk_forward_summary(*, approved: bool):
    review = WalkForwardHumanReview(
        correlation_id="corr-proof",
        export_dir="E:/lab/export",
        run_id="run-proof",
        review_status="approved" if approved else "pending",
        reviewed_by="operator.aziz" if approved else None,
        reviewed_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc) if approved else None,
        walk_forward_window_count=5 if approved else 0,
        temporal_split_confirmed=approved,
        no_future_data_leak_confirmed=approved,
        feature_timestamp_alignment_confirmed=approved,
        calibration_fit_window_confirmed=approved,
    )
    return summarize_walk_forward_review(review)


def test_local_lab_artifact_proof_assessment_is_conservative_without_ablation():
    records = _good_records()
    meta_result = build_meta_runtime_result_from_records(records, total_opportunities=2)
    loss_attribution = build_trade_loss_attribution_report(
        "corr-proof",
        dtr_records=records,
        diagnostics=(),
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )

    assessment = build_local_lab_artifact_proof_assessment(
        correlation_id="corr-proof",
        export_dir="E:/lab/export",
        run_id="run-proof",
        meta_result=meta_result,
        trade_loss_attribution=loss_attribution,
        walk_forward_review=_walk_forward_summary(approved=True),
    )

    assert assessment.proof_summary.anti_cowardice_pass is True
    assert assessment.proof_summary.friction_regret_pass is True
    assert assessment.proof_summary.walk_forward_pass is True
    assert assessment.proof_summary.regime_segmentation_pass is True
    assert assessment.proof_summary.operational_burden_pass is True
    assert assessment.proof_summary.capital_efficiency_pass is True
    assert assessment.ready_for_vps_import is False
    assert assessment.validation_reasons == (
        "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",
        "PROOF_ABLATION_DELTA_CE_REQUIRED",
    )
    assert "ABLATION_DELTA_NET_PNL" in assessment.pending_dimensions
    assert "ABLATION_DELTA_CE" in assessment.pending_dimensions


def test_local_lab_artifact_proof_assessment_requires_approved_walk_forward_review():
    records = _good_records()
    meta_result = build_meta_runtime_result_from_records(records, total_opportunities=2)
    loss_attribution = build_trade_loss_attribution_report(
        "corr-proof",
        dtr_records=records,
        diagnostics=(),
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )

    assessment = build_local_lab_artifact_proof_assessment(
        correlation_id="corr-proof",
        export_dir="E:/lab/export",
        run_id="run-proof",
        meta_result=meta_result,
        trade_loss_attribution=loss_attribution,
        walk_forward_review=_walk_forward_summary(approved=False),
    )

    assert assessment.proof_summary.walk_forward_pass is False
    assert "PROOF_WALK_FORWARD_REQUIRED" in assessment.validation_reasons
    assert "WALK_FORWARD_HUMAN_REVIEW" in assessment.pending_dimensions


def test_local_lab_artifact_proof_assessment_can_pass_with_real_ablation():
    records = _good_records()
    meta_result = build_meta_runtime_result_from_records(records, total_opportunities=2)
    loss_attribution = build_trade_loss_attribution_report(
        "corr-proof",
        dtr_records=records,
        diagnostics=(),
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )
    ablation_study = build_local_lab_ablation_study(
        correlation_id="corr-proof",
        candidate_export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        candidate_run_id="run-candidate",
        baseline_run_id="run-baseline",
        candidate_dataset_manifest_id="dataset-proof",
        baseline_dataset_manifest_id="dataset-proof",
        candidate_records=records,
        baseline_records=_baseline_records(),
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
    )

    assessment = build_local_lab_artifact_proof_assessment(
        correlation_id="corr-proof",
        export_dir="E:/lab/export",
        run_id="run-proof",
        meta_result=meta_result,
        trade_loss_attribution=loss_attribution,
        walk_forward_review=_walk_forward_summary(approved=True),
        ablation_study=ablation_study,
    )

    assert assessment.ready_for_vps_import is True
    assert assessment.validation_reasons == ()
    assert assessment.proof_summary.ablation_delta_net_pnl > 0.01
    assert assessment.proof_summary.ablation_delta_ce is not None
    assert assessment.proof_summary.ablation_delta_ce >= 0.0
