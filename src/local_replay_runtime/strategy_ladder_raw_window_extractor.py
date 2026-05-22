"""Raw-window extraction for Strategy Ladder candidate replay."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from time import perf_counter, process_time
import gzip
import json
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
    deterministic_payload_hash,
)
from local_replay_runtime.strategy_ladder_window_cache import (
    StrategyLadderWindowCache,
    StrategyLadderWindowCacheMetrics,
    StrategyLadderWindowCacheRequest,
)
from local_replay_runtime.strategy_ladder_window_index import (
    StrategyLadderWindowIndex,
    StrategyLadderWindowLookupMetrics,
)

_RAW_WINDOW_PROGRESS_EVERY = 50
_ENGINE_C_STRUCTURAL_LOOKBACK_MS = 60 * 60 * 1000
_ECONOMIC_EDGE_OHLCV_LOOKBACK_MS = 60 * 60 * 1000
_REPLAY_OUTCOME_OHLCV_POST_BARS = 10


@dataclass(frozen=True)
class _WindowSliceRequest:
    source_path: Path
    target_path: Path
    window_start_ms: int
    window_end_ms: int
    include_anchor_before_start: bool = False


@dataclass(frozen=True)
class _WindowSliceExecutionStats:
    slice_counts: dict[str, int]
    parsed_row_count: int
    files_scanned: int
    wall_time_s: float
    cpu_time_s: float


@dataclass(frozen=True)
class StrategyLadderRawWindowExtractionResult:
    status: str
    manifests: tuple[StrategyLadderRawWindowManifest, ...]
    indexed_lookup_metrics: StrategyLadderWindowLookupMetrics
    window_cache_metrics: StrategyLadderWindowCacheMetrics
    jsonl_parsing_wall_time_s: float = 0.0
    jsonl_parsing_cpu_time_s: float = 0.0
    jsonl_rows_processed: int = 0
    jsonl_files_scanned: int = 0

    def __iter__(self):
        yield self.status
        yield self.manifests


def _map_book_depth_status(levels: int | None, *, book_present: bool) -> str:
    if not book_present:
        return "BOOK_DEPTH_MISSING"
    if levels is None:
        return "BOOK_DEPTH_NOT_PROVEN"
    if levels <= 0:
        return "BOOK_DEPTH_MISSING"
    if levels == 1:
        return "BOOK_TOP_OF_BOOK_ONLY"
    if levels < 20:
        return "BOOK_LIMITED_DEPTH_AVAILABLE"
    return "BOOK_DEPTH20_AVAILABLE"


def _map_fallback_book_depth_status(
    levels: int | None,
    *,
    book_present: bool,
) -> str:
    """Fail closed for legacy raw-root fallback extraction.

    Depth20 requires governed silver-index lineage plus reconstruction. Raw-root
    path hints may still surface limited-depth evidence, but they must never
    auto-promote to BOOK_DEPTH20_AVAILABLE.
    """

    status = _map_book_depth_status(levels, book_present=book_present)
    if status == "BOOK_DEPTH20_AVAILABLE":
        return "BOOK_LIMITED_DEPTH_AVAILABLE"
    return status


def _search_paths(root: Path, pair: str, token: str) -> tuple[Path, ...]:
    pair_root = root / pair
    candidates: list[Path] = []
    search_roots = (pair_root,) if pair_root.is_dir() else (root,)
    for search_root in search_roots:
        for path in search_root.rglob("*"):
            if not path.is_file():
                continue
            lowered = path.name.lower()
            if token in lowered and pair.lower() in str(path).lower():
                candidates.append(path.resolve())
    return tuple(sorted(dict.fromkeys(candidates)))


def _hint_path(candidate: StrategyLadderCandidateEvent, key: str, raw_root: Path) -> Path | None:
    payload = candidate.compatibility_payload or {}
    raw_value = payload.get(key)
    if not raw_value:
        return None
    path = Path(str(raw_value))
    if not path.is_absolute():
        path = (raw_root / path).resolve()
    return path if path.exists() else None


def _timeframe_to_ms(raw_value: str | None) -> int | None:
    if not raw_value:
        return None
    normalized = raw_value.strip().lower()
    if not normalized:
        return None
    unit = normalized[-1]
    if unit.isdigit():
        try:
            return int(normalized) * 60_000
        except ValueError:
            return None
    try:
        magnitude = int(normalized[:-1])
    except ValueError:
        return None
    if magnitude <= 0:
        return None
    if unit == "m":
        return magnitude * 60_000
    if unit == "h":
        return magnitude * 60 * 60_000
    if unit == "d":
        return magnitude * 24 * 60 * 60_000
    return None


def _is_gzip_path(path: Path) -> bool:
    return path.name.lower().endswith(".gz")


def _open_text_input(path: Path, *, newline: str | None = None):
    if _is_gzip_path(path):
        return gzip.open(path, "rt", encoding="utf-8-sig", newline=newline)
    return path.open("r", encoding="utf-8-sig", newline=newline)


def _read_first_json_row(path: Path) -> dict[str, object] | None:
    lowered = path.name.lower()
    if lowered.endswith((".json", ".json.gz")):
        with _open_text_input(path) as handle:
            payload = json.load(handle)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return payload[0]
        if isinstance(payload, dict):
            records = payload.get("records")
            if isinstance(records, list) and records and isinstance(records[0], dict):
                return records[0]
            return payload
        return None
    if lowered.endswith((".jsonl", ".jsonl.gz", ".data", ".data.gz")):
        with _open_text_input(path) as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                return payload if isinstance(payload, dict) else None
        return None
    if lowered.endswith((".csv", ".csv.gz")):
        with _open_text_input(path, newline="") as handle:
            reader = csv.DictReader(handle)
            try:
                row = next(reader)
            except StopIteration:
                return None
            return dict(row)
    return None


def _row_timestamp_ms(row: dict[str, object]) -> int | None:
    raw_value = row.get("timestamp_ms")
    if raw_value in (None, ""):
        raw_value = row.get("ts")
    try:
        return int(raw_value) if raw_value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _write_window_slices(
    requests: tuple[_WindowSliceRequest, ...],
) -> _WindowSliceExecutionStats:
    started_wall = perf_counter()
    started_cpu = process_time()
    if not requests:
        return _WindowSliceExecutionStats(
            slice_counts={},
            parsed_row_count=0,
            files_scanned=0,
            wall_time_s=0.0,
            cpu_time_s=0.0,
        )
    counts = {str(request.target_path.resolve()): 0 for request in requests}
    grouped: dict[Path, list[_WindowSliceRequest]] = {}
    for request in requests:
        grouped.setdefault(request.source_path.resolve(), []).append(request)

    parsed_row_count = 0
    initialized_targets: set[Path] = set()
    for source_path, source_requests in grouped.items():
        for request in source_requests:
            request.target_path.parent.mkdir(parents=True, exist_ok=True)
        handles = []
        for request in source_requests:
            target_resolved = request.target_path.resolve()
            mode = "a" if target_resolved in initialized_targets else "w"
            handles.append(
                (
                    request,
                    request.target_path.open(mode, encoding="utf-8", newline="\n"),
                )
            )
            initialized_targets.add(target_resolved)
        anchor_lines: dict[_WindowSliceRequest, tuple[int, str] | None] = {
            request: None for request in source_requests
        }
        anchor_flushed: dict[_WindowSliceRequest, bool] = {
            request: False for request in source_requests
        }
        min_start_ms = min(request.window_start_ms for request in source_requests)
        max_end_ms = max(request.window_end_ms for request in source_requests)
        try:
            if not source_path.exists():
                continue
            with _open_text_input(source_path) as source_handle:
                for line in source_handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        row = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    parsed_row_count += 1
                    timestamp_ms = _row_timestamp_ms(row)
                    if timestamp_ms is None:
                        continue
                    for request, _target_handle in handles:
                        if (
                            request.include_anchor_before_start
                            and timestamp_ms <= request.window_start_ms
                        ):
                            anchor_lines[request] = (timestamp_ms, stripped)
                    if timestamp_ms < min_start_ms:
                        continue
                    if timestamp_ms > max_end_ms:
                        break
                    for request, target_handle in handles:
                        if request.window_start_ms <= timestamp_ms <= request.window_end_ms:
                            anchor = anchor_lines.get(request)
                            if (
                                request.include_anchor_before_start
                                and not anchor_flushed[request]
                                and anchor is not None
                                and anchor[0] < request.window_start_ms
                            ):
                                target_handle.write(anchor[1])
                                target_handle.write("\n")
                                counts[str(request.target_path.resolve())] += 1
                            anchor_flushed[request] = True
                            target_handle.write(stripped)
                            target_handle.write("\n")
                            counts[str(request.target_path.resolve())] += 1
                for request, target_handle in handles:
                    anchor = anchor_lines.get(request)
                    if (
                        request.include_anchor_before_start
                        and not anchor_flushed[request]
                        and anchor is not None
                    ):
                        target_handle.write(anchor[1])
                        target_handle.write("\n")
                        counts[str(request.target_path.resolve())] += 1
        finally:
            for _request, target_handle in handles:
                target_handle.close()
    return _WindowSliceExecutionStats(
        slice_counts=counts,
        parsed_row_count=parsed_row_count,
        files_scanned=len(grouped),
        wall_time_s=perf_counter() - started_wall,
        cpu_time_s=process_time() - started_cpu,
    )


def _shared_materialized_window_path(
    output_dir: Path,
    *,
    source_type: str,
    pair: str,
    timeframe: str,
    window_start_ms: int,
    window_end_ms: int,
    depth: int | None,
    source_hash: str,
    include_anchor_before_start: bool,
    filename: str,
) -> Path:
    cache_key = deterministic_payload_hash(
        {
            "source_type": source_type,
            "pair": pair,
            "timeframe": timeframe,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
            "depth": depth,
            "source_hash": source_hash,
            "include_anchor_before_start": include_anchor_before_start,
        }
    )
    return (
        output_dir
        / "_shared_windows"
        / source_type
        / pair
        / cache_key
        / filename
    )


def _entries_source_hash(
    entries: tuple[StrategyLadderSilverIndexEntry, ...],
) -> str | None:
    if not entries:
        return None
    payload: list[dict[str, object]] = []
    for entry in entries:
        path = str(Path(entry.path).resolve()) if entry.path else ""
        token = str(entry.file_hash or path).strip()
        if not token:
            return None
        payload.append(
            {
                "token": token,
                "source_id": entry.source_id,
                "date": entry.date,
                "min_timestamp_ms": entry.min_timestamp_ms,
                "max_timestamp_ms": entry.max_timestamp_ms,
            }
        )
    return deterministic_payload_hash(payload)


def _dedupe_slice_requests(
    requests: tuple[_WindowSliceRequest, ...],
) -> tuple[_WindowSliceRequest, ...]:
    deduped: dict[
        tuple[str, str, int, int, bool],
        _WindowSliceRequest,
    ] = {}
    for request in requests:
        key = (
            str(request.source_path.resolve()),
            str(request.target_path.resolve()),
            request.window_start_ms,
            request.window_end_ms,
            request.include_anchor_before_start,
        )
        deduped.setdefault(key, request)
    return tuple(deduped.values())


def _infer_depth_levels(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    lowered = path.name.lower()
    if "depth20" in lowered:
        return 20
    if "depth10" in lowered:
        return 10
    if "depth5" in lowered:
        return 5
    if "top_of_book" in lowered or "tob" in lowered:
        return 1
    first_row = _read_first_json_row(path)
    if isinstance(first_row, dict):
        data = first_row.get("data")
        if isinstance(data, dict):
            bids = data.get("b") or data.get("bids")
            asks = data.get("a") or data.get("asks")
            if isinstance(bids, list) and isinstance(asks, list):
                return min(len(bids), len(asks))
        for key in ("depth_levels", "book_depth_levels", "levels"):
            raw_value = first_row.get(key)
            if raw_value in (None, ""):
                continue
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                continue
    return None


def _derive_window_status(
    *,
    trade_present: bool,
    book_present: bool,
    ohlcv_present: bool,
    metadata_present: bool,
    book_status: str,
) -> tuple[str, str]:
    if trade_present and book_present and ohlcv_present:
        window_status = (
            "RAW_WINDOW_READY"
            if book_status == "BOOK_DEPTH20_AVAILABLE"
            else "RAW_WINDOW_PARTIAL"
        )
    elif not trade_present and not book_present and not ohlcv_present:
        window_status = "RAW_WINDOW_NOT_PROVEN"
    elif not trade_present:
        window_status = "RAW_WINDOW_MISSING_TRADES"
    elif not book_present:
        window_status = "RAW_WINDOW_MISSING_BOOK"
    elif not ohlcv_present:
        window_status = "RAW_WINDOW_MISSING_OHLCV"
    else:
        window_status = "RAW_WINDOW_PARTIAL"

    if not trade_present and not book_present and not ohlcv_present:
        source_coverage_status = "RAW_WINDOW_SOURCE_NOT_PROVEN"
    elif not trade_present:
        source_coverage_status = "RAW_WINDOW_SOURCE_MISSING_TRADES"
    elif not book_present:
        source_coverage_status = "RAW_WINDOW_SOURCE_MISSING_BOOK"
    elif not ohlcv_present:
        source_coverage_status = "RAW_WINDOW_SOURCE_MISSING_OHLCV"
    elif not metadata_present:
        source_coverage_status = "RAW_WINDOW_SOURCE_MISSING_METADATA"
    elif window_status != "RAW_WINDOW_READY":
        source_coverage_status = "RAW_WINDOW_SOURCE_COVERAGE_PARTIAL"
    else:
        source_coverage_status = "RAW_WINDOW_SOURCE_COVERAGE_COMPLETE"
    return window_status, source_coverage_status


def _materialized_path_has_rows(
    path: str | None,
    *,
    slice_counts: dict[str, int],
) -> bool:
    if not path:
        return False
    resolved = str(Path(path).resolve())
    if slice_counts.get(resolved, 0) > 0:
        return True
    try:
        file_path = Path(path)
        return file_path.is_file() and file_path.stat().st_size > 0
    except OSError:
        return False


def _resolve_component_path(
    *,
    candidate: StrategyLadderCandidateEvent,
    raw_root: Path,
    key: str,
    token: str,
    window_index: StrategyLadderWindowIndex | None = None,
) -> Path | None:
    hinted = _hint_path(candidate, key, raw_root)
    if hinted is not None:
        return hinted
    if window_index is not None:
        matches = window_index.lookup_raw_paths(pair=candidate.pair, token=token)
    else:
        matches = _search_paths(raw_root, candidate.pair, token)
    return matches[0] if matches else None


def _effective_slice_bounds(
    *,
    candidate: StrategyLadderCandidateEvent,
    source_type: str,
    logical_window_start_ms: int,
    logical_window_end_ms: int,
) -> tuple[int, int]:
    """Return the materialized slice bounds for one source type.

    The manifest keeps the logical replay window unchanged. Some engine builders
    need extra pre-history inside the materialized file itself; otherwise the
    replay path silently degrades into fallback geometry.
    """

    pad_before_ms = 0
    pad_after_ms = 0
    if source_type == "ohlcv":
        # Economic provenance edge fallback is causal and requires one hour of
        # prior OHLCV context. Without this, B2 native replay silently
        # degenerates to DEFAULT_TO_CALIBRATE 5.0 bps for A/B/D as soon as the
        # logical replay window is shorter than the edge lookback.
        pad_before_ms = max(pad_before_ms, _ECONOMIC_EDGE_OHLCV_LOOKBACK_MS)
        # Replay outcome evidence measures h1/h5/h10 forward returns and
        # MFE/MAE over the first 10 future bars. Keep the manifest logical
        # window unchanged, but materialize enough future OHLCV rows for the
        # evidence layer to avoid false MISSING_POST_WINDOW blockers.
        timeframe_ms = _timeframe_to_ms(candidate.timeframe)
        if timeframe_ms is not None:
            pad_after_ms = max(
                pad_after_ms,
                timeframe_ms * _REPLAY_OUTCOME_OHLCV_POST_BARS,
            )
    if candidate.engine_id == "engine_c" and source_type in {"trades", "ohlcv"}:
        # Engine C doc21 breakout reconstruction requires one hour of
        # pre-break OHLCV/trade lookback. Without this, every governed replay
        # window degrades to DETECTED_FALLBACK_INWINDOW_RANGE and appears
        # "late" even when the candidate timestamp itself is valid.
        pad_before_ms = max(pad_before_ms, _ENGINE_C_STRUCTURAL_LOOKBACK_MS)
    padded_end_ms = max(
        logical_window_end_ms,
        candidate.resolved_timestamp_ms + pad_after_ms,
    )
    return max(0, logical_window_start_ms - pad_before_ms), padded_end_ms


def _load_silver_index(
    silver_index_path: Path | None,
    silver_index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
) -> tuple[StrategyLadderSilverIndexEntry, ...]:
    if silver_index_entries:
        return silver_index_entries
    if silver_index_path is None or not silver_index_path.is_file():
        return ()
    payload = json.loads(silver_index_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_entries = payload.get("entries", ())
    else:
        raw_entries = payload
    if not isinstance(raw_entries, list):
        return ()
    entries: list[StrategyLadderSilverIndexEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        entries.append(StrategyLadderSilverIndexEntry.model_validate(item))
    return tuple(entries)


def _entry_overlaps_window(
    entry: StrategyLadderSilverIndexEntry,
    *,
    window_start_ms: int,
    window_end_ms: int,
) -> bool:
    if entry.min_timestamp_ms is None or entry.max_timestamp_ms is None:
        return True
    return entry.max_timestamp_ms >= window_start_ms and entry.min_timestamp_ms <= window_end_ms


def _sort_entries(
    entries: tuple[StrategyLadderSilverIndexEntry, ...],
) -> tuple[StrategyLadderSilverIndexEntry, ...]:
    return tuple(
        sorted(
            entries,
            key=lambda item: (
                -int(item.source_priority),
                item.path,
            ),
        )
    )


def _entries_for_candidate(
    *,
    entries: tuple[StrategyLadderSilverIndexEntry, ...],
    window_index: StrategyLadderWindowIndex | None,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    data_types: tuple[str, ...],
    timeframe: str | None = None,
) -> tuple[StrategyLadderSilverIndexEntry, ...]:
    if window_index is not None:
        return window_index.lookup_silver_entries(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            data_types=data_types,
            timeframe=timeframe,
        )
    allowed = set(data_types)
    rows = tuple(
        entry
        for entry in entries
        if entry.pair == pair
        and entry.data_type in allowed
        and (not timeframe or not entry.timeframe or entry.timeframe == timeframe)
        and _entry_overlaps_window(
            entry,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )
    )
    return _sort_entries(rows)


def _levels_from_index_status(status: str) -> int | None:
    if status == "BOOK_DEPTH20_AVAILABLE":
        return 20
    if status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        return 10
    if status == "BOOK_TOP_OF_BOOK_ONLY":
        return 1
    if status == "BOOK_DEPTH_MISSING":
        return 0
    return None


def _resolve_from_silver_index(
    *,
    output_dir: Path,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    entries: tuple[StrategyLadderSilverIndexEntry, ...],
    window_before_ms: int,
    window_after_ms: int,
    progress_callback: Callable[[str, int], None] | None = None,
) -> StrategyLadderRawWindowExtractionResult:
    window_index = StrategyLadderWindowIndex.from_silver_entries(entries)
    window_cache = StrategyLadderWindowCache(output_dir.parent / "_window_cache")
    manifests: list[StrategyLadderRawWindowManifest] = []
    pending_manifests: list[tuple[StrategyLadderRawWindowManifest, Path]] = []
    pending_slices: list[_WindowSliceRequest] = []
    cache_requests: list[StrategyLadderWindowCacheRequest] = []
    ready_count = 0
    partial_count = 0
    for candidate in candidate_events:
        window_start_ms = max(0, candidate.resolved_timestamp_ms - window_before_ms)
        window_end_ms = candidate.resolved_timestamp_ms + window_after_ms
        trade_slice_start_ms, trade_slice_end_ms = _effective_slice_bounds(
            candidate=candidate,
            source_type="trades",
            logical_window_start_ms=window_start_ms,
            logical_window_end_ms=window_end_ms,
        )
        ohlcv_slice_start_ms, ohlcv_slice_end_ms = _effective_slice_bounds(
            candidate=candidate,
            source_type="ohlcv",
            logical_window_start_ms=window_start_ms,
            logical_window_end_ms=window_end_ms,
        )
        manifest_dir = output_dir / candidate.pair / candidate.candidate_id
        trade_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=trade_slice_start_ms,
            window_end_ms=trade_slice_end_ms,
            data_types=("trades",),
        )
        ohlcv_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=ohlcv_slice_start_ms,
            window_end_ms=ohlcv_slice_end_ms,
            data_types=("ohlcv", "klines"),
            timeframe=candidate.timeframe,
        )
        snapshot_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            data_types=("orderbook_snapshot",),
        )
        delta_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            data_types=("orderbook_delta",),
        )
        metadata_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            data_types=("metadata",),
        )
        generic_book_entries = _entries_for_candidate(
            entries=entries,
            window_index=window_index,
            pair=candidate.pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            data_types=("orderbook",),
        )
        trade_entry = trade_entries[0] if trade_entries else None
        ohlcv_entry = ohlcv_entries[0] if ohlcv_entries else None
        snapshot_entry = snapshot_entries[0] if snapshot_entries else None
        delta_entry = delta_entries[0] if delta_entries else None
        metadata_entry = metadata_entries[0] if metadata_entries else None
        generic_book_entry = generic_book_entries[0] if generic_book_entries else None
        book_entry = snapshot_entry or delta_entry or generic_book_entry
        book_levels = None
        book_status = "BOOK_DEPTH_MISSING"
        if snapshot_entry is not None:
            book_status = snapshot_entry.depth_source_status or "BOOK_DEPTH_NOT_PROVEN"
            book_levels = _levels_from_index_status(book_status)
        elif delta_entry is not None:
            book_status = "BOOK_DEPTH_NOT_PROVEN"
        elif generic_book_entry is not None:
            book_status = generic_book_entry.depth_source_status or "BOOK_DEPTH_NOT_PROVEN"
            book_levels = _levels_from_index_status(book_status)

        status, source_coverage_status = _derive_window_status(
            trade_present=trade_entry is not None,
            book_present=book_entry is not None,
            ohlcv_present=ohlcv_entry is not None,
            metadata_present=metadata_entry is not None,
            book_status=book_status,
        )

        raw_sources_used = tuple(
            dict.fromkeys(
                item.source_id
                for item in (
                    *trade_entries,
                    snapshot_entry,
                    delta_entry,
                    *ohlcv_entries,
                    metadata_entry,
                    generic_book_entry,
                )
                if item is not None
            )
        )
        raw_trade_path = trade_entry.path if trade_entry is not None else None
        if trade_entry is not None and trade_entry.path:
            trade_slice_path = manifest_dir / "trades.jsonl"
            if len(trade_entries) == 1 and trade_entry.file_hash:
                trade_slice_path = _shared_materialized_window_path(
                    output_dir,
                    source_type="trades",
                    pair=candidate.pair,
                    timeframe=candidate.timeframe or "",
                    window_start_ms=trade_slice_start_ms,
                    window_end_ms=trade_slice_end_ms,
                    depth=None,
                    source_hash=trade_entry.file_hash,
                    include_anchor_before_start=False,
                    filename="trades.jsonl",
                )
                cache_requests.append(
                    StrategyLadderWindowCacheRequest(
                        source_type="trades",
                        pair=candidate.pair,
                        timeframe=candidate.timeframe or "",
                        window_start_ms=trade_slice_start_ms,
                        window_end_ms=trade_slice_end_ms,
                        depth=None,
                        source_hash=trade_entry.file_hash,
                        include_anchor_before_start=False,
                        source_path=Path(trade_entry.path),
                        target_path=trade_slice_path,
                    )
                )
            else:
                for entry in trade_entries:
                    pending_slices.append(
                        _WindowSliceRequest(
                            source_path=Path(entry.path),
                            target_path=trade_slice_path,
                            window_start_ms=trade_slice_start_ms,
                            window_end_ms=trade_slice_end_ms,
                        )
                    )
            if len(trade_entries) == 1 and not trade_entry.file_hash:
                pending_slices.append(
                    _WindowSliceRequest(
                        source_path=Path(trade_entry.path),
                        target_path=trade_slice_path,
                        window_start_ms=trade_slice_start_ms,
                        window_end_ms=trade_slice_end_ms,
                    )
                )
            raw_trade_path = str(trade_slice_path.resolve())

        raw_book_path = None
        if snapshot_entry is not None and snapshot_entry.path:
            snapshot_slice_path = manifest_dir / "orderbook_snapshot.jsonl"
            if snapshot_entry.file_hash:
                snapshot_slice_path = _shared_materialized_window_path(
                    output_dir,
                    source_type="orderbook_snapshot",
                    pair=candidate.pair,
                    timeframe=candidate.timeframe or "",
                    window_start_ms=window_start_ms,
                    window_end_ms=window_end_ms,
                    depth=book_levels,
                    source_hash=snapshot_entry.file_hash,
                    include_anchor_before_start=True,
                    filename="orderbook_snapshot.jsonl",
                )
                cache_requests.append(
                    StrategyLadderWindowCacheRequest(
                        source_type="orderbook_snapshot",
                        pair=candidate.pair,
                        timeframe=candidate.timeframe or "",
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        depth=book_levels,
                        source_hash=snapshot_entry.file_hash,
                        include_anchor_before_start=True,
                        source_path=Path(snapshot_entry.path),
                        target_path=snapshot_slice_path,
                    )
                )
            else:
                pending_slices.append(
                    _WindowSliceRequest(
                        source_path=Path(snapshot_entry.path),
                        target_path=snapshot_slice_path,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        include_anchor_before_start=True,
                    )
                )
            raw_book_path = str(snapshot_slice_path.resolve())
        elif generic_book_entry is not None and generic_book_entry.path:
            book_slice_path = manifest_dir / "orderbook.jsonl"
            if generic_book_entry.file_hash:
                book_slice_path = _shared_materialized_window_path(
                    output_dir,
                    source_type="orderbook",
                    pair=candidate.pair,
                    timeframe=candidate.timeframe or "",
                    window_start_ms=window_start_ms,
                    window_end_ms=window_end_ms,
                    depth=book_levels,
                    source_hash=generic_book_entry.file_hash,
                    include_anchor_before_start=False,
                    filename="orderbook.jsonl",
                )
                cache_requests.append(
                    StrategyLadderWindowCacheRequest(
                        source_type="orderbook",
                        pair=candidate.pair,
                        timeframe=candidate.timeframe or "",
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        depth=book_levels,
                        source_hash=generic_book_entry.file_hash,
                        include_anchor_before_start=False,
                        source_path=Path(generic_book_entry.path),
                        target_path=book_slice_path,
                    )
                )
            else:
                pending_slices.append(
                    _WindowSliceRequest(
                        source_path=Path(generic_book_entry.path),
                        target_path=book_slice_path,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                    )
                )
            raw_book_path = str(book_slice_path.resolve())

        raw_book_delta_path = delta_entry.path if delta_entry is not None else None
        delta_slice_start_ms = window_start_ms
        # When replay evidence reconstructs book state from a snapshot anchor,
        # it must replay every subsequent delta from that anchor forward.
        # If we slice deltas only from the logical replay window start, later
        # in-window deltas can be applied on top of a stale snapshot and leave
        # the book permanently crossed/incoherent.
        if (
            snapshot_entry is not None
            and snapshot_entry.min_timestamp_ms is not None
        ):
            try:
                delta_slice_start_ms = min(
                    delta_slice_start_ms,
                    int(snapshot_entry.min_timestamp_ms),
                )
            except (TypeError, ValueError):
                delta_slice_start_ms = window_start_ms
        if delta_entry is not None and delta_entry.path:
            if len(delta_entries) == 1 and delta_entry.file_hash:
                raw_book_delta_path = str(Path(delta_entry.path).resolve())
            else:
                delta_slice_path = manifest_dir / "orderbook_delta.jsonl"
                delta_source_hash = _entries_source_hash(delta_entries)
                if delta_source_hash:
                    delta_slice_path = _shared_materialized_window_path(
                        output_dir,
                        source_type="orderbook_delta",
                        pair=candidate.pair,
                        timeframe=candidate.timeframe or "",
                        window_start_ms=delta_slice_start_ms,
                        window_end_ms=window_end_ms,
                        depth=book_levels,
                        source_hash=delta_source_hash,
                        include_anchor_before_start=delta_slice_start_ms < window_start_ms,
                        filename="orderbook_delta.jsonl",
                    )
                for entry in delta_entries:
                    pending_slices.append(
                        _WindowSliceRequest(
                            source_path=Path(entry.path),
                            target_path=delta_slice_path,
                            window_start_ms=delta_slice_start_ms,
                            window_end_ms=window_end_ms,
                        )
                    )
                raw_book_delta_path = str(delta_slice_path.resolve())

        raw_ohlcv_path = ohlcv_entry.path if ohlcv_entry is not None else None
        if ohlcv_entry is not None and ohlcv_entry.path:
            ohlcv_slice_path = manifest_dir / "ohlcv.jsonl"
            if len(ohlcv_entries) == 1 and ohlcv_entry.file_hash:
                ohlcv_slice_path = _shared_materialized_window_path(
                    output_dir,
                    source_type="ohlcv",
                    pair=candidate.pair,
                    timeframe=candidate.timeframe or "",
                    window_start_ms=ohlcv_slice_start_ms,
                    window_end_ms=ohlcv_slice_end_ms,
                    depth=None,
                    source_hash=ohlcv_entry.file_hash,
                    include_anchor_before_start=False,
                    filename="ohlcv.jsonl",
                )
                cache_requests.append(
                    StrategyLadderWindowCacheRequest(
                        source_type="ohlcv",
                        pair=candidate.pair,
                        timeframe=candidate.timeframe or "",
                        window_start_ms=ohlcv_slice_start_ms,
                        window_end_ms=ohlcv_slice_end_ms,
                        depth=None,
                        source_hash=ohlcv_entry.file_hash,
                        include_anchor_before_start=False,
                        source_path=Path(ohlcv_entry.path),
                        target_path=ohlcv_slice_path,
                    )
                )
            else:
                for entry in ohlcv_entries:
                    pending_slices.append(
                        _WindowSliceRequest(
                            source_path=Path(entry.path),
                            target_path=ohlcv_slice_path,
                            window_start_ms=ohlcv_slice_start_ms,
                            window_end_ms=ohlcv_slice_end_ms,
                        )
                    )
            if len(ohlcv_entries) == 1 and not ohlcv_entry.file_hash:
                pending_slices.append(
                    _WindowSliceRequest(
                        source_path=Path(ohlcv_entry.path),
                        target_path=ohlcv_slice_path,
                        window_start_ms=ohlcv_slice_start_ms,
                        window_end_ms=ohlcv_slice_end_ms,
                    )
                )
            raw_ohlcv_path = str(ohlcv_slice_path.resolve())

        manifest = StrategyLadderRawWindowManifest(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            timestamp_ms=candidate.resolved_timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=raw_book_path,
            raw_book_delta_path=raw_book_delta_path,
            raw_ohlcv_path=raw_ohlcv_path,
            raw_metadata_path=metadata_entry.path if metadata_entry is not None else None,
            book_depth_levels_available=book_levels,
            book_depth_source_status=book_status,
            window_extraction_status=status,
            raw_sources_used=raw_sources_used,
            trade_source_id=trade_entry.source_id if trade_entry is not None else None,
            book_snapshot_source_id=snapshot_entry.source_id if snapshot_entry is not None else None,
            book_delta_source_id=delta_entry.source_id if delta_entry is not None else None,
            ohlcv_source_id=ohlcv_entry.source_id if ohlcv_entry is not None else None,
            metadata_source_id=metadata_entry.source_id if metadata_entry is not None else None,
            source_coverage_status=source_coverage_status,
            input_data_hash=candidate.input_data_hash,
        )
        pending_manifests.append((manifest, manifest_dir))

    cache_plan = window_cache.build_plan(tuple(cache_requests))
    cached_slice_requests = tuple(
        _WindowSliceRequest(
            source_path=miss.request.source_path,
            target_path=miss.cache_path,
            window_start_ms=miss.request.window_start_ms,
            window_end_ms=miss.request.window_end_ms,
            include_anchor_before_start=miss.request.include_anchor_before_start,
        )
        for miss in cache_plan.misses
    )
    slice_requests = _dedupe_slice_requests(
        tuple((*pending_slices, *cached_slice_requests))
    )
    slice_stats = _write_window_slices(slice_requests)
    slice_counts = dict(slice_stats.slice_counts)
    slice_counts.update(window_cache.materialize_cache_hits(cache_plan))
    slice_counts.update(
        window_cache.materialize_cache_misses(
            cache_plan,
            extracted_counts=slice_counts,
        )
    )
    for manifest, manifest_dir in pending_manifests:
        trade_present = _materialized_path_has_rows(
            manifest.raw_trade_path,
            slice_counts=slice_counts,
        )
        book_snapshot_present = _materialized_path_has_rows(
            manifest.raw_book_path,
            slice_counts=slice_counts,
        )
        book_delta_present = _materialized_path_has_rows(
            manifest.raw_book_delta_path,
            slice_counts=slice_counts,
        )
        ohlcv_present = _materialized_path_has_rows(
            manifest.raw_ohlcv_path,
            slice_counts=slice_counts,
        )
        metadata_present = bool(
            manifest.raw_metadata_path and Path(manifest.raw_metadata_path).exists()
        )
        book_present = book_snapshot_present or book_delta_present
        book_status = manifest.book_depth_source_status
        book_levels = manifest.book_depth_levels_available
        if not book_snapshot_present and book_delta_present:
            book_status = "BOOK_DEPTH_NOT_PROVEN"
            book_levels = None
        elif not book_present:
            book_status = "BOOK_DEPTH_MISSING"
            book_levels = None
        status, source_coverage_status = _derive_window_status(
            trade_present=trade_present,
            book_present=book_present,
            ohlcv_present=ohlcv_present,
            metadata_present=metadata_present,
            book_status=book_status,
        )
        manifest = manifest.model_copy(
            update={
                "raw_trade_path": manifest.raw_trade_path if trade_present else None,
                "raw_book_path": manifest.raw_book_path if book_snapshot_present else None,
                "raw_book_delta_path": (
                    manifest.raw_book_delta_path if book_delta_present else None
                ),
                "raw_ohlcv_path": manifest.raw_ohlcv_path if ohlcv_present else None,
                "raw_metadata_path": (
                    manifest.raw_metadata_path if metadata_present else None
                ),
                "book_depth_levels_available": book_levels,
                "book_depth_source_status": book_status,
                "window_extraction_status": status,
                "source_coverage_status": source_coverage_status,
            }
        )
        if manifest.window_extraction_status == "RAW_WINDOW_READY":
            ready_count += 1
        elif manifest.window_extraction_status != "RAW_WINDOW_NOT_PROVEN":
            partial_count += 1
        manifest = manifest.model_copy(
            update={"artifact_hash": deterministic_payload_hash(manifest.model_dump(mode="json"))}
        )
        manifest_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(manifest_dir / "window_manifest.json", manifest.model_dump(mode="json"))
        manifests.append(manifest)
        _emit_raw_window_progress(
            progress_callback,
            ready_count=ready_count,
            partial_count=partial_count,
            manifest_count=len(manifests),
        )

    overall_status = _overall_raw_window_status(
        ready_count=ready_count,
        partial_count=partial_count,
    )
    _emit_raw_window_progress(
        progress_callback,
        ready_count=ready_count,
        partial_count=partial_count,
        manifest_count=len(manifests),
        force=True,
    )
    return StrategyLadderRawWindowExtractionResult(
        status=overall_status,
        manifests=tuple(manifests),
        indexed_lookup_metrics=window_index.metrics_snapshot(),
        window_cache_metrics=window_cache.metrics_snapshot(),
        jsonl_parsing_wall_time_s=round(slice_stats.wall_time_s, 6),
        jsonl_parsing_cpu_time_s=round(slice_stats.cpu_time_s, 6),
        jsonl_rows_processed=slice_stats.parsed_row_count,
        jsonl_files_scanned=slice_stats.files_scanned,
    )


def extract_strategy_ladder_raw_windows(
    output_dir: Path,
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_root: Path | None = None,
    silver_index_path: Path | None = None,
    silver_index_entries: tuple[StrategyLadderSilverIndexEntry, ...] = (),
    window_before_ms: int = 300_000,
    window_after_ms: int = 300_000,
    progress_callback: Callable[[str, int], None] | None = None,
) -> StrategyLadderRawWindowExtractionResult:
    """Resolve deterministic raw-window manifests for Strategy Ladder candidates."""

    output_dir.mkdir(parents=True, exist_ok=True)
    if not candidate_events:
        return StrategyLadderRawWindowExtractionResult(
            status="RAW_WINDOW_NOT_PROVEN",
            manifests=(),
            indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(),
            window_cache_metrics=StrategyLadderWindowCacheMetrics(),
        )

    loaded_index = _load_silver_index(silver_index_path, silver_index_entries)
    if loaded_index:
        return _resolve_from_silver_index(
            output_dir=output_dir,
            candidate_events=candidate_events,
            entries=loaded_index,
            window_before_ms=window_before_ms,
            window_after_ms=window_after_ms,
            progress_callback=progress_callback,
        )

    if raw_root is None:
        return StrategyLadderRawWindowExtractionResult(
            status="RAW_WINDOW_NOT_PROVEN",
            manifests=(),
            indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(),
            window_cache_metrics=StrategyLadderWindowCacheMetrics(),
        )

    window_index = StrategyLadderWindowIndex.from_raw_root(raw_root)
    manifests: list[StrategyLadderRawWindowManifest] = []
    ready_count = 0
    partial_count = 0
    for candidate in candidate_events:
        raw_trade_path = _resolve_component_path(
            candidate=candidate,
            raw_root=raw_root,
            key="raw_trade_path",
            token="trade",
            window_index=window_index,
        )
        raw_book_path = _resolve_component_path(
            candidate=candidate,
            raw_root=raw_root,
            key="raw_book_path",
            token="book",
            window_index=window_index,
        )
        raw_ohlcv_path = _resolve_component_path(
            candidate=candidate,
            raw_root=raw_root,
            key="raw_ohlcv_path",
            token="ohlcv",
            window_index=window_index,
        )
        levels = _infer_depth_levels(raw_book_path)
        book_status = _map_fallback_book_depth_status(
            levels,
            book_present=raw_book_path is not None,
        )
        status, source_coverage_status = _derive_window_status(
            trade_present=raw_trade_path is not None,
            book_present=raw_book_path is not None,
            ohlcv_present=raw_ohlcv_path is not None,
            metadata_present=True,
            book_status=book_status,
        )
        if status == "RAW_WINDOW_READY":
            ready_count += 1
        elif status != "RAW_WINDOW_NOT_PROVEN":
            partial_count += 1
        manifest = StrategyLadderRawWindowManifest(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            timestamp_ms=candidate.resolved_timestamp_ms,
            window_start_ms=max(0, candidate.resolved_timestamp_ms - window_before_ms),
            window_end_ms=candidate.resolved_timestamp_ms + window_after_ms,
            raw_trade_path=str(raw_trade_path.resolve()) if raw_trade_path is not None else None,
            raw_book_path=str(raw_book_path.resolve()) if raw_book_path is not None else None,
            raw_ohlcv_path=str(raw_ohlcv_path.resolve()) if raw_ohlcv_path is not None else None,
            book_depth_levels_available=levels,
            book_depth_source_status=book_status,
            window_extraction_status=status,
            source_coverage_status=source_coverage_status,
            input_data_hash=candidate.input_data_hash,
        )
        manifest = manifest.model_copy(
            update={"artifact_hash": deterministic_payload_hash(manifest.model_dump(mode="json"))}
        )
        manifest_dir = output_dir / candidate.pair / candidate.candidate_id
        manifest_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(manifest_dir / "window_manifest.json", manifest.model_dump(mode="json"))
        manifests.append(manifest)
        _emit_raw_window_progress(
            progress_callback,
            ready_count=ready_count,
            partial_count=partial_count,
            manifest_count=len(manifests),
        )

    overall_status = _overall_raw_window_status(
        ready_count=ready_count,
        partial_count=partial_count,
    )
    _emit_raw_window_progress(
        progress_callback,
        ready_count=ready_count,
        partial_count=partial_count,
        manifest_count=len(manifests),
        force=True,
    )
    return StrategyLadderRawWindowExtractionResult(
        status=overall_status,
        manifests=tuple(manifests),
        indexed_lookup_metrics=window_index.metrics_snapshot(),
        window_cache_metrics=StrategyLadderWindowCacheMetrics(),
    )


def load_strategy_ladder_raw_window_manifests(
    root: Path,
) -> tuple[StrategyLadderRawWindowManifest, ...]:
    """Read all window manifests below one raw-window output root."""

    manifests: list[StrategyLadderRawWindowManifest] = []
    for path in sorted(root.rglob("window_manifest.json")):
        manifests.append(
            StrategyLadderRawWindowManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        )
    return tuple(manifests)


def _overall_raw_window_status(*, ready_count: int, partial_count: int) -> str:
    if ready_count == 0 and partial_count == 0:
        return "RAW_WINDOW_NOT_PROVEN"
    if ready_count == 0 or partial_count > 0:
        return "RAW_WINDOW_PARTIAL"
    return "RAW_WINDOW_READY"


def _emit_raw_window_progress(
    progress_callback: Callable[[str, int], None] | None,
    *,
    ready_count: int,
    partial_count: int,
    manifest_count: int,
    force: bool = False,
) -> None:
    if progress_callback is None or manifest_count <= 0:
        return
    if not force and manifest_count not in {1} and manifest_count % _RAW_WINDOW_PROGRESS_EVERY != 0:
        return
    progress_callback(
        _overall_raw_window_status(
            ready_count=ready_count,
            partial_count=partial_count,
        ),
        manifest_count,
    )


__all__ = [
    "extract_strategy_ladder_raw_windows",
    "load_strategy_ladder_raw_window_manifests",
    "StrategyLadderRawWindowExtractionResult",
]
