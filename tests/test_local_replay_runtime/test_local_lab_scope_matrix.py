from __future__ import annotations

from local_replay_runtime import (
    LocalLabScopeAnalysisRow,
    build_local_lab_scope_matrix,
    build_local_lab_scope_slug,
    discover_local_lab_scope_keys,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from interface_contracts import ArtifactProofSummary


def _records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
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


def test_discover_local_lab_scope_keys_enumerates_pair_engine_grid():
    scopes = discover_local_lab_scope_keys(_records())

    assert [(scope.pair, scope.engine_id) for scope in scopes] == [
        ("BTCUSDT", "engine_a"),
        ("ETHUSDT", "engine_b"),
    ]
    assert scopes[0].scope_slug == build_local_lab_scope_slug("BTCUSDT", "engine_a")


def test_build_local_lab_scope_matrix_counts_ready_vs_blocked():
    matrix = build_local_lab_scope_matrix(
        correlation_id="corr-scope",
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
                calibration_methods_review_path="E:/lab/scopes/btcusdt__engine_a/local_lab_calibration_methods_review.json",
                candidate_record_count=2,
                baseline_record_count=2,
                executed_records=2,
                losing_trade_count=0,
                artifact_ablation_ready=True,
                artifact_proof_ready=True,
                calibration_methods_review_status="ready",
                calibration_methods_review_ready=True,
                release_ready=True,
                proof_summary=_proof_summary(),
            ),
            LocalLabScopeAnalysisRow(
                pair="ETHUSDT",
                engine_id="engine_b",
                scope_slug=build_local_lab_scope_slug("ETHUSDT", "engine_b"),
                review_output_dir="E:/lab/scopes/ethusdt__engine_b/post_trade_review",
                review_bundle_path="E:/lab/scopes/ethusdt__engine_b/post_trade_review/meta_learning_review.bundle.json",
                trade_loss_attribution_path="E:/lab/scopes/ethusdt__engine_b/post_trade_review/trade_loss_attribution.json",
                artifact_ablation_study_path="E:/lab/scopes/ethusdt__engine_b/artifact_ablation_study.json",
                artifact_proof_summary_path="E:/lab/scopes/ethusdt__engine_b/artifact_proof_summary.json",
                artifact_proof_assessment_path="E:/lab/scopes/ethusdt__engine_b/artifact_proof_assessment.json",
                calibration_methods_review_path="E:/lab/scopes/ethusdt__engine_b/local_lab_calibration_methods_review.json",
                candidate_record_count=2,
                baseline_record_count=2,
                executed_records=2,
                losing_trade_count=1,
                artifact_ablation_ready=False,
                artifact_proof_ready=False,
                artifact_proof_validation_reasons=("PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",),
                calibration_methods_review_status="partial",
                calibration_methods_review_ready=False,
                release_ready=False,
                release_blocking_reasons=("PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",),
                proof_summary=_proof_summary(),
            ),
        ),
    )

    assert matrix.scope_count == 2
    assert matrix.ready_scope_count == 1
    assert matrix.blocked_scope_count == 1
    assert matrix.release_ready_scope_count == 1
    assert matrix.release_blocked_scope_count == 1
