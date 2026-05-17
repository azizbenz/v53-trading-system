"""Canonical indexed lookup support for Strategy Ladder replay windows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, Field

from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)


class StrategyLadderWindowLookupMetrics(BaseModel, frozen=True):
    """Compact metrics describing indexed replay window lookup behaviour."""

    schema_version: str = Field(default="v1", min_length=1)
    status: str = "INDEX_LOOKUP_NOT_PROVEN"
    query_count: int = Field(default=0, ge=0)
    indexed_lookup_hit_count: int = Field(default=0, ge=0)
    index_lookup_miss_count: int = Field(default=0, ge=0)
    fallback_scan_count: int = Field(default=0, ge=0)
    repeated_lookup_count: int = Field(default=0, ge=0)
    query_cache_hit_count: int = Field(default=0, ge=0)
    files_scanned: int = Field(default=0, ge=0)
    duplicate_scan_detected_count: int = Field(default=0, ge=0)
    candidate_entries_evaluated: int = Field(default=0, ge=0)
    unique_paths_indexed: int = Field(default=0, ge=0)
    silver_index_lookup_wall_time_s: float = Field(default=0.0, ge=0.0)
    filesystem_scan_wall_time_s: float = Field(default=0.0, ge=0.0)
    indexed_lookup_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)


@dataclass(frozen=True)
class _IndexedRawFile:
    path: Path
    lowered_path: str
    lowered_name: str


def _date_bucket_from_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).strftime("%Y-%m-%d")


def _date_buckets_for_window(window_start_ms: int, window_end_ms: int) -> tuple[str, ...]:
    if window_end_ms < window_start_ms:
        return ()
    start_day = datetime.fromtimestamp(window_start_ms / 1000.0, tz=UTC).date()
    end_day = datetime.fromtimestamp(window_end_ms / 1000.0, tz=UTC).date()
    buckets: list[str] = []
    current = start_day
    while current <= end_day:
        buckets.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(buckets)


def _entry_date_bucket(entry: StrategyLadderSilverIndexEntry) -> str:
    if entry.date:
        return entry.date
    if entry.min_timestamp_ms is not None:
        return _date_bucket_from_timestamp(entry.min_timestamp_ms)
    if entry.max_timestamp_ms is not None:
        return _date_bucket_from_timestamp(entry.max_timestamp_ms)
    return ""


def _entry_bucket_keys(entry: StrategyLadderSilverIndexEntry) -> tuple[str, ...]:
    keys: list[str] = [""]
    if entry.date:
        keys.append(entry.date)
    if entry.min_timestamp_ms is not None:
        keys.append(_date_bucket_from_timestamp(entry.min_timestamp_ms))
    if entry.max_timestamp_ms is not None:
        keys.append(_date_bucket_from_timestamp(entry.max_timestamp_ms))
    return tuple(dict.fromkeys(item for item in keys if item))


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
            key=lambda item: (-int(item.source_priority), item.path),
        )
    )


def _token_aliases(token: str) -> tuple[str, ...]:
    lowered = token.lower()
    if lowered == "trade":
        return ("trade", "trades")
    if lowered == "book":
        return ("book", "orderbook", "snapshot", "depth", "delta")
    if lowered == "ohlcv":
        return ("ohlcv", "kline", "klines", "candle")
    return (lowered,)


class StrategyLadderWindowIndex:
    """Deterministic indexed lookup for silver-index and fallback raw paths."""

    def __init__(
        self,
        *,
        silver_entries: tuple[StrategyLadderSilverIndexEntry, ...] = (),
        raw_root: Path | None = None,
    ) -> None:
        self._silver_by_bucket: dict[
            tuple[str, str, str, str],
            tuple[StrategyLadderSilverIndexEntry, ...],
        ] = {}
        self._raw_root = raw_root.resolve() if raw_root is not None else None
        self._raw_files: tuple[_IndexedRawFile, ...] | None = None
        self._query_cache: dict[tuple[object, ...], tuple[object, ...]] = {}
        self._query_cache_hits: set[tuple[object, ...]] = set()
        self._query_count = 0
        self._indexed_lookup_hit_count = 0
        self._index_lookup_miss_count = 0
        self._fallback_scan_count = 0
        self._repeated_lookup_count = 0
        self._query_cache_hit_count = 0
        self._files_scanned = 0
        self._duplicate_scan_detected_count = 0
        self._candidate_entries_evaluated = 0
        self._unique_paths_indexed = 0
        self._silver_index_lookup_wall_time_s = 0.0
        self._filesystem_scan_wall_time_s = 0.0
        if silver_entries:
            buckets: dict[
                tuple[str, str, str, str],
                list[StrategyLadderSilverIndexEntry],
            ] = defaultdict(list)
            unique_paths = {
                str(Path(entry.path).resolve()) for entry in silver_entries if entry.path
            }
            for entry in silver_entries:
                for bucket_key in _entry_bucket_keys(entry) or ("",):
                    buckets[
                        (
                            entry.pair,
                            entry.data_type,
                            entry.timeframe or "",
                            bucket_key,
                        )
                    ].append(entry)
            self._silver_by_bucket = {
                key: _sort_entries(tuple(value)) for key, value in buckets.items()
            }
            self._unique_paths_indexed = len(unique_paths)

    @classmethod
    def from_silver_entries(
        cls,
        entries: tuple[StrategyLadderSilverIndexEntry, ...],
    ) -> "StrategyLadderWindowIndex":
        return cls(silver_entries=entries)

    @classmethod
    def from_raw_root(cls, raw_root: Path) -> "StrategyLadderWindowIndex":
        return cls(raw_root=raw_root)

    def lookup_silver_entries(
        self,
        *,
        pair: str,
        window_start_ms: int,
        window_end_ms: int,
        data_types: tuple[str, ...],
        timeframe: str | None = None,
    ) -> tuple[StrategyLadderSilverIndexEntry, ...]:
        self._query_count += 1
        signature = (
            "silver",
            pair,
            tuple(sorted(data_types)),
            timeframe or "",
            window_start_ms,
            window_end_ms,
        )
        started = perf_counter()
        cached = self._query_cache.get(signature)
        if cached is not None:
            self._repeated_lookup_count += 1
            self._query_cache_hit_count += 1
            self._silver_index_lookup_wall_time_s += perf_counter() - started
            return tuple(cached)  # type: ignore[return-value]

        buckets = _date_buckets_for_window(window_start_ms, window_end_ms)
        timeframe_keys = ((timeframe or ""), "")
        candidates: list[StrategyLadderSilverIndexEntry] = []
        seen_paths: set[str] = set()
        for data_type in data_types:
            for timeframe_key in timeframe_keys:
                for bucket in (*buckets, ""):
                    for entry in self._silver_by_bucket.get(
                        (pair, data_type, timeframe_key, bucket),
                        (),
                    ):
                        resolved = str(Path(entry.path).resolve())
                        if resolved in seen_paths:
                            continue
                        seen_paths.add(resolved)
                        candidates.append(entry)
        self._candidate_entries_evaluated += len(candidates)
        resolved = _sort_entries(
            tuple(
                entry
                for entry in candidates
                if _entry_overlaps_window(
                    entry,
                    window_start_ms=window_start_ms,
                    window_end_ms=window_end_ms,
                )
            )
        )
        if resolved:
            self._indexed_lookup_hit_count += 1
        else:
            self._index_lookup_miss_count += 1
        self._query_cache[signature] = tuple(resolved)
        self._silver_index_lookup_wall_time_s += perf_counter() - started
        return resolved

    def lookup_raw_paths(self, *, pair: str, token: str) -> tuple[Path, ...]:
        self._query_count += 1
        signature = ("raw", pair.lower(), token.lower())
        started = perf_counter()
        cached = self._query_cache.get(signature)
        if cached is not None:
            self._repeated_lookup_count += 1
            self._query_cache_hit_count += 1
            self._filesystem_scan_wall_time_s += perf_counter() - started
            return tuple(cached)  # type: ignore[return-value]
        self._ensure_raw_files_indexed()
        lowered_pair = pair.lower()
        aliases = _token_aliases(token)
        matches = tuple(
            sorted(
                file.path.resolve()
                for file in (self._raw_files or ())
                if lowered_pair in file.lowered_path
                and any(alias in file.lowered_name for alias in aliases)
            )
        )
        self._fallback_scan_count += 1
        if matches:
            self._indexed_lookup_hit_count += 1
        else:
            self._index_lookup_miss_count += 1
        self._query_cache[signature] = tuple(matches)
        self._filesystem_scan_wall_time_s += perf_counter() - started
        return matches

    def metrics_snapshot(self) -> StrategyLadderWindowLookupMetrics:
        total_effective_queries = self._indexed_lookup_hit_count + self._index_lookup_miss_count
        hit_rate = (
            round(self._indexed_lookup_hit_count / total_effective_queries, 6)
            if total_effective_queries > 0
            else None
        )
        status = "INDEXED_WINDOW_LOOKUP_READY"
        if self._indexed_lookup_hit_count == 0 and self._index_lookup_miss_count > 0:
            status = "INDEX_LOOKUP_MISS"
        elif self._indexed_lookup_hit_count == 0 and self._fallback_scan_count > 0:
            status = "FALLBACK_SCAN_USED"
        return StrategyLadderWindowLookupMetrics(
            status=status,
            query_count=self._query_count,
            indexed_lookup_hit_count=self._indexed_lookup_hit_count,
            index_lookup_miss_count=self._index_lookup_miss_count,
            fallback_scan_count=self._fallback_scan_count,
            repeated_lookup_count=self._repeated_lookup_count,
            query_cache_hit_count=self._query_cache_hit_count,
            files_scanned=self._files_scanned,
            duplicate_scan_detected_count=self._duplicate_scan_detected_count,
            candidate_entries_evaluated=self._candidate_entries_evaluated,
            unique_paths_indexed=self._unique_paths_indexed,
            silver_index_lookup_wall_time_s=round(self._silver_index_lookup_wall_time_s, 6),
            filesystem_scan_wall_time_s=round(self._filesystem_scan_wall_time_s, 6),
            indexed_lookup_hit_rate=hit_rate,
        )

    def _ensure_raw_files_indexed(self) -> None:
        if self._raw_root is None or self._raw_files is not None:
            if self._raw_files is not None:
                self._duplicate_scan_detected_count += 1
            return
        started = perf_counter()
        indexed: list[_IndexedRawFile] = []
        files_scanned = 0
        for path in self._raw_root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            indexed.append(
                _IndexedRawFile(
                    path=resolved,
                    lowered_path=str(resolved).lower(),
                    lowered_name=resolved.name.lower(),
                )
            )
            files_scanned += 1
        self._raw_files = tuple(indexed)
        self._files_scanned += files_scanned
        self._unique_paths_indexed = max(self._unique_paths_indexed, files_scanned)
        self._filesystem_scan_wall_time_s += perf_counter() - started


__all__ = [
    "StrategyLadderWindowIndex",
    "StrategyLadderWindowLookupMetrics",
]
