from __future__ import annotations

import pytest

from data_backbone.microstructure.order_flow_imbalance import (
    MAX_OFI_WINDOW_EVENTS,
    OFI_DEPTH_EPS,
    ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
    OrderBookTopLevelPoint,
    compute_depth_adjusted_ofi,
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
    assert result.raw_ofi == pytest.approx(result.value)
    assert result.unit_status == "RAW_SIGNED_SIZE_IMBALANCE"
    assert result.cross_pair_comparable is False
    assert result.normalization_status == "ENGINE_LOCAL_THRESHOLDS"
    assert result.ofi_depth_adjusted == pytest.approx(result.value / (14.0 + 9.0))
    assert result.depth_adjusted_unit_status == "DEPTH_ADJUSTED_RATIO"
    assert result.depth_adjusted_cross_pair_comparable is True
    assert result.depth_adjustment_status == "DEPTH_ADJUSTED_RATIO"


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

    with pytest.raises(ValueError, match="non-decreasing"):
        compute_order_flow_imbalance(points, pair="BTCUSDT")


def test_depth_adjusted_ofi_returns_none_on_zero_depth() -> None:
    assert (
        compute_depth_adjusted_ofi(
            10.0,
            top_k_bid_depth=0.0,
            top_k_ask_depth=0.0,
            eps=OFI_DEPTH_EPS,
        )
        is None
    )


def test_order_flow_imbalance_marks_zero_depth_as_insufficient() -> None:
    points = [
        OrderBookTopLevelPoint(
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            bid_size=10.0,
            ask_price=101.0,
            ask_size=10.0,
        ),
        OrderBookTopLevelPoint(
            timestamp_ns=2_000_000_000,
            bid_price=100.0,
            bid_size=0.0,
            ask_price=101.0,
            ask_size=0.0,
        ),
    ]

    result = compute_order_flow_imbalance(points, pair="BTCUSDT", window_events=1)

    assert result.ofi_depth_adjusted is None
    assert result.depth_adjusted_cross_pair_comparable is False
    assert result.depth_adjustment_status == "OFI_INSUFFICIENT_DEPTH"
