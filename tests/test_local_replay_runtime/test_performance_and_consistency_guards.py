"""Tests for LOCAL_REPLAY performance mode and consistency guards."""

from __future__ import annotations

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    ReplayRunManifest,
    build_performance_mode_guard_report,
    build_replay_session_config,
    compare_replay_runs,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _manifest(*, performance_mode: str) -> ReplayRunManifest:
    return ReplayRunManifest(
        run_id=f"run-{performance_mode}",
        strategy_id="strategy-a",
        strategy_version="a.v1",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v1.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-1",
        timeframe_scope="2026-03-01T00:00:00Z/2026-03-01T00:01:00Z",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        formula_set_version="formula.v1",
        scoring_version="score.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode=performance_mode,  # type: ignore[arg-type]
        artifact_schema_version="1.0.0",
        artifact_hash=f"artifact-{performance_mode}",
        clock_id=f"clock-{performance_mode}",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_060_000,
        tick_count=1,
        record_count=1,
    )


def _records(*, final_score: float = 0.8, penalized_score: float = 0.82):
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            raw_score=0.85,
            penalized_score=penalized_score,
            final_score=final_score,
            expected_cost=0.0008,
            realized_cost=0.0008,
            gross_return=0.0018,
            ce_expected=0.0007,
            ranking_position=1,
            final_size=1.0,
            runtime_mode="local_replay",
            input_source="historical_data_gateway",
            timestamp=1_700_000_000.0,
        ),
    )


def test_build_performance_mode_guard_report_allows_research_fast_mode():
    manifest = _manifest(performance_mode="research_fast_mode")
    session_config = build_replay_session_config(
        manifest,
        input_kind="historical_dataset",
        input_path="E:/datasets/replay.json",
        input_record_count=1,
    )

    report = build_performance_mode_guard_report(session_config, manifest)

    assert report.guard_passed is True
    assert report.performance_mode == "research_fast_mode"
    assert report.log_detail_level == "summary"
    assert "log_frequency" in report.allowed_lightenings
    assert "features" in report.forbidden_changes


def test_compare_replay_runs_accepts_equivalent_records():
    report = compare_replay_runs(
        _records(),
        _records(),
        reference_label="shadow_fidelity_mode",
        candidate_label="research_fast_mode",
    )

    assert report.consistent is True
    assert report.compared_records == 1
    assert report.decision_drift_ids == ()


def test_compare_replay_runs_rejects_business_decision_drift():
    candidate = (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.HARD_BLOCKED,
            raw_score=0.85,
            penalized_score=0.75,
            final_score=0.7,
            hard_block_reasons=("ce_negative",),
            ranking_position=0,
            final_size=0.0,
            runtime_mode="local_replay",
            input_source="historical_data_gateway",
            timestamp=1_700_000_000.0,
        ),
    )

    report = compare_replay_runs(
        _records(),
        candidate,
        reference_label="shadow_fidelity_mode",
        candidate_label="research_fast_mode",
    )

    assert report.consistent is False
    assert report.decision_drift_ids == ("dtr-1",)
    assert report.penalty_drift_ids == ("dtr-1",)
    assert report.final_size_drift_ids == ("dtr-1",)
    assert report.hard_block_drift_ids == ("dtr-1",)
