"""Gate — engine input builders read .jsonl.gz raw paths without crashing.

Reproduces the production bug surfaced by the cockpit candidate detail (run
7ec6198f): ENGINE_NATIVE_RUN_FAILED:UnicodeDecodeError 0x8b — the engine_a/c/d
input builders opened raw_ohlcv_path / raw_trade_path as PLAIN text, so a
``.jsonl.gz`` path (silver passthrough OR the new compressed slices) crashed on
the gzip magic byte and hard-blocked the candidate. These builders MUST be
gz-aware (the rest of the pipeline already is).
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_a_input_builder import (
    _load_ohlcv_in_window as a_load_ohlcv,
)
from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
    _load_ohlcv_in_window as c_load_ohlcv,
    _compute_realized_vol_at_break as c_realized_vol,
)
from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
    _load_ohlcv_in_window as d_load_ohlcv,
)

CT = 1_700_000_000_000


def _ohlcv_rows() -> list[dict]:
    return [
        {"timestamp_ms": CT - i * 60_000, "open": 100.0 + i, "high": 101.0 + i,
         "low": 99.0 + i, "close": 100.5 + i, "volume": 10.0 + i}
        for i in range(10)
    ]


def _trade_rows() -> list[dict]:
    # oscillating prices so realized kernel vol has return variation to estimate
    return [
        {"timestamp_ms": CT - i * 1000,
         "price": round(29000.0 + (10.0 if i % 2 else -8.0), 2), "qty": 0.1}
        for i in range(60)
    ]


def _write_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r) + "\n")


def test_engine_a_loads_ohlcv_from_gz(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl.gz"
    _write_gz(p, _ohlcv_rows())
    rows = a_load_ohlcv(p, window_start_ms=CT - 600_000, window_end_ms=CT, lookback_ms=0)
    assert len(rows) > 0  # would raise UnicodeDecodeError before the fix


def test_engine_c_loads_ohlcv_from_gz(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl.gz"
    _write_gz(p, _ohlcv_rows())
    rows = c_load_ohlcv(p, window_start_ms=CT - 600_000, window_end_ms=CT, lookback_ms=0)
    assert len(rows) > 0


def test_engine_c_realized_vol_gz_equals_plain(tmp_path: Path) -> None:
    """The gz trade read must produce the SAME realized-vol result as plain
    .jsonl (proves the read is equivalent, no crash, no data divergence). The
    bug was a UnicodeDecodeError on the .gz path; parity is the gate."""
    rows = _trade_rows()
    gz = tmp_path / "trades.jsonl.gz"
    plain = tmp_path / "trades.jsonl"
    _write_gz(gz, rows)
    plain.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    rec_gz = c_realized_vol(pair="BTCUSDT", raw_trade_path=gz, t_break_ms=CT, lookback_ms=60_000)
    rec_plain = c_realized_vol(pair="BTCUSDT", raw_trade_path=plain, t_break_ms=CT, lookback_ms=60_000)
    # identical outcome regardless of compression (both None or equal record)
    assert (rec_gz is None) == (rec_plain is None)
    if rec_gz is not None:
        assert rec_gz == rec_plain


def test_engine_d_loads_ohlcv_from_gz(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl.gz"
    _write_gz(p, _ohlcv_rows())
    rows = d_load_ohlcv(p, window_start_ms=CT - 600_000, window_end_ms=CT, lookback_ms=0)
    assert len(rows) > 0


def test_engine_a_plain_jsonl_still_works(tmp_path: Path) -> None:
    """Back-compat: plain .jsonl (no gz) must still load."""
    p = tmp_path / "ohlcv.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in _ohlcv_rows()) + "\n", encoding="utf-8")
    rows = a_load_ohlcv(p, window_start_ms=CT - 600_000, window_end_ms=CT, lookback_ms=0)
    assert len(rows) > 0
