"""OHLCV temporal-completeness validator — coverage for 5m / 15m timeframes.

Latent defect (validated 2026-06-04): `_assess_ohlcv_temporal_completeness`
only knew the critical set {1m, 10m}. Any run whose timeframes were not in that
set (e.g. the canonical 5m / 15m research run) produced a *structural*
`OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN` — the validator skipped the entries
entirely rather than assessing them. These tests lock the corrected behaviour:
5m / 15m are now first-class assessable timeframes with the same severity
classifier (READY / PARTIAL_DAY_ACCEPTED / BLOCKED / NOT_PROVEN) as 1m / 10m.
"""

from __future__ import annotations

from local_replay_runtime import strategy_ladder_data_factory as data_factory_module
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)


def _ohlcv_entry(
    *,
    timeframe: str,
    date: str,
    row_count: int,
    expected_interval_ms: int,
    missing: int = 0,
    duplicate: int = 0,
) -> StrategyLadderSilverIndexEntry:
    return StrategyLadderSilverIndexEntry(
        source_id=f"kline_{timeframe}_{date}",
        source_root="/scratch",
        source_priority=10,
        exchange="bybit",
        market_type="spot",
        data_type="ohlcv",
        pair="BTCUSDT",
        timeframe=timeframe,
        date=date,
        path=f"/scratch/{timeframe}/{date}.jsonl",
        storage_format="jsonl",
        min_timestamp_ms=0,
        max_timestamp_ms=0,
        row_count=row_count,
        file_hash=f"hash-{timeframe}-{date}",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="KLINE_SCHEMA_READY",
        expected_interval_ms=expected_interval_ms,
        missing_candle_count=missing,
        duplicate_candle_count=duplicate,
    )


def _assess(
    entries: list[StrategyLadderSilverIndexEntry],
    timeframes: tuple[str, ...],
) -> tuple[str, int, tuple[str, ...], tuple[str, ...]]:
    return data_factory_module._assess_ohlcv_temporal_completeness(
        index_entries=tuple(entries),
        requested_timeframes=timeframes,
        expected_dates=(),
    )


def test_5m_15m_full_days_ready() -> None:
    """Red-green for the validator gap: full 5m (288/day) + 15m (96/day) → READY.

    Before the fix this returned a structural NOT_PROVEN (empty critical set).
    """
    dates = ("2025-01-01", "2025-01-02", "2025-01-03")
    entries = [
        _ohlcv_entry(timeframe="5m", date=d, row_count=288, expected_interval_ms=300_000)
        for d in dates
    ] + [
        _ohlcv_entry(timeframe="15m", date=d, row_count=96, expected_interval_ms=900_000)
        for d in dates
    ]
    status, blocked, critical, blockers = _assess(entries, ("5m", "15m"))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_READY"
    assert critical == ("5m", "15m")
    assert blocked == 0
    assert blockers == ()


def test_5m_partial_day_accepted() -> None:
    """200/288 = 69.4% (>=65%, <99%) → research-acceptable, promotion-blocked."""
    entries = [
        _ohlcv_entry(
            timeframe="5m", date="2025-01-01", row_count=200, expected_interval_ms=300_000
        ),
    ]
    status, blocked, critical, blockers = _assess(entries, ("5m",))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_PARTIAL_DAY_ACCEPTED"
    assert "OHLCV_5M_PARTIAL_DAY_ACCEPTED" in blockers
    assert blocked == 0


def test_5m_interval_mismatch_is_hard_blocked() -> None:
    """Wrong interval (900_000 = 15m) on a 5m entry = data-integrity fail → BLOCKED."""
    entries = [
        _ohlcv_entry(
            timeframe="5m", date="2025-01-01", row_count=288, expected_interval_ms=900_000
        ),
    ]
    status, blocked, critical, blockers = _assess(entries, ("5m",))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED"
    assert "OHLCV_5M_TEMPORAL_COMPLETENESS_BLOCKED" in blockers
    assert blocked == 1


def test_15m_missing_candles_is_hard_blocked() -> None:
    """Internal gap (missing_candle_count > 0) is always fail-close → BLOCKED."""
    entries = [
        _ohlcv_entry(
            timeframe="15m",
            date="2025-01-01",
            row_count=96,
            expected_interval_ms=900_000,
            missing=2,
        ),
    ]
    status, blocked, critical, blockers = _assess(entries, ("15m",))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED"
    assert "OHLCV_15M_TEMPORAL_COMPLETENESS_BLOCKED" in blockers


def test_5m_below_min_assessment_is_not_proven() -> None:
    """Too few rows (10 < min-assessment 20) → NOT_PROVEN (cannot judge), not BLOCKED."""
    entries = [
        _ohlcv_entry(
            timeframe="5m", date="2025-01-01", row_count=10, expected_interval_ms=300_000
        ),
    ]
    status, blocked, critical, blockers = _assess(entries, ("5m",))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN"
    assert "OHLCV_5M_TEMPORAL_COMPLETENESS_NOT_PROVEN" in blockers
    assert blocked == 0


def test_1m_10m_full_days_still_ready_regression() -> None:
    """Existing 1m / 10m behaviour must be unchanged by the 5m / 15m extension."""
    entries = [
        _ohlcv_entry(
            timeframe="1m", date="2025-01-01", row_count=1440, expected_interval_ms=60_000
        ),
        _ohlcv_entry(
            timeframe="10m", date="2025-01-01", row_count=144, expected_interval_ms=600_000
        ),
    ]
    status, blocked, critical, blockers = _assess(entries, ("1m", "10m"))
    assert status == "OHLCV_TEMPORAL_COMPLETENESS_READY"
    assert critical == ("1m", "10m")
