from __future__ import annotations

from dataclasses import dataclass, replace

from execution_backbone.execution_routing_bridge import ExecutionRoutingBridge
from execution_backbone.execution_routing_features import (
    ExecutionRoutingFeatureSnapshot,
    ExecutionRoutingTopOfBookSnapshot,
    ExecutionRoutingVenueFees,
)
from execution_backbone.execution_runtime import (
    ExecutionOpportunity,
    ExecutionRuntime,
    RemoteExecutionState,
    ReplaceReceipt,
    SubmitReceipt,
    VenueOrderEvent,
)
from execution_backbone.order_decider.hybrid_router import HybridRouter
from execution_backbone.order_decider.hybrid_router_calibration import HybridRouterCalibration
from execution_backbone.order_decider.hybrid_router_metrics import HybridRouterMetricsSink
from execution_backbone.order_decider.hybrid_router_shadow import ShadowRoutingLogger


def build_calibration(**overrides: object) -> HybridRouterCalibration:
    return replace(HybridRouterCalibration.default_shadow(), **overrides)


def build_snapshot(
    *,
    side: str = "BUY",
    expected_edge_bps: float = 6.0,
    spread_bps: float = 2.0,
    candidate_notional: float = 100.0,
    final_size: float = 0.5,
    signal_age_s: float = 0.1,
    best_bid_price: float = 100.0,
    best_bid_size: float = 1.0,
    best_ask_price: float = 100.1,
    best_ask_size: float = 1.0,
    top_n_bid_notional: float = 1000.0,
    top_n_ask_notional: float = 1000.0,
    order_book_imbalance: float = 0.4,
    microprice_pressure: float = 0.4,
    aggressive_trade_imbalance: float = 0.3,
    short_window_volatility: float = 0.01,
    short_window_volatility_z: float = 0.0,
    observation_coverage_ratio: float = 0.95,
    market_toxicity_score: float = 0.1,
    regime_transition_risk: float = 0.1,
    regime_stability_score: float = 0.9,
    expected_duration_bucket: str = "short",
    maker_fee_bps: float = 1.0,
    taker_fee_bps: float = 2.0,
) -> ExecutionRoutingFeatureSnapshot:
    return ExecutionRoutingFeatureSnapshot(
        side=side,
        expected_edge_bps=expected_edge_bps,
        spread_bps=spread_bps,
        candidate_notional=candidate_notional,
        final_size=final_size,
        signal_age_s=signal_age_s,
        best_bid_price=best_bid_price,
        best_bid_size=best_bid_size,
        best_ask_price=best_ask_price,
        best_ask_size=best_ask_size,
        top_n_bid_notional=top_n_bid_notional,
        top_n_ask_notional=top_n_ask_notional,
        order_book_imbalance=order_book_imbalance,
        microprice_pressure=microprice_pressure,
        aggressive_trade_imbalance=aggressive_trade_imbalance,
        short_window_volatility=short_window_volatility,
        short_window_volatility_z=short_window_volatility_z,
        observation_coverage_ratio=observation_coverage_ratio,
        market_toxicity_score=market_toxicity_score,
        regime_transition_risk=regime_transition_risk,
        regime_stability_score=regime_stability_score,
        expected_duration_bucket=expected_duration_bucket,
        maker_fee_bps=maker_fee_bps,
        taker_fee_bps=taker_fee_bps,
    )


def build_router(
    *,
    calibration: HybridRouterCalibration | None = None,
    metrics_sink: HybridRouterMetricsSink | None = None,
) -> tuple[HybridRouter, HybridRouterCalibration, HybridRouterMetricsSink]:
    resolved_metrics = metrics_sink or HybridRouterMetricsSink()
    resolved_calibration = calibration or HybridRouterCalibration.default_shadow()
    return (
        HybridRouter(resolved_calibration, resolved_metrics),
        resolved_calibration,
        resolved_metrics,
    )


def build_opportunity(
    *,
    intent_id: str = "intent-1",
    pair: str = "BTCUSDT",
    side: str = "buy",
    quantity: float = 0.5,
    expected_gain: float = 0.0006,
    expected_cost: float = 0.0002,
    spread_bps: float = 2.0,
    routing_features: ExecutionRoutingFeatureSnapshot | None = None,
    metadata: dict[str, object] | None = None,
    **updates: object,
) -> ExecutionOpportunity:
    opportunity = ExecutionOpportunity(
        intent_id=intent_id,
        pair=pair,
        engine_id="engine_a",
        side=side,
        quantity=quantity,
        expected_gain=expected_gain,
        expected_cost=expected_cost,
        score=0.82,
        justification="validated execution path",
        spread_bps=spread_bps,
        reference_price=100.0,
        routing_features=routing_features,
        metadata={} if metadata is None else metadata,
    )
    return opportunity.model_copy(update=updates)


@dataclass(frozen=True)
class FakeLobSnapshot:
    computed_at_ns: int = 1_000_000_000
    observation_coverage_ratio: float = 0.95
    spread_bps: float = 2.0
    order_book_imbalance: float = 0.4
    microprice_pressure: float = 0.4
    aggressive_trade_imbalance: float = 0.3
    short_window_volatility: float = 0.01


@dataclass(frozen=True)
class FakeRegimeSignal:
    market_toxicity_score: float = 0.1
    regime_transition_risk: float = 0.1
    regime_stability_score: float = 0.9
    expected_duration_bucket: str = "short"


def build_top_of_book(
    *,
    best_bid_price: float = 100.0,
    best_bid_size: float = 1.0,
    best_ask_price: float = 100.1,
    best_ask_size: float = 1.0,
    top_n_bid_notional: float = 1000.0,
    top_n_ask_notional: float = 1000.0,
    captured_at_ns: int = 1_000_000_000,
) -> ExecutionRoutingTopOfBookSnapshot:
    return ExecutionRoutingTopOfBookSnapshot(
        best_bid_price=best_bid_price,
        best_bid_size=best_bid_size,
        best_ask_price=best_ask_price,
        best_ask_size=best_ask_size,
        top_n_bid_notional=top_n_bid_notional,
        top_n_ask_notional=top_n_ask_notional,
        captured_at_ns=captured_at_ns,
    )


def build_venue_fees(
    *,
    maker_fee_bps: float = 1.0,
    taker_fee_bps: float = 2.0,
) -> ExecutionRoutingVenueFees:
    return ExecutionRoutingVenueFees(
        maker_fee_bps=maker_fee_bps,
        taker_fee_bps=taker_fee_bps,
    )


class FakeExecutionVenue:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, object, float]] = []
        self.replacements: list[tuple[str, str, object, float]] = []
        self.cancel_requests: list[tuple[str, float, str]] = []
        self._events: list[VenueOrderEvent] = []
        self.remote_state = RemoteExecutionState()
        self._counter = 0
        self.constraints_by_pair: dict[str, object] = {}

    def fetch_venue_constraints(self, pair: str) -> object | None:
        return self.constraints_by_pair.get(pair)

    def submit_order(self, intent: object, now: float) -> SubmitReceipt:
        self._counter += 1
        order_id = f"ord-{self._counter}"
        self.submissions.append((order_id, intent, now))
        return SubmitReceipt(order_id=order_id, submitted_at=now)

    def replace_order(self, original_order_id: str, intent: object, now: float) -> ReplaceReceipt:
        self._counter += 1
        replacement_order_id = f"ord-{self._counter}"
        self.replacements.append((original_order_id, replacement_order_id, intent, now))
        return ReplaceReceipt(
            original_order_id=original_order_id,
            replacement_order_id=replacement_order_id,
            replaced_at=now,
            submitted_at=now,
        )

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        self.cancel_requests.append((order_id, now, reason))

    def poll_order_events(self) -> tuple[VenueOrderEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def fetch_remote_state(self) -> RemoteExecutionState:
        return self.remote_state

    def push_events(self, *events: VenueOrderEvent) -> None:
        self._events.extend(events)


def build_runtime(
    *,
    adapter: FakeExecutionVenue | None = None,
    calibration: HybridRouterCalibration | None = None,
    metrics_sink: HybridRouterMetricsSink | None = None,
    shadow_logger: ShadowRoutingLogger | None = None,
    bridge: ExecutionRoutingBridge | None = None,
    lob_snapshot: object | None = None,
    regime_signal: object | None = None,
    top_of_book: ExecutionRoutingTopOfBookSnapshot | None = None,
    venue_fees: ExecutionRoutingVenueFees | None = None,
    spread_guard_model: object | None = None,
) -> tuple[ExecutionRuntime, FakeExecutionVenue, HybridRouterMetricsSink, ShadowRoutingLogger]:
    resolved_adapter = adapter or FakeExecutionVenue()
    resolved_calibration = calibration or HybridRouterCalibration.default_shadow()
    resolved_metrics = metrics_sink or HybridRouterMetricsSink()
    router = HybridRouter(resolved_calibration, resolved_metrics)
    resolved_shadow_logger = shadow_logger or ShadowRoutingLogger(resolved_metrics)
    resolved_bridge = bridge or ExecutionRoutingBridge(
        resolved_calibration,
        resolved_metrics,
        resolve_current_time_ns=lambda: 1_500_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )
    resolved_lob_snapshot = lob_snapshot or FakeLobSnapshot()
    resolved_regime_signal = regime_signal or FakeRegimeSignal()
    resolved_top_of_book = top_of_book or build_top_of_book()
    resolved_venue_fees = venue_fees or build_venue_fees()
    runtime = ExecutionRuntime(
        resolved_adapter,
        hybrid_router=router,
        hybrid_router_shadow_logger=resolved_shadow_logger,
        hybrid_router_metrics_sink=resolved_metrics,
        execution_routing_bridge=resolved_bridge,
        routing_lob_snapshot_resolver=lambda pair: resolved_lob_snapshot,
        routing_regime_signal_resolver=lambda pair: resolved_regime_signal,
        routing_top_of_book_resolver=lambda pair: resolved_top_of_book,
        routing_venue_fees_resolver=lambda pair: resolved_venue_fees,
        spread_guard_model=spread_guard_model,
    )
    return runtime, resolved_adapter, resolved_metrics, resolved_shadow_logger
