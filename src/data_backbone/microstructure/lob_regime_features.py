"""Live LOB microstructure features for governed RegimeDetectorML inference."""

from __future__ import annotations

from hashlib import sha256
import json
import math
import statistics
from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_backbone.microstructure.order_flow_imbalance import (
    OrderBookTopLevelPoint,
    compute_order_flow_imbalance,
)
from interface_contracts.regime_detector_artifact import RegimeDetectorFeatureSetVersion


LOB_REGIME_METHOD_VERSION = "lob_regime.live_microstructure.v2"
LOB_REGIME_METHOD_VERSION_HASH = sha256(LOB_REGIME_METHOD_VERSION.encode("utf-8")).hexdigest()
LOB_REGIME_FEATURE_SET_V1 = RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1.value
LOB_REGIME_FEATURE_SET_V2 = RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2.value
CANONICAL_LOB_REGIME_FEATURE_SET_VERSION = LOB_REGIME_FEATURE_SET_V2
SUPPORTED_LOB_REGIME_FEATURE_SET_VERSIONS = (
    LOB_REGIME_FEATURE_SET_V1,
    LOB_REGIME_FEATURE_SET_V2,
)
DEFAULT_LOB_REGIME_WINDOW_SECONDS = 5.0
MAX_LOB_REGIME_WINDOW_SECONDS = 30.0
DEFAULT_LOB_REGIME_TOP_N = 5
MAX_LOB_REGIME_TOP_N = 10

_EPS = 1e-12
_LOB_REGIME_FEATURE_NAMES_V1 = (
    "spread_bps",
    "order_book_imbalance",
    "microprice_pressure",
    "depth_skew",
    "book_shape_skew",
    "liquidity_thinning_score",
    "wall_strength_bid",
    "wall_strength_ask",
    "wall_persistence_bid",
    "wall_persistence_ask",
    "wall_pullaway_bid",
    "wall_pullaway_ask",
    "near_touch_cancel_ratio_bid",
    "near_touch_cancel_ratio_ask",
    "executed_vs_displayed_bid",
    "executed_vs_displayed_ask",
    "real_wall_score_bid",
    "real_wall_score_ask",
    "spoof_like_suspicion_bid",
    "spoof_like_suspicion_ask",
    "deceptive_liquidity_score",
    "ofi_short_window",
    "aggressive_trade_imbalance",
    "short_window_volatility",
)
_LOB_REGIME_FEATURE_NAMES_V2 = (
    *_LOB_REGIME_FEATURE_NAMES_V1,
    "wall_persistence_conditional_bid",
    "wall_persistence_conditional_ask",
    "observation_coverage_ratio",
)


class _WindowedLobInputs(NamedTuple):
    normalized_pair: str
    eval_time_ns: int
    window_depth: tuple["LobDepth20Snapshot", ...]
    window_trades: tuple["LobAggTrade", ...]


class _BasicBookFeatures(NamedTuple):
    bid_depth: float
    ask_depth: float
    spread_bps: float
    order_book_imbalance: float
    depth_skew: float
    microprice_pressure: float


class _WallFeatureBundle(NamedTuple):
    wall_strength_bid: float
    wall_strength_ask: float
    wall_persistence_bid: float
    wall_persistence_ask: float
    wall_persistence_conditional_bid: float
    wall_persistence_conditional_ask: float
    wall_pullaway_bid: float
    wall_pullaway_ask: float
    near_touch_cancel_ratio_bid: float
    near_touch_cancel_ratio_ask: float
    executed_vs_displayed_bid: float
    executed_vs_displayed_ask: float
    book_shape_skew: float
    real_wall_score_bid: float
    real_wall_score_ask: float
    spoof_like_suspicion_bid: float
    spoof_like_suspicion_ask: float
    deceptive_liquidity_score: float
    observation_coverage_ratio: float
    reason_codes: tuple[str, ...]


class _LiquidityFeatureBundle(NamedTuple):
    liquidity_thinning_score: float


class LobBookLevel(BaseModel):
    """One price level from a depth snapshot."""

    price: float = Field(..., gt=0.0)
    size: float = Field(..., ge=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class LobDepth20Snapshot(BaseModel):
    """Depth20-like book snapshot used for live LOB regime features."""

    pair: str = Field(..., min_length=1)
    timestamp_ns: int = Field(..., ge=1)
    bids: tuple[LobBookLevel, ...] = Field(..., min_length=1, max_length=20)
    asks: tuple[LobBookLevel, ...] = Field(..., min_length=1, max_length=20)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_crossed_book(self) -> "LobDepth20Snapshot":
        if self.asks[0].price < self.bids[0].price:
            raise ValueError("best ask must be >= best bid")
        return self


class LobAggTrade(BaseModel):
    """Aggressive trade event aligned with the depth window."""

    timestamp_ns: int = Field(..., ge=1)
    price: float = Field(..., gt=0.0)
    quantity: float = Field(..., ge=0.0)
    aggressor_side: Literal["buy", "sell"]

    model_config = ConfigDict(frozen=True, extra="forbid")


class LobRegimeFeatureSnapshot(BaseModel):
    """Typed VPS-live LOB features for shadow RegimeDetectorML inference."""

    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    window_seconds: float = Field(..., gt=0.0, le=MAX_LOB_REGIME_WINDOW_SECONDS)
    top_n: int = Field(..., ge=1, le=MAX_LOB_REGIME_TOP_N)
    n_depth_events: int = Field(..., ge=0)
    n_trades: int = Field(..., ge=0)
    data_status: Literal["ready", "insufficient_data", "stale"]
    insufficient_data: bool = False
    spread_bps: float = 0.0
    order_book_imbalance: float = 0.0
    microprice_pressure: float = 0.0
    depth_skew: float = 0.0
    book_shape_skew: float = 0.0
    liquidity_thinning_score: float = 0.0
    wall_strength_bid: float = 0.0
    wall_strength_ask: float = 0.0
    wall_persistence_bid: float = 0.0
    wall_persistence_ask: float = 0.0
    wall_persistence_conditional_bid: float = 0.0
    wall_persistence_conditional_ask: float = 0.0
    wall_pullaway_bid: float = 0.0
    wall_pullaway_ask: float = 0.0
    near_touch_cancel_ratio_bid: float = 0.0
    near_touch_cancel_ratio_ask: float = 0.0
    executed_vs_displayed_bid: float = 0.0
    executed_vs_displayed_ask: float = 0.0
    real_wall_score_bid: float = 0.0
    real_wall_score_ask: float = 0.0
    spoof_like_suspicion_bid: float = 0.0
    spoof_like_suspicion_ask: float = 0.0
    deceptive_liquidity_score: float = 0.0
    observation_coverage_ratio: float = 0.0
    ofi_short_window: float = 0.0
    aggressive_trade_imbalance: float = 0.0
    short_window_volatility: float = 0.0
    reason_codes: tuple[str, ...] = ()
    input_data_hash: str = Field(..., min_length=8)
    method_version_hash: str = Field(default=LOB_REGIME_METHOD_VERSION_HASH, min_length=8)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator(
        "spread_bps",
        "order_book_imbalance",
        "microprice_pressure",
        "depth_skew",
        "book_shape_skew",
        "liquidity_thinning_score",
        "wall_strength_bid",
        "wall_strength_ask",
        "wall_persistence_bid",
        "wall_persistence_ask",
        "wall_persistence_conditional_bid",
        "wall_persistence_conditional_ask",
        "wall_pullaway_bid",
        "wall_pullaway_ask",
        "near_touch_cancel_ratio_bid",
        "near_touch_cancel_ratio_ask",
        "executed_vs_displayed_bid",
        "executed_vs_displayed_ask",
        "real_wall_score_bid",
        "real_wall_score_ask",
        "spoof_like_suspicion_bid",
        "spoof_like_suspicion_ask",
        "deceptive_liquidity_score",
        "observation_coverage_ratio",
        "ofi_short_window",
        "aggressive_trade_imbalance",
        "short_window_volatility",
    )
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("LOB regime feature values must be finite")
        return float(value)

    def as_feature_map(self) -> dict[str, float]:
        """Return the backward-compatible V1 feature map."""

        return self.as_feature_map_for_version(LOB_REGIME_FEATURE_SET_V1)

    def as_feature_map_for_version(self, feature_set_version: str) -> dict[str, float]:
        """Return a stable numeric feature map for an explicit schema version."""

        feature_map = {
            "spread_bps": self.spread_bps,
            "order_book_imbalance": self.order_book_imbalance,
            "microprice_pressure": self.microprice_pressure,
            "depth_skew": self.depth_skew,
            "book_shape_skew": self.book_shape_skew,
            "liquidity_thinning_score": self.liquidity_thinning_score,
            "wall_strength_bid": self.wall_strength_bid,
            "wall_strength_ask": self.wall_strength_ask,
            "wall_persistence_bid": self.wall_persistence_bid,
            "wall_persistence_ask": self.wall_persistence_ask,
            "wall_pullaway_bid": self.wall_pullaway_bid,
            "wall_pullaway_ask": self.wall_pullaway_ask,
            "near_touch_cancel_ratio_bid": self.near_touch_cancel_ratio_bid,
            "near_touch_cancel_ratio_ask": self.near_touch_cancel_ratio_ask,
            "executed_vs_displayed_bid": self.executed_vs_displayed_bid,
            "executed_vs_displayed_ask": self.executed_vs_displayed_ask,
            "real_wall_score_bid": self.real_wall_score_bid,
            "real_wall_score_ask": self.real_wall_score_ask,
            "spoof_like_suspicion_bid": self.spoof_like_suspicion_bid,
            "spoof_like_suspicion_ask": self.spoof_like_suspicion_ask,
            "deceptive_liquidity_score": self.deceptive_liquidity_score,
            "ofi_short_window": self.ofi_short_window,
            "aggressive_trade_imbalance": self.aggressive_trade_imbalance,
            "short_window_volatility": self.short_window_volatility,
        }
        if feature_set_version == LOB_REGIME_FEATURE_SET_V1:
            return feature_map
        if feature_set_version == LOB_REGIME_FEATURE_SET_V2:
            return {
                **feature_map,
                "wall_persistence_conditional_bid": self.wall_persistence_conditional_bid,
                "wall_persistence_conditional_ask": self.wall_persistence_conditional_ask,
                "observation_coverage_ratio": self.observation_coverage_ratio,
            }
        raise ValueError(f"unsupported lob regime feature_set_version: {feature_set_version}")

    @staticmethod
    def feature_names_for_version(feature_set_version: str) -> tuple[str, ...]:
        """Return the ordered feature names for a supported schema version."""

        return lob_regime_feature_names(feature_set_version)


def lob_regime_feature_names(feature_set_version: str) -> tuple[str, ...]:
    """Resolve the ordered LOB regime feature names for a schema version."""

    if feature_set_version == LOB_REGIME_FEATURE_SET_V1:
        return _LOB_REGIME_FEATURE_NAMES_V1
    if feature_set_version == LOB_REGIME_FEATURE_SET_V2:
        return _LOB_REGIME_FEATURE_NAMES_V2
    raise ValueError(f"unsupported lob regime feature_set_version: {feature_set_version}")


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, float(value)))


def _mid(snapshot: LobDepth20Snapshot) -> float:
    return (snapshot.bids[0].price + snapshot.asks[0].price) / 2.0


def _side_levels(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    top_n: int,
) -> tuple[LobBookLevel, ...]:
    levels = snapshot.bids if side == "bid" else snapshot.asks
    return levels[: min(top_n, len(levels))]


def _short_volatility_bps(trades: tuple[LobAggTrade, ...]) -> float:
    if len(trades) < 2:
        return 0.0
    prices = [trade.price for trade in trades if trade.price > 0.0]
    if len(prices) < 2:
        return 0.0
    mean_price = statistics.fmean(prices)
    if mean_price <= 0.0:
        return 0.0
    return statistics.pstdev(prices) / mean_price * 10_000.0


def _aggressive_trade_imbalance(trades: tuple[LobAggTrade, ...]) -> float:
    buy_qty = sum(trade.quantity for trade in trades if trade.aggressor_side == "buy")
    sell_qty = sum(trade.quantity for trade in trades if trade.aggressor_side == "sell")
    return (buy_qty - sell_qty) / (buy_qty + sell_qty + _EPS)


def _ofi_short_window(snapshots: tuple[LobDepth20Snapshot, ...], *, pair: str) -> float:
    if len(snapshots) < 2:
        return 0.0
    points = [
        OrderBookTopLevelPoint(
            timestamp_ns=snapshot.timestamp_ns,
            bid_price=snapshot.bids[0].price,
            bid_size=snapshot.bids[0].size,
            ask_price=snapshot.asks[0].price,
            ask_size=snapshot.asks[0].size,
        )
        for snapshot in snapshots
    ]
    return compute_order_flow_imbalance(
        points,
        pair=pair,
        window_events=max(1, len(points) - 1),
        computed_at_ns=points[-1].timestamp_ns,
    ).value


def _hash_input(
    *,
    pair: str,
    computed_at_ns: int,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trades: tuple[LobAggTrade, ...],
) -> str:
    payload = {
        "pair": pair,
        "computed_at_ns": computed_at_ns,
        "depth": [event.model_dump(mode="json") for event in depth_events],
        "trades": [trade.model_dump(mode="json") for trade in trades],
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _insufficient_snapshot(
    *,
    pair: str,
    computed_at_ns: int,
    window_seconds: float,
    top_n: int,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trades: tuple[LobAggTrade, ...],
    status: Literal["insufficient_data", "stale"],
    reason_codes: tuple[str, ...],
) -> LobRegimeFeatureSnapshot:
    return LobRegimeFeatureSnapshot(
        pair=pair,
        computed_at_ns=computed_at_ns,
        window_seconds=window_seconds,
        top_n=top_n,
        n_depth_events=len(depth_events),
        n_trades=len(trades),
        data_status=status,
        insufficient_data=True,
        reason_codes=reason_codes,
        input_data_hash=_hash_input(
            pair=pair,
            computed_at_ns=computed_at_ns,
            depth_events=depth_events,
            trades=trades,
        ),
    )


def _validate_lob_regime_knobs(*, window_seconds: float, top_n: int) -> None:
    if not 0.0 < window_seconds <= MAX_LOB_REGIME_WINDOW_SECONDS:
        raise ValueError(f"window_seconds must be in (0, {MAX_LOB_REGIME_WINDOW_SECONDS}]")
    if not 1 <= top_n <= MAX_LOB_REGIME_TOP_N:
        raise ValueError(f"top_n must be in [1, {MAX_LOB_REGIME_TOP_N}]")


def _windowed_lob_inputs(
    depth_events: tuple[LobDepth20Snapshot, ...],
    trades: tuple[LobAggTrade, ...],
    *,
    pair: str,
    computed_at_ns: int | None,
    window_seconds: float,
) -> _WindowedLobInputs:
    normalized_pair = pair.strip().upper()
    if not normalized_pair:
        raise ValueError("pair must not be blank")
    latest_observed_ns = max(
        [event.timestamp_ns for event in depth_events] + [trade.timestamp_ns for trade in trades],
        default=0,
    )
    eval_time_ns = latest_observed_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns <= 0:
        raise ValueError("computed_at_ns must be provided when no events are available")
    if any(event.timestamp_ns > eval_time_ns for event in depth_events) or any(
        trade.timestamp_ns > eval_time_ns for trade in trades
    ):
        raise ValueError("LOB regime feature inputs must not contain future events")

    window_start_ns = eval_time_ns - int(window_seconds * 1_000_000_000)
    return _WindowedLobInputs(
        normalized_pair=normalized_pair,
        eval_time_ns=eval_time_ns,
        window_depth=tuple(
            event
            for event in sorted(depth_events, key=lambda item: item.timestamp_ns)
            if window_start_ns <= event.timestamp_ns <= eval_time_ns
        ),
        window_trades=tuple(
            trade
            for trade in sorted(trades, key=lambda item: item.timestamp_ns)
            if window_start_ns <= trade.timestamp_ns <= eval_time_ns
        ),
    )


def _window_rejection_snapshot(
    inputs: _WindowedLobInputs,
    *,
    window_seconds: float,
    top_n: int,
) -> LobRegimeFeatureSnapshot | None:
    if len(inputs.window_depth) < 2:
        return _insufficient_snapshot(
            pair=inputs.normalized_pair,
            computed_at_ns=inputs.eval_time_ns,
            window_seconds=window_seconds,
            top_n=top_n,
            depth_events=inputs.window_depth,
            trades=inputs.window_trades,
            status="insufficient_data",
            reason_codes=("LOB_REGIME_INSUFFICIENT_DEPTH_EVENTS",),
        )
    if inputs.eval_time_ns - inputs.window_depth[-1].timestamp_ns > int(
        window_seconds * 1_000_000_000
    ):
        return _insufficient_snapshot(
            pair=inputs.normalized_pair,
            computed_at_ns=inputs.eval_time_ns,
            window_seconds=window_seconds,
            top_n=top_n,
            depth_events=inputs.window_depth,
            trades=inputs.window_trades,
            status="stale",
            reason_codes=("LOB_REGIME_DEPTH_STALE",),
        )
    return None


def _basic_book_features(latest: LobDepth20Snapshot, *, top_n: int) -> _BasicBookFeatures:
    mid = _mid(latest)
    bid_depth = sum(level.size for level in _side_levels(latest, side="bid", top_n=top_n))
    ask_depth = sum(level.size for level in _side_levels(latest, side="ask", top_n=top_n))
    order_book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth + _EPS)
    microprice = (
        (latest.asks[0].price * latest.bids[0].size)
        + (latest.bids[0].price * latest.asks[0].size)
    ) / (latest.bids[0].size + latest.asks[0].size + _EPS)
    return _BasicBookFeatures(
        bid_depth=bid_depth,
        ask_depth=ask_depth,
        spread_bps=(latest.asks[0].price - latest.bids[0].price) / (mid + _EPS) * 10_000.0,
        order_book_imbalance=order_book_imbalance,
        depth_skew=order_book_imbalance,
        microprice_pressure=(microprice - mid) / (mid + _EPS) * 10_000.0,
    )


def _wall_feature_bundle(
    window_depth: tuple[LobDepth20Snapshot, ...],
    window_trades: tuple[LobAggTrade, ...],
    *,
    pair: str,
    computed_at_ns: int,
    window_seconds: float,
    top_n: int,
    touch_eps_bps: float,
) -> _WallFeatureBundle:
    from data_backbone.microstructure.walls_and_spoofing import evaluate_walls_and_spoofing

    walls = evaluate_walls_and_spoofing(
        pair=pair,
        computed_at_ns=computed_at_ns,
        depth_events=window_depth,
        trade_events=window_trades,
        window_seconds=window_seconds,
        top_n_levels=top_n,
        touch_eps_bps=touch_eps_bps,
    )
    return _WallFeatureBundle(
        wall_strength_bid=walls.wall_strength_bid,
        wall_strength_ask=walls.wall_strength_ask,
        wall_persistence_bid=walls.wall_persistence_bid,
        wall_persistence_ask=walls.wall_persistence_ask,
        wall_persistence_conditional_bid=walls.wall_persistence_conditional_bid,
        wall_persistence_conditional_ask=walls.wall_persistence_conditional_ask,
        wall_pullaway_bid=walls.wall_pullaway_bid,
        wall_pullaway_ask=walls.wall_pullaway_ask,
        near_touch_cancel_ratio_bid=walls.near_touch_cancel_ratio_bid,
        near_touch_cancel_ratio_ask=walls.near_touch_cancel_ratio_ask,
        executed_vs_displayed_bid=walls.executed_vs_displayed_bid,
        executed_vs_displayed_ask=walls.executed_vs_displayed_ask,
        book_shape_skew=walls.book_shape_skew,
        real_wall_score_bid=walls.real_wall_score_bid,
        real_wall_score_ask=walls.real_wall_score_ask,
        spoof_like_suspicion_bid=walls.spoof_suspicion_score_bid,
        spoof_like_suspicion_ask=walls.spoof_suspicion_score_ask,
        deceptive_liquidity_score=walls.deceptive_liquidity_score,
        observation_coverage_ratio=walls.observation_coverage_ratio,
        reason_codes=walls.reason_codes,
    )


def _liquidity_features(
    window_depth: tuple[LobDepth20Snapshot, ...],
    *,
    bid_depth: float,
    ask_depth: float,
    top_n: int,
) -> _LiquidityFeatureBundle:
    historical_avg_depth = statistics.fmean(
        sum(level.size for level in _side_levels(event, side="bid", top_n=top_n))
        + sum(level.size for level in _side_levels(event, side="ask", top_n=top_n))
        for event in window_depth
    )
    liquidity_thinning_score = _clip(
        1.0 - ((bid_depth + ask_depth) / (historical_avg_depth + _EPS))
    )
    return _LiquidityFeatureBundle(liquidity_thinning_score=liquidity_thinning_score)


def _ready_lob_regime_snapshot(
    *,
    inputs: _WindowedLobInputs,
    basic: _BasicBookFeatures,
    walls: _WallFeatureBundle,
    liquidity: _LiquidityFeatureBundle,
    window_seconds: float,
    top_n: int,
) -> LobRegimeFeatureSnapshot:
    return LobRegimeFeatureSnapshot(
        pair=inputs.normalized_pair,
        computed_at_ns=inputs.eval_time_ns,
        window_seconds=window_seconds,
        top_n=top_n,
        n_depth_events=len(inputs.window_depth),
        n_trades=len(inputs.window_trades),
        data_status="ready",
        insufficient_data=False,
        spread_bps=basic.spread_bps,
        order_book_imbalance=basic.order_book_imbalance,
        microprice_pressure=basic.microprice_pressure,
        depth_skew=basic.depth_skew,
        book_shape_skew=walls.book_shape_skew,
        liquidity_thinning_score=liquidity.liquidity_thinning_score,
        wall_strength_bid=walls.wall_strength_bid,
        wall_strength_ask=walls.wall_strength_ask,
        wall_persistence_bid=walls.wall_persistence_bid,
        wall_persistence_ask=walls.wall_persistence_ask,
        wall_persistence_conditional_bid=walls.wall_persistence_conditional_bid,
        wall_persistence_conditional_ask=walls.wall_persistence_conditional_ask,
        wall_pullaway_bid=walls.wall_pullaway_bid,
        wall_pullaway_ask=walls.wall_pullaway_ask,
        near_touch_cancel_ratio_bid=walls.near_touch_cancel_ratio_bid,
        near_touch_cancel_ratio_ask=walls.near_touch_cancel_ratio_ask,
        executed_vs_displayed_bid=walls.executed_vs_displayed_bid,
        executed_vs_displayed_ask=walls.executed_vs_displayed_ask,
        real_wall_score_bid=walls.real_wall_score_bid,
        real_wall_score_ask=walls.real_wall_score_ask,
        spoof_like_suspicion_bid=walls.spoof_like_suspicion_bid,
        spoof_like_suspicion_ask=walls.spoof_like_suspicion_ask,
        deceptive_liquidity_score=walls.deceptive_liquidity_score,
        observation_coverage_ratio=walls.observation_coverage_ratio,
        ofi_short_window=_ofi_short_window(inputs.window_depth, pair=inputs.normalized_pair),
        aggressive_trade_imbalance=_aggressive_trade_imbalance(inputs.window_trades),
        short_window_volatility=_short_volatility_bps(inputs.window_trades),
        reason_codes=("LOB_REGIME_FEATURES_READY", *walls.reason_codes),
        input_data_hash=_hash_input(
            pair=inputs.normalized_pair,
            computed_at_ns=inputs.eval_time_ns,
            depth_events=inputs.window_depth,
            trades=inputs.window_trades,
        ),
    )


def build_lob_regime_feature_snapshot(
    depth_events: tuple[LobDepth20Snapshot, ...],
    trades: tuple[LobAggTrade, ...] = (),
    *,
    pair: str,
    computed_at_ns: int | None = None,
    window_seconds: float = DEFAULT_LOB_REGIME_WINDOW_SECONDS,
    top_n: int = DEFAULT_LOB_REGIME_TOP_N,
    touch_eps_bps: float = 2.0,
) -> LobRegimeFeatureSnapshot:
    """Compute audit-ready live LOB features using only events available at time t."""

    _validate_lob_regime_knobs(window_seconds=window_seconds, top_n=top_n)
    inputs = _windowed_lob_inputs(
        depth_events,
        trades,
        pair=pair,
        computed_at_ns=computed_at_ns,
        window_seconds=window_seconds,
    )
    rejected = _window_rejection_snapshot(inputs, window_seconds=window_seconds, top_n=top_n)
    if rejected is not None:
        return rejected

    latest = inputs.window_depth[-1]
    basic = _basic_book_features(latest, top_n=top_n)
    walls = _wall_feature_bundle(
        inputs.window_depth,
        inputs.window_trades,
        pair=inputs.normalized_pair,
        computed_at_ns=inputs.eval_time_ns,
        window_seconds=window_seconds,
        top_n=top_n,
        touch_eps_bps=touch_eps_bps,
    )
    liquidity = _liquidity_features(
        inputs.window_depth,
        bid_depth=basic.bid_depth,
        ask_depth=basic.ask_depth,
        top_n=top_n,
    )
    return _ready_lob_regime_snapshot(
        inputs=inputs,
        basic=basic,
        walls=walls,
        liquidity=liquidity,
        window_seconds=window_seconds,
        top_n=top_n,
    )

__all__ = [
    "LOB_REGIME_METHOD_VERSION",
    "LOB_REGIME_METHOD_VERSION_HASH",
    "LOB_REGIME_FEATURE_SET_V1",
    "LOB_REGIME_FEATURE_SET_V2",
    "CANONICAL_LOB_REGIME_FEATURE_SET_VERSION",
    "SUPPORTED_LOB_REGIME_FEATURE_SET_VERSIONS",
    "DEFAULT_LOB_REGIME_WINDOW_SECONDS",
    "MAX_LOB_REGIME_WINDOW_SECONDS",
    "DEFAULT_LOB_REGIME_TOP_N",
    "MAX_LOB_REGIME_TOP_N",
    "LobBookLevel",
    "LobDepth20Snapshot",
    "LobAggTrade",
    "LobRegimeFeatureSnapshot",
    "lob_regime_feature_names",
    "build_lob_regime_feature_snapshot",
]
