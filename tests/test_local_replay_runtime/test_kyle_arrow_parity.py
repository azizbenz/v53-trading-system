"""Phase 1+2 parity gate — reconstruction readers via Arrow core.

Phase 1: _load_sorted_trade_points bit-identical vs JSONL, accepts parquet.
Phase 2: _load_reconstruction_snapshots + _load_reconstruction_deltas
         bit-identical vs JSONL, accepts parquet.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from local_replay_runtime.strategy_ladder_arrow_window import load_silver_table
from local_replay_runtime.strategy_ladder_economic_provenance import (
    _load_reconstruction_deltas,
    _load_reconstruction_snapshots,
    _load_sorted_trade_points,
)

BASE_MS = 1_700_000_000_000


def _trade_rows(n: int) -> list[dict]:
    return [
        {
            "timestamp_ms": BASE_MS + i * 1000,
            "price": round(29_000.0 + i * 0.5, 6),
            "qty": round(0.01 + (i % 13) * 0.003, 6),
            "side": "buy" if i % 2 else "sell",
        }
        for i in range(n)
    ]


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _old_parse(path: Path) -> tuple[tuple[int, float, float], ...]:
    """Reference: the original per-row JSONL parse (inline copy)."""
    result: list[tuple[int, float, float]] = []
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                ts_ms = int(row.get("timestamp_ms") or 0)
                price = float(row.get("price") or 0.0)
                volume = float(row.get("qty") or row.get("volume") or 0.0)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if price <= 0.0 or volume <= 0.0:
                continue
            result.append((ts_ms, price, volume))
    result.sort(key=lambda item: item[0])
    return tuple(result)


def test_arrow_kyle_parse_matches_jsonl_bit_for_bit(tmp_path: Path) -> None:
    rows = _trade_rows(4_000)
    src = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src, rows)

    expected = _old_parse(src)

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    got = _load_sorted_trade_points(str(src))

    assert len(got) == len(expected) > 0
    assert got == expected, "Arrow-backed parse diverged from JSONL reference"


def test_kyle_parse_heterogeneous_rows_match_reference(tmp_path: Path) -> None:
    """Edge cases that stress the per-row qty/volume fallback + skip rules: must
    match the reference parse byte-for-byte (guards the direct-parse Gain-1 path).
    """
    rows = [
        {"timestamp_ms": BASE_MS + 5000, "price": 100.0, "qty": 1.5},          # normal qty
        {"timestamp_ms": BASE_MS + 1000, "price": 101.0, "volume": 2.0},       # volume, no qty -> use volume
        {"timestamp_ms": BASE_MS + 2000, "price": 102.0, "qty": 0, "volume": 3.0},  # qty falsy -> volume
        {"timestamp_ms": BASE_MS + 3000, "price": 103.0, "qty": 0, "volume": 0},     # both 0 -> skipped
        {"timestamp_ms": BASE_MS + 4000, "price": 0.0, "qty": 5.0},            # price 0 -> skipped
        {"timestamp_ms": BASE_MS + 6000, "price": 104.0, "qty": 0.7, "trade_id": "X", "is_buyer_maker": True},  # extras
        {"timestamp_ms": BASE_MS + 500, "price": 105.0, "qty": 0.3},           # earliest -> sort first
    ]
    src = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src, rows)
    expected = _old_parse(src)

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    got = _load_sorted_trade_points(str(src))

    assert got == expected, f"heterogeneous parse diverged: {got} != {expected}"
    # explicit invariants: skipped rows gone, sorted, fallback applied
    assert len(got) == 5  # 7 rows - 2 skipped
    assert [p[0] for p in got] == sorted(p[0] for p in got)  # sorted by ts
    assert got[0] == (BASE_MS + 500, 105.0, 0.3)  # earliest first


def test_arrow_kyle_parquet_equals_jsonl_gz(tmp_path: Path) -> None:
    """Same trade data written as jsonl.gz AND parquet → identical tuples."""
    rows = _trade_rows(2_000)
    src_gz = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src_gz, rows)

    # Write parquet from the same rows via Arrow
    load_silver_table.cache_clear()
    table = load_silver_table(str(src_gz))
    pq_path = tmp_path / "trades.parquet"
    pq.write_table(table, pq_path, compression="zstd")

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    from_gz = _load_sorted_trade_points(str(src_gz))

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    from_pq = _load_sorted_trade_points(str(pq_path))

    assert len(from_gz) > 0
    assert from_gz == from_pq, "Parquet parse diverged from jsonl.gz parse"


def test_kyle_empty_file_returns_empty(tmp_path: Path) -> None:
    src = tmp_path / "empty.jsonl.gz"
    _write_jsonl_gz(src, [])

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    result = _load_sorted_trade_points(str(src))

    assert result == ()


def test_kyle_skips_zero_price_and_volume(tmp_path: Path) -> None:
    rows = [
        {"timestamp_ms": BASE_MS, "price": 0.0, "qty": 1.0},
        {"timestamp_ms": BASE_MS + 1000, "price": 100.0, "qty": 0.0},
        {"timestamp_ms": BASE_MS + 2000, "price": 100.0, "qty": 1.5},
    ]
    src = tmp_path / "trades.jsonl.gz"
    _write_jsonl_gz(src, rows)

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    result = _load_sorted_trade_points(str(src))

    assert len(result) == 1
    ts, price, vol = result[0]
    assert ts == BASE_MS + 2000
    assert price == pytest.approx(100.0)
    assert vol == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Phase 2: _load_reconstruction_snapshots parity
# ---------------------------------------------------------------------------


def _snapshot_rows(n: int) -> list[dict]:
    return [
        {
            "timestamp_ms": BASE_MS + i * 5000,
            "update_id": 1000 + i,
            "bids": [[str(29000.0 - i * 0.1), str(1.0 + i * 0.01)]],
            "asks": [[str(29001.0 + i * 0.1), str(0.5 + i * 0.01)]],
        }
        for i in range(n)
    ]


def _delta_rows(n: int) -> list[dict]:
    return [
        {
            "timestamp_ms": BASE_MS + i * 1000,
            "update_id": 2000 + i,
            "bids": [[str(29000.0 + i * 0.05), str(0.8)]],
            "asks": [[str(29001.0 + i * 0.05), str(0.3)]],
            "type": "delta",
        }
        for i in range(n)
    ]


def _old_parse_snapshots(path: Path) -> tuple[tuple[int, int, dict], ...]:
    """Reference: original JSONL-only snapshot parse."""
    out: list[tuple[int, int, dict]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                ts = int(row.get("timestamp_ms") or 0)
                uid = int(row.get("update_id") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            out.append((ts, uid, row))
    out.sort(key=lambda item: item[0])
    return tuple(out)


def _old_parse_deltas(path: Path) -> tuple[tuple[int, int, dict], ...]:
    """Reference: original JSONL-only delta parse (gz-aware)."""
    import gzip as _gzip
    out: list[tuple[int, int, dict]] = []
    opener = _gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                uid = int(row.get("update_id") or 0)
                ts = int(row.get("timestamp_ms") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            out.append((uid, ts, row))
    out.sort(key=lambda item: item[0])
    return tuple(out)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_reconstruction_snapshots_arrow_matches_jsonl(tmp_path: Path) -> None:
    rows = _snapshot_rows(200)
    src = tmp_path / "orderbook_snapshot.jsonl"
    _write_jsonl(src, rows)

    expected = _old_parse_snapshots(src)

    _load_reconstruction_snapshots.cache_clear()
    load_silver_table.cache_clear()
    got = _load_reconstruction_snapshots(str(src))

    assert len(got) == len(expected) > 0
    for (ts_g, uid_g, row_g), (ts_e, uid_e, row_e) in zip(got, expected):
        assert ts_g == ts_e
        assert uid_g == uid_e
        assert row_g["bids"] == row_e["bids"]
        assert row_g["asks"] == row_e["asks"]


def test_reconstruction_snapshots_parquet_equals_jsonl(tmp_path: Path) -> None:
    rows = _snapshot_rows(100)
    src_jsonl = tmp_path / "orderbook_snapshot.jsonl"
    _write_jsonl(src_jsonl, rows)

    load_silver_table.cache_clear()
    pq_path = tmp_path / "orderbook_snapshot.parquet"
    pq.write_table(load_silver_table(str(src_jsonl)), pq_path)

    _load_reconstruction_snapshots.cache_clear()
    load_silver_table.cache_clear()
    from_jsonl = _load_reconstruction_snapshots(str(src_jsonl))

    _load_reconstruction_snapshots.cache_clear()
    load_silver_table.cache_clear()
    from_pq = _load_reconstruction_snapshots(str(pq_path))

    assert len(from_jsonl) > 0
    assert [(ts, uid) for ts, uid, _ in from_jsonl] == [(ts, uid) for ts, uid, _ in from_pq]
    # The L2 book payload (bids/asks) IS the signal — it must survive the Parquet
    # round-trip bit-for-bit, not just the (ts, uid) keys.
    for (_, _, row_j), (_, _, row_p) in zip(from_jsonl, from_pq):
        assert row_j["bids"] == row_p["bids"]
        assert row_j["asks"] == row_p["asks"]


def test_reconstruction_deltas_arrow_matches_jsonl_gz(tmp_path: Path) -> None:
    rows = _delta_rows(500)
    src = tmp_path / "orderbook_delta.jsonl.gz"
    _write_jsonl_gz(src, rows)

    expected = _old_parse_deltas(src)

    _load_reconstruction_deltas.cache_clear()
    load_silver_table.cache_clear()
    got = _load_reconstruction_deltas(str(src))

    assert len(got) == len(expected) > 0
    for (uid_g, ts_g, _), (uid_e, ts_e, _) in zip(got, expected):
        assert uid_g == uid_e
        assert ts_g == ts_e


def test_reconstruction_deltas_parquet_equals_jsonl_gz(tmp_path: Path) -> None:
    rows = _delta_rows(300)
    src_gz = tmp_path / "orderbook_delta.jsonl.gz"
    _write_jsonl_gz(src_gz, rows)

    load_silver_table.cache_clear()
    pq_path = tmp_path / "orderbook_delta.parquet"
    pq.write_table(load_silver_table(str(src_gz)), pq_path)

    _load_reconstruction_deltas.cache_clear()
    load_silver_table.cache_clear()
    from_gz = _load_reconstruction_deltas(str(src_gz))

    _load_reconstruction_deltas.cache_clear()
    load_silver_table.cache_clear()
    from_pq = _load_reconstruction_deltas(str(pq_path))

    assert len(from_gz) > 0
    assert [(uid, ts) for uid, ts, _ in from_gz] == [(uid, ts) for uid, ts, _ in from_pq]
    # Delta book payload must also survive the Parquet round-trip bit-for-bit.
    for (_, _, row_g), (_, _, row_p) in zip(from_gz, from_pq):
        assert row_g["bids"] == row_p["bids"]
        assert row_g["asks"] == row_p["asks"]


def test_kyle_per_row_qty_volume_fallback(tmp_path: Path) -> None:
    """A row with a falsy ``qty`` but a positive ``volume`` must defer to volume
    PER ROW (old ``row.get('qty') or row.get('volume')`` semantics), not be
    dropped because the column-wide branch only looked at ``qty``."""
    rows = [
        {"timestamp_ms": BASE_MS + 0, "price": 100.0, "qty": 0.0, "volume": 2.0},   # qty falsy → use volume
        {"timestamp_ms": BASE_MS + 1000, "price": 101.0, "qty": 1.5, "volume": 9.9},  # qty wins
    ]
    src = tmp_path / "trades.jsonl"
    _write_jsonl(src, rows)

    _load_sorted_trade_points.cache_clear()
    load_silver_table.cache_clear()
    result = _load_sorted_trade_points(str(src))

    assert len(result) == 2
    assert result[0] == (BASE_MS + 0, 100.0, 2.0)       # fell back to volume
    assert result[1] == (BASE_MS + 1000, 101.0, 1.5)    # used qty


def test_load_silver_table_keeps_field_absent_from_first_row(tmp_path: Path) -> None:
    """Union-key parse: a field present only on a LATER row is NOT dropped (the
    from_pylist row-0-schema bug the audit flagged)."""
    rows = [
        {"timestamp_ms": BASE_MS + 0, "price": 100.0, "qty": 0.1},
        {"timestamp_ms": BASE_MS + 1000, "price": 101.0, "qty": 0.2, "trade_id": "LATE"},
    ]
    src = tmp_path / "trades.jsonl"
    _write_jsonl(src, rows)

    load_silver_table.cache_clear()
    table = load_silver_table(str(src))
    assert "trade_id" in table.column_names
    assert table.column("trade_id").to_pylist()[1] == "LATE"
