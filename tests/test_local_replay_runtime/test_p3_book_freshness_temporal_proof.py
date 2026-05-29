"""P3 (2026-05-29) — test book freshness temporal proof on gold rows.

Covers B1+B2+C1+C5 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - B1: per-timeframe `max_book_age_ms` configurable
  - B2: explicit `book_freshness_status` enum (FRESH/STALE/MISSING)
  - C5: per-TF calibration: 1m=10s, 5m=30s, 15m=60s, 1h=300s
  - measure_spread_bps_from_book_snapshot returns 3-tuple with age_ms

Validates:
  - Schema accepts 3 new fields (back-compat)
  - tolerance_ms_for_timeframe returns correct value per TF
  - derive_book_freshness_status derives correct enum
  - measure_spread returns age_ms in the 3-tuple
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_economic_provenance import (
    derive_book_freshness_status,
    measure_spread_bps_from_book_snapshot,
    tolerance_ms_for_timeframe,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def test_tolerance_ms_for_timeframe_returns_calibrated_value_per_tf() -> None:
    """Audit C5 calibration: 1m=10s, 5m=30s, 15m=60s, 1h=300s."""
    assert tolerance_ms_for_timeframe("1m") == 10_000
    assert tolerance_ms_for_timeframe("3m") == 20_000
    assert tolerance_ms_for_timeframe("5m") == 30_000
    assert tolerance_ms_for_timeframe("15m") == 60_000
    assert tolerance_ms_for_timeframe("30m") == 120_000
    assert tolerance_ms_for_timeframe("1h") == 300_000
    assert tolerance_ms_for_timeframe("4h") == 600_000
    assert tolerance_ms_for_timeframe("1d") == 1_800_000


def test_tolerance_ms_for_timeframe_falls_back_to_60s_for_unknown() -> None:
    assert tolerance_ms_for_timeframe("unknown") == 60_000
    assert tolerance_ms_for_timeframe("") == 60_000
    assert tolerance_ms_for_timeframe(None) == 60_000


def test_tolerance_ms_for_timeframe_normalizes_case_and_whitespace() -> None:
    assert tolerance_ms_for_timeframe("15M") == 60_000
    assert tolerance_ms_for_timeframe("  1h  ") == 300_000


def test_derive_book_freshness_status_fresh_when_within_tolerance() -> None:
    assert derive_book_freshness_status(
        age_ms=5_000, tolerance_ms=10_000
    ) == "BOOK_DEPTH20_AVAILABLE_FRESH"
    # Edge case: exactly at tolerance counts as FRESH
    assert derive_book_freshness_status(
        age_ms=10_000, tolerance_ms=10_000
    ) == "BOOK_DEPTH20_AVAILABLE_FRESH"


def test_derive_book_freshness_status_stale_when_beyond_tolerance() -> None:
    assert derive_book_freshness_status(
        age_ms=120_000, tolerance_ms=60_000, stale_max_age_ms=24 * 60 * 60 * 1000
    ) == "BOOK_DEPTH20_AVAILABLE_STALE"


def test_derive_book_freshness_status_missing_when_beyond_stale_max() -> None:
    assert derive_book_freshness_status(
        age_ms=25 * 60 * 60 * 1000, tolerance_ms=60_000, stale_max_age_ms=24 * 60 * 60 * 1000
    ) == "BOOK_DEPTH20_MISSING"


def test_derive_book_freshness_status_missing_when_snapshot_not_found() -> None:
    assert derive_book_freshness_status(
        age_ms=None, tolerance_ms=60_000, snapshot_found=False
    ) == "BOOK_DEPTH20_MISSING"


def test_derive_book_freshness_status_not_proven_when_age_unknown() -> None:
    """age_ms=None + snapshot_found=True (not yet measured) → NOT_PROVEN."""
    assert derive_book_freshness_status(
        age_ms=None, tolerance_ms=60_000, snapshot_found=True
    ) == "BOOK_FRESHNESS_NOT_PROVEN"


def test_measure_spread_returns_3_tuple_with_age_ms_for_fresh_snapshot(
    tmp_path: Path,
) -> None:
    book_file = tmp_path / "orderbook_snapshot.jsonl"
    rows = [
        {
            "timestamp_ms": 1_745_884_800_000,
            "bids": [["100.00", "10"]],
            "asks": [["100.10", "10"]],
        },
    ]
    book_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    spread_bps, status, age_ms = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_file,
        timestamp_ms=1_745_884_800_500,  # 500ms after the snapshot
        tolerance_ms=60_000,
    )

    assert spread_bps is not None
    assert status == "MEASURED_FROM_BOOK_SNAPSHOT"
    assert age_ms == 500


def test_measure_spread_returns_none_age_when_book_path_missing() -> None:
    spread_bps, status, age_ms = measure_spread_bps_from_book_snapshot(
        raw_book_path=None,
        timestamp_ms=1_745_884_800_000,
    )

    assert spread_bps is None
    assert status == "BOOK_PATH_MISSING"
    assert age_ms is None


def test_measure_spread_returns_age_for_stale_snapshot(tmp_path: Path) -> None:
    book_file = tmp_path / "orderbook_snapshot.jsonl"
    rows = [
        {
            "timestamp_ms": 1_745_884_800_000,
            "bids": [["100.00", "10"]],
            "asks": [["100.10", "10"]],
        },
    ]
    book_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Request a timestamp far beyond tolerance but within stale_max
    spread_bps, status, age_ms = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_file,
        timestamp_ms=1_745_884_800_000 + 5 * 60 * 60 * 1000,  # 5 hours later
        tolerance_ms=60_000,
        enable_reconstruction_fallback=False,  # force stale path
    )

    assert spread_bps is not None
    assert status == "MEASURED_FROM_BOOK_SNAPSHOT_STALE"
    assert age_ms == 5 * 60 * 60 * 1000


def test_strategy_ladder_feature_row_accepts_p3_freshness_fields() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        book_snapshot_age_ms=42_000,
        book_freshness_status="BOOK_DEPTH20_AVAILABLE_FRESH",
        book_freshness_tolerance_ms=60_000,
    )

    assert row.book_snapshot_age_ms == 42_000
    assert row.book_freshness_status == "BOOK_DEPTH20_AVAILABLE_FRESH"
    assert row.book_freshness_tolerance_ms == 60_000


def test_strategy_ladder_feature_row_p3_back_compat_defaults() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
    )

    assert row.book_snapshot_age_ms is None
    assert row.book_freshness_status == "BOOK_FRESHNESS_NOT_PROVEN"
    assert row.book_freshness_tolerance_ms is None
