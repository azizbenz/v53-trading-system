"""Focused tests for aggregate replay scope identity."""

from __future__ import annotations

from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    build_replay_scope_identity,
)


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-scope-1",
        source_path="inmemory://dataset-scope-1",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-3",
                timestamp_ms=1_700_000_120_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                feature_values={"spread_bps": 5.0},
            ),
        ),
    )


def test_build_replay_scope_identity_builds_typed_aggregate_scope() -> None:
    dataset = _dataset()

    identity = build_replay_scope_identity(
        datasets=(dataset,),
        input_kind="historical_dataset",
        performance_mode="research_fast_mode",
        chunk_count=3,
        selected_chunk_indices=(3, 1),
        requested_window_start_ms=1_700_000_000_000,
        requested_window_end_ms=1_700_000_120_000,
    )

    assert identity.dataset_id == "dataset-scope-1"
    assert tuple(engine.value for engine in identity.engine_scope) == ("engine_a", "engine_b")
    assert identity.pair_scope == ("BTCUSDT", "ETHUSDT")
    assert identity.selected_chunk_indices == (1, 3)
    assert identity.effective_start_timestamp_ms == 1_700_000_000_000
    assert identity.effective_end_timestamp_ms == 1_700_000_120_000
    assert identity.canonical_key == (
        "dataset-scope-1:historical_dataset:research_fast_mode:"
        "engine_a,engine_b:BTCUSDT,ETHUSDT:3:1,3:"
        "1700000000000-1700000120000:1700000000000-1700000120000"
    )
