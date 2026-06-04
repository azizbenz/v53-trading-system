"""End-to-end byte-parity gate for the streamed ``_write_window_slices``.

The Opus audit (2026-06-01) found the building blocks (slice_window, anchor,
resolve) were parity-tested but the INTEGRATED writer — the function that
produces the on-disk slices downstream actually consumes — was not. The earlier
implementation re-serialized ``pa.Table.from_pylist(...).to_pylist()``, which
(a) inferred the schema from row 0 only → silently dropped fields present only
on later rows, and (b) promoted ints to floats. These tests drive the real
``_write_window_slices`` and assert the written slice is byte-for-byte identical
to the verbatim source lines (no field dropped, no number reformatted), plus the
multi-source (schema-drift) and missing-source contracts.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_arrow_window import load_silver_table
import local_replay_runtime.strategy_ladder_raw_window_extractor as extractor
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    _WindowSliceRequest,
    _write_window_slices,
)

BASE = 1_700_000_000_000


def _write_lines(path: Path, lines: list[str], *, gz: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = "\n".join(lines) + "\n"
    if gz:
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(blob)
    else:
        path.write_text(blob, encoding="utf-8")


def _read_lines(path: Path) -> list[str]:
    if path.name.lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


def test_write_slices_byte_exact_on_heterogeneous_rows(tmp_path: Path) -> None:
    """Rows whose first line lacks fields present on later lines (+ an int-valued
    price) must round-trip byte-for-byte — the exact failure the audit flagged."""
    rows = [
        {"timestamp_ms": BASE + 0, "price": 100, "qty": 1},                 # int price, NO extras
        {"timestamp_ms": BASE + 1000, "price": 100.5, "qty": 0.2, "side": "buy"},
        {"timestamp_ms": BASE + 2000, "price": 100.25, "qty": 0.3, "trade_id": "T2"},
        {"timestamp_ms": BASE + 3000, "price": 100.75, "qty": 0.4, "is_buyer_maker": True},
        {"timestamp_ms": BASE + 4000, "price": 101, "qty": 0.5},
    ]
    src_lines = [json.dumps(r) for r in rows]
    src = tmp_path / "trades.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "slice" / "trades.jsonl"

    load_silver_table.cache_clear()
    _write_window_slices(
        (
            _WindowSliceRequest(
                source_path=src,
                target_path=target,
                window_start_ms=BASE + 1000,
                window_end_ms=BASE + 3000,
            ),
        )
    )

    out = _read_lines(target)
    # window covers rows 1,2,3 — byte-identical to the verbatim source lines
    assert out == [src_lines[1], src_lines[2], src_lines[3]]

    # And the fields that the old from_pylist(row-0-schema) path dropped survive.
    parsed = [json.loads(line) for line in out]
    assert parsed[1]["trade_id"] == "T2"
    assert parsed[2]["is_buyer_maker"] is True


def test_write_slices_preserves_int_price_representation(tmp_path: Path) -> None:
    """An integer-valued price must NOT be reformatted to a float (29000 stays
    29000, not 29000.0) — verbatim emission guarantees this."""
    src_lines = [
        json.dumps({"timestamp_ms": BASE + 0, "price": 29000, "qty": 0.01}),
        json.dumps({"timestamp_ms": BASE + 1000, "price": 29000.5, "qty": 0.02}),
    ]
    src = tmp_path / "trades.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "out" / "trades.jsonl"

    load_silver_table.cache_clear()
    _write_window_slices(
        (
            _WindowSliceRequest(
                source_path=src,
                target_path=target,
                window_start_ms=BASE,
                window_end_ms=BASE + 1000,
            ),
        )
    )
    out = _read_lines(target)
    assert out == src_lines
    assert '"price": 29000,' in out[0]  # int, not 29000.0


def test_write_slices_anchor_row_is_byte_exact(tmp_path: Path) -> None:
    """The prepended anchor row (last strictly before window_start) is emitted
    verbatim, ahead of the window rows, in byte-exact form."""
    rows = [{"timestamp_ms": BASE + i * 1000, "price": 100.0 + i, "qty": 0.1} for i in range(10)]
    src_lines = [json.dumps(r) for r in rows]
    src = tmp_path / "orderbook_delta.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "out" / "orderbook_delta.jsonl"

    # window_start between row 4 and 5 (half-step) → anchor must be row 4
    load_silver_table.cache_clear()
    _write_window_slices(
        (
            _WindowSliceRequest(
                source_path=src,
                target_path=target,
                window_start_ms=BASE + 4 * 1000 + 500,
                window_end_ms=BASE + 7 * 1000,
                include_anchor_before_start=True,
            ),
        )
    )
    out = _read_lines(target)
    # anchor (row 4) prepended, then rows 5,6,7 — all verbatim
    assert out == [src_lines[4], src_lines[5], src_lines[6], src_lines[7]]


def test_write_slices_does_not_prepend_anchor_at_exact_start(tmp_path: Path) -> None:
    rows = [{"timestamp_ms": BASE + i * 1000, "price": 100.0 + i} for i in range(4)]
    src_lines = [json.dumps(r) for r in rows]
    src = tmp_path / "orderbook_delta.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "out" / "orderbook_delta.jsonl"

    _write_window_slices(
        (
            _WindowSliceRequest(
                source_path=src,
                target_path=target,
                window_start_ms=BASE + 1000,
                window_end_ms=BASE + 3000,
                include_anchor_before_start=True,
            ),
        )
    )

    assert _read_lines(target) == [src_lines[1], src_lines[2], src_lines[3]]


def test_write_slices_unsorted_source_keeps_exact_anchor_semantics(tmp_path: Path) -> None:
    rows = [
        {"timestamp_ms": BASE + 3000, "price": 103.0},
        {"timestamp_ms": BASE + 1000, "price": 101.0},
        {"timestamp_ms": BASE + 2000, "price": 102.0, "anchor_version": "old"},
        {"timestamp_ms": BASE + 2000, "price": 102.5, "anchor_version": "new"},
    ]
    src_lines = [json.dumps(r) for r in rows]
    src = tmp_path / "orderbook_delta_unsorted.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "out" / "orderbook_delta.jsonl"

    _write_window_slices(
        (
            _WindowSliceRequest(
                source_path=src,
                target_path=target,
                window_start_ms=BASE + 2500,
                window_end_ms=BASE + 3500,
                include_anchor_before_start=True,
            ),
        )
    )

    assert _read_lines(target) == [src_lines[3], src_lines[0]]


def test_write_slices_streams_jsonl_without_arrow_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load_silver_table(path_str: str) -> None:
        raise AssertionError(f"JSONL streaming path loaded Arrow table: {path_str}")

    monkeypatch.setattr(extractor, "load_silver_table", fail_load_silver_table)
    src_lines = [
        json.dumps({"timestamp_ms": BASE + 0, "price": 100.0}),
        json.dumps({"timestamp_ms": BASE + 1000, "price": 100.5}),
        json.dumps({"timestamp_ms": BASE + 2000, "price": 101.0}),
    ]
    src = tmp_path / "trades.jsonl.gz"
    _write_lines(src, src_lines, gz=True)
    target = tmp_path / "out" / "trades.jsonl"

    _write_window_slices(
        (_WindowSliceRequest(src, target, BASE + 1000, BASE + 2000),)
    )

    assert _read_lines(target) == [src_lines[1], src_lines[2]]


def test_write_slices_multi_source_schema_drift_does_not_crash(tmp_path: Path) -> None:
    """Two source files merged into ONE target with DIFFERENT key sets (a field
    present one day, absent the next) must not raise (the old pa.concat_tables
    path could) and must keep every row, verbatim."""
    day1 = [json.dumps({"timestamp_ms": BASE + 0, "price": 100.0, "qty": 0.1, "extra_a": 1})]
    day2 = [json.dumps({"timestamp_ms": BASE + 1000, "price": 101.0, "qty": 0.2, "extra_b": 2})]
    src1 = tmp_path / "d1" / "orderbook_delta.jsonl"
    src2 = tmp_path / "d2" / "orderbook_delta.jsonl"
    _write_lines(src1, day1)
    _write_lines(src2, day2)
    target = tmp_path / "merged" / "orderbook_delta.jsonl"

    load_silver_table.cache_clear()
    _write_window_slices(
        (
            _WindowSliceRequest(src1, target, BASE, BASE + 5000),
            _WindowSliceRequest(src2, target, BASE, BASE + 5000),
        )
    )
    out = _read_lines(target)
    assert out == [day1[0], day2[0]]  # both days present, verbatim, in source order


def test_write_slices_missing_source_creates_empty_file(tmp_path: Path) -> None:
    """A request whose source does not exist still yields an (empty) slice file —
    same contract as the old streaming writer (downstream opens it, finds 0 rows,
    rather than hitting FileNotFoundError)."""
    src = tmp_path / "does_not_exist.jsonl"
    target = tmp_path / "out" / "trades.jsonl"

    load_silver_table.cache_clear()
    stats = _write_window_slices(
        (_WindowSliceRequest(src, target, BASE, BASE + 5000),)
    )
    assert target.is_file()
    assert _read_lines(target) == []
    assert stats.slice_counts[str(target.resolve())] == 0


def test_write_slices_byte_exact_from_gzip_source(tmp_path: Path) -> None:
    """A gz source decompresses and slices to byte-exact verbatim lines."""
    src_lines = [json.dumps({"timestamp_ms": BASE + i * 1000, "price": 100.0 + i, "qty": 0.1}) for i in range(6)]
    src = tmp_path / "trades.jsonl.gz"
    _write_lines(src, src_lines, gz=True)
    target = tmp_path / "out" / "trades.jsonl"

    load_silver_table.cache_clear()
    _write_window_slices(
        (_WindowSliceRequest(src, target, BASE + 2000, BASE + 4000),)
    )
    assert _read_lines(target) == [src_lines[2], src_lines[3], src_lines[4]]


def test_write_slices_byte_exact_to_gzip_target(tmp_path: Path) -> None:
    """A gz target stores the same logical JSONL lines."""
    src_lines = [
        json.dumps({"timestamp_ms": BASE + i * 1000, "price": 100.0 + i, "qty": 0.1})
        for i in range(5)
    ]
    src = tmp_path / "trades.jsonl"
    _write_lines(src, src_lines)
    target = tmp_path / "out" / "trades.jsonl.gz"

    _write_window_slices(
        (_WindowSliceRequest(src, target, BASE + 1000, BASE + 3000),)
    )

    assert _read_lines(target) == [src_lines[1], src_lines[2], src_lines[3]]
