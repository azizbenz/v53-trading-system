"""Strategy Ladder engine-native bridge — pont microstructure (Audit 2026-05-06 P3a).

Ce module est le pont entre les artefacts raw_windows produits par le rail
Strategy Ladder et le seam canonique microstructure
(`data_backbone.microstructure`). Il lit les fichiers JSONL bruts (trades,
orderbook snapshots + deltas, OHLCV) et calcule les 5 records canoniques
utilises par les engine runners A/B/C/D.

ARCHITECTURE BOOK (2026-05-07 fix) : OFI et QueuePressure exigent une serie
d'etats de book consecutifs. Les fichiers `orderbook_snapshot/` ne contiennent
que ~2 snapshots/jour (sparse), donc une fenetre 5min y attrape rarement
plus d'un snapshot. La solution canonique est de :
  1. Identifier le snapshot le plus recent <= window_start_ms
  2. Charger les deltas applicables (update_id > snapshot.update_id) jusqu'a window_end_ms
  3. Appliquer les deltas sequentiellement pour reconstruire l'etat book event-par-event
  4. A chaque delta dans la fenetre, capturer l'etat top-of-book / top-k

Le pont produit ainsi N etats book consecutifs (typiquement 100-1000+) au lieu
d'un unique snapshot, debloquant le calcul OFI et donnant une mesure robuste
de QueuePressure sur la fenetre.

LIMITATION P3a RESOLVED 2026-05-30 (C-wire) : le pont charge maintenant le
microstructure-aware `engine_c_structure_resolver` qui calcule les 7 champs
structurels (breakout_strength, range_quality, compression_quality,
volume_confirmation, followthrough_room, extension_pct, retrace_risk) depuis
les 5 records microstructure (OFI, VPIN, queue_pressure, kyle, realized_kernel_vol)
+ base_payload OHLCV. Le payload merge est validé contre `EngineCInput`. Le
bridge_status `ENGINE_NATIVE_BRIDGE_FULL_PATH_READY` est émis quand les 5
records sont OK et la validation EngineCInput passe. Fallback par-champ
préservé via envelope `EngineCStructureField` (research_only_if_legacy_fallback
remonté pour P5 validators).
"""

from __future__ import annotations

import gzip
import json
import zlib
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

from data_backbone.microstructure.engine_input_provenance import (
    build_engine_a_runner_microstructure_updates,
    compose_engine_c_input_payload,
    compose_engine_d_input_payload,
)
from data_backbone.microstructure.breakout_microstructure_features import (
    BreakoutMicrostructureInputs,
    FRESHNESS_FRESH,
    FRESHNESS_NOT_PROVEN,
    resolve_breakout_microstructure_features,
)
from engines.engine_c.structure_resolver_c import (
    build_engine_c_input_from_breakout_features,
)
from data_backbone.microstructure.kyle_lambda import (
    KyleLambdaRecord,
    KyleTradePoint,
    compute_kyle_lambda,
)
from data_backbone.microstructure.order_flow_imbalance import (
    OrderBookTopLevelPoint,
    OrderFlowImbalanceRecord,
    compute_order_flow_imbalance,
)
from data_backbone.microstructure.queue_pressure import (
    QueuePressureBookPoint,
    QueuePressureRecord,
    compute_queue_pressure,
)
from data_backbone.microstructure.realized_kernel_vol import (
    RealizedKernelPricePoint,
    RealizedKernelVolRecord,
    compute_realized_kernel_vol,
)
from data_backbone.microstructure.vpin import (
    VpinRecord,
    VpinTradePoint,
    compute_vpin,
)


_NS_PER_MS = 1_000_000
_DEFAULT_VPIN_BUCKETS_PER_DAY = 50  # TO_CALIBRATE: pair-specific buckets/day
# Si window etroit, on charge aussi les snapshots juste avant pour fournir au
# moins 2 points consecutifs a OFI (sinon OFI_INSUFFICIENT_BOOK).
_OFI_PREWINDOW_LOOKBACK_MS = 60_000
_ENGINE_C_TRADE_MICROSTRUCTURE_FEATURES = frozenset(
    {"kyle_lambda", "vpin", "realized_vol_current", "realized_vol_at_break"}
)
_ENGINE_C_BOOK_MICROSTRUCTURE_FEATURES = frozenset(
    {"cumulative_ofi", "queue_pressure"}
)

_MICROSTRUCTURE_RECORD_CACHE: dict[tuple[object, ...], tuple[object, ...]] = {}
_MICROSTRUCTURE_JSONL_FILE_CACHE: dict[
    tuple[str, int | None, int | None],
    tuple[dict[str, object], ...],
] = {}
_MICROSTRUCTURE_JSONL_TIME_INDEX_CACHE: dict[
    tuple[str, int | None, int | None],
    tuple[tuple[int, ...], tuple[dict[str, object], ...]],
] = {}
# Patch A2-OPT-1 (2026-05-25) — Pre-filtered delta cache by (file, base_update_id).
# Avoids O(N²) re-filtering of orderbook deltas across 1440 decisions per day.
# Each entry stores the time-indexed deltas where update_id > base_update_id,
# ready for O(log N) bisect by window_end_ms.
_MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE: dict[
    tuple[str, int | None, int | None, int],
    tuple[tuple[int, ...], tuple[dict[str, object], ...]],
] = {}
# Patch A2-OPT-4 (2026-05-26 — F16-D Pilier 0) — Progressive book state cache.
# Eliminates the O(N²) cost of `_reconstruct_book_states` rebuilding the book
# from-scratch for each decision. After processing decision k, we cache the
# (bid_book, ask_book, last_applied_uid) state at window_end_k. Decision k+1
# (with contiguous window) reuses this state and applies only the new deltas.
# Cache key: (snapshot_path_signature, delta_path_signature, base_update_id)
# Cache value: list of (last_applied_uid, last_applied_ts_ms, bid_book_dict, ask_book_dict)
# Bounded list keeps a few recent boundary states for non-monotonic access patterns.
_PROGRESSIVE_BOOK_STATE_CACHE: dict[
    tuple[tuple[str, int | None, int | None], tuple[str, int | None, int | None], int],
    list[tuple[int, int, dict[float, float], dict[float, float]]],
] = {}
_PROGRESSIVE_BOOK_STATE_CACHE_MAX_BOUNDARIES = 4
# Patch B2-RECON-SHARE (2026-06-04) — Partition-shared book-state timeline.
# B2 candidates of the same (pair, base snapshot) each reconstructed the book
# from scratch: the progressive cache key above includes the per-candidate
# delta-slice path, so it never shares (measured 0/15 hit on subset20). This
# cache holds ONE cumulative book-state timeline per (pair, base_update_id) —
# path-independent — so overlapping/nested candidate windows reuse it and return
# only their [window_start, window_end] sub-slice. Bit-identical to a from-base
# reconstruction: each timeline state is the cumulative book at a delta uid;
# filtering to the candidate window reproduces the legacy per-window emit.
_PARTITION_BOOK_TIMELINE_CACHE: "dict[tuple[str, int], _PartitionBookTimeline]" = {}
# Runtime toggle: default False so the A2 gold path (which shares the same
# Engine-C builder and is RAM-sensitive across 1440 decisions/day) keeps the
# legacy bounded-book progressive cache. The B2 runner enables it around its
# materialization loop only — there candidates of one (pair, day) reuse the
# shared timeline, and the RAM guard reclaims it under pressure.
# Monkeypatchable in tests for A/B parity.
_PARTITION_BOOK_TIMELINE_ENABLED = False
_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS: dict[str, object] = {
    "hit_count": 0,
    "miss_count": 0,
    "time_index_hit_count": 0,
    "time_index_miss_count": 0,
    "time_indexed_row_count": 0,
    "rows_loaded": 0,
    "bytes_loaded": 0,
    "paths_loaded": {},
    "invalid_file_count": 0,
    "invalid_paths": {},
    # Patch A2-OPT-1 (2026-05-25) — counters for the delta-by-base cache.
    "deltas_after_base_hit_count": 0,
    "deltas_after_base_miss_count": 0,
    # Patch B2-RECON-SHARE (2026-06-04) — partition-shared timeline counters.
    # build_count = distinct (pair, base) timelines reconstructed (one per
    # partition, NOT per candidate); reuse_count = candidates served without
    # extending; extend_deltas = gap deltas applied across all extensions.
    "partition_timeline_build_count": 0,
    "partition_timeline_reuse_count": 0,
    "partition_timeline_extend_deltas": 0,
}


def reset_microstructure_file_cache_stats(*, clear_cache: bool = True) -> None:
    """Reset the audit counters for the microstructure JSONL file cache."""

    if clear_cache:
        evict_microstructure_file_cache()
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.clear()
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.update(
        {
            "hit_count": 0,
            "miss_count": 0,
            "time_index_hit_count": 0,
            "time_index_miss_count": 0,
            "time_indexed_row_count": 0,
            "rows_loaded": 0,
            "bytes_loaded": 0,
            "paths_loaded": {},
            "invalid_file_count": 0,
            "invalid_paths": {},
            "deltas_after_base_hit_count": 0,
            "deltas_after_base_miss_count": 0,
            # Patch B2-RECON-SHARE (2026-06-04) — partition-shared timeline counters.
            "partition_timeline_build_count": 0,
            "partition_timeline_reuse_count": 0,
            "partition_timeline_extend_deltas": 0,
            # Patch A2-OPT-4 (2026-05-26) — progressive book state cache counters.
            "progressive_book_state_hit_count": 0,
            "progressive_book_state_miss_count": 0,
            "progressive_book_state_advance_deltas": 0,
            "progressive_book_state_full_reconstruct_count": 0,
            # Patch 2026-05-28 (A2 long-run guard): eviction counters let A2
            # bound memory between date partitions without hiding cumulative
            # file-cache audit stats.
            "eviction_count": 0,
            "evicted_cached_path_count": 0,
            "evicted_cached_row_count": 0,
        }
    )


def evict_microstructure_file_cache() -> dict[str, int]:
    """Clear cached microstructure rows while preserving cumulative counters."""

    cached_path_count = len(_MICROSTRUCTURE_JSONL_FILE_CACHE)
    cached_row_count = sum(len(rows) for rows in _MICROSTRUCTURE_JSONL_FILE_CACHE.values())
    _MICROSTRUCTURE_JSONL_FILE_CACHE.clear()
    _MICROSTRUCTURE_JSONL_TIME_INDEX_CACHE.clear()
    _MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE.clear()
    _PROGRESSIVE_BOOK_STATE_CACHE.clear()
    _PARTITION_BOOK_TIMELINE_CACHE.clear()
    _MICROSTRUCTURE_RECORD_CACHE.clear()
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["eviction_count"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("eviction_count") or 0) + 1
    )
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["evicted_cached_path_count"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("evicted_cached_path_count") or 0)
        + cached_path_count
    )
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["evicted_cached_row_count"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("evicted_cached_row_count") or 0)
        + cached_row_count
    )
    return {
        "evicted_cached_path_count": cached_path_count,
        "evicted_cached_row_count": cached_row_count,
    }


def get_microstructure_file_cache_stats() -> dict[str, object]:
    """Return a JSON-serializable snapshot of the microstructure file cache."""

    paths_loaded = _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("paths_loaded")
    path_payload: dict[str, object] = {}
    if isinstance(paths_loaded, dict):
        path_payload = {str(key): value for key, value in paths_loaded.items()}
    invalid_paths = _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("invalid_paths")
    invalid_path_payload: dict[str, object] = {}
    if isinstance(invalid_paths, dict):
        invalid_path_payload = {str(key): value for key, value in invalid_paths.items()}
    return {
        "cache_status": "A2_MICROSTRUCTURE_FILE_CACHE_READY",
        "hit_count": int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("hit_count") or 0),
        "miss_count": int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("miss_count") or 0),
        "file_cache_hit_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("hit_count") or 0
        ),
        "file_cache_miss_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("miss_count") or 0
        ),
        "rows_loaded": int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("rows_loaded") or 0),
        "bytes_loaded": int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("bytes_loaded") or 0),
        "invalid_file_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("invalid_file_count") or 0
        ),
        "cached_file_count": len(_MICROSTRUCTURE_JSONL_FILE_CACHE),
        "cached_path_count": len(_MICROSTRUCTURE_JSONL_FILE_CACHE),
        "cached_row_count": sum(len(rows) for rows in _MICROSTRUCTURE_JSONL_FILE_CACHE.values()),
        "time_index_hit_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_index_hit_count") or 0
        ),
        "time_index_miss_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_index_miss_count") or 0
        ),
        "time_indexed_path_count": len(_MICROSTRUCTURE_JSONL_TIME_INDEX_CACHE),
        "time_indexed_row_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_indexed_row_count") or 0
        ),
        # Patch A2-OPT-1 (2026-05-25) — deltas-by-base cache counters.
        "deltas_after_base_hit_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("deltas_after_base_hit_count") or 0
        ),
        "deltas_after_base_miss_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("deltas_after_base_miss_count") or 0
        ),
        "deltas_after_base_cache_size": len(_MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE),
        # Patch B2-RECON-SHARE (2026-06-04) — partition-shared timeline counters.
        "partition_timeline_build_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_build_count") or 0
        ),
        "partition_timeline_reuse_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_reuse_count") or 0
        ),
        "partition_timeline_extend_deltas": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_extend_deltas") or 0
        ),
        "partition_timeline_cache_size": len(_PARTITION_BOOK_TIMELINE_CACHE),
        # Patch A2-OPT-4 (2026-05-26) — progressive book state cache counters.
        "progressive_book_state_hit_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_hit_count") or 0
        ),
        "progressive_book_state_miss_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_miss_count") or 0
        ),
        "progressive_book_state_advance_deltas": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_advance_deltas") or 0
        ),
        "progressive_book_state_full_reconstruct_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_full_reconstruct_count") or 0
        ),
        "progressive_book_state_cache_size": len(_PROGRESSIVE_BOOK_STATE_CACHE),
        "eviction_count": int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("eviction_count") or 0),
        "evicted_cached_path_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("evicted_cached_path_count") or 0
        ),
        "evicted_cached_row_count": int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("evicted_cached_row_count") or 0
        ),
        "paths_loaded": path_payload,
        "invalid_paths": invalid_path_payload,
    }


def set_partition_book_timeline_enabled(enabled: bool) -> bool:
    """Patch B2-RECON-SHARE (2026-06-04) — toggle the partition-shared book
    timeline (B2 materialization only). Returns the prior value so callers can
    restore it in a ``finally`` block. A2 leaves this False (legacy progressive).
    """
    global _PARTITION_BOOK_TIMELINE_ENABLED
    prior = _PARTITION_BOOK_TIMELINE_ENABLED
    _PARTITION_BOOK_TIMELINE_ENABLED = bool(enabled)
    return prior


def evict_partition_book_timelines() -> int:
    """Patch B2-RECON-SHARE (2026-06-04) — drop cached partition book timelines
    and return the count evicted. Surgical (does not touch the JSONL file / delta
    caches), used to release B2 timeline memory after the materialization phase.
    """
    count = len(_PARTITION_BOOK_TIMELINE_CACHE)
    _PARTITION_BOOK_TIMELINE_CACHE.clear()
    return count


def _path_cache_signature(path_like: Path | str | None) -> tuple[str, int | None, int | None]:
    if path_like is None:
        return ("", None, None)
    path = Path(path_like)
    try:
        resolved = path.resolve()
        stat = resolved.stat()
    except OSError:
        return (str(path), None, None)
    return (str(resolved), stat.st_mtime_ns, stat.st_size)


def _progressive_book_state_cache_key(
    *,
    snapshot_path: Path,
    delta_path: Path,
    base_update_id: int,
) -> tuple[tuple[str, int | None, int | None], tuple[str, int | None, int | None], int]:
    return (
        _path_cache_signature(snapshot_path),
        _path_cache_signature(delta_path),
        int(base_update_id),
    )


def _latest_progressive_book_state_boundary(
    *,
    snapshot_path: Path,
    delta_path: Path,
    base_update_id: int,
    window_start_ms: int,
) -> tuple[int, int] | None:
    """Return the latest cached boundary usable before ``window_start_ms``.

    The A2 gold builder evaluates contiguous 1m decisions. Once the progressive
    cache has a cumulative book state before the next decision window, callers
    can load only deltas after that boundary instead of re-slicing and
    re-sorting every historical delta since the daily snapshot.
    """

    cache_key = _progressive_book_state_cache_key(
        snapshot_path=snapshot_path,
        delta_path=delta_path,
        base_update_id=base_update_id,
    )
    cached_entries = _PROGRESSIVE_BOOK_STATE_CACHE.get(cache_key, [])
    best: tuple[int, int] | None = None
    for last_uid, last_ts_ms, _bid_book, _ask_book in cached_entries:
        if last_ts_ms >= window_start_ms:
            continue
        if best is None or last_uid > best[0]:
            best = (last_uid, last_ts_ms)
    return best


@dataclass(frozen=True)
class EngineNativeBridgeResult:
    """Résultat audit-ready du pont microstructure pour un raw_window."""

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    # Audit 2026-05-07 fix : decompose la statistique book pour montrer la
    # reconstruction sequentielle (snapshots + deltas → states).
    n_book_snapshots_loaded: int = 0  # snapshots disponibles dans le fichier
    n_book_deltas_loaded: int = 0  # deltas charges depuis update_id du base snap
    n_book_states_reconstructed: int = 0  # etats produits dans la fenetre
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    engine_c_partial_input_payload: dict[str, object] = field(default_factory=dict)
    # Patch 2026-05-30 — engine_c structure resolver C-wire. When the 5
    # microstructure records succeed AND base_payload carries the OHLCV
    # scalars, the resolver computes the 7 structural fields and the full
    # payload is set + validated against EngineCInput.
    engine_c_full_input_payload: dict[str, object] | None = None
    engine_c_structure_resolution_summary: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for record in (
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
            )
            if record is not None
        )


def _iter_jsonl(path: Path) -> list[dict[str, object]]:
    """Charge un JSONL ligne par ligne en ignorant les lignes vides."""
    if not path.exists():
        return []
    cache_key = _path_cache_signature(path)
    cached = _MICROSTRUCTURE_JSONL_FILE_CACHE.get(cache_key)
    if cached is not None:
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["hit_count"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("hit_count") or 0) + 1
        )
        # Patch A2-OPT-5 (2026-05-26 — F16-D Pilier 1) — Drop the defensive
        # `[dict(row) for row in cached]` deep copy on cache hit. The cached
        # value is already an immutable tuple of dicts produced at miss time;
        # the previous per-hit copy was the dominant source of the 24 GB
        # memory leak observed in B1 engine_native_materialization across
        # 200 candidates (Python GC unable to free 888K-row dict copies fast
        # enough). All downstream consumers (`_jsonl_time_index`,
        # `_load_book_deltas_in_window_with_lookback`, `_load_trades_in_window`)
        # either build their own copies or read row fields without mutation,
        # so returning a shallow `list(cached)` is safe. This converts a
        # 200 × O(N) copy storm into 200 × O(1) shared references.
        return list(cached)
    out: list[dict[str, object]] = []
    if path.suffix.lower() == ".parquet":
        import pyarrow.parquet as _pq
        out = _pq.read_table(path).to_pylist()
    else:
        opener = (
            lambda: gzip.open(path, "rt", encoding="utf-8-sig")
            if str(path).endswith(".gz")
            else path.open("r", encoding="utf-8-sig")
        )
        try:
            with opener() as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        out.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        continue
        except (EOFError, OSError, gzip.BadGzipFile, zlib.error) as exc:
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["invalid_file_count"] = (
                int(
                    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get(
                        "invalid_file_count"
                    )
                    or 0
                )
                + 1
            )
            invalid_paths = _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.setdefault(
                "invalid_paths",
                {},
            )
            if isinstance(invalid_paths, dict):
                invalid_paths[str(path)] = type(exc).__name__
            out = []
    cached_rows = tuple(dict(row) for row in out)
    _MICROSTRUCTURE_JSONL_FILE_CACHE[cache_key] = cached_rows
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["miss_count"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("miss_count") or 0) + 1
    )
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["rows_loaded"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("rows_loaded") or 0)
        + len(cached_rows)
    )
    if cache_key[2] is not None:
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["bytes_loaded"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("bytes_loaded") or 0)
            + int(cache_key[2])
        )
    paths_loaded = _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.setdefault("paths_loaded", {})
    if isinstance(paths_loaded, dict):
        paths_loaded[str(cache_key[0])] = {
            "mtime_ns": cache_key[1],
            "bytes": cache_key[2],
            "rows": len(cached_rows),
        }
    return [dict(row) for row in cached_rows]


def _row_timestamp_ms(row: dict[str, object]) -> int | None:
    ts = row.get("timestamp_ms")
    if not isinstance(ts, (int, float)):
        return None
    return int(ts)


def _jsonl_time_index(
    path: Path,
) -> tuple[tuple[int, ...], tuple[dict[str, object], ...]]:
    cache_key = _path_cache_signature(path)
    cached = _MICROSTRUCTURE_JSONL_TIME_INDEX_CACHE.get(cache_key)
    if cached is not None:
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["time_index_hit_count"] = (
            int(
                _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_index_hit_count")
                or 0
            )
            + 1
        )
        return cached
    rows = _iter_jsonl(path)
    indexed_pairs = sorted(
        ((ts, dict(row)) for row in rows if (ts := _row_timestamp_ms(row)) is not None),
        key=lambda item: item[0],
    )
    timestamps = tuple(ts for ts, _row in indexed_pairs)
    indexed_rows = tuple(row for _ts, row in indexed_pairs)
    cached_index = (timestamps, indexed_rows)
    _MICROSTRUCTURE_JSONL_TIME_INDEX_CACHE[cache_key] = cached_index
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["time_index_miss_count"] = (
        int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_index_miss_count")
            or 0
        )
        + 1
    )
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["time_indexed_row_count"] = (
        int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("time_indexed_row_count")
            or 0
        )
        + len(indexed_rows)
    )
    return cached_index


def _iter_jsonl_timestamp_window(
    path: Path,
    *,
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
) -> list[dict[str, object]]:
    if not path.exists():
        return []
    timestamps, rows = _jsonl_time_index(path)
    left = 0 if window_start_ms is None else bisect_left(timestamps, int(window_start_ms))
    right = len(rows) if window_end_ms is None else bisect_right(timestamps, int(window_end_ms))
    return [dict(row) for row in rows[left:right]]


def _load_trades_in_window(
    raw_trade_path: Path,
    *,
    window_start_ms: int,
    window_end_ms: int,
) -> list[dict[str, object]]:
    """Charge les trades dont le timestamp_ms tombe dans [window_start_ms, window_end_ms]."""
    return _iter_jsonl_timestamp_window(
        raw_trade_path,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
    )


def _trade_flow_score_from_window(trades: list[dict[str, object]]) -> float | None:
    buy_qty = 0.0
    sell_qty = 0.0
    for row in trades:
        side = str(row.get("side") or "").strip().lower()
        try:
            qty = float(row.get("qty") or row.get("quantity") or 0.0)
        except (TypeError, ValueError):
            continue
        if qty <= 0.0:
            continue
        if side == "buy":
            buy_qty += qty
        elif side == "sell":
            sell_qty += qty
    total_qty = buy_qty + sell_qty
    if total_qty <= 0.0:
        return None
    imbalance = (buy_qty - sell_qty) / total_qty
    return max(0.0, min(1.0, 0.5 + 0.5 * imbalance))


def _resolve_book_delta_path(
    raw_book_path: Path | str,
    raw_book_delta_path: Path | str | None,
) -> Path | None:
    """Retourne le chemin vers le fichier deltas orderbook.

    Si `raw_book_delta_path` est fourni, l'utilise directement. Sinon, le derive
    depuis `raw_book_path` selon la convention silver canonique (remplacer
    `orderbook_snapshot` par `orderbook_delta` dans le path). Retourne None si
    aucune derivation n'est possible.
    """
    if raw_book_delta_path:
        return Path(raw_book_delta_path)
    if not raw_book_path:
        return None
    snap_str = str(raw_book_path)
    if "orderbook_snapshot" not in snap_str:
        return None
    derived = snap_str.replace("orderbook_snapshot", "orderbook_delta")
    return Path(derived)


def _select_base_snapshot(
    snapshots: list[dict[str, object]],
    *,
    window_start_ms: int,
) -> dict[str, object] | None:
    """Selectionne le snapshot le plus recent dont timestamp_ms <= window_start_ms.

    Si aucun snapshot avant la fenetre, retourne le plus recent disponible
    (fallback degrade) — la reconstruction reste possible mais part d'un etat
    posterieur a la fenetre, ce qui donnera des resultats partiels.
    """
    if not snapshots:
        return None
    eligible = [
        snap
        for snap in snapshots
        if isinstance(snap.get("timestamp_ms"), (int, float))
        and int(snap["timestamp_ms"]) <= window_start_ms
    ]
    if eligible:
        return max(eligible, key=lambda s: int(s["timestamp_ms"]))
    # Fallback : tous les snapshots sont apres window_start_ms
    return min(
        snapshots,
        key=lambda s: int(s.get("timestamp_ms") or 0),
    )


@dataclass(frozen=True)
class _BookState:
    """Etat instantane top-of-book + top-k apres application d'un delta."""

    timestamp_ms: int
    update_id: int
    bid_levels: tuple[tuple[float, float], ...]  # (price, size) tries desc par price
    ask_levels: tuple[tuple[float, float], ...]  # (price, size) tries asc par price


def _reconstruct_book_states_with_progressive_cache(
    *,
    snapshot_path: Path,
    delta_path: Path,
    base_snapshot: dict[str, object],
    deltas: list[dict[str, object]],
    window_start_ms: int,
    window_end_ms: int,
    top_k: int = 20,
) -> list[_BookState]:
    """Patch A2-OPT-4 (2026-05-26 — F16-D Pilier 0) — Incremental book reconstruction.

    Wraps :func:`_reconstruct_book_states` with a progressive cache that
    preserves the prior cumulative book state across decisions. When decisions
    arrive in monotonic order (typical strategy_ladder usage), only the new
    deltas between two consecutive window_end_ms boundaries are applied,
    converting the per-day cost from O(N²) to O(N).

    The function signature mirrors :func:`_reconstruct_book_states` except
    for the additional path signatures used as cache keys. When the cache
    miss path is taken (first call, non-monotonic access, evicted entry),
    behaviour is identical to the original full-reconstruction logic.
    """
    base_update_id = int(base_snapshot.get("update_id") or 0)
    cache_key = _progressive_book_state_cache_key(
        snapshot_path=snapshot_path,
        delta_path=delta_path,
        base_update_id=base_update_id,
    )
    cached_entries = _PROGRESSIVE_BOOK_STATE_CACHE.get(cache_key, [])

    # Pick the most recent cached boundary whose last_applied_ts_ms < window_start_ms.
    # That state is the correct starting point because all deltas it has applied
    # are strictly before our window, so we won't double-apply anything.
    starting_state: tuple[int, int, dict[float, float], dict[float, float]] | None = None
    for entry in cached_entries:
        last_uid_entry, last_ts_entry, _bid, _ask = entry
        if last_ts_entry < window_start_ms:
            if starting_state is None or last_uid_entry > starting_state[0]:
                starting_state = entry

    if starting_state is not None:
        # Cache hit — clone the cached books (so we don't mutate the cache entry)
        bid_book: dict[float, float] = dict(starting_state[2])
        ask_book: dict[float, float] = dict(starting_state[3])
        last_applied_uid = starting_state[0]
        last_applied_ts = starting_state[1]
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["progressive_book_state_hit_count"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_hit_count") or 0) + 1
        )
    else:
        # Cache miss — initialise from base snapshot
        bid_book = {}
        ask_book = {}
        for level in base_snapshot.get("bids") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size > 0.0:
                bid_book[price] = size
        for level in base_snapshot.get("asks") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size > 0.0:
                ask_book[price] = size
        last_applied_uid = base_update_id
        last_applied_ts = -1
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["progressive_book_state_miss_count"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_miss_count") or 0) + 1
        )

    def _delta_update_id(d: dict[str, object]) -> int:
        try:
            return int(d.get("update_id") or 0)
        except (TypeError, ValueError):
            return 0

    sorted_deltas = sorted(deltas, key=_delta_update_id)
    states: list[_BookState] = []
    advance_count = 0

    for delta in sorted_deltas:
        delta_uid = _delta_update_id(delta)
        if delta_uid <= last_applied_uid:
            continue
        ts = delta.get("timestamp_ms")
        if not isinstance(ts, (int, float)):
            continue
        delta_ts_ms = int(ts)
        if delta_ts_ms > window_end_ms:
            break

        for level in delta.get("bids") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                bid_book.pop(price, None)
            else:
                bid_book[price] = size
        for level in delta.get("asks") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                ask_book.pop(price, None)
            else:
                ask_book[price] = size

        last_applied_uid = delta_uid
        last_applied_ts = delta_ts_ms
        advance_count += 1

        if delta_ts_ms < window_start_ms:
            continue

        sorted_bids = sorted(bid_book.items(), key=lambda x: -x[0])[:top_k]
        sorted_asks = sorted(ask_book.items(), key=lambda x: x[0])[:top_k]
        if not sorted_bids or not sorted_asks:
            continue
        states.append(
            _BookState(
                timestamp_ms=delta_ts_ms,
                update_id=delta_uid,
                bid_levels=tuple(sorted_bids),
                ask_levels=tuple(sorted_asks),
            )
        )

    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["progressive_book_state_advance_deltas"] = (
        int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("progressive_book_state_advance_deltas") or 0)
        + advance_count
    )

    # Persist the final cumulative state at window_end_ms boundary. Keep a
    # bounded ring of recent boundaries so non-monotonic access still gets
    # a closer-than-snapshot starting state.
    if last_applied_ts >= 0:
        boundary_entry = (
            last_applied_uid,
            last_applied_ts,
            dict(bid_book),
            dict(ask_book),
        )
        # Deduplicate by last_applied_uid (idempotent re-runs).
        cached_entries = [
            entry for entry in cached_entries if entry[0] != last_applied_uid
        ]
        cached_entries.append(boundary_entry)
        # Bound: keep newest by last_applied_uid (advancing monotonically).
        cached_entries.sort(key=lambda e: e[0])
        if len(cached_entries) > _PROGRESSIVE_BOOK_STATE_CACHE_MAX_BOUNDARIES:
            cached_entries = cached_entries[-_PROGRESSIVE_BOOK_STATE_CACHE_MAX_BOUNDARIES:]
        _PROGRESSIVE_BOOK_STATE_CACHE[cache_key] = cached_entries

    return states


class _PartitionBookTimeline:
    """Patch B2-RECON-SHARE (2026-06-04) — shared cumulative book-state timeline
    for one ``(pair, base snapshot)`` partition.

    Emits a ``_BookState`` for every applied delta (the timeline's own
    window_start is -inf); each candidate then takes the
    ``[window_start, window_end]`` sub-slice. Parity invariant: every emitted
    state is the cumulative book at a delta ``update_id`` — identical to
    :func:`_reconstruct_book_states` — so filtering reproduces the legacy
    per-window emit exactly, for nested/overlapping B2 windows alike.
    """

    __slots__ = ("bid_book", "ask_book", "last_uid", "covered_ts", "states")

    def __init__(
        self,
        bid_book: dict[float, float],
        ask_book: dict[float, float],
        last_uid: int,
    ) -> None:
        self.bid_book = bid_book
        self.ask_book = ask_book
        self.last_uid = last_uid
        self.covered_ts = -1
        self.states: list[_BookState] = []

    @classmethod
    def from_base(cls, base_snapshot: dict[str, object]) -> "_PartitionBookTimeline":
        bid_book: dict[float, float] = {}
        ask_book: dict[float, float] = {}
        for level in base_snapshot.get("bids") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size > 0.0:
                bid_book[price] = size
        for level in base_snapshot.get("asks") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size > 0.0:
                ask_book[price] = size
        return cls(bid_book, ask_book, int(base_snapshot.get("update_id") or 0))

    def extend(
        self,
        deltas: list[dict[str, object]],
        *,
        window_end_ms: int,
        top_k: int,
    ) -> None:
        """Apply gap deltas (``update_id > last_uid`` and ``ts <= window_end_ms``).

        Mirrors the apply+emit loop of :func:`_reconstruct_book_states` exactly so
        the partition path stays byte-parity with the legacy reconstruction.
        """

        def _delta_update_id(d: dict[str, object]) -> int:
            try:
                return int(d.get("update_id") or 0)
            except (TypeError, ValueError):
                return 0

        for delta in sorted(deltas, key=_delta_update_id):
            delta_uid = _delta_update_id(delta)
            if delta_uid <= self.last_uid:
                continue
            ts = delta.get("timestamp_ms")
            if not isinstance(ts, (int, float)):
                continue
            delta_ts_ms = int(ts)
            if delta_ts_ms > window_end_ms:
                break
            for level in delta.get("bids") or []:
                try:
                    price = float(level[0])
                    size = float(level[1])
                except (TypeError, ValueError, IndexError):
                    continue
                if size <= 0.0:
                    self.bid_book.pop(price, None)
                else:
                    self.bid_book[price] = size
            for level in delta.get("asks") or []:
                try:
                    price = float(level[0])
                    size = float(level[1])
                except (TypeError, ValueError, IndexError):
                    continue
                if size <= 0.0:
                    self.ask_book.pop(price, None)
                else:
                    self.ask_book[price] = size
            self.last_uid = delta_uid
            self.covered_ts = delta_ts_ms
            sorted_bids = sorted(self.bid_book.items(), key=lambda x: -x[0])[:top_k]
            sorted_asks = sorted(self.ask_book.items(), key=lambda x: x[0])[:top_k]
            if not sorted_bids or not sorted_asks:
                continue
            self.states.append(
                _BookState(
                    timestamp_ms=delta_ts_ms,
                    update_id=delta_uid,
                    bid_levels=tuple(sorted_bids),
                    ask_levels=tuple(sorted_asks),
                )
            )

    def window_slice(
        self, window_start_ms: int, window_end_ms: int
    ) -> list[_BookState]:
        return [
            state
            for state in self.states
            if window_start_ms <= state.timestamp_ms <= window_end_ms
        ]


def _partition_shared_book_states(
    *,
    pair: str,
    raw_book_path: Path | str,
    delta_path: Path,
    base_snapshot: dict[str, object],
    window_start_ms: int,
    window_end_ms: int,
    top_k: int = 20,
) -> tuple[list[_BookState], int]:
    """Patch B2-RECON-SHARE (2026-06-04) — reconstruct ``[ws, we]`` book states
    via a ``(pair, base_update_id)`` partition-shared timeline.

    Returns ``(window_states, gap_deltas_loaded)``. Candidates of the same
    partition reuse one cumulative timeline instead of re-walking the day's
    deltas each (the measured B2 redundancy: 0/15 progressive-cache hit on
    subset20). When :data:`_PARTITION_BOOK_TIMELINE_ENABLED` is False, falls back
    to the legacy per-candidate progressive path (rollback seam).
    """
    base_update_id = int(base_snapshot.get("update_id") or 0)

    if not _PARTITION_BOOK_TIMELINE_ENABLED:
        boundary = _latest_progressive_book_state_boundary(
            snapshot_path=Path(raw_book_path),
            delta_path=delta_path,
            base_update_id=base_update_id,
            window_start_ms=window_start_ms,
        )
        deltas = _load_book_deltas_in_window_with_lookback(
            delta_path,
            base_update_id=base_update_id,
            window_end_ms=window_end_ms,
            window_start_ms=boundary[1] if boundary is not None else None,
            after_update_id=boundary[0] if boundary is not None else None,
        )
        states = _reconstruct_book_states_with_progressive_cache(
            snapshot_path=Path(raw_book_path),
            delta_path=delta_path,
            base_snapshot=base_snapshot,
            deltas=deltas,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            top_k=top_k,
        )
        return states, len(deltas)

    key = (pair, base_update_id)
    timeline = _PARTITION_BOOK_TIMELINE_CACHE.get(key)
    if timeline is None:
        timeline = _PartitionBookTimeline.from_base(base_snapshot)
        _PARTITION_BOOK_TIMELINE_CACHE[key] = timeline
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["partition_timeline_build_count"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_build_count") or 0)
            + 1
        )

    gap_deltas_loaded = 0
    if window_end_ms > timeline.covered_ts:
        gap_deltas = _load_book_deltas_in_window_with_lookback(
            delta_path,
            base_update_id=base_update_id,
            window_end_ms=window_end_ms,
            window_start_ms=timeline.covered_ts if timeline.covered_ts >= 0 else None,
            after_update_id=(
                timeline.last_uid if timeline.last_uid != base_update_id else None
            ),
        )
        gap_deltas_loaded = len(gap_deltas)
        timeline.extend(gap_deltas, window_end_ms=window_end_ms, top_k=top_k)
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["partition_timeline_extend_deltas"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_extend_deltas") or 0)
            + gap_deltas_loaded
        )
    else:
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["partition_timeline_reuse_count"] = (
            int(_MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get("partition_timeline_reuse_count") or 0)
            + 1
        )

    return timeline.window_slice(window_start_ms, window_end_ms), gap_deltas_loaded


def _reconstruct_book_states(
    *,
    base_snapshot: dict[str, object],
    deltas: list[dict[str, object]],
    window_start_ms: int,
    window_end_ms: int,
    top_k: int = 20,
) -> list[_BookState]:
    """Reconstruit la sequence d'etats book par application sequentielle des deltas.

    Convention orderbook (Bybit/standard) :
      - delta[price, size] avec size > 0 : level mis a jour ou ajoute
      - delta[price, "0"] ou size == 0 : level supprime
      - update_id strictement croissant ; on ne traite que les deltas dont
        update_id > base_snapshot.update_id

    Emet un _BookState seulement pour les deltas dont timestamp_ms est dans
    [window_start_ms, window_end_ms], mais APPLIQUE tous les deltas posterieurs
    au snapshot (y compris pre-fenetre) pour rester aligne sur l'etat reel.
    """
    bid_book: dict[float, float] = {}
    ask_book: dict[float, float] = {}
    base_update_id = int(base_snapshot.get("update_id") or 0)

    # Charger l'etat initial depuis le snapshot
    for level in base_snapshot.get("bids") or []:
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            bid_book[price] = size
    for level in base_snapshot.get("asks") or []:
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            ask_book[price] = size

    # Trier les deltas par update_id croissant
    def _delta_update_id(d: dict[str, object]) -> int:
        try:
            return int(d.get("update_id") or 0)
        except (TypeError, ValueError):
            return 0

    sorted_deltas = sorted(deltas, key=_delta_update_id)
    states: list[_BookState] = []

    for delta in sorted_deltas:
        delta_update_id = _delta_update_id(delta)
        if delta_update_id <= base_update_id:
            continue
        ts = delta.get("timestamp_ms")
        if not isinstance(ts, (int, float)):
            continue
        delta_ts_ms = int(ts)
        if delta_ts_ms > window_end_ms:
            break

        # Appliquer le delta
        for level in delta.get("bids") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                bid_book.pop(price, None)
            else:
                bid_book[price] = size
        for level in delta.get("asks") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                ask_book.pop(price, None)
            else:
                ask_book[price] = size

        # Capturer un etat seulement si le delta est dans la fenetre
        if delta_ts_ms < window_start_ms:
            continue

        # Top-k ordonne (bids desc, asks asc)
        sorted_bids = sorted(bid_book.items(), key=lambda x: -x[0])[:top_k]
        sorted_asks = sorted(ask_book.items(), key=lambda x: x[0])[:top_k]
        if not sorted_bids or not sorted_asks:
            continue
        states.append(
            _BookState(
                timestamp_ms=delta_ts_ms,
                update_id=delta_update_id,
                bid_levels=tuple(sorted_bids),
                ask_levels=tuple(sorted_asks),
            )
        )

    return states


def _load_book_snapshots(raw_book_path: Path) -> list[dict[str, object]]:
    """Charge tous les snapshots du fichier (n'est pas filtre par fenetre :
    on a besoin du snapshot le plus recent <= window_start_ms)."""
    return _iter_jsonl(raw_book_path)


def _deltas_after_base_index(
    raw_book_delta_path: Path,
    *,
    base_update_id: int,
) -> tuple[tuple[int, ...], tuple[dict[str, object], ...]]:
    """Patch A2-OPT-1 (2026-05-25) — Cached time-index of deltas where update_id > base_update_id.

    The previous implementation re-iterated all deltas-up-to-window_end for every
    decision row, producing an O(N²) blowup (1440 decisions × up to 888K deltas).
    Since `base_update_id` is constant across all decisions of a day (one snapshot
    baseline), we pre-filter the deltas by ``update_id > base_update_id`` once,
    then bisect by ``window_end_ms`` per decision in O(log N).

    Returns a (timestamps, rows) tuple suitable for ``bisect_right``.
    """
    cache_signature = _path_cache_signature(raw_book_delta_path)
    cache_key = (cache_signature[0], cache_signature[1], cache_signature[2], int(base_update_id))
    cached = _MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE.get(cache_key)
    if cached is not None:
        _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["deltas_after_base_hit_count"] = (
            int(
                _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get(
                    "deltas_after_base_hit_count"
                )
                or 0
            )
            + 1
        )
        return cached
    timestamps_all, rows_all = _jsonl_time_index(raw_book_delta_path)
    filtered_pairs: list[tuple[int, dict[str, object]]] = []
    for ts, row in zip(timestamps_all, rows_all):
        try:
            uid = int(row.get("update_id") or 0)
        except (TypeError, ValueError):
            continue
        if uid > base_update_id:
            filtered_pairs.append((ts, row))
    filtered_timestamps = tuple(ts for ts, _row in filtered_pairs)
    filtered_rows = tuple(row for _ts, row in filtered_pairs)
    cached_index = (filtered_timestamps, filtered_rows)
    _MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE[cache_key] = cached_index
    _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS["deltas_after_base_miss_count"] = (
        int(
            _MICROSTRUCTURE_JSONL_FILE_CACHE_STATS.get(
                "deltas_after_base_miss_count"
            )
            or 0
        )
        + 1
    )
    return cached_index


def _load_book_deltas_in_window_with_lookback(
    raw_book_delta_path: Path,
    *,
    base_update_id: int,
    window_end_ms: int,
    window_start_ms: int | None = None,
    after_update_id: int | None = None,
) -> list[dict[str, object]]:
    """Charge les deltas dont update_id > base_update_id et timestamp_ms <= window_end_ms.

    Patch A2-OPT-1 (2026-05-25) — Refactored to use the cached
    ``_deltas_after_base_index`` so the (path, base_update_id) filter is paid
    once per day instead of once per decision. Slicing by ``window_end_ms`` uses
    ``bisect_right`` for O(log N) per call.

    Patch A2-OPT-6 (2026-05-26) — when a progressive book-state boundary is
    already available, callers pass ``window_start_ms`` and ``after_update_id``
    so this function returns only the new deltas after that boundary. This
    removes the remaining O(N²) prefix-copy/sort loop on full A2 gold builds.
    """
    if not raw_book_delta_path.exists():
        return []
    timestamps, rows = _deltas_after_base_index(
        raw_book_delta_path,
        base_update_id=base_update_id,
    )
    if not rows:
        return []
    left = 0
    if window_start_ms is not None:
        left = bisect_right(timestamps, int(window_start_ms))
    right = bisect_right(timestamps, int(window_end_ms))
    if right <= left:
        return []
    update_id_floor = max(int(base_update_id), int(after_update_id or base_update_id))
    sliced_rows = rows[left:right]
    if update_id_floor <= int(base_update_id):
        # Return list copy so downstream consumers may mutate without affecting cache.
        return list(sliced_rows)
    filtered_rows: list[dict[str, object]] = []
    for row in sliced_rows:
        try:
            uid = int(row.get("update_id") or 0)
        except (TypeError, ValueError):
            continue
        if uid > update_id_floor:
            filtered_rows.append(row)
    return filtered_rows


def _build_kyle_trade_points(
    trades: list[dict[str, object]],
) -> list[KyleTradePoint]:
    points: list[KyleTradePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
            volume = float(row.get("qty") or row.get("volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0 or volume <= 0.0:
            continue
        points.append(
            KyleTradePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
                volume=volume,
                mid_price=None,
            )
        )
    return points


def _build_vpin_trade_points(
    trades: list[dict[str, object]],
) -> list[VpinTradePoint]:
    points: list[VpinTradePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
            volume = float(row.get("qty") or row.get("volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0 or volume <= 0.0:
            continue
        points.append(
            VpinTradePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
                volume=volume,
            )
        )
    return points


def _book_state_to_ofi_point(state: _BookState) -> OrderBookTopLevelPoint | None:
    """Extrait le top-of-book d'un _BookState reconstruit pour OFI."""
    if not state.bid_levels or not state.ask_levels:
        return None
    bid_price, bid_size = state.bid_levels[0]
    ask_price, ask_size = state.ask_levels[0]
    if bid_price <= 0.0 or ask_price <= 0.0 or ask_price < bid_price:
        return None
    try:
        return OrderBookTopLevelPoint(
            timestamp_ns=state.timestamp_ms * _NS_PER_MS,
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
        )
    except Exception:  # noqa: BLE001
        return None


def _book_state_to_queue_pressure_point(
    state: _BookState,
    *,
    top_k: int = 5,
) -> QueuePressureBookPoint | None:
    """Extrait top-k bid/ask sizes d'un _BookState pour QueuePressure."""
    if not state.bid_levels or not state.ask_levels:
        return None
    try:
        bid_sizes = tuple(size for _, size in state.bid_levels[:top_k])
        ask_sizes = tuple(size for _, size in state.ask_levels[:top_k])
    except (TypeError, ValueError):
        return None
    if not bid_sizes or not ask_sizes:
        return None
    return QueuePressureBookPoint(
        timestamp_ns=state.timestamp_ms * _NS_PER_MS,
        bid_sizes=bid_sizes,
        ask_sizes=ask_sizes,
    )


def _build_realized_kernel_price_points(
    trades: list[dict[str, object]],
) -> list[RealizedKernelPricePoint]:
    points: list[RealizedKernelPricePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0:
            continue
        points.append(
            RealizedKernelPricePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
            )
        )
    return points


def _finite_record_value(record: object | None) -> float | None:
    if record is None:
        return None
    value = getattr(record, "value", None)
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if isfinite(numeric) else None


def build_engine_c_requested_microstructure_features_from_window(
    *,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    requested_feature_names: tuple[str, ...] | set[str] | frozenset[str],
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> dict[str, object]:
    """Build only requested Engine C microstructure scalar features.

    This is an A2 performance seam. It reuses the canonical calculators but
    avoids computing unrelated microstructure records for each gold row.
    """

    requested = {
        str(feature_name)
        for feature_name in requested_feature_names
        if str(feature_name)
        in (
            _ENGINE_C_TRADE_MICROSTRUCTURE_FEATURES
            | _ENGINE_C_BOOK_MICROSTRUCTURE_FEATURES
        )
    }
    if not requested:
        return {}

    values: dict[str, object] = {}
    needs_trade_features = bool(requested & _ENGINE_C_TRADE_MICROSTRUCTURE_FEATURES)
    needs_book_features = bool(requested & _ENGINE_C_BOOK_MICROSTRUCTURE_FEATURES)

    trades_raw: list[dict[str, object]] = []
    if needs_trade_features and raw_trade_path:
        trades_raw = _load_trades_in_window(
            Path(raw_trade_path),
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )

    if "kyle_lambda" in requested:
        kyle_points = _build_kyle_trade_points(trades_raw)
        if len(kyle_points) >= 2:
            try:
                window_seconds = max(1.0, (window_end_ms - window_start_ms) / 1000.0)
                record = compute_kyle_lambda(
                    kyle_points,
                    pair=pair,
                    window_seconds=window_seconds,
                    bucket_seconds=min(60.0, window_seconds),
                )
                value = _finite_record_value(record)
                if value is not None:
                    values["kyle_lambda"] = value
            except Exception:  # noqa: BLE001 - missing feature stays explicit.
                pass

    if "vpin" in requested:
        vpin_points = _build_vpin_trade_points(trades_raw)
        if vpin_points:
            try:
                record = compute_vpin(
                    vpin_points,
                    pair=pair,
                    buckets_per_day=vpin_buckets_per_day,
                    allow_derived_daily_volume=True,
                )
                value = _finite_record_value(record)
                if value is not None:
                    values["vpin"] = value
            except Exception:  # noqa: BLE001
                pass

    if {"realized_vol_current", "realized_vol_at_break"} & requested:
        rk_points = _build_realized_kernel_price_points(trades_raw)
        if len(rk_points) >= 3:
            try:
                record = compute_realized_kernel_vol(rk_points, pair=pair)
                value = _finite_record_value(record)
                if value is not None:
                    if "realized_vol_current" in requested:
                        values["realized_vol_current"] = value
                    if "realized_vol_at_break" in requested:
                        values["realized_vol_at_break"] = value
            except Exception:  # noqa: BLE001
                pass

    if not needs_book_features or not raw_book_path:
        return values

    try:
        snapshots = _load_book_snapshots(Path(raw_book_path))
        base_snap = _select_base_snapshot(snapshots, window_start_ms=window_start_ms)
        if base_snap is None:
            return values
        delta_path = _resolve_book_delta_path(raw_book_path, raw_book_delta_path)
        if delta_path is None or not delta_path.exists():
            return values
        base_update_id = int(base_snap.get("update_id") or 0)
        progressive_boundary = _latest_progressive_book_state_boundary(
            snapshot_path=Path(raw_book_path),
            delta_path=delta_path,
            base_update_id=base_update_id,
            window_start_ms=window_start_ms,
        )
        deltas = _load_book_deltas_in_window_with_lookback(
            delta_path,
            base_update_id=base_update_id,
            window_end_ms=window_end_ms,
            window_start_ms=(
                progressive_boundary[1] if progressive_boundary is not None else None
            ),
            after_update_id=(
                progressive_boundary[0] if progressive_boundary is not None else None
            ),
        )
        # Patch A2-OPT-4 (2026-05-26) — Use the progressive cache wrapper so
        # consecutive decisions in the same day reuse the cumulative book state
        # instead of re-applying all deltas-since-snapshot from scratch.
        book_states = _reconstruct_book_states_with_progressive_cache(
            snapshot_path=Path(raw_book_path),
            delta_path=delta_path,
            base_snapshot=base_snap,
            deltas=deltas,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            top_k=20,
        )
    except OSError:
        return values

    if "cumulative_ofi" in requested:
        ofi_points = [
            point
            for state in book_states
            if (point := _book_state_to_ofi_point(state)) is not None
        ]
        if len(ofi_points) >= 2:
            try:
                record = compute_order_flow_imbalance(ofi_points, pair=pair)
                value = _finite_record_value(record)
                if value is not None:
                    values["cumulative_ofi"] = value
            except Exception:  # noqa: BLE001
                pass

    if "queue_pressure" in requested and book_states:
        queue_point = _book_state_to_queue_pressure_point(book_states[-1], top_k=5)
        if queue_point is not None:
            try:
                record = compute_queue_pressure(queue_point, pair=pair, top_k=5)
                value = _finite_record_value(record)
                if value is not None:
                    values["queue_pressure"] = value
            except Exception:  # noqa: BLE001
                pass

    return values


def build_engine_c_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None = None,
    base_payload: dict[str, object] | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineNativeBridgeResult:
    """Pont microstructure pour engine_c sur une fenêtre raw_window.

    Calcule les 5 records canoniques (Kyle, VPIN, OFI, QueuePressure,
    RealizedKernelVol) puis compose un input PARTIEL engine_c via
    `compose_engine_c_input_payload`. L'input final n'est pas
    `EngineCInput.model_validate()`-compatible tant que les 7 champs
    structurels (breakout_strength, range_quality, ...) ne sont pas
    fournis par un structure-resolver canonique.

    Tous les records sont None individuellement si leurs inputs sont
    insuffisants (window vide, pas de trades, pas de book, etc.).
    Le `bridge_status` documente le statut global.
    """

    warnings: list[str] = []
    trades_raw: list[dict[str, object]] = []
    book_states: list[_BookState] = []
    book_snapshots_count = 0
    book_deltas_count = 0

    # Étape 1a : trades dans la fenêtre
    if raw_trade_path:
        try:
            trades_raw = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    # Étape 1b : reconstruction séquentielle du book via snapshot + deltas.
    # On utilise raw_book_delta_path explicite si fourni, sinon on derive depuis
    # raw_book_path par convention silver canonique (orderbook_snapshot →
    # orderbook_delta dans le path).
    if raw_book_path:
        try:
            snapshots = _load_book_snapshots(Path(raw_book_path))
            book_snapshots_count = len(snapshots)
            base_snap = _select_base_snapshot(
                snapshots, window_start_ms=window_start_ms
            )
            if base_snap is None:
                warnings.append("BOOK_NO_SNAPSHOT_AVAILABLE")
            else:
                base_uid = int(base_snap.get("update_id") or 0)
                delta_path = _resolve_book_delta_path(
                    raw_book_path, raw_book_delta_path
                )
                if delta_path is None or not delta_path.exists():
                    warnings.append(
                        f"BOOK_DELTA_PATH_MISSING:{delta_path}"
                    )
                else:
                    # Patch B2-RECON-SHARE (2026-06-04) — partition-shared book
                    # timeline when the B2 runner enables it; legacy progressive
                    # path (A2-safe) otherwise. Bit-identical book_states.
                    book_states, book_deltas_count = _partition_shared_book_states(
                        pair=pair,
                        raw_book_path=raw_book_path,
                        delta_path=delta_path,
                        base_snapshot=base_snap,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        top_k=20,
                    )
        except OSError as exc:
            warnings.append(f"BOOK_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("BOOK_PATH_MISSING")

    # Étape 2 : calcule les 5 records (chaque échec → record=None + warning)
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None

    kyle_points = _build_kyle_trade_points(trades_raw)
    if len(kyle_points) >= 2:
        try:
            window_seconds = max(1.0, (window_end_ms - window_start_ms) / 1000.0)
            kyle_record = compute_kyle_lambda(
                kyle_points,
                pair=pair,
                window_seconds=window_seconds,
                bucket_seconds=min(60.0, window_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"KYLE_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"KYLE_INSUFFICIENT_TRADES:{len(kyle_points)}")

    vpin_points = _build_vpin_trade_points(trades_raw)
    if len(vpin_points) >= 1:
        try:
            vpin_record = compute_vpin(
                vpin_points,
                pair=pair,
                buckets_per_day=vpin_buckets_per_day,
                allow_derived_daily_volume=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append("VPIN_NO_TRADES")

    # OFI sur la sequence d'etats reconstruits (top-of-book event-par-event).
    ofi_points: list[OrderBookTopLevelPoint] = []
    for state in book_states:
        point = _book_state_to_ofi_point(state)
        if point is not None:
            ofi_points.append(point)
    if len(ofi_points) >= 2:
        try:
            ofi_record = compute_order_flow_imbalance(
                ofi_points,
                pair=pair,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OFI_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"OFI_INSUFFICIENT_BOOK_STATES:{len(ofi_points)}/"
            f"states={len(book_states)}/snaps={book_snapshots_count}/"
            f"deltas={book_deltas_count}"
        )

    # QueuePressure sur le dernier etat reconstruit dans la fenetre
    if book_states:
        latest_state = book_states[-1]
        queue_point = _book_state_to_queue_pressure_point(latest_state, top_k=5)
        if queue_point is not None:
            try:
                queue_pressure_record = compute_queue_pressure(
                    queue_point,
                    pair=pair,
                    top_k=5,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"QUEUE_PRESSURE_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("QUEUE_PRESSURE_BOOK_STATE_BUILD_FAILED")
    else:
        warnings.append("QUEUE_PRESSURE_NO_BOOK_STATES")

    rk_points = _build_realized_kernel_price_points(trades_raw)
    if len(rk_points) >= 2:
        try:
            realized_kernel_record = compute_realized_kernel_vol(
                rk_points,
                pair=pair,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_KERNEL_VOL_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"REALIZED_KERNEL_VOL_INSUFFICIENT_PRICES:{len(rk_points)}")

    # Étape 3 : composition partielle de l'input engine_c.
    # Note : EngineCMicrostructureProvenance.kyle_lambda exige ge=0.0, donc un
    # kyle_record stale avec value <= 0 (non_positive_lambda, slope OLS negatif)
    # ne peut pas etre passe directement. On le filtre avec un warning explicite.
    kyle_for_engine_c: KyleLambdaRecord | None = kyle_record
    if kyle_for_engine_c is not None and (
        kyle_for_engine_c.is_stale or kyle_for_engine_c.value < 0.0
    ):
        warnings.append(
            f"KYLE_FILTERED_FOR_ENGINE_C:stale={kyle_for_engine_c.is_stale}"
            f":value={kyle_for_engine_c.value}"
        )
        kyle_for_engine_c = None

    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    partial_payload: dict[str, object] = {}
    try:
        partial_payload = compose_engine_c_input_payload(
            base,
            pair=pair,
            ofi_record=ofi_record,
            queue_pressure_record=queue_pressure_record,
            vpin_record=vpin_record,
            kyle_lambda_record=kyle_for_engine_c,
            realized_vol_current_record=realized_kernel_record,
            realized_vol_at_break_record=None,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"COMPOSE_ENGINE_C_FAILED:{type(exc).__name__}:{exc}")

    # Patch 2026-05-30 (C-wire) — close LIMITATION P3a. Build the 7 structural
    # fields via engine_c_structure_resolver from the 5 microstructure records
    # + base_payload OHLCV scalars, merge into the engine_c payload, and try
    # EngineCInput.model_validate to surface full-path readiness.
    full_payload: dict[str, object] | None = None
    structure_summary: dict[str, object] = {}
    try:
        resolver_inputs = _build_breakout_microstructure_inputs(
            ofi_record=ofi_record,
            queue_pressure_record=queue_pressure_record,
            vpin_record=vpin_record,
            kyle_record=kyle_for_engine_c,
            realized_kernel_record=realized_kernel_record,
            base_payload=base,
        )
        resolution = resolve_breakout_microstructure_features(resolver_inputs)
        # Engine-specific projection: 7-float dict for EngineCInput contract
        structure_floats = build_engine_c_input_from_breakout_features(resolution)
        full_payload = dict(partial_payload)
        full_payload.update(structure_floats)
        structure_summary = {
            "any_fallback_used": resolution.any_fallback_used,
            "any_research_only_fallback": resolution.any_research_only_fallback,
            "per_field_provenance": {
                name: getattr(resolution, name).provenance
                for name in (
                    "breakout_strength",
                    "range_quality",
                    "compression_quality",
                    "volume_confirmation",
                    "followthrough_room",
                    "extension_pct",
                    "retrace_risk",
                )
            },
            "per_field_confidence": {
                name: getattr(resolution, name).confidence
                for name in (
                    "breakout_strength",
                    "range_quality",
                    "compression_quality",
                    "volume_confirmation",
                    "followthrough_room",
                    "extension_pct",
                    "retrace_risk",
                )
            },
        }
    except Exception as exc:  # noqa: BLE001 — surface as warning, fall back to partial
        warnings.append(
            f"ENGINE_C_STRUCTURE_RESOLVER_FAILED:{type(exc).__name__}:{exc}"
        )

    # Statut final
    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
        )
        if r is not None
    )
    full_path_validated = False
    if n_built == 5 and full_payload is not None:
        # Try EngineCInput.model_validate — surface full-path readiness only
        # when the merged payload satisfies the contract.
        try:
            from engines.engine_c.engine_c_runner import EngineCInput

            EngineCInput.model_validate(full_payload)
            full_path_validated = True
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"ENGINE_C_INPUT_VALIDATION_FAILED:{type(exc).__name__}"
            )

    if n_built == 5 and full_path_validated:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FULL_PATH_READY"
    elif n_built == 5:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineNativeBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_raw),
        n_book_snapshots_loaded=book_snapshots_count,
        n_book_deltas_loaded=book_deltas_count,
        n_book_states_reconstructed=len(book_states),
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        engine_c_partial_input_payload=partial_payload,
        engine_c_full_input_payload=full_payload if full_path_validated else None,
        engine_c_structure_resolution_summary=structure_summary,
        bridge_warnings=tuple(warnings),
    )


def _build_breakout_microstructure_inputs(
    *,
    ofi_record: OrderFlowImbalanceRecord | None,
    queue_pressure_record: QueuePressureRecord | None,
    vpin_record: VpinRecord | None,
    kyle_record: KyleLambdaRecord | None,
    realized_kernel_record: RealizedKernelVolRecord | None,
    base_payload: dict[str, object],
) -> BreakoutMicrostructureInputs:
    """Extract microstructure scalars from records + base_payload for resolver.

    Missing inputs (None records, missing OHLCV scalars) gracefully degrade
    via per-field fallback in resolve_breakout_microstructure_features.
    """

    def _opt_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            f = float(value)
            return f if f == f else None  # NaN check
        except (TypeError, ValueError):
            return None

    ofi_value = (
        _opt_float(ofi_record.value) if ofi_record is not None else None
    )
    queue_value = (
        _opt_float(queue_pressure_record.value)
        if queue_pressure_record is not None
        else None
    )
    vpin_value = _opt_float(vpin_record.value) if vpin_record is not None else None
    realized_vol = (
        _opt_float(realized_kernel_record.value)
        if realized_kernel_record is not None
        else None
    )
    kyle_value = _opt_float(kyle_record.value) if kyle_record is not None else None
    # Kyle lambda × standard 100 USDT notional → expected slippage in bps
    expected_slippage_bps = (
        kyle_value * 100.0 if kyle_value is not None and kyle_value >= 0 else None
    )

    return BreakoutMicrostructureInputs(
        breakout_price=_opt_float(base_payload.get("breakout_level"))
        or _opt_float(base_payload.get("entry_price")),
        entry_price=_opt_float(base_payload.get("entry_price")),
        range_high=_opt_float(base_payload.get("range_high")),
        range_low=_opt_float(base_payload.get("range_low")),
        recent_range_width=(
            _opt_float(base_payload.get("range_high"))
            - _opt_float(base_payload.get("range_low"))
            if _opt_float(base_payload.get("range_high")) is not None
            and _opt_float(base_payload.get("range_low")) is not None
            else None
        ),
        realized_vol_current=realized_vol,
        ofi_normalized=ofi_value,
        cumulative_ofi=ofi_value,
        queue_pressure=queue_value,
        expected_slippage_bps=expected_slippage_bps,
        vpin=vpin_value,
        inputs_freshness_status=(
            FRESHNESS_FRESH
            if all(
                r is not None
                for r in (
                    ofi_record,
                    queue_pressure_record,
                    vpin_record,
                    realized_kernel_record,
                )
            )
            else FRESHNESS_NOT_PROVEN
        ),
    )


# ----------------------------------------------------------------------------
# Helpers internes communs (calcul des records depuis raw_window)
# ----------------------------------------------------------------------------


def _compute_microstructure_records_from_window(
    *,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> tuple[
    KyleLambdaRecord | None,
    VpinRecord | None,
    OrderFlowImbalanceRecord | None,
    QueuePressureRecord | None,
    RealizedKernelVolRecord | None,
    int,  # n_trades_loaded
    int,  # n_book_snapshots_loaded
    int,  # n_book_deltas_loaded
    int,  # n_book_states_reconstructed
    list[str],  # warnings
]:
    """Calcule les 5 records canoniques. Helper partage entre tous les engines."""
    cache_key = (
        pair.strip().upper(),
        int(window_start_ms),
        int(window_end_ms),
        _path_cache_signature(raw_trade_path),
        _path_cache_signature(raw_book_path),
        _path_cache_signature(raw_book_delta_path),
        int(vpin_buckets_per_day),
    )
    cached = _MICROSTRUCTURE_RECORD_CACHE.get(cache_key)
    if cached is not None:
        return (
            cached[0],
            cached[1],
            cached[2],
            cached[3],
            cached[4],
            int(cached[5]),
            int(cached[6]),
            int(cached[7]),
            int(cached[8]),
            list(cached[9]),
        )
    warnings: list[str] = []
    trades_raw: list[dict[str, object]] = []
    book_states: list[_BookState] = []
    book_snapshots_count = 0
    book_deltas_count = 0

    if raw_trade_path:
        try:
            trades_raw = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    if raw_book_path:
        try:
            snapshots = _load_book_snapshots(Path(raw_book_path))
            book_snapshots_count = len(snapshots)
            base_snap = _select_base_snapshot(
                snapshots, window_start_ms=window_start_ms
            )
            if base_snap is None:
                warnings.append("BOOK_NO_SNAPSHOT_AVAILABLE")
            else:
                base_uid = int(base_snap.get("update_id") or 0)
                delta_path = _resolve_book_delta_path(
                    raw_book_path, raw_book_delta_path
                )
                if delta_path is None or not delta_path.exists():
                    warnings.append(f"BOOK_DELTA_PATH_MISSING:{delta_path}")
                else:
                    # Patch B2-RECON-SHARE (2026-06-04) — partition-shared book
                    # timeline when the B2 runner enables it; legacy progressive
                    # path (A2-safe) otherwise. Bit-identical book_states.
                    book_states, book_deltas_count = _partition_shared_book_states(
                        pair=pair,
                        raw_book_path=raw_book_path,
                        delta_path=delta_path,
                        base_snapshot=base_snap,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        top_k=20,
                    )
        except OSError as exc:
            warnings.append(f"BOOK_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("BOOK_PATH_MISSING")

    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None

    kyle_points = _build_kyle_trade_points(trades_raw)
    if len(kyle_points) >= 2:
        try:
            window_seconds = max(1.0, (window_end_ms - window_start_ms) / 1000.0)
            kyle_record = compute_kyle_lambda(
                kyle_points,
                pair=pair,
                window_seconds=window_seconds,
                bucket_seconds=min(60.0, window_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"KYLE_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"KYLE_INSUFFICIENT_TRADES:{len(kyle_points)}")

    vpin_points = _build_vpin_trade_points(trades_raw)
    if len(vpin_points) >= 1:
        try:
            vpin_record = compute_vpin(
                vpin_points,
                pair=pair,
                buckets_per_day=vpin_buckets_per_day,
                allow_derived_daily_volume=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append("VPIN_NO_TRADES")

    ofi_points: list[OrderBookTopLevelPoint] = []
    for state in book_states:
        point = _book_state_to_ofi_point(state)
        if point is not None:
            ofi_points.append(point)
    if len(ofi_points) >= 2:
        try:
            ofi_record = compute_order_flow_imbalance(ofi_points, pair=pair)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OFI_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"OFI_INSUFFICIENT_BOOK_STATES:{len(ofi_points)}/"
            f"states={len(book_states)}/snaps={book_snapshots_count}/"
            f"deltas={book_deltas_count}"
        )

    if book_states:
        latest_state = book_states[-1]
        queue_point = _book_state_to_queue_pressure_point(latest_state, top_k=5)
        if queue_point is not None:
            try:
                queue_pressure_record = compute_queue_pressure(
                    queue_point, pair=pair, top_k=5
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"QUEUE_PRESSURE_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("QUEUE_PRESSURE_BOOK_STATE_BUILD_FAILED")
    else:
        warnings.append("QUEUE_PRESSURE_NO_BOOK_STATES")

    rk_points = _build_realized_kernel_price_points(trades_raw)
    if len(rk_points) >= 2:
        try:
            realized_kernel_record = compute_realized_kernel_vol(rk_points, pair=pair)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_KERNEL_VOL_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"REALIZED_KERNEL_VOL_INSUFFICIENT_PRICES:{len(rk_points)}")

    result = (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        len(trades_raw),
        book_snapshots_count,
        book_deltas_count,
        len(book_states),
        warnings,
    )
    _MICROSTRUCTURE_RECORD_CACHE[cache_key] = (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        len(trades_raw),
        book_snapshots_count,
        book_deltas_count,
        len(book_states),
        tuple(warnings),
    )
    return result


# ----------------------------------------------------------------------------
# Engine D — bridge realized_vol_current + realized_vol_post_close
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineDBridgeResult:
    """Resultat audit-ready du pont microstructure pour engine_d.

    LIMITATION : EngineDInput requiert 8 champs structurels engine-d-specifiques
    (prior_trade_quality, reformation_quality, pullback_quality, continuation_room,
    concentration_headroom, marginal_edge, reentry_lateness, + champs context
    de re-entree). Ces champs n'ont pas de structure-resolver canonique, donc
    `run_engine_d(EngineDInput)` n'est pas invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None
    engine_d_partial_input_payload: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for r in (
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_vol_current_record,
                self.realized_vol_post_close_record,
            )
            if r is not None
        )


def build_engine_d_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None = None,
    raw_book_delta_path: Path | str | None = None,
    post_close_window_end_ms: int | None = None,
    base_payload: dict[str, object] | None = None,
) -> EngineDBridgeResult:
    """Pont microstructure engine_d.

    Calcule realized_vol_current depuis les trades dans [window_start_ms, window_end_ms]
    et realized_vol_post_close depuis les trades dans [window_end_ms,
    post_close_window_end_ms] (si fourni). Compose un input partiel engine_d via
    compose_engine_d_input_payload.
    """
    warnings: list[str] = []
    trades_in_window: list[dict[str, object]] = []
    trades_post_close: list[dict[str, object]] = []

    if raw_trade_path:
        try:
            trades_in_window = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
            if post_close_window_end_ms is not None and post_close_window_end_ms > window_end_ms:
                trades_post_close = _load_trades_in_window(
                    Path(raw_trade_path),
                    window_start_ms=window_end_ms,
                    window_end_ms=post_close_window_end_ms,
                )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    n_book_snapshots = 0
    n_book_deltas = 0
    n_book_states = 0

    rk_current_points = _build_realized_kernel_price_points(trades_in_window)
    if len(rk_current_points) >= 2:
        try:
            realized_vol_current_record = compute_realized_kernel_vol(
                rk_current_points, pair=pair
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_VOL_CURRENT_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"REALIZED_VOL_CURRENT_INSUFFICIENT_PRICES:{len(rk_current_points)}"
        )

    if post_close_window_end_ms is not None:
        rk_post_close_points = _build_realized_kernel_price_points(trades_post_close)
        if len(rk_post_close_points) >= 2:
            try:
                realized_vol_post_close_record = compute_realized_kernel_vol(
                    rk_post_close_points, pair=pair
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(
                    f"REALIZED_VOL_POST_CLOSE_FAILED:{type(exc).__name__}:{exc}"
                )
        else:
            warnings.append(
                f"REALIZED_VOL_POST_CLOSE_INSUFFICIENT_PRICES:"
                f"{len(rk_post_close_points)}"
            )
    else:
        warnings.append("REALIZED_VOL_POST_CLOSE_WINDOW_NOT_PROVIDED")

    if raw_book_path is not None or raw_book_delta_path is not None:
        (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            common_realized_record,
            _n_trades,
            n_book_snapshots,
            n_book_deltas,
            n_book_states,
            common_warnings,
        ) = _compute_microstructure_records_from_window(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=raw_book_path,
            raw_book_delta_path=raw_book_delta_path,
        )
        if realized_vol_current_record is None:
            realized_vol_current_record = common_realized_record
        warnings.extend(common_warnings)

    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    partial_payload: dict[str, object] = {}
    try:
        partial_payload = compose_engine_d_input_payload(
            base,
            pair=pair,
            realized_vol_current_record=realized_vol_current_record,
            realized_vol_post_close_record=realized_vol_post_close_record,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"COMPOSE_ENGINE_D_FAILED:{type(exc).__name__}:{exc}")

    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_vol_current_record,
            realized_vol_post_close_record,
        )
        if r is not None
    )
    vol_built = sum(
        1
        for r in (realized_vol_current_record, realized_vol_post_close_record)
        if r is not None
    )
    if vol_built == 2:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineDBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_in_window),
        n_book_snapshots_loaded=n_book_snapshots,
        n_book_deltas_loaded=n_book_deltas,
        n_book_states_reconstructed=n_book_states,
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_post_close_record=realized_vol_post_close_record,
        engine_d_partial_input_payload=partial_payload,
        bridge_warnings=tuple(warnings),
    )


# ----------------------------------------------------------------------------
# Engine A — bridge ofi_flow_score + realized_kernel_vol_scale +
#                realized_vol_current + kyle_lambda_cost_uplift
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineABridgeResult:
    """Resultat audit-ready du pont microstructure pour engine_a.

    LIMITATION : EngineAInput requiert ~5 champs structurels REQUIRED
    (direction_score, continuation_score, structure_quality, zone_proximity,
    trend_stability) sans structure-resolver canonique. `run_engine_a()` n'est
    pas invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    ofi_record: OrderFlowImbalanceRecord | None = None
    vpin_record: VpinRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    kyle_lambda_record: KyleLambdaRecord | None = None
    engine_a_microstructure_updates: dict[str, float | None] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for r in (
                self.ofi_record,
                self.vpin_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
                self.kyle_lambda_record,
            )
            if r is not None
        )


def build_engine_a_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineABridgeResult:
    """Pont microstructure engine_a.

    Reutilise les helpers communs pour calculer les records canoniques, puis
    appelle `build_engine_a_runner_microstructure_updates` du seam
    `data_backbone.microstructure.engine_input_provenance` pour produire les
    additive updates aux scalar inputs Engine A :
      - ofi_flow_score, realized_kernel_vol_scale, realized_vol_current,
        kyle_lambda_cost_uplift

    Note : ces additive updates s'appliquent SUR un EngineAInput de base que le
    caller doit construire (avec direction_score, continuation_score, etc.).
    """
    (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        n_trades,
        n_snaps,
        n_deltas,
        n_states,
        warnings,
    ) = _compute_microstructure_records_from_window(
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=raw_trade_path,
        raw_book_path=raw_book_path,
        raw_book_delta_path=raw_book_delta_path,
        vpin_buckets_per_day=vpin_buckets_per_day,
    )

    # Engine A additive seam updates via le pont canonique. Filtrer Kyle stale
    # comme pour engine_c (EngineAMicrostructureProvenance.kyle_lambda_cost_uplift
    # exige ge=0.0).
    kyle_for_engine_a: KyleLambdaRecord | None = kyle_record
    if kyle_for_engine_a is not None and (
        kyle_for_engine_a.is_stale or kyle_for_engine_a.value < 0.0
    ):
        warnings.append(
            f"KYLE_FILTERED_FOR_ENGINE_A:stale={kyle_for_engine_a.is_stale}"
            f":value={kyle_for_engine_a.value}"
        )
        kyle_for_engine_a = None

    updates: dict[str, float | None] = {}
    try:
        updates = build_engine_a_runner_microstructure_updates(
            pair=pair,
            ofi_record=ofi_record,
            realized_kernel_record=realized_kernel_record,
            kyle_lambda_record=kyle_for_engine_a,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"BUILD_ENGINE_A_UPDATES_FAILED:{type(exc).__name__}:{exc}")
    if updates.get("ofi_flow_score") is None and raw_trade_path is not None:
        try:
            flow_score = _trade_flow_score_from_window(
                _load_trades_in_window(
                    Path(raw_trade_path),
                    window_start_ms=window_start_ms,
                    window_end_ms=window_end_ms,
                )
            )
        except OSError as exc:
            warnings.append(f"ENGINE_A_TRADE_FLOW_FALLBACK_FAILED:{type(exc).__name__}")
            flow_score = None
        if flow_score is not None:
            updates["flow_score"] = flow_score
            warnings.append("ENGINE_A_FLOW_SCORE_FROM_TRADE_IMBALANCE")

    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
        )
        if r is not None
    )
    if n_built == 5:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineABridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=n_trades,
        n_book_snapshots_loaded=n_snaps,
        n_book_deltas_loaded=n_deltas,
        n_book_states_reconstructed=n_states,
        ofi_record=ofi_record,
        vpin_record=vpin_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        kyle_lambda_record=kyle_record,
        engine_a_microstructure_updates=updates,
        bridge_warnings=tuple(warnings),
    )


# ----------------------------------------------------------------------------
# Engine B — bridge local_mean + local_std + vpin
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineBBridgeResult:
    """Resultat audit-ready du pont engine_b.

    EngineBInput requiert 4 champs : pair, current_price, local_mean, local_std.
    Le bridge calcule current_price (= dernier prix de la fenetre), local_mean
    (= moyenne arithmetique des prix) et local_std (= ecart-type empirique) depuis
    les trades dans la fenetre. VPIN partage le pipeline microstructure commun.

    LIMITATION : les autres champs sweep_score / absorption_score /
    poc_reversion_score / false_breakout_score / execution_fragility /
    market_toxicity / etc. necessitent d'autres modules microstructure
    (walls_and_spoofing, etc.) non cables ici. `run_engine_b()` n'est pas
    invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    current_price: float | None = None
    local_mean: float | None = None
    local_std: float | None = None
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    engine_b_partial_input_payload: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        # Compte les composantes critiques disponibles (price, mean, std, vpin)
        return sum(
            1
            for v in (
                self.current_price,
                self.local_mean,
                self.local_std,
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
            )
            if v is not None
        )


def _compute_local_mean_std_from_trades(
    trades: list[dict[str, object]],
) -> tuple[float | None, float | None, float | None]:
    """Retourne (current_price, local_mean, local_std) depuis trades dans la fenetre.

    - current_price : prix du dernier trade (par timestamp_ms)
    - local_mean    : moyenne arithmetique des prix (volume-weighted serait
                       preferable mais demande calibration ; ici simple mean)
    - local_std     : ecart-type empirique non-biaise (N-1 denominator)

    Retourne (None, None, None) si moins de 2 trades exploitables.
    """
    prices: list[tuple[int, float]] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0:
            continue
        prices.append((ts_ms, price))
    if len(prices) < 2:
        return None, None, None
    prices.sort(key=lambda x: x[0])
    values = [p for _, p in prices]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = variance ** 0.5
    current = values[-1]
    return current, mean, std


def build_engine_b_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None = None,
    raw_book_delta_path: Path | str | None = None,
    base_payload: dict[str, object] | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineBBridgeResult:
    """Pont microstructure engine_b.

    Calcule current_price, local_mean, local_std depuis les trades dans la fenetre
    et VPIN via le pipeline microstructure commun. Compose un input partiel
    engine_b en respectant les defaults TO_CALIBRATE pour les autres champs.
    """
    warnings: list[str] = []
    trades_in_window: list[dict[str, object]] = []

    if raw_trade_path:
        try:
            trades_in_window = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    current_price, local_mean, local_std = _compute_local_mean_std_from_trades(
        trades_in_window
    )
    if current_price is None:
        warnings.append(
            f"LOCAL_MEAN_STD_INSUFFICIENT_TRADES:{len(trades_in_window)}"
        )

    # VPIN via le pipeline commun (re-utilise sans book — book est optionnel
    # pour engine_b car local_mean/std sont les inputs critiques)
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None
    n_book_snapshots = 0
    n_book_deltas = 0
    n_book_states = 0

    if raw_book_path is not None or raw_book_delta_path is not None:
        (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
            _n_trades,
            n_book_snapshots,
            n_book_deltas,
            n_book_states,
            common_warnings,
        ) = _compute_microstructure_records_from_window(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=raw_book_path,
            raw_book_delta_path=raw_book_delta_path,
            vpin_buckets_per_day=vpin_buckets_per_day,
        )
        warnings.extend(common_warnings)
    else:
        vpin_points = _build_vpin_trade_points(trades_in_window)
        if len(vpin_points) >= 1:
            try:
                vpin_record = compute_vpin(
                    vpin_points,
                    pair=pair,
                    buckets_per_day=vpin_buckets_per_day,
                    allow_derived_daily_volume=True,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("VPIN_NO_TRADES")

    # Compose payload partiel engine_b (pas de compose_engine_b dans le seam,
    # on construit manuellement en respectant les contraintes Pydantic
    # EngineBInput : pair, current_price>0, local_mean>0, local_std>=0).
    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    if current_price is not None and current_price > 0.0:
        base.setdefault("current_price", current_price)
    if local_mean is not None and local_mean > 0.0:
        base.setdefault("local_mean", local_mean)
    if local_std is not None and local_std >= 0.0:
        base.setdefault("local_std", local_std)
    if vpin_record is not None:
        # EngineBInput.vpin_current : Field(default=None, ge=0.0, le=1.0)
        base.setdefault("vpin_current", vpin_record.value)

    n_critical = sum(
        1
        for v in (current_price, local_mean, local_std, vpin_record)
        if v is not None
    )
    if n_critical == 4:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_critical > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineBBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_in_window),
        n_book_snapshots_loaded=n_book_snapshots,
        n_book_deltas_loaded=n_book_deltas,
        n_book_states_reconstructed=n_book_states,
        current_price=current_price,
        local_mean=local_mean,
        local_std=local_std,
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        engine_b_partial_input_payload=base,
        bridge_warnings=tuple(warnings),
    )


__all__ = [
    "EngineNativeBridgeResult",
    "EngineDBridgeResult",
    "EngineABridgeResult",
    "EngineBBridgeResult",
    "build_engine_c_microstructure_inputs_from_window",
    "build_engine_c_requested_microstructure_features_from_window",
    "build_engine_d_microstructure_inputs_from_window",
    "build_engine_a_microstructure_inputs_from_window",
    "build_engine_b_microstructure_inputs_from_window",
    "evict_microstructure_file_cache",
    "get_microstructure_file_cache_stats",
    "set_partition_book_timeline_enabled",
    "evict_partition_book_timelines",
    "reset_microstructure_file_cache_stats",
]
