from __future__ import annotations

import pytest

from data_backbone.microstructure.order_flow_imbalance import (
    MAX_OFI_WINDOW_EVENTS,
    ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
    OrderBookTopLevelPoint,
    compute_order_book_event_contribution,
    compute_order_flow_imbalance,
)


def test_order_book_event_contribution_matches_cont_formula() -> None:
    previous = OrderBookTopLevelPoint(
        timestamp_ns=1_000_000_000,
        bid_price=100.0,
        bid_size=10.0,
        ask_price=101.0,
        ask_size=12.0,
    )
    current = OrderBookTopLevelPoint(
        timestamp_ns=2_000_000_000,
        bid_price=100.0,
        bid_size=14.0,
        ask_price=101.0,
        ask_size=9.0,
    )

    assert compute_order_book_event_contribution(previous, current) == pytest.approx(7.0)


def test_order_flow_imbalance_cumulates_last_n_events_only() -> None:
    points = [
        OrderBookTopLevelPoint(  # e1 = +1
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            bid_size=10.0,
            ask_price=101.0,
            ask_size=10.0,
        ),
        OrderBookTopLevelPoint(
            timestamp_ns=2_000_000_000,
            bid_price=100.0,
            bid_size=12.0,
            ask_price=101.0,
            ask_size=11.0,
        ),
        OrderBookTopLevelPoint(  # e2 = -23
            timestamp_ns=3_000_000_000,
            bid_price=99.5,
            bid_size=8.0,
            ask_price=100.5,
            ask_size=11.0,
        ),
        OrderBookTopLevelPoint(  # e3 = +16
            timestamp_ns=4_000_000_000,
            bid_price=100.0,
            bid_size=14.0,
            ask_price=100.5,
            ask_size=9.0,
        ),
    ]

    result = compute_order_flow_imbalance(points, pair="btcusdt", window_events=2)

    assert result.value == pytest.approx(-7.0)
    assert result.window_used == pytest.approx((2, 2.0))
    assert result.n_events_used == 3
    assert result.pair == "BTCUSDT"
    assert result.method_version_hash == ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH


def test_order_flow_imbalance_uses_available_events_when_window_is_larger() -> None:
    points = [
        OrderBookTopLevelPoint(
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            bid_size=10.0,
            ask_price=101.0,
            ask_size=11.0,
        ),
        OrderBookTopLevelPoint(
            timestamp_ns=2_000_000_000,
            bid_price=100.0,
            bid_size=13.0,
            ask_price=101.0,
            ask_size=10.0,
        ),
    ]

    result = compute_order_flow_imbalance(points, pair="ETHUSDT", window_events=200)

    assert result.window_used == pytest.approx((1, 1.0))
    assert result.n_events_used == 2
    assert result.input_data_hash


def test_order_flow_imbalance_rejects_invalid_inputs() -> None:
    points = [
        OrderBookTopLevelPoint(
            timestamp_ns=2_000_000_000,
            bid_price=100.0,
            bid_size=10.0,
            ask_price=101.0,
            ask_size=11.0,
        ),
        OrderBookTopLevelPoint(
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            bid_size=13.0,
            ask_price=101.0,
            ask_size=10.0,
        ),
    ]

    with pytest.raises(ValueError, match="window_events"):
        compute_order_flow_imbalance(points[::-1], pair="BTCUSDT", window_events=MAX_OFI_WINDOW_EVENTS + 1)

    with pytest.raises(ValueError, match="strictly ordered"):
        compute_order_flow_imbalance(points, pair="BTCUSDT")
