"""Tests for governed LOCAL_REPLAY orchestration with chunking and resume."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from interface_contracts import StrategyClassification
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayOrchestratorRequest,
    orchestrate_local_replay_export,
)


def _scratch_dir(name: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "replay_orchestrator_tests" / name


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-orchestrator-1",
        source_path="inmemory://dataset-orchestrator-1",
        source="test_dataset",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.91,
                penalized_score=0.88,
                final_score=0.86,
                expected_edge_bps=17.0,
                spread_bps=3.0,
                slippage_bps=4.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.86,
                production_expected_cost=0.00086,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=21.0,
                feature_values={"spread_bps": 3.0, "imbalance": 0.1},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.84,
                penalized_score=0.8,
                final_score=0.77,
                expected_edge_bps=9.0,
                spread_bps=4.0,
                slippage_bps=3.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.77,
                production_expected_cost=0.00077,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=11.0,
                feature_values={"spread_bps": 4.0, "imbalance": -0.02},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-3",
                timestamp_ms=1_700_000_120_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.73,
                penalized_score=0.7,
                final_score=0.68,
                expected_edge_bps=8.0,
                spread_bps=5.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.68,
                production_expected_cost=0.00068,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=8.0,
                feature_values={"spread_bps": 5.0, "imbalance": 0.04},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-4",
                timestamp_ms=1_700_000_180_000,
                pair="SOLUSDT",
                engine_id="engine_c",
                raw_score=0.62,
                penalized_score=0.58,
                final_score=0.52,
                expected_edge_bps=6.0,
                spread_bps=6.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.5,
                target_decision_state="reduced",
                production_decision_state="reduced",
                production_final_score=0.52,
                production_expected_cost=0.00071,
                candidate_size=1.0,
                final_size=0.5,
                gross_return_bps=5.0,
                feature_values={"spread_bps": 6.0, "imbalance": 0.07},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-5",
                timestamp_ms=1_700_000_240_000,
                pair="XRPUSDT",
                engine_id="engine_d",
                raw_score=0.44,
                penalized_score=0.19,
                final_score=0.12,
                expected_edge_bps=2.0,
                spread_bps=8.0,
                slippage_bps=3.0,
                latency_penalty_bps=2.0,
                fill_ratio=0.0,
                target_decision_state="hard_blocked",
                production_decision_state="hard_blocked",
                production_final_score=0.12,
                production_expected_cost=0.0014,
                hard_block_reasons=("ce_negative",),
                primary_reason="ce_negative",
                feature_values={"spread_bps": 8.0, "imbalance": -0.16},
            ),
        ),
    )


def test_orchestrator_slices_dataset_by_chunk_and_persists_slice_outputs():
    output_dir = _scratch_dir("chunked_export")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-chunk-1",
                strategy_id="strategy-orchestrator-a",
                strategy_version="a.v9.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.0.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                chunk_index=2,
            )
        )

        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        session_config = json.loads(
            (output_dir / "replay_session_config.json").read_text(encoding="utf-8")
        )
        session_state = json.loads(
            (output_dir / "replay_session_state.json").read_text(encoding="utf-8")
        )

        assert result.resumed is False
        assert result.processed_dataset.record_count == 2
        assert [row.opportunity_id for row in result.processed_dataset.rows] == ["op-2", "op-3"]
        assert manifest["record_count"] == 2
        assert manifest["tick_count"] == 2
        assert manifest["tested_pairs"] == ["BTCUSDT", "ETHUSDT"]
        assert session_config["chunk_count"] == 3
        assert session_config["chunk_index"] == 2
        assert session_state["processed_records"] == 2
        assert session_state["lifecycle_state"] == "export_completed"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_resume_reuses_completed_export_without_new_dataset_inputs():
    output_dir = _scratch_dir("resume_export")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        first = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-resume-1",
                strategy_id="strategy-resume-a",
                strategy_version="a.v9.1",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.1.r1",
                performance_mode="shadow_fidelity_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
            )
        )
        original_manifest = (output_dir / "replay_run_manifest.json").read_text(encoding="utf-8")

        resumed = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-ignored-during-resume",
                strategy_id="strategy-ignored",
                strategy_version="a.v0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v0.r1",
                performance_mode="research_fast_mode",
                resume=True,
            )
        )

        assert first.resumed is False
        assert resumed.resumed is True
        assert resumed.session_config.run_id == "run-orchestrator-resume-1"
        assert resumed.processed_dataset.record_count == 5
        assert resumed.processed_dataset.dataset_id == "dataset-orchestrator-1"
        assert (output_dir / "replay_run_manifest.json").read_text(encoding="utf-8") == original_manifest
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_run_all_chunks_writes_chunk_dirs_and_root_aggregate():
    output_dir = _scratch_dir("aggregate_export")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-aggregate-1",
                strategy_id="strategy-aggregate-a",
                strategy_version="a.v9.3",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.3.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                run_all_chunks=True,
            )
        )

        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert result.chunk_session_path == output_dir / "replay_chunk_session.json"
        assert result.completed_chunk_indices == (1, 2, 3)
        assert result.chunk_output_dirs == (
            output_dir / "chunks" / "chunk_0001",
            output_dir / "chunks" / "chunk_0002",
            output_dir / "chunks" / "chunk_0003",
        )
        assert manifest["record_count"] == 5
        assert manifest["tick_count"] == 5
        assert manifest["tested_pairs"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
        assert session_bundle["aggregate_ready"] is True
        assert session_bundle["completed_chunk_indices"] == [1, 2, 3]
        assert len(session_bundle["chunk_artifacts"]) == 3
        assert len(dtr_lines) == 5
        for chunk_dir in result.chunk_output_dirs:
            assert (chunk_dir / "replay_run_manifest.json").exists()
            assert (chunk_dir / "replay_dtr.jsonl").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_run_all_chunks_resume_reuses_completed_session():
    output_dir = _scratch_dir("aggregate_resume_complete")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-aggregate-resume-1",
                strategy_id="strategy-aggregate-resume-a",
                strategy_version="a.v9.5",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.5.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                run_all_chunks=True,
            )
        )

        resumed = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-aggregate-resume-1",
                strategy_id="strategy-aggregate-resume-a",
                strategy_version="a.v9.5",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.5.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                run_all_chunks=True,
                resume=True,
            )
        )

        session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))

        assert resumed.resumed is True
        assert resumed.completed_chunk_indices == (1, 2, 3)
        assert resumed.resumed_chunk_indices == (1, 2, 3)
        assert session_bundle["resumed_chunk_indices"] == [1, 2, 3]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_run_all_chunks_resume_repairs_missing_chunk_and_reaggregates():
    output_dir = _scratch_dir("aggregate_resume_partial")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-aggregate-partial-1",
                strategy_id="strategy-aggregate-partial-a",
                strategy_version="a.v9.6",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.6.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                run_all_chunks=True,
            )
        )
        shutil.rmtree(output_dir / "chunks" / "chunk_0002", ignore_errors=True)

        resumed = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-aggregate-partial-1",
                strategy_id="strategy-aggregate-partial-a",
                strategy_version="a.v9.6",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.6.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                run_all_chunks=True,
                resume=True,
            )
        )

        session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert resumed.resumed is True
        assert resumed.completed_chunk_indices == (1, 2, 3)
        assert resumed.resumed_chunk_indices == (1, 3)
        assert session_bundle["resumed_chunk_indices"] == [1, 3]
        assert (output_dir / "chunks" / "chunk_0002" / "replay_run_manifest.json").exists()
        assert len(dtr_lines) == 5
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_run_all_chunks_accepts_explicit_chunk_selection():
    output_dir = _scratch_dir("aggregate_selected_chunks")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-selected-chunks-1",
                strategy_id="strategy-selected-chunks-a",
                strategy_version="a.v9.8",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.8.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=3,
                selected_chunk_indices=(1, 3),
                run_all_chunks=True,
            )
        )

        session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert result.completed_chunk_indices == (1, 3)
        assert result.chunk_output_dirs == (
            output_dir / "chunks" / "chunk_0001",
            output_dir / "chunks" / "chunk_0003",
        )
        assert session_bundle["selected_chunk_indices"] == [1, 3]
        assert len(dtr_lines) == 3
        assert (output_dir / "chunks" / "chunk_0001" / "replay_run_manifest.json").exists()
        assert not (output_dir / "chunks" / "chunk_0002").exists()
        assert (output_dir / "chunks" / "chunk_0003" / "replay_run_manifest.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_orchestrator_filters_dataset_by_time_window_before_chunking():
    output_dir = _scratch_dir("aggregate_windowed")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = orchestrate_local_replay_export(
            ReplayOrchestratorRequest(
                output_dir=output_dir,
                run_id="run-orchestrator-windowed-1",
                strategy_id="strategy-windowed-a",
                strategy_version="a.v9.9",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v9.9.r1",
                performance_mode="research_fast_mode",
                input_kind="historical_dataset",
                dataset=_dataset(),
                chunk_count=2,
                run_all_chunks=True,
                window_start_ms=1_700_000_060_000,
                window_end_ms=1_700_000_180_000,
            )
        )

        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert result.processed_dataset.record_count == 3
        assert manifest["record_count"] == 3
        assert manifest["tested_pairs"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        assert session_bundle["window_start_ms"] == 1700000060000
        assert session_bundle["window_end_ms"] == 1700000180000
        assert len(dtr_lines) == 3
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
