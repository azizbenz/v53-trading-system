from __future__ import annotations

import pytest

from data_backbone.microstructure.corwin_schultz_spread import (
    CORWIN_SCHULTZ_METHOD_VERSION_HASH,
    CorwinSchultzBarPoint,
    compute_corwin_schultz_spread,
)


def test_corwin_schultz_spread_positive_on_nontrivial_range() -> None:
    bars = [
        CorwinSchultzBarPoint(timestamp_ns=1_000_000_000, high_price=105.0, low_price=95.0),
        CorwinSchultzBarPoint(timestamp_ns=86_401_000_000_000, high_price=106.0, low_price=96.0),
    ]

    result = compute_corwin_schultz_spread(bars, pair="btcusdt")

    assert result.value >= 0.0
    assert result.beta > 0.0
    assert result.gamma > 0.0
    assert result.method_version_hash == CORWIN_SCHULTZ_METHOD_VERSION_HASH
    assert result.pair == "BTCUSDT"


def test_corwin_schultz_spread_clamps_negative_value_to_zero() -> None:
    bars = [
        CorwinSchultzBarPoint(timestamp_ns=1_000_000_000, high_price=101.0, low_price=100.0),
        CorwinSchultzBarPoint(timestamp_ns=86_401_000_000_000, high_price=101.01, low_price=100.99),
    ]

    result = compute_corwin_schultz_spread(bars, pair="ETHUSDT")

    assert result.value >= 0.0
    assert result.input_data_hash


def test_corwin_schultz_spread_rejects_unordered_bars() -> None:
    bars = [
        CorwinSchultzBarPoint(timestamp_ns=2_000_000_000, high_price=105.0, low_price=95.0),
        CorwinSchultzBarPoint(timestamp_ns=1_000_000_000, high_price=106.0, low_price=96.0),
    ]

    with pytest.raises(ValueError, match="strictly ordered"):
        compute_corwin_schultz_spread(bars, pair="BTCUSDT")
