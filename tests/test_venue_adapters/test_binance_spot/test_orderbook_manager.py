from data_backbone.freshness_checker.venue_stream_freshness import evaluate_venue_stream_freshness
from venue_adapters.binance_spot.orderbook_manager import (
    BinanceDepthDelta,
    BinanceDepthSnapshot,
    BinanceOrderBookManager,
    OrderBookSyncState,
)


def test_orderbook_manager_applies_snapshot_then_delta():
    manager = BinanceOrderBookManager(pair="BTCUSDT", gap_threshold_s=5.0, silence_threshold_s=30.0)
    snapshot = BinanceDepthSnapshot(
        pair="BTCUSDT",
        last_update_id=100,
        bids=(("100.0", "1.0"),),
        asks=(("101.0", "2.0"),),
        recv_time_s=10.0,
    )
    manager.apply_snapshot(snapshot)

    status = manager.apply_delta(
        BinanceDepthDelta(
            pair="BTCUSDT",
            first_update_id=101,
            final_update_id=102,
            bids=(("100.5", "1.5"),),
            asks=(("101.0", "0"), ("101.5", "2.0")),
            recv_time_s=11.0,
        )
    )

    assert status.state == OrderBookSyncState.SYNCED
    assert status.last_update_id == 102
    assert status.top_bid == "100.5"
    assert status.top_ask == "101.5"


def test_orderbook_manager_marks_sequence_gap_stale():
    manager = BinanceOrderBookManager(pair="BTCUSDT", gap_threshold_s=5.0, silence_threshold_s=30.0)
    manager.apply_snapshot(
        BinanceDepthSnapshot(
            pair="BTCUSDT",
            last_update_id=100,
            bids=(("100.0", "1.0"),),
            asks=(("101.0", "2.0"),),
            recv_time_s=10.0,
        )
    )

    status = manager.apply_delta(
        BinanceDepthDelta(
            pair="BTCUSDT",
            first_update_id=105,
            final_update_id=106,
            bids=(("100.2", "1.0"),),
            asks=(),
            recv_time_s=11.0,
        )
    )

    assert status.state == OrderBookSyncState.STALE
    assert status.requires_resync is True
    assert status.reason == "sequence_gap"


def test_orderbook_manager_marks_time_gap_stale():
    manager = BinanceOrderBookManager(pair="BTCUSDT", gap_threshold_s=5.0, silence_threshold_s=30.0)
    manager.apply_snapshot(
        BinanceDepthSnapshot(
            pair="BTCUSDT",
            last_update_id=100,
            bids=(("100.0", "1.0"),),
            asks=(("101.0", "2.0"),),
            recv_time_s=10.0,
        )
    )

    status = manager.apply_delta(
        BinanceDepthDelta(
            pair="BTCUSDT",
            first_update_id=101,
            final_update_id=101,
            bids=(),
            asks=(),
            recv_time_s=16.5,
        )
    )

    assert status.state == OrderBookSyncState.STALE
    assert status.reason == "time_gap"


def test_evaluate_venue_stream_freshness_flags_silence():
    freshness = evaluate_venue_stream_freshness(last_update_time=10.0, now=45.5, stale_threshold_s=30.0)

    assert freshness.is_stale is True
    assert freshness.reason == "heartbeat_silent"
