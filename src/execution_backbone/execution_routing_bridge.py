"""Build-3 live feature bridge for the hybrid routing surface."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Callable

from .execution_runtime_models import ExecutionOpportunity
from .execution_routing_features import (
    ExecutionRoutingFeatureSnapshot,
    ExecutionRoutingTopOfBookSnapshot,
    ExecutionRoutingVenueFees,
    RoutingFeatureProjectionError,
    attach_snapshot_reason_codes,
)


@dataclass(frozen=True)
class ExecutionRoutingBridgeConfig:
    min_coverage_ratio: float = 0.5
    max_snapshot_age_s: float = 2.0
    vol_zscore_window_s: float = 300.0


class ExecutionRoutingBridge:
    """Project current live VPS inputs into the Build-3 hybrid routing feature contract."""

    def __init__(
        self,
        *,
        config: ExecutionRoutingBridgeConfig | None = None,
        resolve_current_time_ns: Callable[[], int] | None = None,
        resolve_volatility_stats: Callable[[str, float], tuple[float, float] | None] | None = None,
    ) -> None:
        self._config = config or ExecutionRoutingBridgeConfig()
        self._resolve_current_time_ns = resolve_current_time_ns or time.monotonic_ns
        self._resolve_volatility_stats = resolve_volatility_stats

    def project(
        self,
        *,
        opportunity: ExecutionOpportunity,
        lob_regime_snapshot: object,
        regime_signal: object,
        top_of_book: ExecutionRoutingTopOfBookSnapshot,
        venue_fees: ExecutionRoutingVenueFees,
    ) -> ExecutionRoutingFeatureSnapshot:
        computed_at_ns = int(_require_attr(lob_regime_snapshot, "computed_at_ns"))
        observation_coverage_ratio = float(_require_attr(lob_regime_snapshot, "observation_coverage_ratio"))
        current_time_ns = int(self._resolve_current_time_ns())
        age_s = max(0.0, (current_time_ns - computed_at_ns) / 1_000_000_000.0)
        if age_s > self._config.max_snapshot_age_s:
            raise RoutingFeatureProjectionError(
                f"LOB snapshot is stale: age_s={age_s:.6f} > {self._config.max_snapshot_age_s:.6f}"
            )
        if observation_coverage_ratio < self._config.min_coverage_ratio:
            raise RoutingFeatureProjectionError(
                "LOB snapshot observation_coverage_ratio below governed minimum"
            )

        side = _normalize_side(opportunity.side)
        reason_codes: list[str] = []
        short_window_volatility = float(_require_attr(lob_regime_snapshot, "short_window_volatility"))
        short_window_volatility_z = _resolve_short_window_volatility_z(
            pair=opportunity.pair,
            short_window_volatility=short_window_volatility,
            window_seconds=self._config.vol_zscore_window_s,
            resolve_volatility_stats=self._resolve_volatility_stats,
            reason_codes=reason_codes,
        )
        snapshot = ExecutionRoutingFeatureSnapshot(
            side=side,
            expected_edge_bps=float(opportunity.expected_gain) * 10_000.0,
            spread_bps=float(_require_attr(lob_regime_snapshot, "spread_bps")),
            candidate_notional=_resolve_candidate_notional(opportunity, top_of_book),
            final_size=float(opportunity.quantity),
            signal_age_s=_resolve_signal_age_s(opportunity, current_time_ns),
            best_bid_price=float(top_of_book.best_bid_price),
            best_bid_size=float(top_of_book.best_bid_size),
            best_ask_price=float(top_of_book.best_ask_price),
            best_ask_size=float(top_of_book.best_ask_size),
            top_n_bid_notional=float(top_of_book.top_n_bid_notional),
            top_n_ask_notional=float(top_of_book.top_n_ask_notional),
            order_book_imbalance=float(_require_attr(lob_regime_snapshot, "order_book_imbalance")),
            microprice_pressure=float(_require_attr(lob_regime_snapshot, "microprice_pressure")),
            aggressive_trade_imbalance=float(_require_attr(lob_regime_snapshot, "aggressive_trade_imbalance")),
            short_window_volatility=short_window_volatility,
            short_window_volatility_z=short_window_volatility_z,
            observation_coverage_ratio=observation_coverage_ratio,
            market_toxicity_score=float(_require_attr(regime_signal, "market_toxicity_score")),
            regime_transition_risk=float(_require_attr(regime_signal, "regime_transition_risk")),
            regime_stability_score=float(_require_attr(regime_signal, "regime_stability_score")),
            expected_duration_bucket=_resolve_duration_bucket(regime_signal),
            maker_fee_bps=float(venue_fees.maker_fee_bps),
            taker_fee_bps=float(venue_fees.taker_fee_bps),
        )
        return attach_snapshot_reason_codes(snapshot, tuple(reason_codes))


def _require_attr(source: object, name: str) -> object:
    if not hasattr(source, name):
        raise RoutingFeatureProjectionError(f"Missing live routing attribute: {name}")
    value = getattr(source, name)
    if isinstance(value, (int, float)) and not math.isfinite(float(value)):
        raise RoutingFeatureProjectionError(f"Non-finite live routing attribute: {name}")
    return value


def _resolve_duration_bucket(regime_signal: object) -> str:
    raw_value = _require_attr(regime_signal, "expected_duration_bucket")
    enum_value = getattr(raw_value, "value", raw_value)
    return str(enum_value)


def _normalize_side(side: str) -> str:
    normalized = side.strip().casefold()
    if normalized == "buy":
        return "BUY"
    if normalized == "sell":
        return "SELL"
    raise RoutingFeatureProjectionError(f"Unsupported execution side: {side!r}")


def _resolve_candidate_notional(
    opportunity: ExecutionOpportunity,
    top_of_book: ExecutionRoutingTopOfBookSnapshot,
) -> float:
    anchor = opportunity.reference_price if opportunity.reference_price is not None else opportunity.price_limit
    if anchor is None:
        anchor = top_of_book.best_ask_price if opportunity.side.strip().casefold() == "buy" else top_of_book.best_bid_price
    notional = float(opportunity.quantity) * float(anchor)
    if not math.isfinite(notional) or notional <= 0.0:
        raise RoutingFeatureProjectionError("candidate_notional must be finite and > 0")
    return notional


def _resolve_signal_age_s(opportunity: ExecutionOpportunity, current_time_ns: int) -> float:
    if opportunity.signal_arrival_monotonic_s is None:
        return 0.0
    current_time_s = current_time_ns / 1_000_000_000.0
    age_s = current_time_s - float(opportunity.signal_arrival_monotonic_s)
    if not math.isfinite(age_s):
        raise RoutingFeatureProjectionError("signal_age_s must be finite")
    return max(0.0, age_s)


def _resolve_short_window_volatility_z(
    *,
    pair: str,
    short_window_volatility: float,
    window_seconds: float,
    resolve_volatility_stats: Callable[[str, float], tuple[float, float] | None] | None,
    reason_codes: list[str],
) -> float:
    if resolve_volatility_stats is None:
        reason_codes.append("vol_zscore_unavailable")
        return 0.0
    stats = resolve_volatility_stats(pair, window_seconds)
    if stats is None:
        reason_codes.append("vol_zscore_unavailable")
        return 0.0
    mean_value, std_value = stats
    if not math.isfinite(mean_value) or not math.isfinite(std_value) or std_value <= 0.0:
        reason_codes.append("vol_zscore_unavailable")
        return 0.0
    z_score = (float(short_window_volatility) - mean_value) / std_value
    if not math.isfinite(z_score):
        reason_codes.append("vol_zscore_unavailable")
        return 0.0
    return float(z_score)


__all__ = [
    "ExecutionRoutingBridge",
    "ExecutionRoutingBridgeConfig",
]
