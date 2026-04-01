"""Post-review resolution tests for Build-9X governed lifecycle handling."""

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
    AppendOnlyMetaLearningStore,
    TradeLearningInput,
    apply_candidate_replay_results,
    apply_human_review_resolution,
    evaluate_learning_capacity,
    run_meta_learning_review,
)
from meta_learning.persistence_store import _EVENT_FILE
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


def _trade_input(correlation_id: str = "corr-9x-resolution") -> TradeLearningInput:
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
            dataset_id="dataset-build9x",
            pair_scope=("BTCUSDT", "ETHUSDT"),
            record_count=record_count,
        ),
        ReplayClockRef(
            clock_id="clock-build9x",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_100_000,
            tick_count=100,
        ),
    )


def test_apply_candidate_replay_results_marks_candidates_ready_for_shadow_review():
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
    )

    ready_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in bundle.candidates
        if candidate.governance_stage.value == "ready_for_replay"
    )
    replay_approved_bundle = apply_human_review_resolution(
        bundle,
        actor="alice.ops",
        resolution="replay_approved",
        rationale="Human review accepted the governed replay candidates.",
    )

    updated_bundle = apply_candidate_replay_results(
        replay_approved_bundle,
        passed_candidate_ids=ready_candidate_ids,
    )

    assert ready_candidate_ids
    assert all(
        hypothesis.governance_stage.value == "replay_approved"
        for hypothesis in replay_approved_bundle.hypotheses
    )
    assert all(
        candidate.governance_stage.value == "ready_for_shadow_review"
        for candidate in updated_bundle.candidates
        if candidate.candidate_id in ready_candidate_ids
    )
    assert all(
        candidate.promotion_state.value == "shadow_candidate"
        for candidate in updated_bundle.candidates
        if candidate.candidate_id in ready_candidate_ids
    )
    assert any(
        transition.from_state == "replay_running" and transition.to_state == "replay_passed"
        for transition in updated_bundle.lifecycle_transitions
    )
    assert any(
        transition.from_state == "replay_passed" and transition.to_state == "ready_for_shadow_review"
        for transition in updated_bundle.lifecycle_transitions
    )
    assert all(entry.eligible is False for entry in updated_bundle.archive_eligibility)


def test_apply_human_review_resolution_can_approve_shadow_then_deploy_and_archive():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input("corr-9x-deploy"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
    )
    ready_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in bundle.candidates
        if candidate.governance_stage.value == "ready_for_replay"
    )
    replay_approved_bundle = apply_human_review_resolution(
        bundle,
        actor="alice.ops",
        resolution="replay_approved",
        rationale="Human review accepted the replay package.",
    )
    replay_ready_bundle = apply_candidate_replay_results(
        replay_approved_bundle,
        passed_candidate_ids=ready_candidate_ids,
    )

    assert ready_candidate_ids
    shadow_bundle = apply_human_review_resolution(
        replay_ready_bundle,
        actor="alice.ops",
        resolution="shadow_candidate_approved",
        rationale="Replay evidence is stable enough for governed shadow review.",
    )
    deployed_bundle = apply_human_review_resolution(
        shadow_bundle,
        actor="alice.ops",
        resolution="deployed_versioned",
        rationale="Shadow review stayed healthy and versioned deployment is approved.",
    )

    assert shadow_bundle.review_decisions[-1].actor == "alice.ops"
    assert shadow_bundle.review_decisions[-1].final_verdict_recorded is False
    assert all(hypothesis.governance_stage.value == "shadow_candidate" for hypothesis in shadow_bundle.hypotheses)
    assert all(entry.eligible is False for entry in shadow_bundle.archive_eligibility)

    assert deployed_bundle.review_decisions[-1].verdict == "deployed_versioned"
    assert deployed_bundle.review_decisions[-1].final_verdict_recorded is True
    assert all(hypothesis.governance_stage.value == "deployed_versioned" for hypothesis in deployed_bundle.hypotheses)
    assert all(diagnostic.status.value == "archived" for diagnostic in deployed_bundle.diagnostics)
    assert all(entry.eligible is True for entry in deployed_bundle.archive_eligibility)
    assert all(entry.archived_at is not None for entry in deployed_bundle.archive_eligibility)
    assert deployed_bundle.memory_record.archived is True
    assert "archived=yes" in deployed_bundle.review_export.markdown_body


def test_apply_candidate_replay_results_requires_replay_approved_hypotheses():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input("corr-9x-gated-replay"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
    )

    ready_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in bundle.candidates
        if candidate.governance_stage.value == "ready_for_replay"
    )

    try:
        apply_candidate_replay_results(
            bundle,
            passed_candidate_ids=ready_candidate_ids,
        )
    except ValueError as exc:
        assert "REPLAY_APPROVED" in str(exc)
    else:
        raise AssertionError("Replay results must stay blocked until human replay approval is recorded")


def test_shadow_candidate_approved_requires_all_hypotheses_to_have_shadow_ready_candidates():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input("corr-9x-partial-shadow"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
    )
    replay_approved_bundle = apply_human_review_resolution(
        bundle,
        actor="alice.ops",
        resolution="replay_approved",
        rationale="Replay approval granted before execution.",
    )
    ready_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in replay_approved_bundle.candidates
        if candidate.governance_stage.value == "ready_for_replay"
    )
    partial_shadow_bundle = apply_candidate_replay_results(
        replay_approved_bundle,
        passed_candidate_ids=ready_candidate_ids[:1],
    )

    try:
        apply_human_review_resolution(
            partial_shadow_bundle,
            actor="alice.ops",
            resolution="shadow_candidate_approved",
            rationale="This should stay blocked because only part of the bundle passed replay.",
        )
    except ValueError as exc:
        assert "ready_for_shadow_review" in str(exc)
    else:
        raise AssertionError("Partial replay success must not promote the whole bundle to shadow candidate")


def test_apply_human_review_resolution_can_reject_under_review_blocked_bundle():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    blocked_bundle = run_meta_learning_review(
        _trade_input("corr-9x-reject"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        capacity_snapshot=evaluate_learning_capacity(
            queue_depth=6400,
            queue_oldest_age_ms=900,
            log_loss_total=1,
        ),
    )

    resolved_bundle = apply_human_review_resolution(
        blocked_bundle,
        actor="bob.ops",
        resolution="replay_rejected_closed_no_action",
        rationale="Incomplete capture and weak evidence do not justify replay.",
    )

    assert resolved_bundle.review_decisions[-1].review_state.value == "rejected"
    assert resolved_bundle.review_decisions[-1].final_verdict_recorded is True
    assert all(hypothesis.governance_stage.value == "closed_no_action" for hypothesis in resolved_bundle.hypotheses)
    assert all(diagnostic.status.value == "archived" for diagnostic in resolved_bundle.diagnostics)
    assert all(entry.eligible is True for entry in resolved_bundle.archive_eligibility)
    assert all(entry.archived_at is not None for entry in resolved_bundle.archive_eligibility)
    assert resolved_bundle.memory_record.archived is True


def test_apply_human_review_resolution_replay_approved_keeps_review_open():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input("corr-9x-replay-approved"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
    )

    replay_approved_bundle = apply_human_review_resolution(
        bundle,
        actor="carol.ops",
        resolution="replay_approved",
        rationale="Replay may proceed but no final verdict is recorded yet.",
    )

    assert replay_approved_bundle.review_decisions[-1].review_state.value == "approved"
    assert replay_approved_bundle.review_decisions[-1].final_verdict_recorded is False
    assert all(
        hypothesis.governance_stage.value == "replay_approved"
        for hypothesis in replay_approved_bundle.hypotheses
    )
    assert all(entry.eligible is False for entry in replay_approved_bundle.archive_eligibility)


def test_apply_human_review_resolution_persists_archive_events(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    blocked_bundle = run_meta_learning_review(
        _trade_input("corr-9x-persist-archive"),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        capacity_snapshot=evaluate_learning_capacity(
            queue_depth=6500,
            queue_oldest_age_ms=950,
            log_loss_total=1,
        ),
    )

    apply_human_review_resolution(
        blocked_bundle,
        actor="carol.ops",
        resolution="replay_rejected_closed_no_action",
        rationale="Governed archive path should be persisted.",
        state_dir=repo_tmp_path,
    )

    store = AppendOnlyMetaLearningStore(repo_tmp_path)
    event_types = [record["event_type"] for record in store.read_records(_EVENT_FILE)]

    assert "review_decision_recorded" in event_types
    assert "diagnostic_archived" in event_types
    assert "hypothesis_archived" in event_types


def test_append_only_persistence_keeps_event_ids_unique_across_multiple_review_steps(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref, clock_ref = _replay_refs(len(records))
    bundle = run_meta_learning_review(
        _trade_input("corr-9x-event-ids"),
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
        actor="dora.ops",
        resolution="replay_approved",
        rationale="Replay approval is now explicit.",
        state_dir=repo_tmp_path,
    )
    ready_candidate_ids = tuple(
        candidate.candidate_id
        for candidate in replay_approved_bundle.candidates
        if candidate.governance_stage.value == "ready_for_replay"
    )
    apply_candidate_replay_results(
        replay_approved_bundle,
        passed_candidate_ids=ready_candidate_ids,
        state_dir=repo_tmp_path,
    )

    store = AppendOnlyMetaLearningStore(repo_tmp_path)
    event_ids = [record["event_id"] for record in store.read_records(_EVENT_FILE)]

    assert event_ids
    assert len(event_ids) == len(set(event_ids))
