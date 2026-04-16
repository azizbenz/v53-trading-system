from __future__ import annotations

import pytest

from data_backbone.microstructure.queue_pressure import (
    DEFAULT_QUEUE_PRESSURE_TOP_K,
    QUEUE_PRESSURE_METHOD_VERSION_HASH,
    QueuePressureBookPoint,
    compute_queue_pressure,
)


def test_queue_pressure_positive_when_bid_depth_dominates() -> None:
    point = QueuePressureBookPoint(
        timestamp_ns=1_000_000_000,
        bid_sizes=(10.0, 8.0, 6.0, 4.0, 2.0),
        ask_sizes=(5.0, 4.0, 3.0, 2.0, 1.0),
    )

    result = compute_queue_pressure(point, pair="btcusdt")

    assert result.value == pytest.approx((30.0 - 15.0) / 45.0)
    assert result.top_k_used == DEFAULT_QUEUE_PRESSURE_TOP_K
    assert result.method_version_hash == QUEUE_PRESSURE_METHOD_VERSION_HASH
    assert result.pair == "BTCUSDT"


def test_queue_pressure_zero_when_both_sides_empty() -> None:
    point = QueuePressureBookPoint(
        timestamp_ns=1_000_000_000,
        bid_sizes=(0.0, 0.0),
        ask_sizes=(0.0, 0.0),
    )

    result = compute_queue_pressure(point, pair="ETHUSDT", top_k=2)

    assert result.value == pytest.approx(0.0)
    assert result.top_k_used == 2
    assert result.window_used == (1, None)


def test_queue_pressure_uses_available_levels_when_top_k_exceeds_depth() -> None:
    point = QueuePressureBookPoint(
        timestamp_ns=1_000_000_000,
        bid_sizes=(3.0, 2.0),
        ask_sizes=(1.0, 2.0),
    )

    result = compute_queue_pressure(point, pair="SOLUSDT", top_k=5)

    assert result.top_k_used == 2
    assert result.value == pytest.approx((5.0 - 3.0) / 8.0)
    assert result.input_data_hash


def test_queue_pressure_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="book sizes"):
        QueuePressureBookPoint(
            timestamp_ns=1_000_000_000,
            bid_sizes=(-1.0,),
            ask_sizes=(1.0,),
        )

    point = QueuePressureBookPoint(
        timestamp_ns=1_000_000_000,
        bid_sizes=(1.0,),
        ask_sizes=(1.0,),
    )
    with pytest.raises(ValueError, match="top_k"):
        compute_queue_pressure(point, pair="BTCUSDT", top_k=0)
