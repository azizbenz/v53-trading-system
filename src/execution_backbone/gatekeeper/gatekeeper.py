"""Bounded canonical execution gatekeeper over the existing Build-3 guard chain."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field
from sharia_compliance.contracts import ShariaPermit, ShariaRejection

from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeDecision
from execution_backbone.order_decider.execution_guard import (
    GuardResult,
    GuardVerdict,
    check_execution_guards,
)
from execution_backbone.order_decider.intent_builder import (
    ExecutionIntent,
    NoTradeDecision,
    NoTradeReason,
    OrderType,
    VenueConstraintSnapshot,
    build_intent,
)
from execution_backbone.order_decider.order_type_selector import (
    OrderTypeDecision,
    select_order_type,
)
from execution_backbone.order_decider.timeout_policy_selector import select_timeout_policy
from execution_backbone.rate_limiter import ExecutionRateLimitDecision
from execution_backbone.spread_guard import ExecutionSpreadGuardDecision


class ExecutionOpportunityLike(Protocol):
    intent_id: str
    pair: str
    engine_id: str
    side: str
    quantity: float
    expected_gain: float
    expected_cost: float
    score: float
    justification: str
    spread_bps: float
    safety_margin: float
    pair_suspended: bool
    pair_health_score: float
    pair_health_min: float
    risk_budget_available: bool
    infrastructure_ok: bool
    data_stale: bool
    max_acceptable_cost: float
    reference_price: float | None
    price_limit: float | None
    profile: str
    venue_constraints: VenueConstraintSnapshot | None
    metadata: dict[str, object]


class ExecutionNoTradeFilterOutcomeLike(Protocol):
    blocked: bool
    block_reason_codes: tuple[str, ...]
    detail: str


class SpreadGuardResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> ExecutionSpreadGuardDecision | None:
        ...


class FeeAwareEdgeResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> FeeAwareEdgeDecision | None:
        ...


class ShariaTradeAuthorizerResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> ShariaPermit | ShariaRejection | None:
        ...


class RateLimitResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> ExecutionRateLimitDecision | None:
        ...


class VenueConstraintResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> VenueConstraintSnapshot | None:
        ...


class VenueOrderNormalizer(Protocol):
    def __call__(
        self,
        *,
        quantity: float,
        side: str,
        order_type: OrderType,
        price_limit: float | None,
        reference_price: float | None,
        constraints: VenueConstraintSnapshot,
    ) -> "ExecutionVenueNormalizationResult":
        ...


class MaxSpreadForMarketResolver(Protocol):
    def __call__(self, opportunity: ExecutionOpportunityLike) -> float:
        ...


class ExecutionNoTradeFilterResolver(Protocol):
    def __call__(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> ExecutionNoTradeFilterOutcomeLike | None:
        ...


class ExecutionGateName(StrEnum):
    SPREAD_GUARD = "spread_guard"
    ORDER_TYPE = "order_type"
    FEE_AWARE_EDGE = "fee_aware_edge"
    SHARIA = "sharia"
    RATE_LIMITER = "rate_limiter"
    EXECUTION_GUARD = "execution_guard"
    PRICE_LIMIT = "price_limit"
    VENUE_CONSTRAINTS = "venue_constraints"
    EXECUTION_NO_TRADE_FILTER = "execution_no_trade_filter"


class ExecutionGateTraceVerdict(StrEnum):
    PASSED = "passed"
    REFUSED = "refused"


class ExecutionGateRefusalDisposition(StrEnum):
    NO_TRADE = "no_trade"
    BLOCKED = "blocked"


class ExecutionGateTrace(BaseModel, frozen=True):
    gate_name: ExecutionGateName
    verdict: ExecutionGateTraceVerdict
    reason_code: str = ""
    detail: str = ""


class ExecutionVenueNormalizationResult(BaseModel, frozen=True):
    quantity: float
    quantity_exact: str
    price_limit: float | None = None
    price_limit_exact: str | None = None
    error_detail: str | None = None


class ExecutionPermit(BaseModel, frozen=True):
    intent: ExecutionIntent
    detail: str = ""
    order_decision: OrderTypeDecision
    trace: tuple[ExecutionGateTrace, ...] = ()


class ExecutionRefusal(BaseModel, frozen=True):
    disposition: ExecutionGateRefusalDisposition
    gate_name: ExecutionGateName
    no_trade: NoTradeDecision
    detail: str = ""
    reason_codes: tuple[str, ...] = ()
    guard: GuardResult | None = None
    trace: tuple[ExecutionGateTrace, ...] = ()


class ExecutionGatekeeper:
    """Canonical Build-3 authorization wrapper over the existing execution guard chain."""

    def __init__(
        self,
        *,
        resolve_spread_guard: SpreadGuardResolver,
        resolve_fee_aware_edge: FeeAwareEdgeResolver,
        authorize_sharia: ShariaTradeAuthorizerResolver,
        resolve_rate_limit: RateLimitResolver,
        resolve_venue_constraints: VenueConstraintResolver,
        normalize_venue_order_fields: VenueOrderNormalizer,
        resolve_max_spread_for_market: MaxSpreadForMarketResolver,
        evaluate_execution_no_trade_filter: ExecutionNoTradeFilterResolver,
    ) -> None:
        self._resolve_spread_guard = resolve_spread_guard
        self._resolve_fee_aware_edge = resolve_fee_aware_edge
        self._authorize_sharia = authorize_sharia
        self._resolve_rate_limit = resolve_rate_limit
        self._resolve_venue_constraints = resolve_venue_constraints
        self._normalize_venue_order_fields = normalize_venue_order_fields
        self._resolve_max_spread_for_market = resolve_max_spread_for_market
        self._evaluate_execution_no_trade_filter = evaluate_execution_no_trade_filter

    def authorize(
        self,
        opportunity: ExecutionOpportunityLike,
    ) -> ExecutionPermit | ExecutionRefusal:
        trace: list[ExecutionGateTrace] = []

        spread_guard_decision = self._resolve_spread_guard(opportunity)
        if spread_guard_decision is not None and spread_guard_decision.blocked:
            return self._refuse(
                gate_name=ExecutionGateName.SPREAD_GUARD,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.HARD_BLOCKER,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=spread_guard_decision.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_spread_guard_context(spread_guard_decision),
                reason_codes=(spread_guard_decision.reason_code,),
                trace=trace,
            )
        if spread_guard_decision is not None:
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.SPREAD_GUARD,
                verdict=ExecutionGateTraceVerdict.PASSED,
                reason_code=spread_guard_decision.reason_code,
                detail=spread_guard_decision.detail,
            )

        order_decision = select_order_type(
            expected_gain=opportunity.expected_gain,
            expected_cost=opportunity.expected_cost,
            safety_margin=opportunity.safety_margin,
            spread_bps=opportunity.spread_bps,
            max_spread_for_market=self._resolve_max_spread_for_market(opportunity),
        )
        if order_decision.order_type == OrderType.NO_TRADE:
            reason = (
                NoTradeReason.COST_EXCEEDS_EDGE
                if order_decision.net_expected <= 0
                else NoTradeReason.HARD_BLOCKER
            )
            return self._refuse(
                gate_name=ExecutionGateName.ORDER_TYPE,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=reason,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=order_decision.reason,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_order_type_context(order_decision),
                trace=trace,
            )
        self._append_trace(
            trace,
            gate_name=ExecutionGateName.ORDER_TYPE,
            verdict=ExecutionGateTraceVerdict.PASSED,
            reason_code=order_decision.order_type.value,
            detail=order_decision.reason,
        )

        edge_gate_decision = self._resolve_fee_aware_edge(opportunity)
        if edge_gate_decision is not None and not edge_gate_decision.allowed:
            return self._refuse(
                gate_name=ExecutionGateName.FEE_AWARE_EDGE,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.COST_EXCEEDS_EDGE,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=edge_gate_decision.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_fee_aware_edge_context(edge_gate_decision),
                reason_codes=(edge_gate_decision.reason_code,),
                trace=trace,
            )
        if edge_gate_decision is not None:
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.FEE_AWARE_EDGE,
                verdict=ExecutionGateTraceVerdict.PASSED,
                reason_code=edge_gate_decision.reason_code,
                detail=edge_gate_decision.detail,
            )

        sharia_decision = self._authorize_sharia(opportunity)
        if sharia_decision is not None and not sharia_decision.allowed:
            detail = sharia_decision.detail.strip() or sharia_decision.reason_code
            return self._refuse(
                gate_name=ExecutionGateName.SHARIA,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.SHARIA_BLOCKED,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_sharia_context(sharia_decision),
                reason_codes=(sharia_decision.reason_code,),
                trace=trace,
            )
        if sharia_decision is not None:
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.SHARIA,
                verdict=ExecutionGateTraceVerdict.PASSED,
                detail="sharia authorization accepted",
            )

        rate_limit_decision = self._resolve_rate_limit(opportunity)
        if rate_limit_decision is not None and rate_limit_decision.blocked:
            return self._refuse(
                gate_name=ExecutionGateName.RATE_LIMITER,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.HARD_BLOCKER,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=rate_limit_decision.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_rate_limit_context(rate_limit_decision),
                reason_codes=(rate_limit_decision.reason_code,),
                trace=trace,
            )
        if rate_limit_decision is not None:
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.RATE_LIMITER,
                verdict=ExecutionGateTraceVerdict.PASSED,
                reason_code=rate_limit_decision.reason_code,
                detail=rate_limit_decision.detail,
            )

        guard = check_execution_guards(
            pair_suspended=opportunity.pair_suspended,
            pair_health_score=opportunity.pair_health_score,
            pair_health_min=opportunity.pair_health_min,
            risk_budget_available=opportunity.risk_budget_available,
            infrastructure_ok=opportunity.infrastructure_ok,
            data_stale=opportunity.data_stale,
            expected_cost=opportunity.expected_cost,
            max_acceptable_cost=opportunity.max_acceptable_cost,
        )
        if guard.verdict == GuardVerdict.BLOCK:
            return self._refuse(
                gate_name=ExecutionGateName.EXECUTION_GUARD,
                disposition=ExecutionGateRefusalDisposition.BLOCKED,
                reason=_map_guard_reason(guard),
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=guard.detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                guard=guard,
                trace=trace,
            )
        self._append_trace(
            trace,
            gate_name=ExecutionGateName.EXECUTION_GUARD,
            verdict=ExecutionGateTraceVerdict.PASSED,
            detail="execution guards accepted",
        )

        price_limit = opportunity.price_limit
        if order_decision.order_type == OrderType.LIMIT and price_limit is None:
            price_limit = opportunity.reference_price
        if order_decision.order_type == OrderType.LIMIT and price_limit is None:
            return self._refuse(
                gate_name=ExecutionGateName.PRICE_LIMIT,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.HARD_BLOCKER,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail="limit order selected without a usable price limit",
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context={"gate": ExecutionGateName.PRICE_LIMIT.value, "order_type": "limit"},
                trace=trace,
            )
        self._append_trace(
            trace,
            gate_name=ExecutionGateName.PRICE_LIMIT,
            verdict=ExecutionGateTraceVerdict.PASSED,
            detail="price limit resolved",
        )

        resolved_constraints = self._resolve_venue_constraints(opportunity)
        quantity = opportunity.quantity
        quantity_exact = ""
        price_limit_exact: str | None = None
        if resolved_constraints is not None:
            normalization = self._normalize_venue_order_fields(
                quantity=opportunity.quantity,
                side=opportunity.side,
                order_type=order_decision.order_type,
                price_limit=price_limit,
                reference_price=opportunity.reference_price,
                constraints=resolved_constraints,
            )
            if normalization.error_detail is not None:
                return self._refuse(
                    gate_name=ExecutionGateName.VENUE_CONSTRAINTS,
                    disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                    reason=NoTradeReason.VENUE_CONSTRAINTS,
                    pair=opportunity.pair,
                    engine_id=opportunity.engine_id,
                    detail=normalization.error_detail,
                    expected_cost=opportunity.expected_cost,
                    expected_gain=opportunity.expected_gain,
                    score=opportunity.score,
                    context={"gate": ExecutionGateName.VENUE_CONSTRAINTS.value},
                    trace=trace,
                )
            quantity = normalization.quantity
            quantity_exact = normalization.quantity_exact
            price_limit = normalization.price_limit
            price_limit_exact = normalization.price_limit_exact
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.VENUE_CONSTRAINTS,
                verdict=ExecutionGateTraceVerdict.PASSED,
                detail="venue constraints normalized",
            )

        timeout_policy = select_timeout_policy(order_decision.order_type)
        intent = build_intent(
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            side=opportunity.side,
            order_type=order_decision.order_type,
            quantity=quantity,
            quantity_exact=quantity_exact,
            expected_cost=opportunity.expected_cost,
            expected_gain=opportunity.expected_gain,
            score=opportunity.score,
            justification=opportunity.justification or order_decision.reason,
            price_limit=price_limit,
            price_limit_exact=price_limit_exact,
            timeout_s=timeout_policy.timeout_s,
            profile=opportunity.profile,
            venue_constraints=resolved_constraints,
        )
        if opportunity.metadata:
            intent = intent.model_copy(update={"metadata": dict(opportunity.metadata)})

        hook_outcome = self._evaluate_execution_no_trade_filter(opportunity)
        if hook_outcome is not None and hook_outcome.blocked:
            detail = hook_outcome.detail.strip()
            if not detail:
                detail = (
                    f"execution no-trade filter blocked {opportunity.pair} / "
                    f"{opportunity.engine_id}"
                )
            return self._refuse(
                gate_name=ExecutionGateName.EXECUTION_NO_TRADE_FILTER,
                disposition=ExecutionGateRefusalDisposition.NO_TRADE,
                reason=NoTradeReason.HARD_BLOCKER,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                detail=detail,
                expected_cost=opportunity.expected_cost,
                expected_gain=opportunity.expected_gain,
                score=opportunity.score,
                context=_build_execution_no_trade_filter_context(hook_outcome),
                reason_codes=hook_outcome.block_reason_codes,
                trace=trace,
            )
        if hook_outcome is not None:
            self._append_trace(
                trace,
                gate_name=ExecutionGateName.EXECUTION_NO_TRADE_FILTER,
                verdict=ExecutionGateTraceVerdict.PASSED,
                detail="execution no-trade filter accepted",
            )

        return ExecutionPermit(
            intent=intent,
            detail=order_decision.reason,
            order_decision=order_decision,
            trace=tuple(trace),
        )

    @staticmethod
    def _append_trace(
        trace: list[ExecutionGateTrace],
        *,
        gate_name: ExecutionGateName,
        verdict: ExecutionGateTraceVerdict,
        reason_code: str = "",
        detail: str = "",
    ) -> None:
        trace.append(
            ExecutionGateTrace(
                gate_name=gate_name,
                verdict=verdict,
                reason_code=reason_code,
                detail=detail,
            )
        )

    def _refuse(
        self,
        *,
        gate_name: ExecutionGateName,
        disposition: ExecutionGateRefusalDisposition,
        reason: NoTradeReason,
        pair: str,
        engine_id: str,
        detail: str,
        expected_cost: float,
        expected_gain: float,
        score: float,
        trace: list[ExecutionGateTrace],
        context: dict[str, str | float | int | bool] | None = None,
        reason_codes: tuple[str, ...] = (),
        guard: GuardResult | None = None,
    ) -> ExecutionRefusal:
        self._append_trace(
            trace,
            gate_name=gate_name,
            verdict=ExecutionGateTraceVerdict.REFUSED,
            reason_code=reason_codes[0] if reason_codes else "",
            detail=detail,
        )
        return ExecutionRefusal(
            disposition=disposition,
            gate_name=gate_name,
            no_trade=NoTradeDecision(
                pair=pair,
                engine_id=engine_id,
                reason=reason,
                detail=detail,
                expected_cost=expected_cost,
                expected_gain=expected_gain,
                score=score,
                context={} if context is None else context,
            ),
            detail=detail,
            reason_codes=reason_codes,
            guard=guard,
            trace=tuple(trace),
        )


def _build_fee_aware_edge_context(
    decision: FeeAwareEdgeDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.FEE_AWARE_EDGE.value,
        "reason_code": decision.reason_code,
        "expected_edge_bps": decision.expected_edge_bps,
        "expected_cost_bps": decision.expected_cost_bps,
        "threshold_bps": decision.threshold_bps,
        "edge_multiplier": decision.edge_multiplier,
        "min_absolute_edge_bps": decision.min_absolute_edge_bps,
    }


def _build_rate_limit_context(
    decision: ExecutionRateLimitDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.RATE_LIMITER.value,
        "reason_code": decision.reason_code,
        "current_quota_ratio": (
            0.0 if decision.current_quota_ratio is None else decision.current_quota_ratio
        ),
        "quota_ratio_ceiling": (
            0.0 if decision.quota_ratio_ceiling is None else decision.quota_ratio_ceiling
        ),
    }


def _build_spread_guard_context(
    decision: ExecutionSpreadGuardDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.SPREAD_GUARD.value,
        "reason_code": decision.reason_code,
        "current_spread_bps": (
            0.0 if decision.current_spread_bps is None else decision.current_spread_bps
        ),
        "max_spread_bps": (
            0.0 if decision.max_spread_bps is None else decision.max_spread_bps
        ),
    }


def _build_order_type_context(
    decision: OrderTypeDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.ORDER_TYPE.value,
        "order_type": decision.order_type.value,
        "net_expected": decision.net_expected,
    }


def _build_sharia_context(
    decision: ShariaRejection,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.SHARIA.value,
        "reason_code": decision.reason_code,
    }


def _build_execution_no_trade_filter_context(
    outcome: ExecutionNoTradeFilterOutcomeLike,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": ExecutionGateName.EXECUTION_NO_TRADE_FILTER.value,
        "block_reason_codes": "|".join(outcome.block_reason_codes),
    }


def _map_guard_reason(guard: GuardResult) -> NoTradeReason:
    from execution_backbone.order_decider.execution_guard import BlockReason

    if not guard.blocks:
        return NoTradeReason.HARD_BLOCKER
    mapping = {
        BlockReason.PAIR_SUSPENDED: NoTradeReason.PAIR_SUSPENDED,
        BlockReason.RISK_BUDGET_EXHAUSTED: NoTradeReason.RISK_BUDGET_EXHAUSTED,
        BlockReason.INFRASTRUCTURE_DOWN: NoTradeReason.INFRASTRUCTURE_DOWN,
        BlockReason.COST_TOO_HIGH: NoTradeReason.COST_EXCEEDS_EDGE,
        BlockReason.PAIR_HEALTH_LOW: NoTradeReason.HARD_BLOCKER,
        BlockReason.STALE_DATA: NoTradeReason.HARD_BLOCKER,
    }
    return mapping.get(guard.blocks[0], NoTradeReason.HARD_BLOCKER)


__all__ = [
    "ExecutionGateName",
    "ExecutionGateRefusalDisposition",
    "ExecutionGateTrace",
    "ExecutionGateTraceVerdict",
    "ExecutionGatekeeper",
    "ExecutionPermit",
    "ExecutionRefusal",
    "ExecutionVenueNormalizationResult",
]
