"""Replay clock helpers for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from local_replay_runtime.contracts import ReplayClockRef
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset


class ReplayClockTick(BaseModel, frozen=True):
    """Single deterministic replay tick derived from historical input rows."""

    tick_index: int = Field(..., ge=0)
    timestamp_ms: int = Field(..., ge=0)
    gap_ms: int = Field(default=0, ge=0)


class HistoricalReplayClock(BaseModel, frozen=True):
    """Deterministic clock materialized from a historical replay dataset."""

    clock_ref: ReplayClockRef
    timeframe_scope: str = Field(..., min_length=1)
    ticks: tuple[ReplayClockTick, ...] = Field(..., min_length=1)


def _format_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def build_replay_clock(
    dataset: HistoricalReplayDataset,
    *,
    clock_id: str,
    mode: str = "historical",
) -> HistoricalReplayClock:
    """Build the governed replay clock from the ordered historical dataset."""

    ticks: list[ReplayClockTick] = []
    previous_timestamp_ms: int | None = None
    for index, row in enumerate(dataset.rows):
        gap_ms = 0 if previous_timestamp_ms is None else row.timestamp_ms - previous_timestamp_ms
        ticks.append(
            ReplayClockTick(
                tick_index=index,
                timestamp_ms=row.timestamp_ms,
                gap_ms=gap_ms,
            )
        )
        previous_timestamp_ms = row.timestamp_ms
    return HistoricalReplayClock(
        clock_ref=ReplayClockRef(
            clock_id=clock_id,
            mode=mode,
            start_timestamp_ms=dataset.start_timestamp_ms,
            end_timestamp_ms=dataset.end_timestamp_ms,
            tick_count=len(ticks),
        ),
        timeframe_scope=(
            f"{_format_timestamp(dataset.start_timestamp_ms)}/"
            f"{_format_timestamp(dataset.end_timestamp_ms)}"
        ),
        ticks=tuple(ticks),
    )


__all__ = [
    "ReplayClockTick",
    "HistoricalReplayClock",
    "build_replay_clock",
]
