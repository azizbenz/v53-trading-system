"""Replay bundle and persistence tests for Build-9X."""

from __future__ import annotations

from interface_contracts import (
    EngineId,
    ProfileId,
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
    AppendOnlyMetaLearningStore,
    TradeLearningInput,
    evaluate_learning_capacity,
    run_meta_learning_review,
)
from meta_learning.persistence_store import (
    _CANDIDATE_FILE,
    _DIAGNOSTIC_FILE,
    _EVENT_FILE,
    _EXPORT_BUNDLE_FILE,
    _HYPOTHESIS_FILE,
    _MEMORY_FILE,
    _REVIEW_FILE,
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
        correlation_id="corr-9x-persist",
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


def test_run_meta_learning_review_builds_governed_replay_bundles():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    dataset_ref = ReplayDatasetRef(
        dataset_id="dataset-1",
        pair_scope=("BTCUSDT", "ETHUSDT"),
        record_count=len(records),
    )
    clock_ref = ReplayClockRef(
        clock_id="clock-1",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_100_000,
        tick_count=100,
    )

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

    assert len(bundle.replay_bundles) == len(bundle.candidates)
    assert bundle.review_export.replay_bundles == bundle.replay_bundles
    assert all(candidate.replay_bundle_reference for candidate in bundle.candidates)
    assert all(candidate.comparison_protocol_reference for candidate in bundle.candidates)
    assert all(candidate.tests_required for candidate in bundle.candidates)
    assert all(replay_bundle.execution_plan.validation_ready for replay_bundle in bundle.replay_bundles)
    assert all(replay_bundle.source_version == "5.3.0-build9x" for replay_bundle in bundle.replay_bundles)
    assert all(replay_bundle.contracts_version == "build9x.contracts.v1" for replay_bundle in bundle.replay_bundles)
    assert all(replay_bundle.feature_schema_version == "v53.feature_schema.v1" for replay_bundle in bundle.replay_bundles)
    assert all(candidate.governance_stage.value == "ready_for_replay" for candidate in bundle.candidates)
    assert any(record.from_state == "prepared" and record.to_state == "tests_pending" for record in bundle.lifecycle_transitions)
    assert any(record.from_state == "tests_pending" and record.to_state == "ready_for_replay" for record in bundle.lifecycle_transitions)


def test_run_meta_learning_review_persists_append_only_records(repo_tmp_path):
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    bundle = run_meta_learning_review(
        _trade_input(),
        dtr_records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        state_dir=repo_tmp_path,
    )
    store = AppendOnlyMetaLearningStore(repo_tmp_path)

    assert store.read_records(_DIAGNOSTIC_FILE)
    assert store.read_records(_HYPOTHESIS_FILE)
    assert store.read_records(_CANDIDATE_FILE)
    assert store.read_records(_REVIEW_FILE)
    assert store.read_records(_EVENT_FILE)
    assert store.read_records(_EXPORT_BUNDLE_FILE)
    assert store.read_records(_MEMORY_FILE)
    assert len(store.find_records_by_entity_id(_CANDIDATE_FILE, bundle.candidates[0].candidate_id)) == 1
    assert len(store.find_records_by_entity_id(_EXPORT_BUNDLE_FILE, bundle.replay_bundles[0].bundle_id)) == 1
    assert store.read_records(_REVIEW_FILE)[-1]["review_decisions"]
    assert store.read_records(_REVIEW_FILE)[-1]["archive_eligibility"]
    assert store.read_records(_EXPORT_BUNDLE_FILE)[-1]["retention_policy"] == "keep_while_review_or_replay_open"
    assert store.read_records(_EXPORT_BUNDLE_FILE)[-1]["retention_locked"] is True
    assert any(record["event_type"] == "candidate_state_changed" for record in store.read_records(_EVENT_FILE))


def test_run_meta_learning_review_persists_capacity_backpressure_trace(repo_tmp_path):
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
        state_dir=repo_tmp_path,
    )
    store = AppendOnlyMetaLearningStore(repo_tmp_path)
    review_records = store.read_records(_REVIEW_FILE)
    event_records = store.read_records(_EVENT_FILE)

    assert review_records[-1]["capacity_snapshot"]["capture_mode"] == "capture_minimale"
    assert review_records[-1]["review_export"]["review_blocked_due_to_incomplete_data"] is True
    assert review_records[-1]["review_decisions"][0]["review_state"] == "needs_revision"
    assert review_records[-1]["lifecycle_transitions"]
    assert bundle.replay_bundles == ()
    assert any(record["event_type"] == "learning.storage.backpressure" for record in event_records)
    assert any(record["event_type"] == "review_decision_recorded" for record in event_records)
    assert any(record["event_type"] == "hypothesis_state_changed" for record in event_records)
