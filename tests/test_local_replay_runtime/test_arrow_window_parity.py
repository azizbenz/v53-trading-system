"""Parity + perf proof for the Arrow window-extraction core (Phase 0 + 1b).

Gate: the Arrow vectorized slice must select the EXACT same rows (timestamps,
order, values) as the current JSONL per-row filter — the microstructure signal
is preserved bit-for-bit.  Also covers ``slice_window_with_anchor`` (the
book-snapshot anchor logic used in Phase 1b extractor wiring).
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import pyarrow.parquet as pq

from local_replay_runtime.strategy_ladder_arrow_window import (
    load_silver_table,
    resolve_slice_path,
    slice_window,
    slice_window_with_anchor,
    write_window_parquet,
)

BASE = 1_700_000_000_000


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _jsonl_filter(rows: list[dict], start_ms: int, end_ms: int) -> list[dict]:
    """The current per-row JSONL window filter (reference behaviour)."""
    return [r for r in rows if start_ms <= int(r["timestamp_ms"]) <= end_ms]


def _trade_rows(n: int) -> list[dict]:
    return [
        {
            "timestamp_ms": BASE + i * 1000,
            "price": round(100.0 + i * 0.01, 6),
            "qty": round(1.0 + (i % 7) * 0.5, 6),
            "side": "buy" if i % 2 else "sell",
        }
        for i in range(n)
    ]


def test_arrow_slice_matches_jsonl_filter_bit_for_bit(tmp_path: Path) -> None:
    rows = _trade_rows(5_000)
    path = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(path, rows)
    start_ms, end_ms = BASE + 1_000_000, BASE + 3_500_000  # mid window

    expected = _jsonl_filter(rows, start_ms, end_ms)

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    sliced = slice_window(table, start_ms, end_ms)

    # bit parity: same timestamps, same order, same field values
    assert sliced.column("timestamp_ms").to_pylist() == [
        r["timestamp_ms"] for r in expected
    ]
    assert sliced.column("price").to_pylist() == [r["price"] for r in expected]
    assert sliced.column("qty").to_pylist() == [r["qty"] for r in expected]
    assert sliced.column("side").to_pylist() == [r["side"] for r in expected]
    assert sliced.num_rows == len(expected) > 0


def test_window_parquet_roundtrip_preserves_rows(tmp_path: Path) -> None:
    rows = _trade_rows(2_000)
    src = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src, rows)
    load_silver_table.cache_clear()
    sliced = slice_window(load_silver_table(str(src)), BASE, BASE + 500_000)

    pq_path = tmp_path / "window.parquet"
    n = write_window_parquet(sliced, pq_path)
    back = pq.read_table(pq_path)

    assert n == sliced.num_rows
    assert back.column("timestamp_ms").to_pylist() == sliced.column("timestamp_ms").to_pylist()
    assert back.column("price").to_pylist() == sliced.column("price").to_pylist()


def test_arrow_loads_once_and_is_faster_than_reparse(tmp_path: Path) -> None:
    rows = _trade_rows(60_000)
    path = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(path, rows)
    windows = [
        (BASE + i * 2_000_000, BASE + i * 2_000_000 + 4_200_000) for i in range(8)
    ]

    # reference: re-parse the whole file per window (current pattern)
    t0 = time.perf_counter()
    ref_total = 0
    for ws, we in windows:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            parsed = [json.loads(line) for line in handle if line.strip()]
        ref_total += len(_jsonl_filter(parsed, ws, we))
    reparse_s = time.perf_counter() - t0

    # arrow: load once, slice many
    load_silver_table.cache_clear()
    t1 = time.perf_counter()
    table = load_silver_table(str(path))
    arrow_total = 0
    for ws, we in windows:
        arrow_total += slice_window(table, ws, we).num_rows
    arrow_s = time.perf_counter() - t1

    assert arrow_total == ref_total
    # load-once + vectorized slice must beat re-parse-per-window comfortably
    assert arrow_s < reparse_s
    load_silver_table.cache_clear()


# ---------------------------------------------------------------------------
# Phase 1b: slice_window_with_anchor parity tests
# ---------------------------------------------------------------------------


def test_anchor_prepends_last_row_before_window_start(tmp_path: Path) -> None:
    """The anchor row (last row strictly before window_start) must be first in
    the result when no row sits at exactly window_start_ms."""
    rows = _trade_rows(200)
    path = tmp_path / "book.jsonl.gz"
    _write_jsonl_gz(path, rows)
    # window_start between row 99 (ts=BASE+99_000) and row 100 (ts=BASE+100_000)
    # so no row is AT window_start → anchor should be row 99
    window_start_ms = BASE + 99 * 1000 + 500  # half-step
    window_end_ms = BASE + 150 * 1000

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    result = slice_window_with_anchor(table, window_start_ms, window_end_ms)

    ts_list = result.column("timestamp_ms").to_pylist()
    # anchor is row 99 (ts = BASE + 99_000), then rows 100..150
    assert ts_list[0] == BASE + 99 * 1000, "anchor row should be first"
    assert ts_list[1] == BASE + 100 * 1000
    assert ts_list[-1] == window_end_ms


def test_anchor_matches_streaming_reference(tmp_path: Path) -> None:
    """slice_window_with_anchor output must be bit-identical to the streaming
    extractor's anchor behavior.

    The streaming extractor tracks anchor as last row with ts <= window_start,
    but only writes it when anchor_ts < window_start.  When a row exists AT
    window_start_ms the anchor pointer is overwritten to that row and the write
    guard fails — so no extra row is prepended.  Use a window that starts
    between two rows (no row AT window_start_ms) to test the anchor-prepend
    path without triggering that edge case."""
    rows = _trade_rows(500)
    path = tmp_path / "book.jsonl.gz"
    _write_jsonl_gz(path, rows)
    # window_start chosen at a half-step so no row falls exactly at it
    window_start_ms = BASE + 200 * 1000 + 500   # between row 200 and 201
    window_end_ms = BASE + 300 * 1000

    # Reference: streaming extractor behavior (inline copy)
    anchor: dict | None = None
    ref_rows: list[dict] = []
    for row in rows:
        ts = int(row["timestamp_ms"])
        if ts <= window_start_ms:
            anchor = row
        if window_start_ms <= ts <= window_end_ms:
            if anchor is not None and int(anchor["timestamp_ms"]) < window_start_ms and not ref_rows:
                ref_rows.append(anchor)
            ref_rows.append(row)

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    result = slice_window_with_anchor(table, window_start_ms, window_end_ms)

    got_ts = result.column("timestamp_ms").to_pylist()
    expected_ts = [r["timestamp_ms"] for r in ref_rows]
    assert got_ts == expected_ts, "Arrow anchor output diverged from streaming reference"


def test_anchor_suppressed_when_row_at_exact_window_start(tmp_path: Path) -> None:
    """When a row exists at exactly window_start_ms, streaming extractor does
    NOT prepend the prior anchor (the pointer is overwritten).  Arrow must match."""
    rows = _trade_rows(300)
    path = tmp_path / "book.jsonl.gz"
    _write_jsonl_gz(path, rows)
    # window_start_ms exactly matches row 100
    window_start_ms = BASE + 100 * 1000
    window_end_ms = BASE + 150 * 1000

    # Reference: streaming extractor — anchor at 99 gets overwritten by row 100,
    # write guard (anchor_ts < start) fails → no anchor prepended
    ref_rows = [r for r in rows if window_start_ms <= r["timestamp_ms"] <= window_end_ms]

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    result = slice_window_with_anchor(table, window_start_ms, window_end_ms)

    got_ts = result.column("timestamp_ms").to_pylist()
    expected_ts = [r["timestamp_ms"] for r in ref_rows]
    assert got_ts == expected_ts, "Arrow should NOT prepend anchor when row exists at window_start_ms"


def test_anchor_absent_when_no_rows_before_window(tmp_path: Path) -> None:
    """When all rows are >= window_start_ms, no anchor is prepended."""
    rows = _trade_rows(100)
    path = tmp_path / "book.jsonl.gz"
    _write_jsonl_gz(path, rows)
    # window covers ALL rows — no row is strictly before the start
    window_start_ms = BASE  # first row has ts == BASE, not strictly before
    window_end_ms = BASE + 50 * 1000

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    result = slice_window_with_anchor(table, window_start_ms, window_end_ms)
    plain = slice_window(table, window_start_ms, window_end_ms)

    # result == plain (no anchor prepended when no row is strictly before start)
    assert result.column("timestamp_ms").to_pylist() == plain.column("timestamp_ms").to_pylist()


def test_anchor_when_window_has_no_rows(tmp_path: Path) -> None:
    """When window contains zero rows but an anchor exists, anchor is returned."""
    rows = _trade_rows(50)
    path = tmp_path / "book.jsonl.gz"
    _write_jsonl_gz(path, rows)
    # window far in the future — no rows match
    window_start_ms = BASE + 10_000_000
    window_end_ms = BASE + 11_000_000

    load_silver_table.cache_clear()
    table = load_silver_table(str(path))
    result = slice_window_with_anchor(table, window_start_ms, window_end_ms)

    # anchor is row 49 (last row strictly before the future window)
    assert result.num_rows == 1
    assert result.column("timestamp_ms").to_pylist()[0] == BASE + 49 * 1000


# ---------------------------------------------------------------------------
# Phase 1c: resolve_slice_path tests
# ---------------------------------------------------------------------------


def test_resolve_slice_path_prefers_jsonl_gz(tmp_path: Path) -> None:
    """When .jsonl.gz, .jsonl and .parquet all exist, .jsonl.gz (the compressed
    canonical slice format) is preferred."""
    (tmp_path / "trades.jsonl").write_text("")
    (tmp_path / "trades.parquet").write_text("")
    (tmp_path / "trades.jsonl.gz").write_text("")
    result = resolve_slice_path(tmp_path, "trades")
    assert result.name == "trades.jsonl.gz"


def test_resolve_slice_path_falls_back_to_plain_jsonl(tmp_path: Path) -> None:
    """When only plain .jsonl exists (no .gz), it is returned."""
    (tmp_path / "trades.jsonl").write_text("")
    result = resolve_slice_path(tmp_path, "trades")
    assert result.name == "trades.jsonl"


def test_resolve_slice_path_default_when_neither_exists(tmp_path: Path) -> None:
    """When no slice file exists, .jsonl.gz is returned as default (the writer
    creates it compressed)."""
    result = resolve_slice_path(tmp_path, "trades")
    assert result.name == "trades.jsonl.gz"


# ---------------------------------------------------------------------------
# Phase 2: write_rows_parquet (silver dual-write sidecar) parity
# ---------------------------------------------------------------------------


def test_write_rows_parquet_roundtrip_preserves_union_keys(tmp_path: Path) -> None:
    """In-memory rows → Parquet sidecar → load_silver_table must preserve every
    field, including one absent from the first row (the from_pylist row-0-schema
    trap), and stay numerically faithful."""
    from local_replay_runtime.strategy_ladder_arrow_window import write_rows_parquet

    rows = [
        {"timestamp_ms": BASE, "price": 100, "qty": 1},                 # no trade_id
        {"timestamp_ms": BASE + 1000, "price": 100.5, "qty": 0.2, "trade_id": "T2"},
    ]
    pq_path = tmp_path / "trades.parquet"
    n = write_rows_parquet(rows, pq_path)
    assert n == 2
    assert pq_path.is_file()

    load_silver_table.cache_clear()
    back = load_silver_table(str(pq_path)).to_pylist()
    assert [r["timestamp_ms"] for r in back] == [BASE, BASE + 1000]
    assert back[1]["trade_id"] == "T2"          # field absent from row 0 survived
    assert float(back[0]["price"]) == 100.0
    assert float(back[1]["qty"]) == 0.2


def test_write_rows_parquet_empty_is_readable(tmp_path: Path) -> None:
    """An empty silver partition still produces a valid (0-row) Parquet sidecar."""
    from local_replay_runtime.strategy_ladder_arrow_window import write_rows_parquet

    pq_path = tmp_path / "empty.parquet"
    assert write_rows_parquet([], pq_path) == 0
    load_silver_table.cache_clear()
    assert load_silver_table(str(pq_path)).num_rows == 0


# ---------------------------------------------------------------------------
# Phase 3 IPC sidecar: parse path == mmap path == baseline (cross-process share)
# ---------------------------------------------------------------------------


def test_load_silver_table_ipc_sidecar_parity(tmp_path: Path, monkeypatch) -> None:
    rows = _trade_rows(2_000)
    src = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src, rows)

    # baseline: no IPC cache (direct parse)
    monkeypatch.delenv("V53_IPC_CACHE_DIR", raising=False)
    load_silver_table.cache_clear()
    base_rows = load_silver_table(str(src)).to_pylist()

    # IPC active: 1st call parses + writes the sidecar; 2nd call mmaps it
    cache = tmp_path / "ipc"
    cache.mkdir()
    monkeypatch.setenv("V53_IPC_CACHE_DIR", str(cache))
    load_silver_table.cache_clear()
    first = load_silver_table(str(src)).to_pylist()  # parse + write sidecar
    load_silver_table.cache_clear()
    second = load_silver_table(str(src)).to_pylist()  # mmap the sidecar

    assert any(p.suffix == ".arrow" for p in cache.iterdir()), "no IPC sidecar written"
    assert first == base_rows, "parse-then-write path diverged from baseline"
    assert second == base_rows, "mmap path diverged from baseline"
    load_silver_table.cache_clear()
