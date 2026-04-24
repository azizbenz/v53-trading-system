"""Tests for replay session config and state persistence."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayExecutionInput,
    ReplayRunManifest,
    ReplaySessionStateStore,
    ReplaySessionStoreConfig,
    build_replay_session_config,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import repo_build_path


def _scratch_dir(name: str) -> Path:
    return repo_build_path("replay_session_state_tests", f"{name}_{uuid4().hex}")


def test_build_replay_session_config_projects_mode_defaults_and_chunk_window():
    manifest = ReplayRunManifest(
        run_id="run-session-1",
        strategy_id="strategy-a",
        strategy_version="a.v1",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v1.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-1",
        timeframe_scope="2026-03-01T00:00:00Z/2026-03-01T04:00:00Z",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        formula_set_version="formula.v1",
        scoring_version="score.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode="research_fast_mode",
        artifact_schema_version="1.0.0",
        artifact_hash="artifact-1",
        clock_id="clock-1",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_240_000,
        tick_count=4,
        record_count=12,
    )

    config = build_replay_session_config(
        manifest,
        input_kind="historical_dataset",
        input_path="E:/datasets/replay.json",
        input_record_count=12,
        chunk_count=4,
        chunk_index=2,
        rewind_requested=True,
    )

    assert config.runtime_mode == "local_replay"
    assert config.input_kind == "historical_dataset"
    assert config.log_detail_level == "summary"
    assert config.monitoring_detail_level == "summary"
    assert config.chunk_window_ms == 60_000
    assert config.rewind_requested is True


def test_replay_session_state_store_persists_export_completion():
    output_dir = _scratch_dir("session_store")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        dataset = HistoricalReplayDataset.from_records(
            dataset_id="dataset-session-store",
            source_path="inmemory://session_store",
            records=(
                HistoricalReplayOpportunity(
                    opportunity_id="op-1",
                    timestamp_ms=1_700_000_000_000,
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    raw_score=0.9,
                    final_score=0.85,
                    expected_edge_bps=16.0,
                    spread_bps=3.0,
                    slippage_bps=4.0,
                    latency_penalty_bps=1.0,
                    fill_ratio=1.0,
                    target_decision_state="executed",
                    production_decision_state="executed",
                    production_final_score=0.85,
                    production_expected_cost=0.0008,
                    gross_return_bps=18.0,
                    feature_values={"spread_bps": 3.0},
                ),
            ),
        )
        execution_input = ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id="run-session-store-1",
                strategy_id="strategy-session-a",
                strategy_version="a.v2",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v2.r1",
                profile_scope=ProfileId.LIGHT,
                engine_scope=("engine_a",),
                tested_pairs=("BTCUSDT",),
                dataset_manifest_id=dataset.dataset_id,
                timeframe_scope="2026-03-01T00:00:00Z/2026-03-01T00:01:00Z",
        feature_set_version="2.0.0",
        transform_set_version="2.0.0",
        formula_set_version="formula.v2",
                scoring_version="score.v2",
                regime_version="regime.v2",
                risk_policy_version="risk.v2",
                cost_model_version="cost.v2",
                performance_mode="shadow_fidelity_mode",
        artifact_schema_version="2.0.0",
                artifact_hash="artifact-session-store-1",
                clock_id="clock-session-store-1",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_000_060_000,
                tick_count=1,
                record_count=1,
            ),
            total_opportunities=1,
            dtr_records=(
                build_dtr(
                    dtr_id="dtr-session-store-1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.EXECUTED,
                    expected_cost=0.0008,
                    realized_cost=0.0008,
                    gross_return=0.0018,
                    ce_expected=0.0008,
                    runtime_mode="local_replay",
                    input_source="historical_data_gateway",
                    timestamp=1_700_000_000.0,
                ),
            ),
            feature_bridge_payload={
                "bridge_status": "ok",
                "dataset_id": "dataset-session-store-1",
                "feature_set_version": "2.0.0",
                "transform_set_version": "2.0.0",
                "pairs": ["BTCUSDT"],
                "engines": ["engine_a"],
            },
        parity_diagnostics_payload={
            "parity_status": "ok",
            "dataset_id": "dataset-session-store-1",
            "decision_match_rate": 1.0,
        },
            review_notes=("session_store",),
        )
        session_config = build_replay_session_config(
            execution_input.run_manifest,
            input_kind="historical_dataset",
            input_path=dataset.source_path,
            input_record_count=dataset.record_count,
        )
        store = ReplaySessionStateStore(
            config=ReplaySessionStoreConfig(
                state_dir=output_dir,
                persist_state=True,
            )
        )

        store.initialize(session_config, output_dir=output_dir)
        store.mark_dataset_ready(dataset)
        execution_result = execute_local_replay_export(output_dir, execution_input)
        store.mark_export_completed(execution_result)

        reloaded = ReplaySessionStateStore(
            config=ReplaySessionStoreConfig(
                state_dir=output_dir,
                persist_state=True,
            )
        )
        state = reloaded.build_state()

        assert state.lifecycle_state == "export_completed"
        assert state.run_id == "run-session-store-1"
        assert state.processed_records == 1
        assert state.produced_dtr_count == 1
        assert state.feature_bridge_ready is True
        assert state.parity_diagnostics_ready is True
        assert state.replay_metrics_ready is True
        assert state.replay_dtr_ready is True
        assert len(state.artifact_paths) == 6
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_replay_session_state_store_backs_up_corrupted_state_and_marks_last_error():
    output_dir = _scratch_dir("session_store_corrupted")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        state_path = output_dir / "replay_session_state.json"
        state_path.write_text("{ invalid json", encoding="utf-8")

        store = ReplaySessionStateStore(
            config=ReplaySessionStoreConfig(
                state_dir=output_dir,
                persist_state=True,
            )
        )
        state = store.build_state()

        assert state_path.with_suffix(".corrupted").exists()
        assert "state_file_corrupted" in state.last_error
        assert state.lifecycle_state == "idle"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
