"""Facade and review-queue tests for Build-9X."""

from __future__ import annotations

from interface_contracts import EngineId, ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import ReplayClockRef, ReplayDatasetRef
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_learning import (
    DiagnosticResult,
    DiagnosticSeverity,
    HypothesisGovernanceStage,
    LearningHypothesis,
    MetaLearningFacade,
    MetaLearningFacadeProtocol,
    TradeLearningInput,
    build_review_queue,
    evaluate_learning_capacity,
    run_meta_learning_review,
)
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


def _trade_input(correlation_id: str = "corr-9x-facade") -> TradeLearningInput:
    return TradeLearningInput(
        correlation_id=correlation_id,
        dtr_ids=("dtr-1", "dtr-2"),
        pair="BTCUSDT",
        engine_id=EngineId.B,
        profile=ProfileId.LIGHT,
        source_runtime_mode=RuntimeMode.SHADOW,
        strategy_classification=StrategyClassification.B_VARIANT,
        source_version="5.3.0-build9x",
    )


def _reports():
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
    return (
        ReplayDatasetRef(
            dataset_id="dataset-build9x-facade",
            pair_scope=("BTCUSDT", "ETHUSDT"),
            record_count=record_count,
        ),
        ReplayClockRef(
            clock_id="clock-build9x-facade",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_100_000,
            tick_count=100,
        ),
    )


def test_build_review_queue_prioritizes_critical_under_review_hypotheses():
    diagnostics = (
        DiagnosticResult(
            diagnostic_id="diag-critical",
            correlation_id="corr-queue",
            category="sterilization",
            summary="Critical degradation",
            severity=DiagnosticSeverity.CRITICAL,
            structured_log_key="build9x.critical",
        ),
        DiagnosticResult(
            diagnostic_id="diag-normal",
            correlation_id="corr-queue",
            category="near_miss",
            summary="Normal review item",
            severity=DiagnosticSeverity.WARNING,
            structured_log_key="build9x.normal",
        ),
    )
    hypotheses = (
        LearningHypothesis(
            hypothesis_id="hyp-normal",
            correlation_id="corr-queue",
            category="near_miss",
            title="Normal queue item",
            rationale="Review required",
            diagnostic_ids=("diag-normal",),
            target_module="meta_learning",
            target_parameter_family="near_miss",
            expected_effect="Validate queue ordering",
            risk_of_regression="medium",
            required_replay_scope="near_miss:local_replay",
            segmentation_used=("near_miss",),
            comparison_metrics=("ce_net",),
            rejection_criteria=("economic regression",),
            governance_stage=HypothesisGovernanceStage.UNDER_REVIEW,
        ),
        LearningHypothesis(
            hypothesis_id="hyp-critical",
            correlation_id="corr-queue",
            category="sterilization",
            title="Critical queue item",
            rationale="Must be reviewed first",
            diagnostic_ids=("diag-critical",),
            target_module="meta_learning",
            target_parameter_family="sterilization",
            expected_effect="Validate critical prioritization",
            risk_of_regression="high",
            required_replay_scope="sterilization:local_replay",
            segmentation_used=("sterilization",),
            comparison_metrics=("ce_net",),
            rejection_criteria=("economic regression",),
            governance_stage=HypothesisGovernanceStage.UNDER_REVIEW,
        ),
        LearningHypothesis(
            hypothesis_id="hyp-closed",
            correlation_id="corr-queue",
            category="sterilization",
            title="Closed item",
            rationale="Should not return to queue",
            diagnostic_ids=("diag-critical",),
            target_module="meta_learning",
            target_parameter_family="sterilization",
            expected_effect="Stay excluded",
            risk_of_regression="high",
            required_replay_scope="sterilization:local_replay",
            segmentation_used=("sterilization",),
            comparison_metrics=("ce_net",),
            rejection_criteria=("economic regression",),
            sample_size=2,
            governance_stage=HypothesisGovernanceStage.REPLAY_APPROVED,
        ),
    )

    queue = build_review_queue(hypotheses, diagnostics)

    assert [entry.hypothesis_id for entry in queue] == ["hyp-critical", "hyp-normal"]
    assert queue[0].priority == "critical"
    assert queue[1].priority == "normal"


def test_meta_learning_facade_can_query_bundle_and_mark_review_decision():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    trade_input = _trade_input()
    bundle = run_meta_learning_review(
        trade_input,
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
    )
    facade = MetaLearningFacade(bundles=(bundle,))

    assert isinstance(facade, MetaLearningFacadeProtocol)
    assert facade.ingest_learning_input(trade_input) == trade_input.correlation_id
    assert facade.create_diagnostic(bundle.correlation_id).correlation_id == bundle.correlation_id
    assert facade.get_review_queue()

    first_diagnostic = bundle.diagnostics[0]
    first_hypothesis = facade.register_hypothesis(first_diagnostic.diagnostic_id)
    assert first_hypothesis is not None
    first_candidate = facade.prepare_candidate(first_hypothesis.hypothesis_id)
    replay_bundle = facade.export_replay_bundle(first_candidate.candidate_id)
    assert replay_bundle.candidate_id == first_candidate.candidate_id

    decision_id = facade.mark_review_decision(
        bundle.review_export.export_ref,
        "replay_approved",
        "alice.ops",
        "Governed replay approval granted.",
    )

    assert decision_id.endswith("human_review:2")
    assert facade.get_review_queue() == []
    assert all(
        hypothesis.governance_stage.value == "replay_approved"
        for hypothesis in facade.list_hypotheses()
    )


def test_meta_learning_facade_can_read_history_and_counters_from_persisted_state(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    trade_input = _trade_input("corr-9x-history")
    capacity_snapshot = evaluate_learning_capacity(
        queue_depth=5400,
        queue_oldest_age_ms=800,
        log_loss_total=1,
    )
    bundle = run_meta_learning_review(
        trade_input,
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        capacity_snapshot=capacity_snapshot,
        state_dir=repo_tmp_path,
    )
    facade = MetaLearningFacade(state_dir=repo_tmp_path)

    history = facade.get_learning_history(bundle.diagnostics[0].diagnostic_id)
    counters = facade.get_learning_counters(bundle.correlation_id)
    queue = facade.get_review_queue()

    assert history
    assert any("diagnostic:" in record.summary for record in history)
    assert counters is not None
    assert counters.capture_mode.value == "capture_minimale"
    assert queue
    assert all(entry.governance_stage.value == "under_review" for entry in queue)
