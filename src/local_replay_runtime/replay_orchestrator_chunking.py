"""Dataset chunking helpers for governed LOCAL_REPLAY exports."""

from __future__ import annotations

from pathlib import Path

from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.replay_orchestrator_models import ReplayOrchestratorRequest


def _slice_dataset_for_chunk(
    dataset: HistoricalReplayDataset,
    *,
    chunk_count: int,
    chunk_index: int,
) -> HistoricalReplayDataset:
    if chunk_index > chunk_count:
        raise ValueError("chunk_index must stay <= chunk_count")
    total = len(dataset.rows)
    start = total * (chunk_index - 1) // chunk_count
    end = total * chunk_index // chunk_count
    chunk_rows = dataset.rows[start:end]
    if not chunk_rows:
        raise ValueError("chunk replay produced an empty dataset slice")
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        records=chunk_rows,
        source=dataset.source,
    )


def _chunk_output_dir(output_dir: Path, chunk_index: int) -> Path:
    return output_dir / "chunks" / f"chunk_{chunk_index:04d}"


def _filter_dataset_by_window(
    dataset: HistoricalReplayDataset,
    *,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> HistoricalReplayDataset:
    if window_start_ms is None and window_end_ms is None:
        return dataset
    filtered_rows = tuple(
        row
        for row in dataset.rows
        if (window_start_ms is None or row.timestamp_ms >= window_start_ms)
        and (window_end_ms is None or row.timestamp_ms <= window_end_ms)
    )
    if not filtered_rows:
        raise ValueError("requested replay window produced an empty dataset slice")
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        records=filtered_rows,
        source=dataset.source,
    )


def _resolve_chunk_indices(request: ReplayOrchestratorRequest) -> tuple[int, ...]:
    if request.run_all_chunks:
        if request.selected_chunk_indices:
            return tuple(sorted(request.selected_chunk_indices))
        return tuple(range(1, request.chunk_count + 1))
    return (request.chunk_index,)


__all__ = [
    "_chunk_output_dir",
    "_filter_dataset_by_window",
    "_resolve_chunk_indices",
    "_slice_dataset_for_chunk",
]
