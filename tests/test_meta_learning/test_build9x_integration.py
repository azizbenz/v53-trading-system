"""End-to-end governed flow tests for the real Build-9X layer."""

from __future__ import annotations

from interface_contracts import EngineId, ProfileId, RuntimeMode, StrategyClassification
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_learning import (
    Build9XMergeGateName,
    DiagnosticResult,
    LearningMemoryRecord,
    LearningMemoryStore,
    TradeLearningInput,
    build_build9x_projection,
    build_breakdown_report,
    build_improvement_candidates,
    build_learning_checklist,
    build_learning_hypotheses,
    evaluate_learning_capacity,
    export_learning_review,
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


def _trade_input() -> TradeLearningInput:
    return TradeLearningInput(
        correlation_id="corr-9x",
        dtr_ids=("dtr-1", "dtr-2"),
        pair="BTCUSDT",
        engine_id=EngineId.B,
        profile=ProfileId.LIGHT,
        source_runtime_mode=RuntimeMode.SHADOW,
        strategy_classification=StrategyClassification.A_VARIANT,
        source_version="5.3.0-build10",
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


def _diagnostics() -> tuple[DiagnosticResult, ...]:
    return (
        DiagnosticResult(
            diagnostic_id="diag-1",
            correlation_id="corr-9x",
            category="sterilization",
            summary="CRA sterilization elevated at 50%",
            structured_log_key="build9x.sterilization",
        ),
        DiagnosticResult(
            diagnostic_id="diag-2",
            correlation_id="corr-9x",
            category="near_miss",
            summary="Near miss on BTCUSDT: final_score=0.82, state=hard_blocked",
            structured_log_key="build9x.near_miss",
        ),
    )


def test_build9x_full_review_flow_stays_governed():
    diagnostics = _diagnostics()
    mistake_classes = ("economic_sterilization", "near_miss")
    report = build_breakdown_report("corr-9x", diagnostics, mistake_classes)
    checklist = build_learning_checklist("corr-9x", diagnostics, mistake_classes)
    hypotheses = build_learning_hypotheses("corr-9x", diagnostics)
    candidates = build_improvement_candidates(
        "corr-9x",
        StrategyClassification.A_VARIANT,
        hypotheses,
    )
    review_export = export_learning_review("corr-9x", report, checklist, candidates)

    store = LearningMemoryStore()
    record = LearningMemoryRecord(
        correlation_id="corr-9x",
        diagnostics_count=len(diagnostics),
        hypothesis_count=len(hypotheses),
        candidate_count=len(candidates),
        summary=report.summary,
    )
    store = store.append(record)

    assert store.latest() == record
    assert "## Summary" in review_export.markdown_body
    assert "## Hypotheses" in review_export.markdown_body
    assert "## Candidates" in review_export.markdown_body
    assert "## Review Decisions" in review_export.markdown_body
    assert "## Archive Eligibility" in review_export.markdown_body
    assert "## Lifecycle Transitions" in review_export.markdown_body
    assert "## Merge Gates" in review_export.markdown_body
    assert "## Replay Bundles" in review_export.markdown_body
    assert all(candidate.auto_promotion_enabled is False for candidate in review_export.candidates)
    assert all(candidate.promotion_state.value == "replay_only" for candidate in review_export.candidates)


def test_run_meta_learning_review_returns_governed_bundle():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()

    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
    )

    categories = {diagnostic.category for diagnostic in bundle.diagnostics}
    assert {"trace_coverage", "sterilization", "cost_drift", "edge_degraded", "near_miss"} <= categories
    assert bundle.memory_record.candidate_count == len(bundle.candidates)
    assert bundle.review_export.correlation_id == bundle.correlation_id
    assert bundle.review_decisions
    assert bundle.review_decisions[0].actor == "system_build9x"
    assert bundle.review_decisions[0].review_state.value == "pending"
    assert bundle.archive_eligibility
    assert any(entry.entity_kind == "diagnostic" for entry in bundle.archive_eligibility)
    assert all(candidate.promotion_state.value == "replay_only" for candidate in bundle.candidates)
    assert len(bundle.replay_bundles) == len(bundle.candidates)
    assert bundle.review_export.replay_bundles == bundle.replay_bundles
    assert bundle.review_export.review_decisions == bundle.review_decisions
    assert bundle.review_export.archive_eligibility == bundle.archive_eligibility
    assert bundle.merge_gate_report is not None
    assert bundle.merge_gate_report.all_passed is True
    assert bundle.merge_gate_report.gate(Build9XMergeGateName.NO_LIVE_MUTATION_PATH).passed is True
    assert bundle.review_export.merge_gate_report == bundle.merge_gate_report
    assert "## Merge Gates" in bundle.review_export.markdown_body
    assert all(hypothesis.governance_stage.value == "under_review" for hypothesis in bundle.hypotheses)
    assert all(candidate.governance_stage.value in {"tests_pending", "ready_for_replay"} for candidate in bundle.candidates)
    assert bundle.lifecycle_transitions
    assert any(
        transition.from_state == "draft" and transition.to_state == "under_review"
        for transition in bundle.lifecycle_transitions
    )
    assert any(
        transition.from_state == "prepared" and transition.to_state == "tests_pending"
        for transition in bundle.lifecycle_transitions
    )


def test_run_meta_learning_review_blocks_handoff_when_capacity_is_incomplete():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    capacity_snapshot = evaluate_learning_capacity(
        queue_depth=5400,
        queue_oldest_age_ms=800,
        log_loss_total=1,
        export_failures_total=1,
    )

    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        capacity_snapshot=capacity_snapshot,
    )

    projection = build_build9x_projection(bundle)

    assert bundle.replay_bundles == ()
    assert bundle.review_export.review_blocked_due_to_incomplete_data is True
    assert bundle.review_export.capture_mode.value == "capture_minimale"
    assert "## Capacity Guard" in bundle.review_export.markdown_body
    assert bundle.merge_gate_report is not None
    assert bundle.merge_gate_report.all_passed is True
    assert "## Merge Gates" in bundle.review_export.markdown_body
    assert bundle.review_decisions[0].review_state.value == "needs_revision"
    assert bundle.review_decisions[0].final_verdict_recorded is False
    assert all(entry.eligible is False for entry in bundle.archive_eligibility)
    assert "## Lifecycle Transitions" in bundle.review_export.markdown_body
    assert all(hypothesis.governance_stage.value == "under_review" for hypothesis in bundle.hypotheses)
    assert all(candidate.governance_stage.value == "prepared" for candidate in bundle.candidates)
    assert all(candidate.replay_bundle_reference == "" for candidate in bundle.candidates)
    assert bundle.memory_record.verdict == "incomplete_capture_blocked"
    assert bundle.checklist.ready_for_local_replay is False
    assert projection.status == "critical"
    assert projection.review_export_ready is False
    assert projection.learning_capture_mode == "capture_minimale"
    assert projection.learning_backpressure_active is True
    assert projection.enrichment_hypothesis_count > 0
    assert projection.latest_enrichment_target != ""
    assert projection.expected_replay_evidence_count > 0
    assert projection.expected_shadow_evidence_count > 0
    assert any(
        transition.from_state == "draft" and transition.to_state == "under_review"
        for transition in bundle.lifecycle_transitions
    )
    assert any(
        transition.from_state == "open" and transition.to_state == "escalated"
        for transition in bundle.lifecycle_transitions
    )


def test_breakdown_report_fallback_and_empty_candidate_export():
    report = build_breakdown_report("corr-empty", (), ())
    checklist = build_learning_checklist(
        "corr-empty",
        (
            DiagnosticResult(
                diagnostic_id="diag-ok",
                correlation_id="corr-empty",
                category="no_issue",
                summary="No material post-trade issue detected",
                structured_log_key="build9x.no_issue",
            ),
        ),
        (),
    )
    review_export = export_learning_review("corr-empty", report, checklist, ())

    assert report.summary == "No diagnostic summary available"
    assert report.near_miss_pairs == ()
    assert "# Build-9X Review - corr-empty" in review_export.markdown_body
    assert "## Candidates" in review_export.markdown_body
    assert "## Capacity Guard" in review_export.markdown_body
    assert "## Review Decisions" in review_export.markdown_body
    assert "## Archive Eligibility" in review_export.markdown_body
    assert "## Lifecycle Transitions" in review_export.markdown_body
    assert "## Merge Gates" in review_export.markdown_body
    assert "- none" in review_export.markdown_body


def test_no_issue_review_bundle_stays_empty_and_non_promotable():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    clean_bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary.model_copy(update={"dtr_coverage": 1.0}),
        cra_report=cra_report.model_copy(update={"sterilization_rate": 0.0, "alerts": ()}),
        break_even_report=break_even_report.model_copy(update={"has_cost_drift_alert": False, "cost_drift_alert_scopes": ()}),
        edge_report=edge_report.model_copy(update={"degraded_count": 0, "drift_scopes": ()}),
        near_miss_threshold=0.95,
    )

    assert tuple(d.category for d in clean_bundle.diagnostics) == ("no_issue",)
    assert clean_bundle.hypotheses == ()
    assert clean_bundle.candidates == ()
    assert clean_bundle.checklist.ready_for_local_replay is False
    assert "- none" in clean_bundle.review_export.markdown_body


def test_memory_store_keeps_append_order_even_with_same_correlation_id():
    first = LearningMemoryRecord(
        correlation_id="corr-same",
        diagnostics_count=1,
        hypothesis_count=0,
        candidate_count=0,
        summary="first",
    )
    second = LearningMemoryRecord(
        correlation_id="corr-same",
        diagnostics_count=2,
        hypothesis_count=1,
        candidate_count=1,
        summary="second",
    )

    store = LearningMemoryStore().append(first).append(second)

    assert store.records == (first, second)
    assert store.latest() == second
