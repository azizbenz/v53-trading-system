from __future__ import annotations

import pytest

from data_backbone.microstructure.kyle_lambda import (
    DEFAULT_KYLE_WINDOW_SECONDS,
    DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    KYLE_LAMBDA_METHOD_VERSION_HASH,
    KyleTradePoint,
    build_kyle_intervals,
    classify_trade_direction,
    compute_normalized_kyle_impact_bps,
    compute_kyle_lambda,
)


def test_classify_trade_direction_prefers_mid_price_then_tick_rule() -> None:
    first = KyleTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=1.0, mid_price=99.5)
    second = KyleTradePoint(timestamp_ns=2_000_000_000, price=99.0, volume=1.0, mid_price=99.5)
    third = KyleTradePoint(timestamp_ns=3_000_000_000, price=99.2, volume=1.0)

    assert classify_trade_direction(first, previous_trade=None) == 1
    assert classify_trade_direction(second, previous_trade=first, previous_sign=1) == -1
    assert classify_trade_direction(third, previous_trade=second, previous_sign=-1) == 1


def test_build_kyle_intervals_aggregates_signed_volume_by_bucket() -> None:
    trades = [
        KyleTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=1.0, mid_price=99.5),
        KyleTradePoint(timestamp_ns=30_000_000_000, price=101.0, volume=2.0, mid_price=100.5),
        KyleTradePoint(timestamp_ns=90_000_000_000, price=100.0, volume=3.0, mid_price=100.5),
    ]

    intervals = build_kyle_intervals(trades)

    assert len(intervals) == 2
    assert intervals[0].signed_volume == pytest.approx(3.0)
    assert intervals[1].signed_volume == pytest.approx(-3.0)


def test_kyle_lambda_positive_on_informed_flow_synthetic() -> None:
    true_lambda = 0.001
    trades = []
    price = 100.0
    timestamp_ns = 1_000_000_000
    for index in range(10):
        signed_volume = 100.0 if index % 2 == 0 else 150.0
        price += true_lambda * signed_volume
        trades.append(
            KyleTradePoint(
                timestamp_ns=timestamp_ns,
                price=price,
                volume=signed_volume,
                mid_price=price - 0.1,
            )
        )
        timestamp_ns += 60_000_000_000

    result = compute_kyle_lambda(trades, pair="btcusdt")

    assert result.value > 0.0
    assert result.is_stale is False
    assert abs(result.value - true_lambda) < 0.0005
    assert result.pair == "BTCUSDT"
    assert result.method_version_hash == KYLE_LAMBDA_METHOD_VERSION_HASH
    assert result.window_used == pytest.approx((None, 600.0))
    assert result.unit_status == "UNNORMALIZED_LOCAL_OLS_SLOPE"
    assert result.cross_pair_comparable is False
    assert result.normalized_kyle_lambda_available is True
    assert result.normalized_unit_status == "NORMALIZED_BPS_FOR_STANDARD_NOTIONAL"
    assert result.normalized_cross_pair_comparable is True


def test_kyle_lambda_marks_zero_variance_as_stale() -> None:
    trades = [
        KyleTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=10.0, mid_price=99.5),
        KyleTradePoint(timestamp_ns=61_000_000_000, price=101.0, volume=10.0, mid_price=100.5),
        KyleTradePoint(timestamp_ns=121_000_000_000, price=102.0, volume=10.0, mid_price=101.5),
    ]

    result = compute_kyle_lambda(trades, pair="ETHUSDT")

    assert result.is_stale is True
    assert result.stale_reason == "zero_signed_volume_variance"


def test_kyle_lambda_rejects_invalid_window() -> None:
    trades = [
        KyleTradePoint(timestamp_ns=1_000_000_000, price=100.0, volume=10.0, mid_price=99.5),
        KyleTradePoint(timestamp_ns=61_000_000_000, price=101.0, volume=12.0, mid_price=100.5),
    ]

    with pytest.raises(ValueError, match="window_seconds"):
        compute_kyle_lambda(trades, pair="BTCUSDT", window_seconds=DEFAULT_KYLE_WINDOW_SECONDS + 20_000.0)


def test_normalized_kyle_increases_with_raw_lambda() -> None:
    low = compute_normalized_kyle_impact_bps(
        0.0005,
        mid_price=100.0,
        standard_quote_notional=DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    )
    high = compute_normalized_kyle_impact_bps(
        0.001,
        mid_price=100.0,
        standard_quote_notional=DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    )

    assert high > low


def test_normalized_kyle_increases_with_standard_notional() -> None:
    low = compute_normalized_kyle_impact_bps(
        0.001,
        mid_price=100.0,
        standard_quote_notional=500.0,
    )
    high = compute_normalized_kyle_impact_bps(
        0.001,
        mid_price=100.0,
        standard_quote_notional=2_000.0,
    )

    assert high > low


def test_normalized_kyle_decreases_with_larger_mid_price() -> None:
    low_mid = compute_normalized_kyle_impact_bps(
        0.001,
        mid_price=100.0,
        standard_quote_notional=DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    )
    high_mid = compute_normalized_kyle_impact_bps(
        0.001,
        mid_price=200.0,
        standard_quote_notional=DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    )

    assert high_mid < low_mid
