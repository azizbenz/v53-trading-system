"""Pure helper functions for the canonical Build-3 execution gatekeeper."""

from __future__ import annotations

from typing import Protocol

from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeDecision
from execution_backbone.order_decider.execution_guard import GuardResult
from execution_backbone.order_decider.intent_builder import NoTradeReason
from execution_backbone.order_decider.order_type_selector import OrderTypeDecision
from execution_backbone.rate_limiter import ExecutionRateLimitDecision
from execution_backbone.spread_guard import ExecutionSpreadGuardDecision
from sharia_compliance.contracts import ShariaRejection


class ExecutionNoTradeFilterOutcomeLike(Protocol):
    block_reason_codes: tuple[str, ...]


def build_fee_aware_edge_context(
    decision: FeeAwareEdgeDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "fee_aware_edge",
        "reason_code": decision.reason_code,
        "expected_edge_bps": decision.expected_edge_bps,
        "expected_cost_bps": decision.expected_cost_bps,
        "threshold_bps": decision.threshold_bps,
        "edge_multiplier": decision.edge_multiplier,
        "min_absolute_edge_bps": decision.min_absolute_edge_bps,
    }


def build_rate_limit_context(
    decision: ExecutionRateLimitDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "rate_limiter",
        "reason_code": decision.reason_code,
        "current_quota_ratio": 0.0 if decision.current_quota_ratio is None else decision.current_quota_ratio,
        "quota_ratio_ceiling": 0.0 if decision.quota_ratio_ceiling is None else decision.quota_ratio_ceiling,
    }


def build_spread_guard_context(
    decision: ExecutionSpreadGuardDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "spread_guard",
        "reason_code": decision.reason_code,
        "current_spread_bps": 0.0 if decision.current_spread_bps is None else decision.current_spread_bps,
        "max_spread_bps": 0.0 if decision.max_spread_bps is None else decision.max_spread_bps,
    }


def build_order_type_context(
    decision: OrderTypeDecision,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "order_type",
        "order_type": decision.order_type.value,
        "net_expected": decision.net_expected,
    }


def build_sharia_context(
    decision: ShariaRejection,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "sharia",
        "reason_code": decision.reason_code,
    }


def build_execution_no_trade_filter_context(
    outcome: ExecutionNoTradeFilterOutcomeLike,
) -> dict[str, str | float | int | bool]:
    return {
        "gate": "execution_no_trade_filter",
        "block_reason_codes": "|".join(outcome.block_reason_codes),
    }


def map_guard_reason(guard: GuardResult) -> NoTradeReason:
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
