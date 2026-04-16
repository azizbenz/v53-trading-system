"""Focused tests for replay scope identity in chunk session exports."""

from __future__ import annotations

import json
from pathlib import Path

from interface_contracts import StrategyClassification
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayOrchestratorRequest,
    orchestrate_local_replay_export,
)


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-orchestrator-scope-1",
        source_path="inmemory://dataset-orchestrator-scope-1",
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
                feature_values={"spread_bps": 3.0},
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
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-3",
                timestamp_ms=1_700_000_120_000,
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
                feature_values={"spread_bps": 6.0},
            ),
        ),
    )


def test_orchestrator_persists_replay_scope_identity_for_chunk_session(
    repo_tmp_path: Path,
) -> None:
    output_dir = repo_tmp_path / "aggregate_scope_identity"

    result = orchestrate_local_replay_export(
        ReplayOrchestratorRequest(
            output_dir=output_dir,
            run_id="run-orchestrator-scope-1",
            strategy_id="strategy-orchestrator-scope-a",
            strategy_version="a.v10.0",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v10.0.r1",
            performance_mode="research_fast_mode",
            input_kind="historical_dataset",
            dataset=_dataset(),
            chunk_count=2,
            selected_chunk_indices=(1, 2),
            run_all_chunks=True,
            window_start_ms=1_700_000_000_000,
            window_end_ms=1_700_000_120_000,
        )
    )

    session_bundle = json.loads((output_dir / "replay_chunk_session.json").read_text(encoding="utf-8"))

    assert result.chunk_session_path == output_dir / "replay_chunk_session.json"
    assert session_bundle["replay_scope_identity"] == {
        "dataset_id": "dataset-orchestrator-scope-1",
        "input_kind": "historical_dataset",
        "performance_mode": "research_fast_mode",
        "engine_scope": ["engine_a", "engine_b", "engine_c"],
        "pair_scope": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "chunk_count": 2,
        "selected_chunk_indices": [1, 2],
        "requested_window_start_ms": 1700000000000,
        "requested_window_end_ms": 1700000120000,
        "effective_start_timestamp_ms": 1700000000000,
        "effective_end_timestamp_ms": 1700000120000,
    }
