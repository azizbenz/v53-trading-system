"""Parity + perf proof for the Arrow window-extraction core (Phase 0).

Gate: the Arrow vectorized slice must select the EXACT same rows (timestamps,
order, values) as the current JSONL per-row filter — the microstructure signal
is preserved bit-for-bit.
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import pyarrow.parquet as pq

from local_replay_runtime.strategy_ladder_arrow_window import (
    load_silver_table,
    slice_window,
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
