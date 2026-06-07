"""Regression tests for the orderbook-snapshot ANCHOR resolution.

Companion to e61923a (delta-path derivation). With sparse capture (~1
snapshot/day) the snapshot's captured instant rarely falls inside a row's
tolerance window, so `_book_entries_covering_timestamp` excludes it and the
spread measurement received `raw_book_path=None` -> BOOK_PATH_MISSING ->
DEFAULT_BY_BOOK_STATUS for every row. `_resolve_snapshot_anchor_entry` falls
back to the most recent fully-past snapshot so reconstruction can fire.
"""
from __future__ import annotations

from local_replay_runtime.strategy_ladder_data_factory import (
    _book_entries_covering_timestamp,
    _resolve_snapshot_anchor_entry,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)

# Single daily snapshot captured at 00:00:02 on 2025-11-12.
_SNAP_TS = 1_762_905_602_990
_DAY12_START = 1_762_905_600_000  # 00:00:00
_MIDDAY = _SNAP_TS + 12 * 3_600_000


def _entry(
    *,
    data_type: str,
    date: str,
    path: str,
    min_ts: int | None,
    max_ts: int | None,
    depth_status: str = "BOOK_DEPTH20_AVAILABLE",
) -> StrategyLadderSilverIndexEntry:
    return StrategyLadderSilverIndexEntry(
        source_id=f"{data_type}_{date}",
        source_root="/scratch",
        source_priority=10,
        exchange="bybit",
        market_type="spot",
        data_type=data_type,
        pair="BTCUSDT",
        timeframe="",
        date=date,
        path=path,
        storage_format="jsonl-gz",
        min_timestamp_ms=min_ts,
        max_timestamp_ms=max_ts,
        row_count=1,
        file_hash=f"hash-{data_type}-{date}",
        depth_source_status=depth_status,
        schema_status="BOOK_SCHEMA_READY",
    )


def _sparse_book_entries() -> tuple[StrategyLadderSilverIndexEntry, ...]:
    # Snapshot: a single instant. Delta: spans the full day (forward deltas).
    snap = _entry(
        data_type="orderbook_snapshot",
        date="2025-11-12",
        path="/silver/orderbook_snapshot/BTCUSDT/2025/11/12.jsonl.gz",
        min_ts=_SNAP_TS,
        max_ts=_SNAP_TS,
    )
    delta = _entry(
        data_type="orderbook_delta",
        date="2025-11-12",
        path="/silver/orderbook_delta/BTCUSDT/2025/11/12.jsonl.gz",
        min_ts=_SNAP_TS + 200,
        max_ts=_SNAP_TS + 24 * 3_600_000,
    )
    return (snap, delta)


def test_midday_row_resolves_snapshot_anchor_despite_no_coverage() -> None:
    """The bug: midday rows got snapshot_book_path=None -> BOOK_PATH_MISSING."""
    entries = _sparse_book_entries()
    covering = _book_entries_covering_timestamp(entries, timestamp_ms=_MIDDAY)
    # Only the delta covers midday; the snapshot instant does not.
    assert all(e.data_type == "orderbook_delta" for e in covering)

    anchor = _resolve_snapshot_anchor_entry(
        entries, timestamp_ms=_MIDDAY, covering_entries=covering
    )
    assert anchor is not None
    assert anchor.data_type == "orderbook_snapshot"
    assert anchor.path.endswith("orderbook_snapshot/BTCUSDT/2025/11/12.jsonl.gz")


def test_row_before_first_snapshot_has_no_anchor_no_lookahead() -> None:
    """A row earlier than the only snapshot must NOT borrow a future snapshot."""
    entries = _sparse_book_entries()
    covering = _book_entries_covering_timestamp(entries, timestamp_ms=_DAY12_START)
    anchor = _resolve_snapshot_anchor_entry(
        entries, timestamp_ms=_DAY12_START, covering_entries=covering
    )
    assert anchor is None


def test_tie_break_prefers_later_date_for_forward_delta_pairing() -> None:
    """Same boundary instant in two day files -> prefer the later-dated entry."""
    snap_d11 = _entry(
        data_type="orderbook_snapshot",
        date="2025-11-11",
        path="/silver/orderbook_snapshot/BTCUSDT/2025/11/11.jsonl.gz",
        min_ts=_SNAP_TS,
        max_ts=_SNAP_TS,
    )
    snap_d12, delta_d12 = _sparse_book_entries()
    entries = (snap_d11, snap_d12, delta_d12)
    covering = _book_entries_covering_timestamp(entries, timestamp_ms=_MIDDAY)
    anchor = _resolve_snapshot_anchor_entry(
        entries, timestamp_ms=_MIDDAY, covering_entries=covering
    )
    assert anchor is not None
    assert anchor.date == "2025-11-12"


def test_covering_snapshot_preferred_when_dense_no_regression() -> None:
    """Dense capture: a snapshot covers the row -> Tier-1 path unchanged."""
    dense_snap = _entry(
        data_type="orderbook_snapshot",
        date="2025-11-12",
        path="/silver/orderbook_snapshot/BTCUSDT/2025/11/12.jsonl.gz",
        min_ts=_MIDDAY - 5_000,
        max_ts=_MIDDAY + 5_000,
    )
    older_snap = _entry(
        data_type="orderbook_snapshot",
        date="2025-11-12",
        path="/silver/orderbook_snapshot/BTCUSDT/2025/11/12-early.jsonl.gz",
        min_ts=_SNAP_TS,
        max_ts=_SNAP_TS,
    )
    entries = (older_snap, dense_snap)
    covering = _book_entries_covering_timestamp(entries, timestamp_ms=_MIDDAY)
    anchor = _resolve_snapshot_anchor_entry(
        entries, timestamp_ms=_MIDDAY, covering_entries=covering
    )
    assert anchor is not None
    assert anchor.path.endswith("12.jsonl.gz")  # the covering (dense) one
