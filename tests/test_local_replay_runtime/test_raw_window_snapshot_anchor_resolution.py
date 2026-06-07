"""Regression tests for the raw-window orderbook-snapshot ANCHOR resolution.

Twin of the A2 gold anchor fix. With sparse capture (~1 snapshot/day) the
snapshot instant rarely overlaps a replay window, so ``_entry_overlaps_window``
drops it, ``snapshot_entry`` is None, the window manifest has no
``raw_book_path``, and B2 fails closed with SPREAD_BLOCKED_BY_MISSING_BOOK for
every candidate (0 trades). ``_resolve_snapshot_anchor_entries`` falls back to
the most recent fully-past snapshot so the slice carries the reconstruction
anchor.
"""
from __future__ import annotations

from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    _entry_overlaps_window,
    _resolve_snapshot_anchor_entries,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)

_SNAP_TS = 1_762_905_602_990  # 2025-11-12 00:00:02
_MIDDAY_WINDOW_START = _SNAP_TS + 12 * 3_600_000


def _snapshot(date: str, path: str, *, min_ts: int, max_ts: int):
    return StrategyLadderSilverIndexEntry(
        source_id=f"book_snapshot_{date}",
        source_root="/scratch",
        source_priority=10,
        exchange="bybit",
        market_type="spot",
        data_type="orderbook_snapshot",
        pair="BTCUSDT",
        timeframe="",
        date=date,
        path=path,
        storage_format="jsonl-gz",
        min_timestamp_ms=min_ts,
        max_timestamp_ms=max_ts,
        row_count=1,
        file_hash=f"hash-{date}",
        depth_source_status="BOOK_DEPTH20_AVAILABLE",
        schema_status="BOOK_SCHEMA_READY",
    )


def test_snapshot_instant_does_not_overlap_later_window() -> None:
    snap = _snapshot(
        "2025-11-12", "/silver/.../12.jsonl.gz", min_ts=_SNAP_TS, max_ts=_SNAP_TS
    )
    assert not _entry_overlaps_window(
        snap,
        window_start_ms=_MIDDAY_WINDOW_START,
        window_end_ms=_MIDDAY_WINDOW_START + 900_000,
    )


def test_anchor_resolves_to_most_recent_past_snapshot() -> None:
    entries = (
        _snapshot(
            "2025-11-12",
            "/silver/orderbook_snapshot/BTCUSDT/2025/11/12.jsonl.gz",
            min_ts=_SNAP_TS,
            max_ts=_SNAP_TS,
        ),
    )
    anchor = _resolve_snapshot_anchor_entries(
        entries, pair="BTCUSDT", window_start_ms=_MIDDAY_WINDOW_START
    )
    assert len(anchor) == 1
    assert anchor[0].path.endswith("12.jsonl.gz")


def test_window_before_first_snapshot_has_no_anchor() -> None:
    entries = (
        _snapshot(
            "2025-11-12", "/silver/.../12.jsonl.gz", min_ts=_SNAP_TS, max_ts=_SNAP_TS
        ),
    )
    # Window starts 1s before the snapshot -> no causal anchor (no look-ahead).
    anchor = _resolve_snapshot_anchor_entries(
        entries, pair="BTCUSDT", window_start_ms=_SNAP_TS - 1_000
    )
    assert anchor == ()


def test_tie_break_prefers_later_dated_snapshot() -> None:
    entries = (
        _snapshot(
            "2025-11-11",
            "/silver/orderbook_snapshot/BTCUSDT/2025/11/11.jsonl.gz",
            min_ts=_SNAP_TS,
            max_ts=_SNAP_TS,
        ),
        _snapshot(
            "2025-11-12",
            "/silver/orderbook_snapshot/BTCUSDT/2025/11/12.jsonl.gz",
            min_ts=_SNAP_TS,
            max_ts=_SNAP_TS,
        ),
    )
    anchor = _resolve_snapshot_anchor_entries(
        entries, pair="BTCUSDT", window_start_ms=_MIDDAY_WINDOW_START
    )
    assert len(anchor) == 1
    assert anchor[0].date == "2025-11-12"


def test_anchor_ignores_other_pairs() -> None:
    other = _snapshot(
        "2025-11-12", "/silver/.../ETH/12.jsonl.gz", min_ts=_SNAP_TS, max_ts=_SNAP_TS
    )
    other = other.model_copy(update={"pair": "ETHUSDT"})
    anchor = _resolve_snapshot_anchor_entries(
        (other,), pair="BTCUSDT", window_start_ms=_MIDDAY_WINDOW_START
    )
    assert anchor == ()
