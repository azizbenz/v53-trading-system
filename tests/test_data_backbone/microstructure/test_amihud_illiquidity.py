from __future__ import annotations

from math import log

import pytest

from data_backbone.microstructure.amihud_illiquidity import (
    AMIHUD_METHOD_VERSION_HASH,
    AmihudBarPoint,
    compute_amihud_illiquidity,
)


def test_amihud_illiquidity_matches_manual_average() -> None:
    bars = [
        AmihudBarPoint(timestamp_ns=1_000_000_000, close_price=100.0, dollar_volume=1_000.0),
        AmihudBarPoint(timestamp_ns=61_000_000_000, close_price=101.0, dollar_volume=2_000.0),
        AmihudBarPoint(timestamp_ns=121_000_000_000, close_price=100.5, dollar_volume=1_500.0),
    ]

    result = compute_amihud_illiquidity(bars, pair="btcusdt")
    expected = (
        abs(log(101.0) - log(100.0)) / 2_000.0
        + abs(log(100.5) - log(101.0)) / 1_500.0
    ) / 2.0

    assert result.value == pytest.approx(expected)
    assert result.pair == "BTCUSDT"
    assert result.method_version_hash == AMIHUD_METHOD_VERSION_HASH
    assert result.window_used == pytest.approx((None, 120.0))


def test_amihud_illiquidity_is_non_negative() -> None:
    bars = [
        AmihudBarPoint(timestamp_ns=1_000_000_000, close_price=100.0, dollar_volume=1_000.0),
        AmihudBarPoint(timestamp_ns=61_000_000_000, close_price=100.0, dollar_volume=1_000.0),
    ]

    result = compute_amihud_illiquidity(bars, pair="ETHUSDT")

    assert result.value == pytest.approx(0.0)
    assert result.input_data_hash


def test_amihud_illiquidity_rejects_unordered_bars() -> None:
    bars = [
        AmihudBarPoint(timestamp_ns=2_000_000_000, close_price=100.0, dollar_volume=1_000.0),
        AmihudBarPoint(timestamp_ns=1_000_000_000, close_price=101.0, dollar_volume=1_500.0),
    ]

    with pytest.raises(ValueError, match="non-decreasing"):
        compute_amihud_illiquidity(bars, pair="BTCUSDT")
