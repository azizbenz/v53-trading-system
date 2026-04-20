from __future__ import annotations

import pytest

from data_backbone.microstructure.roll_spread import (
    ROLL_SPREAD_METHOD_VERSION_HASH,
    RollTradePoint,
    compute_roll_spread,
)


def test_roll_spread_positive_when_lagged_covariance_is_negative() -> None:
    trades = [
        RollTradePoint(timestamp_ns=1_000_000_000, price=100.0),
        RollTradePoint(timestamp_ns=2_000_000_000, price=101.0),
        RollTradePoint(timestamp_ns=3_000_000_000, price=100.0),
        RollTradePoint(timestamp_ns=4_000_000_000, price=101.0),
        RollTradePoint(timestamp_ns=5_000_000_000, price=100.0),
    ]

    result = compute_roll_spread(trades, pair="btcusdt")

    assert result.value > 0.0
    assert result.covariance < 0.0
    assert result.pair == "BTCUSDT"
    assert result.method_version_hash == ROLL_SPREAD_METHOD_VERSION_HASH


def test_roll_spread_zero_when_covariance_is_non_negative() -> None:
    trades = [
        RollTradePoint(timestamp_ns=1_000_000_000, price=100.0),
        RollTradePoint(timestamp_ns=2_000_000_000, price=101.0),
        RollTradePoint(timestamp_ns=3_000_000_000, price=102.0),
        RollTradePoint(timestamp_ns=4_000_000_000, price=103.0),
    ]

    result = compute_roll_spread(trades, pair="ETHUSDT")

    assert result.value == pytest.approx(0.0)
    assert result.covariance >= 0.0


def test_roll_spread_rejects_unordered_trades() -> None:
    trades = [
        RollTradePoint(timestamp_ns=2_000_000_000, price=100.0),
        RollTradePoint(timestamp_ns=1_000_000_000, price=101.0),
        RollTradePoint(timestamp_ns=3_000_000_000, price=100.0),
    ]

    with pytest.raises(ValueError, match="non-decreasing"):
        compute_roll_spread(trades, pair="BTCUSDT")
