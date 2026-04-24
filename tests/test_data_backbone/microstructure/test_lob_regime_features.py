from __future__ import annotations

import pytest

from data_backbone.microstructure import (
    CANONICAL_LOB_REGIME_FEATURE_SET_VERSION,
    LOB_REGIME_FEATURE_SET_V1,
    LOB_REGIME_FEATURE_SET_V2,
    LobAggTrade,
    LobBookLevel,
    LobDepth20Snapshot,
    build_lob_regime_feature_snapshot,
    evaluate_walls_and_spoofing,
    lob_regime_feature_names,
)


def _levels(best_price: float, best_size: float) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price - 0.1, size=10.0),
        LobBookLevel(price=best_price - 0.2, size=8.0),
        LobBookLevel(price=best_price - 0.3, size=7.0),
        LobBookLevel(price=best_price - 0.4, size=6.0),
    )


def _ask_levels(best_price: float, best_size: float) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price + 0.1, size=10.0),
        LobBookLevel(price=best_price + 0.2, size=8.0),
        LobBookLevel(price=best_price + 0.3, size=7.0),
        LobBookLevel(price=best_price + 0.4, size=6.0),
    )


def _snapshot(timestamp_ns: int, *, bid_size: float, ask_size: float = 20.0) -> LobDepth20Snapshot:
    return LobDepth20Snapshot(
        pair="BTCUSDT",
        timestamp_ns=timestamp_ns,
        bids=_levels(100.0, bid_size),
        asks=_ask_levels(100.1, ask_size),
    )


def test_lob_regime_features_identify_persistent_real_wall() -> None:
    depth = (
        _snapshot(1_000_000_000, bid_size=100.0),
        _snapshot(3_000_000_000, bid_size=98.0),
        _snapshot(6_000_000_000, bid_size=96.0),
    )
    trades = (
        LobAggTrade(
            timestamp_ns=5_500_000_000,
            price=100.0,
            quantity=30.0,
            aggressor_side="sell",
        ),
    )

    snapshot = build_lob_regime_feature_snapshot(
        depth,
        trades,
        pair="BTCUSDT",
        computed_at_ns=6_000_000_000,
        touch_eps_bps=10.0,
    )
    walls = evaluate_walls_and_spoofing(
        pair="BTCUSDT",
        computed_at_ns=6_000_000_000,
        depth_events=depth,
        trade_events=trades,
        touch_eps_bps=10.0,
    )

    assert snapshot.data_status == "ready"
    assert snapshot.wall_persistence_bid > 0.9
    assert snapshot.wall_persistence_conditional_bid >= snapshot.wall_persistence_bid
    assert snapshot.observation_coverage_ratio == pytest.approx(1.0)
    assert snapshot.executed_vs_displayed_bid > 0.1
    assert snapshot.spoof_like_suspicion_bid < 0.5
    assert snapshot.book_shape_skew == pytest.approx(walls.book_shape_skew)
    assert snapshot.real_wall_score_bid == pytest.approx(walls.real_wall_score_bid)
    assert snapshot.real_wall_score_ask == pytest.approx(walls.real_wall_score_ask)
    assert snapshot.deceptive_liquidity_score == pytest.approx(walls.deceptive_liquidity_score)
    assert snapshot.as_feature_map()["spread_bps"] == pytest.approx(snapshot.spread_bps)
    assert "observation_coverage_ratio" not in snapshot.as_feature_map()
    assert snapshot.as_feature_map_for_version(LOB_REGIME_FEATURE_SET_V2)[
        "observation_coverage_ratio"
    ] == pytest.approx(snapshot.observation_coverage_ratio)
    assert snapshot.feature_names_for_version(LOB_REGIME_FEATURE_SET_V2) == lob_regime_feature_names(
        LOB_REGIME_FEATURE_SET_V2
    )
    assert CANONICAL_LOB_REGIME_FEATURE_SET_VERSION == LOB_REGIME_FEATURE_SET_V2
    assert snapshot.as_feature_map()["real_wall_score_bid"] == pytest.approx(
        snapshot.real_wall_score_bid
    )


def test_lob_regime_features_raise_suspicion_when_wall_pulls_away() -> None:
    depth = (
        _snapshot(1_000_000_000, bid_size=120.0),
        _snapshot(2_000_000_000, bid_size=25.0),
        _snapshot(3_000_000_000, bid_size=3.0),
    )

    snapshot = build_lob_regime_feature_snapshot(
        depth,
        (),
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
        touch_eps_bps=10.0,
    )

    assert snapshot.wall_pullaway_bid > 0.9
    assert snapshot.near_touch_cancel_ratio_bid > 0.4
    assert snapshot.spoof_like_suspicion_bid > 0.5
    assert snapshot.deceptive_liquidity_score > 0.25
    assert snapshot.real_wall_score_bid < snapshot.spoof_like_suspicion_bid


def test_lob_regime_features_fail_closed_on_insufficient_depth() -> None:
    snapshot = build_lob_regime_feature_snapshot(
        (_snapshot(1_000_000_000, bid_size=100.0),),
        (),
        pair="BTCUSDT",
        computed_at_ns=1_000_000_000,
    )

    assert snapshot.data_status == "insufficient_data"
    assert snapshot.insufficient_data is True
    assert snapshot.reason_codes == ("LOB_REGIME_INSUFFICIENT_DEPTH_EVENTS",)


def test_lob_regime_features_reject_future_events() -> None:
    with pytest.raises(ValueError, match="future events"):
        build_lob_regime_feature_snapshot(
            (
                _snapshot(1_000_000_000, bid_size=100.0),
                _snapshot(2_000_000_000, bid_size=90.0),
            ),
            (),
            pair="BTCUSDT",
            computed_at_ns=1_500_000_000,
        )


def test_lob_regime_features_versions_are_explicit_and_stable() -> None:
    snapshot = build_lob_regime_feature_snapshot(
        (
            _snapshot(1_000_000_000, bid_size=100.0),
            _snapshot(2_000_000_000, bid_size=95.0),
            _snapshot(3_000_000_000, bid_size=90.0),
        ),
        (),
        pair="BTCUSDT",
        computed_at_ns=3_000_000_000,
    )

    feature_map_v1 = snapshot.as_feature_map_for_version(LOB_REGIME_FEATURE_SET_V1)
    feature_map_v2 = snapshot.as_feature_map_for_version(LOB_REGIME_FEATURE_SET_V2)

    assert "observation_coverage_ratio" not in feature_map_v1
    assert "observation_coverage_ratio" in feature_map_v2
    assert "wall_persistence_conditional_bid" in feature_map_v2
