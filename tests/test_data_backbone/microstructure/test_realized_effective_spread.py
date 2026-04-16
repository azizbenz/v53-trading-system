from __future__ import annotations

import pytest

from data_backbone.microstructure.realized_effective_spread import (
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
    LiveSpreadObservation,
    compute_realized_effective_spread,
)
from interface_contracts.domain_types import Side


def test_realized_effective_spread_for_buy_observation() -> None:
    observation = LiveSpreadObservation(
        timestamp_ns=1_000_000_000,
        bid_price=99.0,
        ask_price=101.0,
        execution_price=100.5,
        side=Side.BUY,
        future_mid_price=101.0,
    )

    result = compute_realized_effective_spread(observation, pair="btcusdt")

    assert result.quoted_spread == pytest.approx(2.0)
    assert result.effective_spread == pytest.approx(1.0)
    assert result.realized_spread == pytest.approx(-1.0)
    assert result.method_version_hash == REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH
    assert result.pair == "BTCUSDT"


def test_realized_effective_spread_for_sell_observation() -> None:
    observation = LiveSpreadObservation(
        timestamp_ns=1_000_000_000,
        bid_price=99.0,
        ask_price=101.0,
        execution_price=99.5,
        side=Side.SELL,
        future_mid_price=99.0,
    )

    result = compute_realized_effective_spread(observation, pair="ETHUSDT")

    assert result.realized_spread == pytest.approx(-1.0)
    assert result.window_used == (1, 300.0)
    assert result.input_data_hash


def test_realized_effective_spread_rejects_crossed_book() -> None:
    with pytest.raises(ValueError, match="ask_price"):
        LiveSpreadObservation(
            timestamp_ns=1_000_000_000,
            bid_price=101.0,
            ask_price=99.0,
            execution_price=100.0,
            side=Side.BUY,
            future_mid_price=100.0,
        )
