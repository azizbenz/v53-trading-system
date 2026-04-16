from __future__ import annotations

import pytest

from data_backbone.microstructure.vpin import (
    DEFAULT_VPIN_BUCKETS_PER_DAY,
    DEFAULT_VPIN_WINDOW_BUCKETS,
    MAX_VPIN_BUCKETS_PER_DAY,
    MAX_VPIN_WINDOW_BUCKETS,
    VPIN_METHOD_VERSION_HASH,
    VpinTradePoint,
    build_equal_volume_buckets,
    compute_vpin,
)


def test_build_equal_volume_buckets_splits_trade_across_bucket_boundary() -> None:
    trades = [
        VpinTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=6.0),
        VpinTradePoint(timestamp_ns=2_000_000_000, price=101.0, volume=6.0),
    ]

    buckets = build_equal_volume_buckets(trades, bucket_volume=5.0)

    assert len(buckets) == 2
    assert buckets[0].total_volume == pytest.approx(5.0)
    assert buckets[1].total_volume == pytest.approx(5.0)
    assert buckets[0].open_price == pytest.approx(100.0)
    assert buckets[0].close_price == pytest.approx(100.0)
    assert buckets[1].open_price == pytest.approx(100.0)
    assert buckets[1].close_price == pytest.approx(101.0)


def test_vpin_is_one_under_one_sided_informed_flow_boundary_case() -> None:
    trades = [
        VpinTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=5.0),
        VpinTradePoint(timestamp_ns=2_000_000_000, price=101.0, volume=5.0),
        VpinTradePoint(timestamp_ns=3_000_000_000, price=102.0, volume=5.0),
        VpinTradePoint(timestamp_ns=4_000_000_000, price=103.0, volume=5.0),
    ]

    result = compute_vpin(
        trades,
        pair="btcusdt",
        buckets_per_day=2,
        window_buckets=2,
        daily_volume=20.0,
    )

    assert result.value == pytest.approx(1.0)
    assert result.n_buckets_used == 2
    assert result.pair == "BTCUSDT"
    assert result.method_version_hash == VPIN_METHOD_VERSION_HASH


def test_vpin_stays_in_unit_interval_on_balanced_flow() -> None:
    trades = [
        VpinTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=4.0),
        VpinTradePoint(timestamp_ns=2_000_000_000, price=101.0, volume=4.0),
        VpinTradePoint(timestamp_ns=3_000_000_000, price=100.0, volume=4.0),
        VpinTradePoint(timestamp_ns=4_000_000_000, price=101.0, volume=4.0),
    ]

    result = compute_vpin(
        trades,
        pair="ETHUSDT",
        buckets_per_day=2,
        window_buckets=2,
        daily_volume=16.0,
    )

    assert 0.0 <= result.value <= 1.0
    assert result.bucket_volume == pytest.approx(8.0)
    assert result.window_used == pytest.approx((2, 3.0))
    assert result.input_data_hash


def test_vpin_uses_defaults_and_available_bucket_window() -> None:
    trades = [
        VpinTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=10.0),
        VpinTradePoint(timestamp_ns=2_000_000_000, price=101.0, volume=10.0),
    ]

    result = compute_vpin(trades, pair="SOLUSDT")

    assert result.n_buckets_used == 50
    assert result.bucket_volume == pytest.approx(0.4)
    assert result.n_events_used == 2
    assert result.window_used == pytest.approx((50, 1.0))
    assert DEFAULT_VPIN_BUCKETS_PER_DAY == 50
    assert DEFAULT_VPIN_WINDOW_BUCKETS == 50


def test_vpin_rejects_invalid_inputs() -> None:
    trades = [
        VpinTradePoint(timestamp_ns=2_000_000_000, price=100.0, volume=5.0),
        VpinTradePoint(timestamp_ns=1_000_000_000, price=101.0, volume=5.0),
    ]

    with pytest.raises(ValueError, match="buckets_per_day"):
        compute_vpin(trades[::-1], pair="BTCUSDT", buckets_per_day=MAX_VPIN_BUCKETS_PER_DAY + 1)

    with pytest.raises(ValueError, match="window_buckets"):
        compute_vpin(trades[::-1], pair="BTCUSDT", window_buckets=MAX_VPIN_WINDOW_BUCKETS + 1)

    with pytest.raises(ValueError, match="strictly ordered"):
        compute_vpin(trades, pair="BTCUSDT", daily_volume=10.0)
