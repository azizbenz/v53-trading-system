"""Gain 2 (2026-06-03) — multicore A2 gold feature build.

A2 profiling proved the gold build is CPU-bound (CPU/wall 0.89) and dominated by
the per-trade-file parse (x3 candidates 5m vs 15m was only +5% wall). The serial
``_write_gold_features`` loops partitions one core. This module parallelizes it
WITHOUT touching the ~700-line build body: it REUSES ``_write_gold_features`` as
the worker, scoped to one ``(pair, timeframe, year-month)`` partition per task.

Why that unit is safe:
- Each task writes exactly ONE output file
  ``features_{tf}/{pair}/{year}/{month}.jsonl.gz`` (the build derives the path
  from ``entry.date``). Distinct files across tasks -> no write collision (the
  serial build does a read-modify-write per day into the month file; running days
  of the SAME month in parallel would corrupt it, so the month is the atomic unit).
- Tasks are independent (own input date files, own output file).

Parity gate: the gold FILES produced must be identical to the serial build (that
is what B1/B2 consume). ``gold_row_limit`` becomes approximate under parallelism
(no global mid-flight break) — callers that need an exact cap must run serial.

Opt-in: the runner engages this only when workers > 1; otherwise the serial
``_write_gold_features`` path is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
    StrategyLadderGoldFeatureManifest,
    StrategyLadderSilverIndexEntry,
)
from local_replay_runtime.strategy_ladder_parallel import (
    ordered_parallel_map,
    resolve_worker_count,
)


@dataclass(frozen=True)
class _GoldPartitionTask:
    """One independent gold-build unit: a (pair, timeframe, year-month) slice.

    Carries a request scoped to that pair+timeframe and the silver index entries
    needed: that partition's kline (ohlcv) entries + ALL of the pair's non-kline
    entries (trades/book/metadata are matched by date inside the build, so extras
    are inert)."""

    pair: str
    timeframe: str
    year_month: str
    request: StrategyLadderDataFactoryRequest
    entries: tuple[StrategyLadderSilverIndexEntry, ...]


def partition_gold_tasks(
    request: StrategyLadderDataFactoryRequest,
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    available_pairs: tuple[str, ...],
) -> tuple[_GoldPartitionTask, ...]:
    """Split the gold build into independent (pair, timeframe, year-month) tasks.

    A task exists for every (pair, tf, ym) that has at least one kline entry. The
    atomic unit is the month (the build's read-modify-write writes one month file)."""
    non_kline_by_pair: dict[str, list[StrategyLadderSilverIndexEntry]] = {}
    kline_groups: dict[tuple[str, str], list[StrategyLadderSilverIndexEntry]] = {}
    tfs_by_group: dict[tuple[str, str], set[str]] = {}
    for entry in index_entries:
        if entry.data_type == "ohlcv":
            pair = entry.pair
            ym = (entry.date or "")[:7]
            kline_groups.setdefault((pair, ym), []).append(entry)
            tf = str(entry.timeframe or "").strip()
            if tf:
                tfs_by_group.setdefault((pair, ym), set()).add(tf)
        else:
            # trades / orderbook_* / metadata — shared per pair (date-matched in build)
            non_kline_by_pair.setdefault(entry.pair, []).append(entry)

    tasks: list[_GoldPartitionTask] = []
    for (pair, ym), klines in kline_groups.items():
        if pair not in available_pairs:
            continue
        # Unit = (pair, year-month) keeping ALL timeframes together: 5m and 15m of
        # the same pair-day share the trade file, so one worker parses it ONCE
        # (per-process lru_cache) for every timeframe — splitting by timeframe would
        # re-parse it per worker and lose that sharing. Output files stay distinct
        # (features_{tf}/...), and the month stays the atomic write unit.
        scoped_request = request.model_copy(update={"pairs": (pair,)})
        entries = tuple(klines) + tuple(non_kline_by_pair.get(pair, ()))
        tasks.append(
            _GoldPartitionTask(
                pair=pair, timeframe=",".join(sorted(tfs_by_group.get((pair, ym), ()))),
                year_month=ym, request=scoped_request, entries=entries,
            )
        )
    # Deterministic order (pair, ym) so the ordered map output is stable.
    tasks.sort(key=lambda t: (t.pair, t.year_month))
    return tuple(tasks)


def _gold_task_worker(task: _GoldPartitionTask) -> StrategyLadderGoldFeatureManifest:
    """Top-level (picklable) worker: build gold for one partition by reusing the
    canonical ``_write_gold_features`` scoped to this task. Imported lazily so the
    heavy data_factory module loads inside the worker process, not at module import."""
    from local_replay_runtime.strategy_ladder_data_factory import _write_gold_features

    return _write_gold_features(
        request=task.request,
        index_entries=task.entries,
        available_pairs=(task.pair,),
    )


def _merge_gold_manifests(
    manifests: tuple[StrategyLadderGoldFeatureManifest, ...],
    *,
    serial_fallback,
) -> StrategyLadderGoldFeatureManifest:
    """Aggregate per-partition manifests into one. The gold FILES are the parity
    source of truth (written by workers); this combines the reporting metadata.
    Re-finalizes the hash via the data_factory finalizer."""
    from local_replay_runtime.strategy_ladder_data_factory import finalize_hashed_model

    if not manifests:
        return serial_fallback()
    base = manifests[0]
    feature_paths: list[str] = []
    blocker_codes: list[str] = []
    feature_groups: set[str] = set()
    groups_declared: set[str] = set()
    groups_generated: set[str] = set()
    groups_ready: set[str] = set()
    silver_tfs: set[str] = set()
    gold_tfs: set[str] = set()
    tfs_pruned: set[str] = set()
    pruning_reason: dict[str, str] = {}
    tf_row_count: dict[str, int] = {}
    streaming_status_counts: dict[str, int] = {}
    row_count = ctx_row = ctx_suppressed = 0
    s_batch = s_requested = s_overlay = s_missing = 0
    cache_used = False
    for m in manifests:
        feature_paths.extend(m.feature_paths)
        blocker_codes.extend(m.blocker_codes)
        feature_groups.update(m.feature_groups)
        groups_declared.update(m.feature_groups_declared)
        groups_generated.update(m.feature_groups_generated)
        groups_ready.update(m.feature_groups_ready)
        silver_tfs.update(m.silver_timeframes_detected)
        gold_tfs.update(m.gold_timeframes_generated)
        tfs_pruned.update(m.timeframes_pruned)
        pruning_reason.update(m.pruning_reason_by_timeframe)
        for k, v in m.timeframe_feature_row_count.items():
            tf_row_count[k] = tf_row_count.get(k, 0) + v
        for k, v in m.microstructure_streaming_status_counts.items():
            streaming_status_counts[k] = streaming_status_counts.get(k, 0) + v
        row_count += m.feature_row_count
        ctx_row += m.gold_context_row_count
        ctx_suppressed += m.gold_context_rows_suppressed_count
        s_batch += m.microstructure_streaming_batch_count
        s_requested += m.microstructure_streaming_requested_row_count
        s_overlay += m.microstructure_streaming_overlay_row_count
        s_missing += m.microstructure_streaming_missing_row_count
        cache_used = cache_used or m.microstructure_cache_used
    # status: READY if any partition produced rows, else keep base status
    store_status = (
        "GOLD_FEATURE_STORE_READY" if row_count > 0 else base.gold_feature_store_status
    )
    merged = StrategyLadderGoldFeatureManifest(
        gold_feature_store_status=store_status,
        feature_paths=tuple(dict.fromkeys(feature_paths)),
        feature_row_count=row_count,
        feature_groups=tuple(sorted(feature_groups)),
        feature_groups_declared=tuple(sorted(groups_declared)),
        feature_groups_generated=tuple(sorted(groups_generated)),
        feature_groups_ready=tuple(sorted(groups_ready)),
        engines_encoded=base.engines_encoded,
        timeframes_encoded=base.timeframes_encoded,
        silver_timeframes_detected=tuple(sorted(silver_tfs)),
        gold_timeframes_generated=tuple(sorted(gold_tfs)),
        timeframes_pruned=tuple(sorted(tfs_pruned)),
        pruning_reason_by_timeframe=pruning_reason,
        timeframe_feature_row_count=tf_row_count,
        gold_decision_window_status=base.gold_decision_window_status,
        gold_context_row_count=ctx_row,
        gold_context_rows_suppressed_count=ctx_suppressed,
        microstructure_cache_used=cache_used,
        feature_equivalence_status=base.feature_equivalence_status,
        microstructure_streaming_status=base.microstructure_streaming_status,
        microstructure_streaming_batch_count=s_batch,
        microstructure_streaming_requested_row_count=s_requested,
        microstructure_streaming_overlay_row_count=s_overlay,
        microstructure_streaming_missing_row_count=s_missing,
        microstructure_streaming_status_counts=streaming_status_counts,
        blocker_codes=tuple(dict.fromkeys(blocker_codes)),
    )
    return finalize_hashed_model(merged)


def build_gold_features_parallel(
    request: StrategyLadderDataFactoryRequest,
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    available_pairs: tuple[str, ...],
    *,
    max_workers: int | str | None = None,
) -> StrategyLadderGoldFeatureManifest:
    """Parallel gold build over (pair, tf, year-month) partitions.

    Falls back to the serial ``_write_gold_features`` when workers <= 1 or there
    is <=1 task (then output is byte-identical to the serial path by construction)."""
    from local_replay_runtime.strategy_ladder_data_factory import _write_gold_features

    def _serial() -> StrategyLadderGoldFeatureManifest:
        return _write_gold_features(
            request=request, index_entries=index_entries, available_pairs=available_pairs
        )

    workers = resolve_worker_count(max_workers)
    tasks = partition_gold_tasks(request, index_entries, available_pairs)
    if workers <= 1 or len(tasks) <= 1:
        return _serial()
    manifests = tuple(
        ordered_parallel_map(
            _gold_task_worker, list(tasks), max_workers=workers,
            affinity_key=lambda t: t.pair,
        )
    )
    return _merge_gold_manifests(manifests, serial_fallback=_serial)


__all__ = [
    "partition_gold_tasks",
    "build_gold_features_parallel",
]
