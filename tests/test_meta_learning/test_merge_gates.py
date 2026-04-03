"""Explicit Build-9X merge-gate coverage."""

from __future__ import annotations

from interface_contracts import (
    EngineId,
    ProfileId,
    PromotionState,
    RuntimeMode,
    StrategyClassification,
)
from local_replay_runtime import ReplayClockRef, ReplayDatasetRef
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_learning import (
    Build9XMergeGateName,
    apply_candidate_replay_results,
    apply_human_review_resolution,
    evaluate_build9x_merge_gates,
    evaluate_learning_capacity,
    run_meta_learning_review,
)
from meta_learning.enums import LearningBacklogState
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)


def _trade_input() -> object:
    from meta_learning import TradeLearningInput

    return TradeLearningInput(
        correlation_id="corr-9x-gates",
        dtr_ids=("dtr-1", "dtr-2"),
        pair="BTCUSDT",
        engine_id=EngineId.B,
        profile=ProfileId.LIGHT,
        source_runtime_mode=RuntimeMode.SHADOW,
        strategy_classification=StrategyClassification.B_VARIANT,
        source_version="5.3.0-build9x",
    )


def _reports() -> tuple[tuple[object, ...], object, object, object, object]:
    records = (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            raw_score=0.92,
            final_score=0.82,
            timestamp=1000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.SELECTED,
            raw_score=0.70,
            final_score=0.68,
            timestamp=1001.0,
        ),
    )
    dtr_summary = build_dtr_summary(records, total_opportunities=4)
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_b",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.40,
                phantom_risk_score=0.80,
                reason="spread_drift",
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_b",
                sterilization_rate=1.0,
                total_trades=1,
                sterilized_count=1,
                alert_level=CRAAlertLevel.CRITICAL,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=10,
                mean_realized_cost=0.0016,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0006,
                profitable_rate=0.4,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0005,
                sample_size=12,
                sharpe_per_trade=-0.15,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.50,
            ),
        )
    )
    return records, dtr_summary, cra_report, break_even_report, edge_report


def _replay_refs(record_count: int) -> tuple[ReplayDatasetRef, ReplayClockRef]:
    dataset_ref = ReplayDatasetRef(
        dataset_id="dataset-9x-gates",
        pair_scope=("BTCUSDT", "ETHUSDT"),
        record_count=record_count,
    )
    clock_ref = ReplayClockRef(
        clock_id="clock-9x-gates",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_100_000,
        tick_count=100,
    )
    return dataset_ref, clock_ref


def test_meta_learning_exports_explicit_merge_gates():
    import meta_learning

    assert {
        "Build9XMergeGateName",
        "Build9XMergeGateResult",
        "Build9XMergeGateReport",
        "evaluate_build9x_merge_gates",
    }.issubset(set(meta_learning.__all__))


def test_evaluate_build9x_merge_gates_passes_for_governed_bundle(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        state_dir=repo_tmp_path,
    )

    report = evaluate_build9x_merge_gates(bundle, state_dir=repo_tmp_path)

    assert bundle.merge_gate_report is not None
    assert bundle.merge_gate_report.all_passed is True
    assert bundle.review_export.merge_gate_report == bundle.merge_gate_report
    assert "## Merge Gates" in bundle.review_export.markdown_body
    assert report.all_passed is True
    assert all(gate.passed for gate in report.gates)
    assert report.gate(Build9XMergeGateName.NO_LIVE_MUTATION_PATH).passed is True
    assert report.gate(Build9XMergeGateName.END_TO_END_ID_CORRELATION).passed is True
    assert report.gate(Build9XMergeGateName.STRUCTURED_LEARNING_LOGS_PRESENT).passed is True
    assert report.gate(Build9XMergeGateName.STATISTICAL_GOVERNANCE_PRESENT).passed is True


def test_no_live_mutation_path_gate_detects_illegal_live_candidate_state():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
    )
    bad_candidate = bundle.candidates[0].model_copy(
        update={
            "promotion_state": PromotionState.MICRO_LIVE_CANDIDATE,
            "auto_promotion_enabled": True,
        }
    )
    corrupted_bundle = bundle.model_copy(
        update={"candidates": (bad_candidate, *bundle.candidates[1:])}
    )

    report = evaluate_build9x_merge_gates(corrupted_bundle)
    gate = report.gate(Build9XMergeGateName.NO_LIVE_MUTATION_PATH)

    assert gate.passed is False
    assert "candidate:corr-9x-gates:candidate:1:auto_promotion_enabled" in gate.blocking_reasons
    assert (
        "candidate:corr-9x-gates:candidate:1:promotion_state=micro_live_candidate"
        in gate.blocking_reasons
    )


def test_end_to_end_id_correlation_gate_detects_replay_reference_mismatch():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
    )
    bad_candidate = bundle.candidates[0].model_copy(
        update={"replay_bundle_reference": "wrong:bundle"}
    )
    corrupted_bundle = bundle.model_copy(
        update={"candidates": (bad_candidate, *bundle.candidates[1:])}
    )

    report = evaluate_build9x_merge_gates(corrupted_bundle)
    gate = report.gate(Build9XMergeGateName.END_TO_END_ID_CORRELATION)

    assert gate.passed is False
    assert "candidate:corr-9x-gates:candidate:1:replay_bundle_ref_mismatch" in gate.blocking_reasons


def test_backpressure_and_resource_gates_pass_when_degraded_capture_is_governed(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        capacity_snapshot=evaluate_learning_capacity(
            queue_depth=5500,
            queue_oldest_age_ms=600,
            log_loss_total=1,
            export_failures_total=1,
        ),
        state_dir=repo_tmp_path,
    )

    report = evaluate_build9x_merge_gates(bundle, state_dir=repo_tmp_path)

    assert bundle.merge_gate_report is not None
    assert bundle.merge_gate_report.all_passed is True
    assert report.all_passed is True
    assert report.gate(Build9XMergeGateName.LEARNING_BACKPRESSURE_HANDLED).passed is True
    assert report.gate(Build9XMergeGateName.RESOURCE_BUDGETS_RESPECTED).passed is True
    assert report.gate(Build9XMergeGateName.STRUCTURED_LEARNING_LOGS_PRESENT).passed is True


def test_resource_budgets_gate_detects_threshold_state_mismatch():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        capacity_snapshot=evaluate_learning_capacity(
            queue_depth=5500,
            queue_oldest_age_ms=600,
            log_loss_total=1,
        ),
    )
    corrupted_bundle = bundle.model_copy(
        update={
            "capacity_snapshot": bundle.capacity_snapshot.model_copy(
                update={"backlog_state": LearningBacklogState.NORMAL}
            )
        }
    )

    report = evaluate_build9x_merge_gates(corrupted_bundle)
    gate = report.gate(Build9XMergeGateName.RESOURCE_BUDGETS_RESPECTED)

    assert gate.passed is False
    assert "backlog_state_expected_protection_got_normal" in gate.blocking_reasons


def test_merge_gates_hold_through_governed_shadow_review_readiness(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        state_dir=repo_tmp_path,
    )
    replay_approved_bundle = apply_human_review_resolution(
        bundle,
        actor="alice.ops",
        resolution="replay_approved",
        rationale="Replay evidence is sufficient for governed replay.",
        state_dir=repo_tmp_path,
    )
    replay_passed_bundle = apply_candidate_replay_results(
        replay_approved_bundle,
        passed_candidate_ids=tuple(
            candidate.candidate_id for candidate in replay_approved_bundle.candidates
        ),
        actor="system_build9x",
        state_dir=repo_tmp_path,
    )
    shadow_ready_bundle = apply_human_review_resolution(
        replay_passed_bundle,
        actor="alice.ops",
        resolution="shadow_candidate_approved",
        rationale="Replay evidence is stable enough for governed shadow review.",
        state_dir=repo_tmp_path,
    )

    report = evaluate_build9x_merge_gates(shadow_ready_bundle, state_dir=repo_tmp_path)

    assert shadow_ready_bundle.merge_gate_report is not None
    assert shadow_ready_bundle.merge_gate_report.all_passed is True
    assert shadow_ready_bundle.review_export.merge_gate_report == shadow_ready_bundle.merge_gate_report
    assert report.all_passed is True
    assert report.gate(Build9XMergeGateName.END_TO_END_ID_CORRELATION).passed is True
    assert report.gate(Build9XMergeGateName.STATISTICAL_GOVERNANCE_PRESENT).passed is True
    assert all(
        hypothesis.governance_stage.value == "shadow_candidate"
        for hypothesis in shadow_ready_bundle.hypotheses
    )
    assert all(
        candidate.governance_stage.value == "ready_for_shadow_review"
        for candidate in shadow_ready_bundle.candidates
    )
