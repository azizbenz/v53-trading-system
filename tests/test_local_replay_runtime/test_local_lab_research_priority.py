from __future__ import annotations

from interface_contracts import ArtifactProofSummary
from local_replay_runtime import (
    LocalLabLossSurrogateReport,
    LocalLabLossSurrogateScopeScore,
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    build_local_lab_research_priority_report,
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


def test_build_local_lab_research_priority_report_ranks_cost_drift_scope_first():
    scope_matrix = LocalLabScopeAnalysisMatrix(
        correlation_id="corr-priority",
        export_dir="E:/lab/export_dir",
        scope_count=2,
        ready_scope_count=1,
        blocked_scope_count=1,
        release_ready_scope_count=1,
        release_blocked_scope_count=1,
        scopes=(
            LocalLabScopeAnalysisRow(
                pair="BTCUSDT",
                engine_id="engine_a",
                scope_slug="btcusdt__engine_a",
                review_output_dir="E:/lab/scopes/btcusdt__engine_a/post_trade_review",
                review_bundle_path="E:/lab/scopes/btcusdt__engine_a/post_trade_review/meta_learning_review.bundle.json",
                trade_loss_attribution_path="E:/lab/scopes/btcusdt__engine_a/post_trade_review/trade_loss_attribution.json",
                artifact_ablation_study_path="E:/lab/scopes/btcusdt__engine_a/artifact_ablation_study.json",
                artifact_proof_summary_path="E:/lab/scopes/btcusdt__engine_a/artifact_proof_summary.json",
                artifact_proof_assessment_path="E:/lab/scopes/btcusdt__engine_a/artifact_proof_assessment.json",
                calibration_methods_review_path="E:/lab/scopes/btcusdt__engine_a/local_lab_calibration_methods_review.json",
                candidate_record_count=3,
                baseline_record_count=3,
                executed_records=3,
                losing_trade_count=2,
                artifact_ablation_ready=True,
                artifact_proof_ready=False,
                artifact_proof_validation_reasons=("PROOF_WALK_FORWARD_REQUIRED",),
                calibration_methods_review_status="partial",
                calibration_methods_review_ready=False,
                release_ready=False,
                release_blocking_reasons=("WALK_FORWARD_REVIEW_REQUIRED",),
                proof_summary=_proof_summary(),
            ),
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
                calibration_methods_review_path="E:/lab/scopes/ethusdt__engine_b/local_lab_calibration_methods_review.json",
                candidate_record_count=5,
                baseline_record_count=5,
                executed_records=5,
                losing_trade_count=1,
                artifact_ablation_ready=True,
                artifact_proof_ready=True,
                artifact_proof_validation_reasons=(),
                calibration_methods_review_status="ready",
                calibration_methods_review_ready=True,
                release_ready=True,
                release_blocking_reasons=(),
                proof_summary=_proof_summary(),
            ),
        ),
    )
    reports = (
        TradeLossAttributionReport(
            correlation_id="corr-priority:btcusdt__engine_a",
            total_records=3,
            executed_records=3,
            losing_trade_count=2,
            attribution_ready=True,
            attributions=(
                TradeLossAttribution(
                    dtr_id="btc-1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state="executed",
                    attribution_status="loss",
                    primary_failure_mode="cost_drift",
                    action_scope="engine_a:BTCUSDT",
                    confidence=0.92,
                    recommended_threshold_ids=("THR-E01", "THR-E02"),
                ),
                TradeLossAttribution(
                    dtr_id="btc-2",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state="executed",
                    attribution_status="loss",
                    primary_failure_mode="edge_degraded",
                    action_scope="engine_a:BTCUSDT",
                    confidence=0.80,
                    recommended_threshold_ids=("THR-E01", "THR-E02"),
                ),
            ),
        ),
        TradeLossAttributionReport(
            correlation_id="corr-priority:ethusdt__engine_b",
            total_records=5,
            executed_records=5,
            losing_trade_count=1,
            attribution_ready=True,
            attributions=(
                TradeLossAttribution(
                    dtr_id="eth-1",
                    pair="ETHUSDT",
                    engine_id="engine_b",
                    decision_state="executed",
                    attribution_status="loss",
                    primary_failure_mode="sterilization",
                    action_scope="engine_b:ETHUSDT",
                    confidence=0.74,
                ),
            ),
        ),
    )

    report = build_local_lab_research_priority_report(
        correlation_id="corr-priority",
        export_dir="E:/lab/export_dir",
        loss_reports=reports,
        scope_matrix=scope_matrix,
    )

    assert report.status == "ready"
    assert report.priority_scope_count == 1
    assert report.highest_priority_scope_slug == "btcusdt__engine_a"
    assert report.highest_priority_score > report.scopes[1].priority_score
    assert report.recommended_threshold_ids == ("THR-E01", "THR-E02")
    assert report.scopes[0].recommended_next_action == "replay_recalibration_candidate"
    assert "COST_DRIFT_PRESENT" in report.scopes[0].reason_codes


def test_build_local_lab_research_priority_report_prioritizes_trace_capture_when_evidence_is_incomplete():
    report = build_local_lab_research_priority_report(
        correlation_id="corr-trace",
        export_dir="E:/lab/export_dir",
        loss_reports=(
            TradeLossAttributionReport(
                correlation_id="corr-trace",
                total_records=1,
                executed_records=1,
                losing_trade_count=1,
                attribution_ready=True,
                attributions=(
                    TradeLossAttribution(
                        dtr_id="trace-1",
                        pair="SOLUSDT",
                        engine_id="engine_c",
                        decision_state="executed",
                        attribution_status="loss",
                        primary_failure_mode="trace_coverage",
                        action_scope="engine_c:SOLUSDT",
                        confidence=0.82,
                    ),
                ),
            ),
        ),
        selected_pair="SOLUSDT",
        selected_engine_id="engine_c",
        artifact_proof_ready=False,
        artifact_proof_validation_reasons=("PROOF_TRACE_COVERAGE_REQUIRED",),
        release_ready_for_shadow=False,
        release_blocking_reasons=("TRACE_COVERAGE_BLOCKS_RECALIBRATION",),
    )

    assert report.status == "ready"
    assert report.scope_count == 1
    assert report.scopes[0].recommended_next_action == "improve_trace_capture"
    assert "TRACE_COVERAGE_PRESENT" in report.scopes[0].reason_codes
    assert report.scopes[0].features.proof_gap_count == 1
    assert report.scopes[0].features.release_gap_count == 1


def test_build_local_lab_research_priority_report_uses_loss_surrogate_signal_when_available():
    reports = (
        TradeLossAttributionReport(
            correlation_id="corr-surrogate:btcusdt__engine_a",
            total_records=2,
            executed_records=2,
            losing_trade_count=1,
            attribution_ready=True,
            attributions=(
                TradeLossAttribution(
                    dtr_id="btc-1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state="executed",
                    attribution_status="loss",
                    primary_failure_mode="edge_degraded",
                    action_scope="engine_a:BTCUSDT",
                    confidence=0.70,
                ),
            ),
        ),
        TradeLossAttributionReport(
            correlation_id="corr-surrogate:ethusdt__engine_b",
            total_records=2,
            executed_records=2,
            losing_trade_count=1,
            attribution_ready=True,
            attributions=(
                TradeLossAttribution(
                    dtr_id="eth-1",
                    pair="ETHUSDT",
                    engine_id="engine_b",
                    decision_state="executed",
                    attribution_status="loss",
                    primary_failure_mode="edge_degraded",
                    action_scope="engine_b:ETHUSDT",
                    confidence=0.70,
                ),
            ),
        ),
    )
    surrogate = LocalLabLossSurrogateReport(
        correlation_id="corr-surrogate",
        export_dir="E:/lab/export_dir",
        status="trained",
        ready=True,
        scope_count=2,
        scored_scope_count=2,
        executed_record_count=4,
        trained_record_count=4,
        loss_count=2,
        non_loss_count=2,
        highest_risk_scope_slug="ethusdt__engine_b",
        highest_risk_probability=0.81,
        scopes=(
            LocalLabLossSurrogateScopeScore(
                pair="BTCUSDT",
                engine_id="engine_a",
                scope_slug="btcusdt__engine_a",
                executed_record_count=2,
                loss_count=1,
                actual_loss_rate=0.5,
                mean_predicted_loss_probability=0.41,
                top_risk_dtr_id="btc-1",
                top_risk_probability=0.44,
                risk_band="low_risk",
            ),
            LocalLabLossSurrogateScopeScore(
                pair="ETHUSDT",
                engine_id="engine_b",
                scope_slug="ethusdt__engine_b",
                executed_record_count=2,
                loss_count=1,
                actual_loss_rate=0.5,
                mean_predicted_loss_probability=0.73,
                top_risk_dtr_id="eth-1",
                top_risk_probability=0.81,
                risk_band="high_risk",
            ),
        ),
    )

    report = build_local_lab_research_priority_report(
        correlation_id="corr-surrogate",
        export_dir="E:/lab/export_dir",
        loss_reports=reports,
        loss_surrogate_report=surrogate,
    )

    assert report.status == "ready"
    assert report.highest_priority_scope_slug == "ethusdt__engine_b"
    assert report.scopes[0].recommended_next_action == "replay_high_risk_scope"
    assert report.scopes[0].features.loss_surrogate_ready is True
    assert report.scopes[0].features.surrogate_top_risk_probability == 0.81
    assert "LOSS_SURROGATE_READY" in report.scopes[0].reason_codes
    assert "SURROGATE_HIGH_RISK_SCOPE" in report.scopes[0].reason_codes
