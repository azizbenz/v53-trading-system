"""Canonical walls and spoof-like deceptive-liquidity detector for V5.3."""
from __future__ import annotations
from collections.abc import Sequence
from hashlib import sha256
import json
import math
import statistics
from typing import Literal, NamedTuple
from pydantic import BaseModel, ConfigDict, Field, field_validator
from data_backbone.microstructure.lob_regime_features import LobAggTrade, LobDepth20Snapshot
WALLS_AND_SPOOFING_METHOD_VERSION = "walls_and_spoofing.deceptive_liquidity.v1"
WALLS_AND_SPOOFING_METHOD_VERSION_HASH = sha256(WALLS_AND_SPOOFING_METHOD_VERSION.encode("utf-8")).hexdigest()
DEFAULT_WALLS_WINDOW_SECONDS = 5.0
MAX_WALLS_WINDOW_SECONDS = 30.0
DEFAULT_WALLS_TOP_N = 5
MAX_WALLS_TOP_N = 10
DEFAULT_SIZE_TOL = 0.20
DEFAULT_TOUCH_EPS_BPS = 2.0
DEFAULT_CANCEL_DROP_RATIO = 0.70
DEFAULT_DOMINANT_SIDE_MARGIN = 0.10
DEFAULT_REAL_WALL_DOMINANCE_FLOOR = 2.0
_EPS = 1e-12
_REASON_CODE_ORDER = ("micro.wall.bid.strong", "micro.wall.ask.strong", "micro.wall.bid.persistent", "micro.wall.ask.persistent", "micro.wall.bid.pullaway", "micro.wall.ask.pullaway", "micro.spoof_like.bid", "micro.spoof_like.ask", "micro.deceptive_liquidity.high", "micro.wall.neutral", "micro.snapshot.insufficient_data", "micro.snapshot.invalid_input")
class _SideObservation(NamedTuple):
    wall_strength: float
    size_at_wall: float
    near_touch: bool
    timestamp_ns: int
class _NearTouchDrop(NamedTuple):
    displayed_size: float
    dropped_size: float
    start_ns: int
    end_ns: int
class _SideFeatures(NamedTuple):
    wall_strength: float
    wall_persistence: float
    wall_persistence_conditional: float
    wall_pullaway: float
    near_touch_cancel_ratio: float
    executed_vs_displayed: float
    real_wall_score: float
    spoof_suspicion_score: float
class WallsAndSpoofingSnapshot(BaseModel):
    """Frozen audit-ready walls/spoof-like feature snapshot."""
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    window_seconds: float = Field(..., gt=0.0, le=MAX_WALLS_WINDOW_SECONDS)
    n_depth_events: int = Field(..., ge=0)
    n_trades: int = Field(..., ge=0)
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
    book_shape_skew: float = 0.0
    microprice_pressure: float = 0.0
    real_wall_score_bid: float = 0.0
    real_wall_score_ask: float = 0.0
    spoof_suspicion_score_bid: float = 0.0
    spoof_suspicion_score_ask: float = 0.0
    deceptive_liquidity_score: float = 0.0
    observation_coverage_ratio: float = 0.0
    real_wall_score_method: str = "HEURISTIC_WEIGHTED_SCORE"
    spoof_suspicion_score_method: str = "HEURISTIC_WEIGHTED_SCORE"
    calibration_status: str = "CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM"
    dominant_side: Literal["bid", "ask", "neutral"] = "neutral"
    insufficient_data: bool = False
    reason_codes: tuple[str, ...] = ()
    input_data_hash: str = Field(..., min_length=64, max_length=64)
    method_version_hash: str = Field(default=WALLS_AND_SPOOFING_METHOD_VERSION_HASH, min_length=64, max_length=64)
    model_config = ConfigDict(frozen=True, extra="forbid")
    @field_validator(
        "wall_strength_bid",
        "wall_strength_ask",
        "wall_persistence_bid",
        "wall_persistence_ask",
        "wall_persistence_conditional_bid", "wall_persistence_conditional_ask", "observation_coverage_ratio",
        "wall_pullaway_bid",
        "wall_pullaway_ask",
        "near_touch_cancel_ratio_bid",
        "near_touch_cancel_ratio_ask",
        "executed_vs_displayed_bid",
        "executed_vs_displayed_ask",
        "book_shape_skew",
        "microprice_pressure",
        "real_wall_score_bid",
        "real_wall_score_ask",
        "spoof_suspicion_score_bid",
        "spoof_suspicion_score_ask",
        "deceptive_liquidity_score",
    )
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("WallsAndSpoofingSnapshot values must be finite")
        return float(value)
def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, float(value)))
def _normalize_pair(pair: str) -> str:
    normalized = pair.strip().upper()
    if not normalized:
        raise ValueError("pair must not be blank")
    return normalized
def _validate_runtime_inputs(
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
    *,
    pair: str,
    computed_at_ns: int,
    window_seconds: float,
    top_n_levels: int,
) -> None:
    _normalize_pair(pair)
    if computed_at_ns <= 0:
        raise ValueError("computed_at_ns must be >= 1")
    if not 0.0 < window_seconds <= MAX_WALLS_WINDOW_SECONDS:
        raise ValueError(f"window_seconds must be in (0, {MAX_WALLS_WINDOW_SECONDS}]")
    if not 3 <= top_n_levels <= MAX_WALLS_TOP_N:
        raise ValueError(f"top_n_levels must be in [3, {MAX_WALLS_TOP_N}]")
    if any(event.pair != pair for event in depth_events):
        raise ValueError("depth_events pair mismatch")
    if any(
        later.timestamp_ns < earlier.timestamp_ns
        for earlier, later in zip(depth_events, depth_events[1:], strict=False)
    ):
        raise ValueError("depth_events timestamps must be non-decreasing")
    if any(
        later.timestamp_ns < earlier.timestamp_ns
        for earlier, later in zip(trade_events, trade_events[1:], strict=False)
    ):
        raise ValueError("trade_events timestamps must be non-decreasing")
    if any(event.bids[0].price >= event.asks[0].price for event in depth_events):
        raise ValueError("best bid must be strictly < best ask")
    for event in depth_events:
        _validate_level_order(event)
def _validate_level_order(snapshot: LobDepth20Snapshot) -> None:
    bid_prices = [level.price for level in snapshot.bids]
    ask_prices = [level.price for level in snapshot.asks]
    if any(later >= earlier for earlier, later in zip(bid_prices, bid_prices[1:], strict=False)):
        raise ValueError("bid levels must be sorted strictly descending by price")
    if any(later <= earlier for earlier, later in zip(ask_prices, ask_prices[1:], strict=False)):
        raise ValueError("ask levels must be sorted strictly ascending by price")
def _has_full_top_n_depth(
    depth_events: tuple[LobDepth20Snapshot, ...],
    *,
    top_n_levels: int,
) -> bool:
    return all(
        len(event.bids) >= top_n_levels and len(event.asks) >= top_n_levels
        for event in depth_events
    )
def _window_inputs(
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
    *,
    computed_at_ns: int,
    window_seconds: float,
) -> tuple[tuple[LobDepth20Snapshot, ...], tuple[LobAggTrade, ...]]:
    window_start_ns = computed_at_ns - int(window_seconds * 1_000_000_000)
    return (
        tuple(
            event
            for event in depth_events
            if window_start_ns <= event.timestamp_ns <= computed_at_ns
        ),
        tuple(
            trade
            for trade in trade_events
            if window_start_ns <= trade.timestamp_ns <= computed_at_ns
        ),
    )
def _hash_input(
    *,
    pair: str,
    computed_at_ns: int,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
) -> str:
    payload = {
        "pair": pair,
        "computed_at_ns": computed_at_ns,
        "depth_events": [event.model_dump(mode="json") for event in depth_events],
        "trade_events": [trade.model_dump(mode="json") for trade in trade_events],
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
def _side_levels(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    top_n_levels: int,
) -> tuple[tuple[float, float], ...]:
    levels = snapshot.bids if side == "bid" else snapshot.asks
    return tuple((level.price, level.size) for level in levels[: min(top_n_levels, len(levels))])
def _dominant_level(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    top_n_levels: int,
) -> tuple[float, float]:
    levels = _side_levels(snapshot, side=side, top_n_levels=top_n_levels)
    if not levels:
        return 0.0, 0.0
    return max(levels, key=lambda item: item[1])
def _size_at_price(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    price: float,
) -> float:
    levels = snapshot.bids if side == "bid" else snapshot.asks
    for level in levels:
        if level.price == price:
            return level.size
    return 0.0
def _mid(snapshot: LobDepth20Snapshot) -> float:
    return (snapshot.bids[0].price + snapshot.asks[0].price) / 2.0
def _wall_strength_raw(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    top_n_levels: int,
) -> float:
    levels = _side_levels(snapshot, side=side, top_n_levels=top_n_levels)
    if not levels:
        return 0.0
    sizes = [size for _, size in levels]
    return max(sizes) / (statistics.fmean(sizes) + _EPS)
def _book_side_skew(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    top_n_levels: int,
) -> float:
    levels = _side_levels(snapshot, side=side, top_n_levels=top_n_levels)
    if not levels:
        return 0.0
    mid = _mid(snapshot)
    total_depth = sum(size for _, size in levels)
    weights = [size / (total_depth + _EPS) for _, size in levels]
    offsets = [price - mid for price, _ in levels]
    mean_offset = sum(weight * offset for weight, offset in zip(weights, offsets, strict=True))
    variance = sum(
        weight * (offset - mean_offset) ** 2
        for weight, offset in zip(weights, offsets, strict=True)
    )
    return mean_offset / math.sqrt(variance + _EPS)
def _microprice_pressure(snapshot: LobDepth20Snapshot) -> float:
    mid = _mid(snapshot)
    microprice = (
        (snapshot.asks[0].price * snapshot.bids[0].size)
        + (snapshot.bids[0].price * snapshot.asks[0].size)
    ) / (snapshot.bids[0].size + snapshot.asks[0].size + _EPS)
    return (microprice - mid) / (mid + _EPS)
def _distance_to_wall(
    snapshot: LobDepth20Snapshot,
    *,
    side: Literal["bid", "ask"],
    wall_price: float,
) -> float:
    mid = _mid(snapshot)
    if side == "bid":
        return (mid - wall_price) / (mid + _EPS)
    return (wall_price - mid) / (mid + _EPS)
def _historical_wall(
    depth_events: tuple[LobDepth20Snapshot, ...],
    *,
    side: Literal["bid", "ask"],
    top_n_levels: int,
    dominance_floor: float,
) -> tuple[float, float]:
    best_price = 0.0
    best_size = 0.0
    for snapshot in depth_events:
        if _wall_strength_raw(snapshot, side=side, top_n_levels=top_n_levels) < dominance_floor:
            continue
        price, size = _dominant_level(snapshot, side=side, top_n_levels=top_n_levels)
        if size > best_size:
            best_price = price
            best_size = size
    return best_price, best_size
def _side_observations(
    depth_events: tuple[LobDepth20Snapshot, ...],
    *,
    side: Literal["bid", "ask"],
    wall_price: float,
    top_n_levels: int,
    touch_eps_bps: float,
) -> tuple[_SideObservation, ...]:
    observations: list[_SideObservation] = []
    for snapshot in depth_events:
        if wall_price <= 0.0:
            observations.append(
                _SideObservation(
                    wall_strength=0.0,
                    size_at_wall=0.0,
                    near_touch=False,
                    timestamp_ns=snapshot.timestamp_ns,
                )
            )
            continue
        distance = _distance_to_wall(snapshot, side=side, wall_price=wall_price)
        observations.append(
            _SideObservation(
                wall_strength=_wall_strength_raw(snapshot, side=side, top_n_levels=top_n_levels),
                size_at_wall=_size_at_price(snapshot, side=side, price=wall_price),
                near_touch=distance <= (touch_eps_bps / 10_000.0),
                timestamp_ns=snapshot.timestamp_ns,
            )
        )
    return tuple(observations)
def _robust_z01(current: float, series: Sequence[float]) -> float:
    finite_series = [float(value) for value in series if math.isfinite(value)]
    if len(finite_series) < 3:
        return _fallback_z01(current)
    median = statistics.median(finite_series)
    mad = statistics.median(abs(value - median) for value in finite_series)
    if mad <= _EPS:
        return _fallback_z01(current)
    robust_z = (current - median) / (mad + _EPS)
    return 1.0 / (1.0 + math.exp(-robust_z))
def _fallback_z01(value: float) -> float:
    positive = max(0.0, float(value))
    return positive / (1.0 + positive)
def _observed_span_ns(depth_events: tuple[LobDepth20Snapshot, ...]) -> int:
    if len(depth_events) < 2:
        return 0
    return max(depth_events[-1].timestamp_ns - depth_events[0].timestamp_ns, 0)
def _wall_persistence(
    observations: tuple[_SideObservation, ...],
    *,
    depth_events: tuple[LobDepth20Snapshot, ...],
    computed_at_ns: int,
    window_seconds: float,
    wall_size: float,
    size_tol: float,
) -> tuple[float, float]:
    if not observations or wall_size <= 0.0:
        return 0.0, 0.0
    active_ns = 0
    total_ns = max(int(window_seconds * 1_000_000_000), 1)
    observed_ns = max(_observed_span_ns(depth_events), 1)
    min_size = wall_size * (1.0 - size_tol)
    for index, observation in enumerate(observations):
        start_ns = depth_events[index].timestamp_ns
        end_ns = (
            depth_events[index + 1].timestamp_ns
            if index + 1 < len(depth_events)
            else computed_at_ns
        )
        if observation.size_at_wall >= min_size:
            active_ns += max(0, end_ns - start_ns)
    return _clip(active_ns / total_ns), _clip(active_ns / observed_ns)
def _near_touch_drops(observations: tuple[_SideObservation, ...]) -> tuple[_NearTouchDrop, ...]:
    drops: list[_NearTouchDrop] = []
    previous: _SideObservation | None = None
    for observation in observations:
        if previous is not None and previous.near_touch:
            drops.append(
                _NearTouchDrop(
                    displayed_size=previous.size_at_wall,
                    dropped_size=max(previous.size_at_wall - observation.size_at_wall, 0.0),
                    start_ns=previous.timestamp_ns,
                    end_ns=observation.timestamp_ns,
                )
            )
        previous = observation
    return tuple(drops)
def _wall_pullaway(
    drops: tuple[_NearTouchDrop, ...],
    *,
    executed_by_interval: Sequence[float],
    cancel_drop_ratio: float,
) -> float:
    if not drops:
        return 0.0
    pullaway_events = sum(
        1
        for drop, executed in zip(drops, executed_by_interval, strict=True)
        if (drop.dropped_size / (drop.displayed_size + _EPS) >= cancel_drop_ratio)
        and executed < drop.dropped_size
    )
    return _clip(pullaway_events / len(drops))
def _near_touch_cancel_ratio(
    drops: tuple[_NearTouchDrop, ...],
    *,
    executed_by_interval: Sequence[float],
) -> float:
    if not drops:
        return 0.0
    displayed = sum(drop.displayed_size for drop in drops)
    cancelled = sum(
        max(drop.dropped_size - executed, 0.0)
        for drop, executed in zip(drops, executed_by_interval, strict=True)
    )
    return _clip(cancelled / (displayed + _EPS))
def _executed_vs_displayed(
    trade_events: tuple[LobAggTrade, ...],
    *,
    side: Literal["bid", "ask"],
    wall_price: float,
    displayed_volume: float,
    touch_eps_bps: float,
) -> float:
    if displayed_volume <= 0.0 or wall_price <= 0.0:
        return 0.0
    executed = _executed_volume_against_wall(
        trade_events,
        side=side,
        wall_price=wall_price,
        touch_eps_bps=touch_eps_bps,
    )
    return _clip(executed / (displayed_volume + _EPS))
def _executed_volume_against_wall(
    trade_events: tuple[LobAggTrade, ...],
    *,
    side: Literal["bid", "ask"],
    wall_price: float,
    touch_eps_bps: float,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> float:
    aggressor_side = "sell" if side == "bid" else "buy"
    executed = 0.0
    for trade in trade_events:
        if trade.aggressor_side != aggressor_side:
            continue
        if start_ns is not None and trade.timestamp_ns < start_ns:
            continue
        if end_ns is not None and trade.timestamp_ns > end_ns:
            continue
        distance_bps = abs(trade.price - wall_price) / (wall_price + _EPS) * 10_000.0
        if distance_bps <= touch_eps_bps:
            executed += trade.quantity
    return executed
def _executed_by_drop_interval(
    trade_events: tuple[LobAggTrade, ...],
    *,
    side: Literal["bid", "ask"],
    wall_price: float,
    touch_eps_bps: float,
    drops: tuple[_NearTouchDrop, ...],
) -> tuple[float, ...]:
    return tuple(
        _executed_volume_against_wall(
            trade_events,
            side=side,
            wall_price=wall_price,
            touch_eps_bps=touch_eps_bps,
            start_ns=drop.start_ns,
            end_ns=drop.end_ns,
        )
        for drop in drops
    )
def _side_activity_measures(
    observations: tuple[_SideObservation, ...],
    *,
    trade_events: tuple[LobAggTrade, ...],
    side: Literal["bid", "ask"],
    wall_price: float,
    touch_eps_bps: float,
    cancel_drop_ratio: float,
) -> tuple[float, float, float]:
    drops = _near_touch_drops(observations)
    executed_by_interval = _executed_by_drop_interval(
        trade_events,
        side=side,
        wall_price=wall_price,
        touch_eps_bps=touch_eps_bps,
        drops=drops,
    )
    wall_pullaway = _wall_pullaway(
        drops,
        executed_by_interval=executed_by_interval,
        cancel_drop_ratio=cancel_drop_ratio,
    )
    displayed_volume = sum(drop.displayed_size for drop in drops)
    return (
        wall_pullaway,
        _near_touch_cancel_ratio(drops, executed_by_interval=executed_by_interval),
        _executed_vs_displayed(
            trade_events,
            side=side,
            wall_price=wall_price,
            displayed_volume=displayed_volume,
            touch_eps_bps=touch_eps_bps,
        ),
    )
def _score_side_features(
    *,
    wall_strength_z01: float,
    persistence: float,
    wall_pullaway: float,
    near_touch_cancel_ratio: float,
    executed_vs_displayed: float,
    microprice_pressure_z01: float,
) -> tuple[float, float]:
    return (
        _clip(
            (0.35 * wall_strength_z01)
            + (0.35 * persistence)
            + (0.20 * executed_vs_displayed)
            - (0.10 * wall_pullaway)
        ),
        _clip(
            (0.25 * wall_strength_z01)
            + (0.25 * wall_pullaway)
            + (0.20 * near_touch_cancel_ratio)
            + (0.20 * (1.0 - executed_vs_displayed))
            + (0.10 * microprice_pressure_z01)
        ),
    )
def _empty_side_features() -> _SideFeatures:
    return _SideFeatures(
        wall_strength=0.0,
        wall_persistence=0.0,
        wall_persistence_conditional=0.0,
        wall_pullaway=0.0,
        near_touch_cancel_ratio=0.0,
        executed_vs_displayed=0.0,
        real_wall_score=0.0,
        spoof_suspicion_score=0.0,
    )
def _side_features(
    observations: tuple[_SideObservation, ...],
    *,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
    side: Literal["bid", "ask"],
    wall_price: float,
    wall_size: float,
    computed_at_ns: int,
    window_seconds: float,
    size_tol: float,
    microprice_pressure_series: Sequence[float],
    touch_eps_bps: float,
    cancel_drop_ratio: float,
) -> _SideFeatures:
    if wall_price <= 0.0 or wall_size <= 0.0:
        return _empty_side_features()
    current_wall_strength = observations[-1].wall_strength if observations else 0.0
    wall_strength_z01 = _robust_z01(
        current_wall_strength,
        [observation.wall_strength for observation in observations],
    )
    wall_pullaway, near_touch_cancel_ratio, executed_vs_displayed = _side_activity_measures(
        observations,
        trade_events=trade_events,
        side=side,
        wall_price=wall_price,
        touch_eps_bps=touch_eps_bps,
        cancel_drop_ratio=cancel_drop_ratio,
    )
    persistence, persistence_conditional = _wall_persistence(
        observations,
        depth_events=depth_events,
        computed_at_ns=computed_at_ns,
        window_seconds=window_seconds,
        wall_size=wall_size,
        size_tol=size_tol,
    )
    microprice_pressure_z01 = _robust_z01(
        abs(microprice_pressure_series[-1]) if microprice_pressure_series else 0.0,
        [abs(value) for value in microprice_pressure_series],
    )
    real_wall_score, spoof_suspicion_score = _score_side_features(
        wall_strength_z01=wall_strength_z01,
        persistence=persistence,
        wall_pullaway=wall_pullaway,
        near_touch_cancel_ratio=near_touch_cancel_ratio,
        executed_vs_displayed=executed_vs_displayed,
        microprice_pressure_z01=microprice_pressure_z01,
    )
    return _SideFeatures(
        wall_strength=current_wall_strength,
        wall_persistence=persistence,
        wall_persistence_conditional=persistence_conditional,
        wall_pullaway=wall_pullaway,
        near_touch_cancel_ratio=near_touch_cancel_ratio,
        executed_vs_displayed=executed_vs_displayed,
        real_wall_score=real_wall_score,
        spoof_suspicion_score=spoof_suspicion_score,
    )
def _reason_codes(
    *,
    bid: _SideFeatures,
    ask: _SideFeatures,
    deceptive_liquidity_score: float,
    dominant_side: Literal["bid", "ask", "neutral"],
    insufficient_data: bool,
) -> tuple[str, ...]:
    if insufficient_data:
        return ("micro.snapshot.insufficient_data",)
    codes: list[str] = []
    if dominant_side == "bid":
        codes.append("micro.wall.bid.strong")
    elif dominant_side == "ask":
        codes.append("micro.wall.ask.strong")
    else:
        codes.append("micro.wall.neutral")
    if bid.wall_persistence >= 0.50 and bid.real_wall_score >= 0.50:
        codes.append("micro.wall.bid.persistent")
    if ask.wall_persistence >= 0.50 and ask.real_wall_score >= 0.50:
        codes.append("micro.wall.ask.persistent")
    if bid.wall_pullaway >= 0.50:
        codes.append("micro.wall.bid.pullaway")
    if ask.wall_pullaway >= 0.50:
        codes.append("micro.wall.ask.pullaway")
    if bid.spoof_suspicion_score >= 0.60:
        codes.append("micro.spoof_like.bid")
    if ask.spoof_suspicion_score >= 0.60:
        codes.append("micro.spoof_like.ask")
    if deceptive_liquidity_score >= 0.60:
        codes.append("micro.deceptive_liquidity.high")
    return tuple(code for code in _REASON_CODE_ORDER if code in codes)
def _insufficient_snapshot(
    *,
    pair: str,
    computed_at_ns: int,
    window_seconds: float,
    n_depth_events: int,
    n_trades: int,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
) -> WallsAndSpoofingSnapshot:
    return WallsAndSpoofingSnapshot(
        pair=pair,
        computed_at_ns=computed_at_ns,
        window_seconds=window_seconds,
        n_depth_events=n_depth_events,
        n_trades=n_trades,
        insufficient_data=True,
        dominant_side="neutral",
        reason_codes=("micro.snapshot.insufficient_data",),
        input_data_hash=_hash_input(
            pair=pair,
            computed_at_ns=computed_at_ns,
            depth_events=depth_events,
            trade_events=trade_events,
        ),
    )
def evaluate_walls_and_spoofing(
    *,
    pair: str,
    computed_at_ns: int,
    depth_events: Sequence[LobDepth20Snapshot],
    trade_events: Sequence[LobAggTrade],
    window_seconds: float = DEFAULT_WALLS_WINDOW_SECONDS,
    top_n_levels: int = DEFAULT_WALLS_TOP_N,
    size_tol: float = DEFAULT_SIZE_TOL,
    touch_eps_bps: float = DEFAULT_TOUCH_EPS_BPS,
    cancel_drop_ratio: float = DEFAULT_CANCEL_DROP_RATIO,
    dominant_side_margin: float = DEFAULT_DOMINANT_SIDE_MARGIN,
    real_wall_dominance_floor: float = DEFAULT_REAL_WALL_DOMINANCE_FLOOR,
) -> WallsAndSpoofingSnapshot:
    """Evaluate walls and spoof-like deceptive liquidity from depth and aggTrades."""
    normalized_pair = _normalize_pair(pair)
    depth = tuple(depth_events)
    trades = tuple(trade_events)
    _validate_runtime_inputs(depth, trades, pair=normalized_pair, computed_at_ns=computed_at_ns, window_seconds=window_seconds, top_n_levels=top_n_levels)
    if not 0.0 <= cancel_drop_ratio <= 1.0:
        raise ValueError("cancel_drop_ratio must be in [0, 1]")
    window_depth, window_trades = _window_inputs(depth, trades, computed_at_ns=computed_at_ns, window_seconds=window_seconds)
    if len(window_depth) < 2 or not _has_full_top_n_depth(window_depth, top_n_levels=top_n_levels):
        return _insufficient_snapshot(pair=normalized_pair, computed_at_ns=computed_at_ns, window_seconds=window_seconds, n_depth_events=len(window_depth), n_trades=len(window_trades), depth_events=window_depth, trade_events=window_trades)
    bid_wall_price, bid_wall_size = _historical_wall(window_depth, side="bid", top_n_levels=top_n_levels, dominance_floor=real_wall_dominance_floor)
    ask_wall_price, ask_wall_size = _historical_wall(window_depth, side="ask", top_n_levels=top_n_levels, dominance_floor=real_wall_dominance_floor)
    microprice_pressure_series = [_microprice_pressure(snapshot) for snapshot in window_depth]
    bid = _side_features(_side_observations(window_depth, side="bid", wall_price=bid_wall_price, top_n_levels=top_n_levels, touch_eps_bps=touch_eps_bps), depth_events=window_depth, trade_events=window_trades, side="bid", wall_price=bid_wall_price, wall_size=bid_wall_size, computed_at_ns=computed_at_ns, window_seconds=window_seconds, size_tol=size_tol, microprice_pressure_series=microprice_pressure_series, touch_eps_bps=touch_eps_bps, cancel_drop_ratio=cancel_drop_ratio)
    ask = _side_features(_side_observations(window_depth, side="ask", wall_price=ask_wall_price, top_n_levels=top_n_levels, touch_eps_bps=touch_eps_bps), depth_events=window_depth, trade_events=window_trades, side="ask", wall_price=ask_wall_price, wall_size=ask_wall_size, computed_at_ns=computed_at_ns, window_seconds=window_seconds, size_tol=size_tol, microprice_pressure_series=microprice_pressure_series, touch_eps_bps=touch_eps_bps, cancel_drop_ratio=cancel_drop_ratio)
    real_wall_delta = bid.real_wall_score - ask.real_wall_score
    if real_wall_delta > dominant_side_margin:
        dominant_side: Literal["bid", "ask", "neutral"] = "bid"
    elif -real_wall_delta > dominant_side_margin:
        dominant_side = "ask"
    else:
        dominant_side = "neutral"
    deceptive_liquidity_score = max(bid.spoof_suspicion_score, ask.spoof_suspicion_score)
    observation_coverage_ratio = _clip(
        _observed_span_ns(window_depth) / max(int(window_seconds * 1_000_000_000), 1)
    )
    latest = window_depth[-1]
    return WallsAndSpoofingSnapshot(
        pair=normalized_pair, computed_at_ns=computed_at_ns, window_seconds=window_seconds, n_depth_events=len(window_depth), n_trades=len(window_trades),
        wall_strength_bid=bid.wall_strength, wall_strength_ask=ask.wall_strength, wall_persistence_bid=bid.wall_persistence, wall_persistence_ask=ask.wall_persistence,
        wall_persistence_conditional_bid=bid.wall_persistence_conditional, wall_persistence_conditional_ask=ask.wall_persistence_conditional,
        wall_pullaway_bid=bid.wall_pullaway, wall_pullaway_ask=ask.wall_pullaway, near_touch_cancel_ratio_bid=bid.near_touch_cancel_ratio, near_touch_cancel_ratio_ask=ask.near_touch_cancel_ratio,
        executed_vs_displayed_bid=bid.executed_vs_displayed, executed_vs_displayed_ask=ask.executed_vs_displayed,
        book_shape_skew=_book_side_skew(latest, side="ask", top_n_levels=top_n_levels) - _book_side_skew(latest, side="bid", top_n_levels=top_n_levels), microprice_pressure=microprice_pressure_series[-1],
        real_wall_score_bid=bid.real_wall_score, real_wall_score_ask=ask.real_wall_score, spoof_suspicion_score_bid=bid.spoof_suspicion_score, spoof_suspicion_score_ask=ask.spoof_suspicion_score,
        deceptive_liquidity_score=deceptive_liquidity_score, observation_coverage_ratio=observation_coverage_ratio, dominant_side=dominant_side, insufficient_data=False,
        reason_codes=_reason_codes(bid=bid, ask=ask, deceptive_liquidity_score=deceptive_liquidity_score, dominant_side=dominant_side, insufficient_data=False),
        input_data_hash=_hash_input(pair=normalized_pair, computed_at_ns=computed_at_ns, depth_events=window_depth, trade_events=window_trades),
    )
__all__ = ["WALLS_AND_SPOOFING_METHOD_VERSION", "WALLS_AND_SPOOFING_METHOD_VERSION_HASH", "DEFAULT_WALLS_WINDOW_SECONDS", "MAX_WALLS_WINDOW_SECONDS", "DEFAULT_WALLS_TOP_N", "MAX_WALLS_TOP_N", "DEFAULT_CANCEL_DROP_RATIO", "WallsAndSpoofingSnapshot", "evaluate_walls_and_spoofing"]
