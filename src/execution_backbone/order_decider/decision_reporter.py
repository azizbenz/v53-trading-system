"""
Build-3 / order_decider / decision_reporter
Produce executable decision reports. Audit trail for every order/no-trade.

Invariant: every decision is traceable. Every order type is explainable ex post.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .intent_builder import ExecutionIntent, NoTradeDecision, OrderType


class DecisionEvent(BaseModel, frozen=True):
    """An order decision event for audit."""

    pair: str
    engine_id: str
    order_type: OrderType
    is_trade: bool
    justification: str
    expected_cost: float = 0.0
    expected_gain: float = 0.0
    net_expected: float = 0.0
    timestamp: float = 0.0


class DecisionStats(BaseModel, frozen=True):
    """Aggregate decision statistics."""

    total_decisions: int = 0
    trades: int = 0
    no_trades: int = 0
    market_orders: int = 0
    limit_orders: int = 0
    by_no_trade_reason: dict[str, int] = Field(default_factory=dict)
    trade_rate: float = 0.0


class DecisionReporter:
    """Track and report order decisions."""

    def __init__(self) -> None:
        self._events: list[DecisionEvent] = []

    def record_trade(self, intent: ExecutionIntent, timestamp: float = 0.0) -> None:
        self._events.append(DecisionEvent(
            pair=intent.pair,
            engine_id=intent.engine_id,
            order_type=intent.order_type,
            is_trade=True,
            justification=intent.justification,
            expected_cost=intent.expected_cost,
            expected_gain=intent.expected_gain,
            net_expected=intent.expected_gain - intent.expected_cost,
            timestamp=timestamp,
        ))

    def record_no_trade(self, decision: NoTradeDecision, timestamp: float = 0.0) -> None:
        self._events.append(DecisionEvent(
            pair=decision.pair,
            engine_id=decision.engine_id,
            order_type=OrderType.NO_TRADE,
            is_trade=False,
            justification=f"{decision.reason}: {decision.detail}",
            expected_cost=decision.expected_cost,
            expected_gain=decision.expected_gain,
            net_expected=decision.expected_gain - decision.expected_cost,
            timestamp=timestamp,
        ))

    def get_stats(self) -> DecisionStats:
        trades = [e for e in self._events if e.is_trade]
        no_trades = [e for e in self._events if not e.is_trade]
        market = sum(1 for e in trades if e.order_type == OrderType.MARKET)
        limit = sum(1 for e in trades if e.order_type == OrderType.LIMIT)

        by_reason: dict[str, int] = {}
        for e in no_trades:
            reason = e.justification.split(":")[0] if ":" in e.justification else e.justification
            by_reason[reason] = by_reason.get(reason, 0) + 1

        total = len(self._events)
        return DecisionStats(
            total_decisions=total,
            trades=len(trades),
            no_trades=len(no_trades),
            market_orders=market,
            limit_orders=limit,
            by_no_trade_reason=by_reason,
            trade_rate=len(trades) / total if total > 0 else 0.0,
        )

    def get_events(self, pair: str | None = None) -> tuple[DecisionEvent, ...]:
        if pair is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.pair == pair)
