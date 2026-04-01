"""Tests for the replay clock derived from historical datasets."""

from __future__ import annotations

from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    build_replay_clock,
)


def test_build_replay_clock_tracks_ordered_ticks_and_timeframe():
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-clock-1",
        source_path="inmemory://clock",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                feature_values={"spread_bps": 3.0},
            ),
        ),
    )

    clock = build_replay_clock(dataset, clock_id="clock-dataset-1")

    assert clock.clock_ref.clock_id == "clock-dataset-1"
    assert clock.clock_ref.tick_count == 2
    assert clock.ticks[0].timestamp_ms == 1_700_000_000_000
    assert clock.ticks[1].gap_ms == 60_000
    assert clock.timeframe_scope.startswith("2023-11-14T22:13:20Z/")
