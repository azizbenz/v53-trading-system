"""Patch RESUME-INDEX-GAP (2026-05-29) — test that resume placeholders unblock pair_universe.

Reproduces the user's blocker: silver index entries built via v2 resume
optimization have row_count=0 (stat-only placeholder), causing
_build_pair_universe_report to declare PAIR_UNIVERSE_EMPTY and block gold.

The fix introduces _entry_has_silver_data() helper that treats resume
placeholders (row_count=0 + file_hash="") as "has data" when the on-disk
file exists with non-zero size.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_data_factory import (  # noqa: E402
    _build_pair_universe_report,
    _entry_has_silver_data,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (  # noqa: E402
    StrategyLadderSilverIndexEntry,
)


def _make_resume_placeholder_entry(
    *,
    pair: str,
    data_type: str,
    date: str,
    silver_path: Path,
) -> StrategyLadderSilverIndexEntry:
    """Build an entry mimicking the v2 resume short-circuit producer."""

    return StrategyLadderSilverIndexEntry(
        source_id="raw_bybit_spot",
        source_root=str(silver_path.parent),
        exchange="bybit",
        market_type="spot",
        data_type=data_type,
        pair=pair,
        date=date,
        path=str(silver_path.resolve()),
        storage_format="jsonl-gz",
        min_timestamp_ms=None,
        max_timestamp_ms=None,
        row_count=0,
        file_hash="",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="TRADE_SCHEMA_READY",
    )


def test_entry_has_silver_data_returns_true_for_counted_entry(tmp_path: Path) -> None:
    silver_file = tmp_path / "x.jsonl.gz"
    silver_file.write_bytes(b"\x1f\x8b\x08\x00stub")
    entry = StrategyLadderSilverIndexEntry(
        source_id="x",
        source_root=str(tmp_path),
        exchange="bybit",
        market_type="spot",
        data_type="trades",
        pair="BTCUSDT",
        path=str(silver_file.resolve()),
        row_count=42,
        file_hash="abc123",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="TRADE_SCHEMA_READY",
    )

    assert _entry_has_silver_data(entry) is True


def test_entry_has_silver_data_accepts_resume_placeholder_with_file_on_disk(tmp_path: Path) -> None:
    silver_file = tmp_path / "y.jsonl.gz"
    silver_file.write_bytes(b"\x1f\x8b\x08\x00real_data_present")
    entry = _make_resume_placeholder_entry(
        pair="ADAUSDT",
        data_type="ohlcv",
        date="2025-04-29",
        silver_path=silver_file,
    )

    assert _entry_has_silver_data(entry) is True


def test_entry_has_silver_data_rejects_resume_placeholder_when_file_missing(tmp_path: Path) -> None:
    entry = _make_resume_placeholder_entry(
        pair="ETHUSDT",
        data_type="trades",
        date="2025-04-29",
        silver_path=tmp_path / "does_not_exist.jsonl.gz",
    )

    assert _entry_has_silver_data(entry) is False


def test_entry_has_silver_data_rejects_resume_placeholder_when_file_empty(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.jsonl.gz"
    empty_file.write_bytes(b"")
    entry = _make_resume_placeholder_entry(
        pair="LINKUSDT",
        data_type="orderbook_snapshot",
        date="2025-04-29",
        silver_path=empty_file,
    )

    assert _entry_has_silver_data(entry) is False


def test_entry_has_silver_data_rejects_legitimate_zero_rows_with_real_hash(tmp_path: Path) -> None:
    silver_file = tmp_path / "z.jsonl.gz"
    silver_file.write_bytes(b"\x1f\x8b\x08\x00empty_gz_header")
    entry = StrategyLadderSilverIndexEntry(
        source_id="x",
        source_root=str(tmp_path),
        exchange="bybit",
        market_type="spot",
        data_type="trades",
        pair="BTCUSDT",
        path=str(silver_file.resolve()),
        row_count=0,
        file_hash="sha256_of_empty_payload",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="TRADE_SCHEMA_READY",
    )

    assert _entry_has_silver_data(entry) is False


def test_pair_universe_accepts_resume_placeholders_and_marks_pair_available(tmp_path: Path) -> None:
    silver_dir = tmp_path / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    entries: list[StrategyLadderSilverIndexEntry] = []
    for data_type in ("ohlcv", "trades", "orderbook_snapshot", "orderbook_delta"):
        for day in ("2025-04-29", "2025-04-30"):
            silver_file = silver_dir / f"{data_type}_{day}.jsonl.gz"
            silver_file.write_bytes(b"\x1f\x8b\x08\x00real_data")
            entries.append(
                _make_resume_placeholder_entry(
                    pair="ADAUSDT",
                    data_type=data_type,
                    date=day,
                    silver_path=silver_file,
                )
            )

    report = _build_pair_universe_report(
        requested_pairs=("ADAUSDT",),
        index_entries=tuple(entries),
    )

    assert report.pair_universe_status == "PAIR_UNIVERSE_READY"
    assert report.available_pairs == ("ADAUSDT",)
    assert report.missing_pairs == ()
    assert len(report.pair_data_coverage) == 1
    coverage = report.pair_data_coverage[0]
    assert coverage.has_trades is True
    assert coverage.has_klines is True
    assert coverage.has_orderbook is True


def test_pair_universe_still_marks_empty_when_files_absent(tmp_path: Path) -> None:
    silver_dir = tmp_path / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    entries = [
        _make_resume_placeholder_entry(
            pair="BTCUSDT",
            data_type="trades",
            date="2025-04-29",
            silver_path=silver_dir / "missing.jsonl.gz",
        )
    ]

    report = _build_pair_universe_report(
        requested_pairs=("BTCUSDT",),
        index_entries=tuple(entries),
    )

    assert report.pair_universe_status == "PAIR_UNIVERSE_EMPTY"
    assert report.available_pairs == ()
    assert report.missing_pairs == ("BTCUSDT",)
