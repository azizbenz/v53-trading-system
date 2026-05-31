"""W2 (2026-05-30) — test post_fill_mid_price computation from OHLCV.

Closes the canonical adverse_selection meter dependency. Per
shadow_execution_simulator._resolve_adverse_selection_surface_resolution,
adverse_selection_fraction requires `post_fill_mid_price` to be set,
otherwise `ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY`.

Validates:
  - Helper reads OHLCV and returns close at `fill_timestamp + delay_ms`
  - Returns None when path missing / no rows after target
  - Handles both jsonl and jsonl.gz
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_detailed_replay import (
    _W2_DEFAULT_ADVERSE_SELECTION_DELAY_MS,
    _compute_post_fill_mid_from_ohlcv,
)


def _write_ohlcv(path: Path, *, gz: bool, rows: list[dict]) -> None:
    body = "\n".join(json.dumps(r) for r in rows) + "\n"
    if gz:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(body)
    else:
        path.write_text(body, encoding="utf-8")


def test_helper_returns_next_close_after_fill_plus_delay(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl"
    fill = 1_700_000_000_000
    _write_ohlcv(
        p,
        gz=False,
        rows=[
            {"timestamp_ms": fill - 60_000, "close": 99.5},
            {"timestamp_ms": fill, "close": 100.0},  # candle at fill
            {"timestamp_ms": fill + 60_000, "close": 100.5},  # next candle (after +5s)
            {"timestamp_ms": fill + 120_000, "close": 101.0},
        ],
    )

    result = _compute_post_fill_mid_from_ohlcv(
        str(p),
        fill_timestamp_ms=fill,
        delay_ms=5_000,
    )

    # Target = fill + 5s. The closest row >= target is fill+60s with close 100.5
    assert result == 100.5


def test_helper_returns_close_in_same_candle_when_candle_after_target(tmp_path: Path) -> None:
    """When target ts falls exactly on a candle boundary, return that close."""
    p = tmp_path / "ohlcv.jsonl"
    fill = 1_700_000_000_000
    _write_ohlcv(
        p,
        gz=False,
        rows=[
            {"timestamp_ms": fill, "close": 100.0},
            {"timestamp_ms": fill + 5_000, "close": 100.2},  # exactly fill+5s
            {"timestamp_ms": fill + 60_000, "close": 100.5},
        ],
    )

    result = _compute_post_fill_mid_from_ohlcv(
        str(p),
        fill_timestamp_ms=fill,
        delay_ms=5_000,
    )

    # ts >= target → fill+5s with close 100.2 is the closest
    assert result == 100.2


def test_helper_returns_none_when_path_missing() -> None:
    result = _compute_post_fill_mid_from_ohlcv(
        None,
        fill_timestamp_ms=1_700_000_000_000,
    )
    assert result is None

    result = _compute_post_fill_mid_from_ohlcv(
        "/nonexistent/path.jsonl",
        fill_timestamp_ms=1_700_000_000_000,
    )
    assert result is None


def test_helper_returns_none_when_no_rows_after_target(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl"
    fill = 1_700_000_000_000
    _write_ohlcv(
        p,
        gz=False,
        rows=[
            {"timestamp_ms": fill - 60_000, "close": 99.5},
            {"timestamp_ms": fill - 30_000, "close": 99.8},
        ],
    )

    result = _compute_post_fill_mid_from_ohlcv(
        str(p),
        fill_timestamp_ms=fill,
        delay_ms=5_000,
    )
    assert result is None


def test_helper_handles_jsonl_gz(tmp_path: Path) -> None:
    p = tmp_path / "ohlcv.jsonl.gz"
    fill = 1_700_000_000_000
    _write_ohlcv(
        p,
        gz=True,
        rows=[
            {"timestamp_ms": fill + 60_000, "close": 100.5},
        ],
    )

    result = _compute_post_fill_mid_from_ohlcv(
        str(p),
        fill_timestamp_ms=fill,
        delay_ms=5_000,
    )
    assert result == 100.5


def test_default_delay_constant_matches_canonical_policy() -> None:
    """5s = CANONICAL_ADVERSE_SELECTION_DELAY_POLICY.default_delay_s × 1000."""
    assert _W2_DEFAULT_ADVERSE_SELECTION_DELAY_MS == 5_000
