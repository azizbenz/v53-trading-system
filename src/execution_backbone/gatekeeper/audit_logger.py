"""Append-only audit logger for canonical gatekeeper decisions."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .gatekeeper import (
    ExecutionGateRefusalDisposition,
    ExecutionGateTrace,
    ExecutionPermit,
    ExecutionRefusal,
)

if TYPE_CHECKING:
    from .gatekeeper import ExecutionOpportunityLike


class ExecutionGatekeeperAuditDecision(StrEnum):
    SUBMITTED = "submitted"
    NO_TRADE = "no_trade"
    BLOCKED = "blocked"


class ExecutionGatekeeperAuditEvent(BaseModel, frozen=True):
    timestamp_s: float = Field(..., ge=0.0)
    intent_id: str
    pair: str
    engine_id: str
    side: str
    quantity: float
    expected_gain: float
    expected_cost: float
    score: float
    decision: str
    gate_name: str = ""
    no_trade_reason: str = ""
    order_id: str = ""
    order_type: str = ""
    detail: str = ""
    reason_codes: tuple[str, ...] = ()
    guard_blocks: tuple[str, ...] = ()
    gate_trace: tuple[ExecutionGateTrace, ...] = ()


class GatekeeperAuditLogger:
    """Bounded append-only JSONL audit logger for gatekeeper outcomes."""

    def __init__(self, output_path: Path | str) -> None:
        self._output_path = Path(output_path)

    def record_refusal(
        self,
        *,
        opportunity: ExecutionOpportunityLike,
        refusal: ExecutionRefusal,
        timestamp_s: float,
    ) -> ExecutionGatekeeperAuditEvent:
        decision = (
            ExecutionGatekeeperAuditDecision.BLOCKED
            if refusal.disposition == ExecutionGateRefusalDisposition.BLOCKED
            else ExecutionGatekeeperAuditDecision.NO_TRADE
        )
        event = ExecutionGatekeeperAuditEvent(
            timestamp_s=timestamp_s,
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            side=opportunity.side,
            quantity=opportunity.quantity,
            expected_gain=opportunity.expected_gain,
            expected_cost=opportunity.expected_cost,
            score=opportunity.score,
            decision=decision,
            gate_name=refusal.gate_name.value,
            no_trade_reason=refusal.no_trade.reason.value,
            detail=refusal.detail,
            reason_codes=refusal.reason_codes,
            guard_blocks=(
                tuple(block.value for block in refusal.guard.blocks)
                if refusal.guard is not None
                else ()
            ),
            gate_trace=refusal.trace,
        )
        self._append(event)
        return event

    def record_submission(
        self,
        *,
        opportunity: ExecutionOpportunityLike,
        permit: ExecutionPermit,
        order_id: str,
        timestamp_s: float,
    ) -> ExecutionGatekeeperAuditEvent:
        event = ExecutionGatekeeperAuditEvent(
            timestamp_s=timestamp_s,
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            side=opportunity.side,
            quantity=opportunity.quantity,
            expected_gain=opportunity.expected_gain,
            expected_cost=opportunity.expected_cost,
            score=opportunity.score,
            decision=ExecutionGatekeeperAuditDecision.SUBMITTED,
            order_id=order_id,
            order_type=permit.intent.order_type.value,
            detail=permit.detail,
            gate_trace=permit.trace,
        )
        self._append(event)
        return event

    def _append(self, event: ExecutionGatekeeperAuditEvent) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=True))
            handle.write("\n")


__all__ = [
    "ExecutionGatekeeperAuditDecision",
    "ExecutionGatekeeperAuditEvent",
    "GatekeeperAuditLogger",
]
