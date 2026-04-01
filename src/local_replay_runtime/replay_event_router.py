"""Replay event router from raw historical events to normalized opportunities."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from interface_contracts import DepthEvent, KlineEvent, SnapshotEvent, TradeEvent

from local_replay_runtime.historical_data_gateway import (
    FeatureScalar,
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from local_replay_runtime.historical_snapshot_loader import (
    HistoricalMarketEventEnvelope,
    HistoricalSnapshotBatch,
    ReplayRouteHint,
)


class ReplayEventRouterConfig(BaseModel, frozen=True):
    """Deterministic routing knobs for raw historical replay events."""

    spread_to_slippage_multiplier: float = Field(default=0.5, ge=0.0)
    default_latency_penalty_bps: float = Field(default=1.0, ge=0.0)


def _merge_route_hints(
    current: ReplayRouteHint,
    incoming: ReplayRouteHint,
) -> ReplayRouteHint:
    merged = current.model_dump()
    incoming_dump = incoming.model_dump()
    default = ReplayRouteHint(
        route_id=current.route_id,
        engine_id=current.engine_id,
    ).model_dump()
    for key, value in incoming_dump.items():
        if key in {"route_id", "engine_id"}:
            continue
        default_value = default.get(key)
        current_value = merged.get(key)
        if isinstance(value, dict):
            merged[key] = {**(current_value or {}), **value}
            continue
        if isinstance(value, tuple):
            if value:
                merged[key] = value
            continue
        if isinstance(value, bool):
            if key == "shared_core_match":
                merged[key] = bool(current_value) and value
            elif value != default_value:
                merged[key] = value
            continue
        if value is None:
            continue
        if current_value == default_value and value != default_value:
            merged[key] = value
            continue
        if key in {
            "raw_score",
            "penalized_score",
            "final_score",
            "expected_edge_bps",
            "slippage_bps",
            "latency_penalty_bps",
            "production_final_score",
            "production_expected_cost",
            "candidate_size",
            "final_size",
            "gross_return_bps",
        } and value != default_value and abs(float(value)) > abs(float(current_value or 0.0)):
            merged[key] = value
            continue
        if value != default_value and current_value == default_value:
            merged[key] = value
    return ReplayRouteHint.model_validate(merged)


def _best_snapshot(
    envelopes: tuple[HistoricalMarketEventEnvelope, ...],
    event_type: type[Any],
) -> Any | None:
    for envelope in reversed(envelopes):
        if isinstance(envelope.event, event_type):
            return envelope.event
    return None


def _close_price(
    snapshot: SnapshotEvent | None,
    kline: KlineEvent | None,
    trade: TradeEvent | None,
    depth: DepthEvent | None,
) -> float:
    if kline is not None:
        return kline.close_price
    if snapshot is not None:
        return snapshot.last_price
    if trade is not None:
        return trade.price
    if depth is not None:
        return round((depth.best_bid + depth.best_ask) / 2.0, 8)
    return 0.0


def _spread_bps(snapshot: SnapshotEvent | None, depth: DepthEvent | None) -> float:
    if snapshot is not None:
        return round(snapshot.spread_bps, 6)
    if depth is not None:
        return round(depth.spread_bps, 6)
    return 0.0


def _event_features(
    snapshot: SnapshotEvent | None,
    kline: KlineEvent | None,
    trade: TradeEvent | None,
    depth: DepthEvent | None,
) -> dict[str, FeatureScalar]:
    features: dict[str, FeatureScalar] = {}
    if snapshot is not None:
        features["snapshot_last_price"] = round(snapshot.last_price, 8)
        features["snapshot_spread_bps"] = round(snapshot.spread_bps, 6)
        features["snapshot_volume_24h"] = round(snapshot.volume_24h, 6)
        if snapshot.funding_rate is not None:
            features["snapshot_funding_rate"] = round(snapshot.funding_rate, 8)
    if depth is not None:
        features["depth_best_bid"] = round(depth.best_bid, 8)
        features["depth_best_ask"] = round(depth.best_ask, 8)
        features["depth_spread_bps"] = round(depth.spread_bps, 6)
    if trade is not None:
        features["trade_price"] = round(trade.price, 8)
        features["trade_notional_usdt"] = round(trade.notional_usdt, 6)
        features["trade_is_maker"] = trade.is_maker
    if kline is not None:
        features["kline_close_price"] = round(kline.close_price, 8)
        features["kline_body_ratio"] = round(kline.body_ratio, 6)
        features["kline_notional_volume_usdt"] = round(kline.notional_volume_usdt, 6)
    return features


def _build_opportunity(
    route_hint: ReplayRouteHint,
    envelopes: tuple[HistoricalMarketEventEnvelope, ...],
    *,
    config: ReplayEventRouterConfig,
) -> HistoricalReplayOpportunity:
    snapshot = _best_snapshot(envelopes, SnapshotEvent)
    depth = _best_snapshot(envelopes, DepthEvent)
    kline = _best_snapshot(envelopes, KlineEvent)
    trade = _best_snapshot(envelopes, TradeEvent)
    latest = envelopes[-1]
    spread_bps = _spread_bps(snapshot, depth)
    slippage_bps = (
        route_hint.slippage_bps
        if route_hint.slippage_bps is not None
        else round(spread_bps * config.spread_to_slippage_multiplier, 6)
    )
    feature_values = {
        **_event_features(snapshot, kline, trade, depth),
        **route_hint.feature_values,
    }
    return HistoricalReplayOpportunity(
        opportunity_id=route_hint.route_id,
        timestamp_ms=latest.timestamp_ms,
        pair=latest.pair,
        engine_id=route_hint.engine_id,
        close_price=_close_price(snapshot, kline, trade, depth),
        regime=route_hint.regime,
        raw_score=route_hint.raw_score,
        penalized_score=route_hint.penalized_score,
        final_score=route_hint.final_score,
        expected_edge_bps=route_hint.expected_edge_bps,
        spread_bps=spread_bps,
        slippage_bps=slippage_bps,
        latency_penalty_bps=max(
            route_hint.latency_penalty_bps,
            config.default_latency_penalty_bps,
        ),
        fill_ratio=route_hint.fill_ratio,
        target_decision_state=route_hint.target_decision_state,
        production_decision_state=route_hint.production_decision_state,
        production_final_score=route_hint.production_final_score,
        production_expected_cost=route_hint.production_expected_cost,
        hard_block_reasons=route_hint.hard_block_reasons,
        ranking_position=route_hint.ranking_position,
        candidate_size=route_hint.candidate_size,
        final_size=route_hint.final_size,
        tier=route_hint.tier,
        gross_return_bps=route_hint.gross_return_bps,
        primary_reason=route_hint.primary_reason,
        feature_values=feature_values,
        shared_core_match=route_hint.shared_core_match,
    )


def route_snapshot_batch_to_dataset(
    snapshot_batch: HistoricalSnapshotBatch,
    *,
    dataset_id: str,
    config: ReplayEventRouterConfig | None = None,
    source: str = "historical_snapshot_router",
) -> HistoricalReplayDataset:
    """Route raw historical events into the normalized replay dataset shape."""

    effective_config = config or ReplayEventRouterConfig()
    grouped: dict[str, list[HistoricalMarketEventEnvelope]] = {}
    route_hints: dict[str, ReplayRouteHint] = {}
    for envelope in snapshot_batch.events:
        grouped.setdefault(envelope.route_id, []).append(envelope)
        if envelope.route_id in route_hints:
            route_hints[envelope.route_id] = _merge_route_hints(
                route_hints[envelope.route_id],
                envelope.route_hint,
            )
        else:
            route_hints[envelope.route_id] = envelope.route_hint

    routed = tuple(
        _build_opportunity(
            route_hints[route_id],
            tuple(
                sorted(
                    envelopes,
                    key=lambda item: (item.timestamp_ms, item.event_type),
                )
            ),
            config=effective_config,
        )
        for route_id, envelopes in sorted(grouped.items())
    )
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset_id,
        source_path=snapshot_batch.source_path,
        records=routed,
        source=source,
    )


__all__ = [
    "ReplayEventRouterConfig",
    "route_snapshot_batch_to_dataset",
]
