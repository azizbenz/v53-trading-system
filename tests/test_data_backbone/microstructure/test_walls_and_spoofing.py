from __future__ import annotations

import pytest
from pydantic import ValidationError

from data_backbone.microstructure import (
    LobAggTrade,
    LobBookLevel,
    LobDepth20Snapshot,
    evaluate_walls_and_spoofing,
)


def _bid_levels(
    best_price: float,
    best_size: float,
    *,
    tail: tuple[float, ...] = (10.0, 8.0, 7.0, 6.0),
) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price - 0.1, size=tail[0]),
        LobBookLevel(price=best_price - 0.2, size=tail[1]),
        LobBookLevel(price=best_price - 0.3, size=tail[2]),
        LobBookLevel(price=best_price - 0.4, size=tail[3]),
    )


def _ask_levels(
    best_price: float,
    best_size: float,
    *,
    tail: tuple[float, ...] = (10.0, 8.0, 7.0, 6.0),
) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price + 0.1, size=tail[0]),
        LobBookLevel(price=best_price + 0.2, size=tail[1]),
        LobBookLevel(price=best_price + 0.3, size=tail[2]),
        LobBookLevel(price=best_price + 0.4, size=tail[3]),
    )


def _snapshot(
    timestamp_ns: int,
    *,
    bid_size: float = 20.0,
    ask_size: float = 20.0,
    best_bid: float = 100.0,
    best_ask: float = 100.1,
    bid_tail: tuple[float, ...] = (10.0, 8.0, 7.0, 6.0),
    ask_tail: tuple[float, ...] = (10.0, 8.0, 7.0, 6.0),
) -> LobDepth20Snapshot:
    return LobDepth20Snapshot(
        pair="BTCUSDT",
        timestamp_ns=timestamp_ns,
        bids=_bid_levels(best_bid, bid_size, tail=bid_tail),
        asks=_ask_levels(best_ask, ask_size, tail=ask_tail),
    )


def test_walls_and_spoofing_identifies_persistent_real_bid_wall() -> None:
    depth = (
        _snapshot(1_000_000_000, bid_size=180.0),
        _snapshot(3_000_000_000, bid_size=178.0),
        _snapshot(6_000_000_000, bid_size=175.0),
    )
    trades = (
        LobAggTrade(
            timestamp_ns=5_500_000_000,
            price=100.0,
            quantity=300.0,
            aggressor_side="sell",
        ),
    )

    snapshot = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=6_000_000_000,
        depth_events=depth,
        trade_events=trades,
        touch_eps_bps=10.0,
    )

    assert snapshot.insufficient_data is False
    assert snapshot.real_wall_score_bid > 0.55
    assert snapshot.spoof_suspicion_score_bid < 0.45
    assert snapshot.executed_vs_displayed_bid > 0.2
    assert snapshot.wall_persistence_conditional_bid >= snapshot.wall_persistence_bid
    assert snapshot.observation_coverage_ratio == pytest.approx(1.0)
    assert snapshot.dominant_side == "bid"
    assert snapshot.real_wall_score_method == "HEURISTIC_WEIGHTED_SCORE"
    assert snapshot.spoof_suspicion_score_method == "HEURISTIC_WEIGHTED_SCORE"
    assert snapshot.calibration_status == "CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM"
    assert "micro.wall.bid.strong" in snapshot.reason_codes


def test_walls_and_spoofing_flags_spoof_like_ask_wall() -> None:
    depth = (
        _snapshot(1_000_000_000, ask_size=140.0),
        _snapshot(2_000_000_000, ask_size=25.0),
        _snapshot(3_000_000_000, ask_size=2.0),
    )

    snapshot = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=depth,
        trade_events=(),
        touch_eps_bps=10.0,
    )

    assert snapshot.wall_pullaway_ask > 0.9
    assert snapshot.near_touch_cancel_ratio_ask > 0.5
    assert snapshot.executed_vs_displayed_ask == 0.0
    assert snapshot.spoof_suspicion_score_ask > 0.6
    assert snapshot.deceptive_liquidity_score >= snapshot.spoof_suspicion_score_ask
    assert "micro.spoof_like.ask" in snapshot.reason_codes


def test_walls_and_spoofing_keeps_homogeneous_book_neutral() -> None:
    depth = (
        _snapshot(
            1_000_000_000,
            bid_size=20.0,
            ask_size=20.0,
            best_bid=100.0,
            best_ask=100.2,
            bid_tail=(20.0, 20.0, 20.0, 20.0),
            ask_tail=(20.0, 20.0, 20.0, 20.0),
        ),
        _snapshot(
            2_000_000_000,
            bid_size=20.0,
            ask_size=20.0,
            best_bid=100.0,
            best_ask=100.2,
            bid_tail=(20.0, 20.0, 20.0, 20.0),
            ask_tail=(20.0, 20.0, 20.0, 20.0),
        ),
        _snapshot(
            3_000_000_000,
            bid_size=20.0,
            ask_size=20.0,
            best_bid=100.0,
            best_ask=100.2,
            bid_tail=(20.0, 20.0, 20.0, 20.0),
            ask_tail=(20.0, 20.0, 20.0, 20.0),
        ),
    )

    snapshot = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=depth,
        trade_events=(),
        touch_eps_bps=10.0,
    )

    assert snapshot.dominant_side == "neutral"
    assert snapshot.real_wall_score_bid < 0.5
    assert snapshot.real_wall_score_ask < 0.5
    assert snapshot.wall_persistence_conditional_bid == pytest.approx(snapshot.wall_persistence_bid)
    assert snapshot.spoof_suspicion_score_bid < 0.5
    assert snapshot.spoof_suspicion_score_ask < 0.5
    assert snapshot.reason_codes == ("micro.wall.neutral",)


def test_walls_and_spoofing_does_not_false_flag_true_sweep() -> None:
    depth = (
        _snapshot(1_000_000_000, ask_size=120.0),
        _snapshot(2_000_000_000, ask_size=110.0),
        _snapshot(3_000_000_000, ask_size=90.0),
    )
    trades = (
        LobAggTrade(
            timestamp_ns=2_200_000_000,
            price=100.1,
            quantity=120.0,
            aggressor_side="buy",
        ),
        LobAggTrade(
            timestamp_ns=2_700_000_000,
            price=100.1,
            quantity=80.0,
            aggressor_side="buy",
        ),
    )

    snapshot = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=depth,
        trade_events=trades,
        touch_eps_bps=10.0,
    )

    assert snapshot.executed_vs_displayed_ask > 0.8
    assert snapshot.spoof_suspicion_score_ask < 0.5
    assert "micro.spoof_like.ask" not in snapshot.reason_codes


def test_walls_and_spoofing_returns_explicit_insufficient_data_snapshot() -> None:
    snapshot = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=1_000_000_000,
        depth_events=(_snapshot(1_000_000_000, bid_size=120.0),),
        trade_events=(),
    )

    assert snapshot.insufficient_data is True
    assert snapshot.reason_codes == ("micro.snapshot.insufficient_data",)
    assert snapshot.real_wall_score_bid == 0.0
    assert snapshot.deceptive_liquidity_score == 0.0

    stale = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=10_000_000_000,
        depth_events=(
            _snapshot(1_000_000_000, bid_size=120.0),
            _snapshot(2_000_000_000, bid_size=118.0),
        ),
        trade_events=(),
    )
    assert stale.insufficient_data is True
    assert stale.reason_codes == ("micro.snapshot.insufficient_data",)

    short_top_n = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=2_000_000_000,
        depth_events=(
            LobDepth20Snapshot(
                pair="BTCUSDT",
                timestamp_ns=1_000_000_000,
                bids=_bid_levels(100.0, 120.0)[:3],
                asks=_ask_levels(100.1, 20.0)[:3],
            ),
            LobDepth20Snapshot(
                pair="BTCUSDT",
                timestamp_ns=2_000_000_000,
                bids=_bid_levels(100.0, 118.0)[:3],
                asks=_ask_levels(100.1, 20.0)[:3],
            ),
        ),
        trade_events=(),
    )
    assert short_top_n.insufficient_data is True
    assert short_top_n.reason_codes == ("micro.snapshot.insufficient_data",)


def test_walls_and_spoofing_rejects_invalid_structure() -> None:
    with pytest.raises(ValidationError):
        LobBookLevel(price=100.0, size=-1.0)

    with pytest.raises(ValueError, match="strictly < best ask"):
        evaluate_walls_and_spoofing(
            pair="BTCUSDT",
            computed_at_ns=2_000_000_000,
            depth_events=(
                _snapshot(1_000_000_000, best_bid=100.0, best_ask=100.0),
                _snapshot(2_000_000_000, best_bid=100.0, best_ask=100.0),
            ),
            trade_events=(),
        )

    with pytest.raises(ValueError, match="non-decreasing"):
        evaluate_walls_and_spoofing(
            pair="BTCUSDT",
            computed_at_ns=2_000_000_000,
            depth_events=(
                _snapshot(2_000_000_000, bid_size=20.0),
                _snapshot(1_000_000_000, bid_size=30.0),
            ),
            trade_events=(),
        )

    with pytest.raises(ValueError, match="top_n_levels must be in \\[3, 10\\]"):
        evaluate_walls_and_spoofing(
            pair="BTCUSDT",
            computed_at_ns=2_000_000_000,
            depth_events=(
                _snapshot(1_000_000_000, bid_size=20.0),
                _snapshot(2_000_000_000, bid_size=20.0),
            ),
            trade_events=(),
            top_n_levels=2,
        )

    with pytest.raises(ValueError, match="sorted strictly"):
        evaluate_walls_and_spoofing(
            pair="BTCUSDT",
            computed_at_ns=2_000_000_000,
            depth_events=(
                LobDepth20Snapshot(
                    pair="BTCUSDT",
                    timestamp_ns=1_000_000_000,
                    bids=(
                        LobBookLevel(price=100.0, size=20.0),
                        LobBookLevel(price=99.8, size=10.0),
                        LobBookLevel(price=99.9, size=8.0),
                        LobBookLevel(price=99.7, size=7.0),
                        LobBookLevel(price=99.6, size=6.0),
                    ),
                    asks=_ask_levels(100.1, 20.0),
                ),
                _snapshot(2_000_000_000, bid_size=20.0),
            ),
            trade_events=(),
        )


def test_walls_and_spoofing_ignores_future_events() -> None:
    stable_depth = (
        _snapshot(1_000_000_000, ask_size=120.0),
        _snapshot(2_000_000_000, ask_size=118.0),
        _snapshot(3_000_000_000, ask_size=117.0),
    )
    future_collapse = stable_depth + (
        _snapshot(6_000_000_000, ask_size=2.0),
    )

    at_t = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=future_collapse,
        trade_events=(),
        touch_eps_bps=10.0,
    )
    after_future = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=6_000_000_000,
        depth_events=future_collapse,
        trade_events=(),
        touch_eps_bps=10.0,
    )

    assert at_t.spoof_suspicion_score_ask < 0.5
    assert after_future.spoof_suspicion_score_ask > at_t.spoof_suspicion_score_ask
    assert at_t.observation_coverage_ratio < 1.0


def test_walls_and_spoofing_is_deterministic_and_hash_stable() -> None:
    depth = (
        _snapshot(1_000_000_000, bid_size=120.0),
        _snapshot(2_000_000_000, bid_size=118.0),
        _snapshot(3_000_000_000, bid_size=115.0),
    )
    trades = (
        LobAggTrade(
            timestamp_ns=2_600_000_000,
            price=100.0,
            quantity=50.0,
            aggressor_side="sell",
        ),
    )

    first = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=depth,
        trade_events=trades,
        touch_eps_bps=10.0,
    )
    second = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        depth_events=depth,
        trade_events=trades,
        touch_eps_bps=10.0,
    )

    assert first == second
    assert first.input_data_hash == second.input_data_hash
    assert first.method_version_hash == second.method_version_hash
