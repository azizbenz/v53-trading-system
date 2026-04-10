"""Append-only audit log for halal policy decisions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .contracts import ShariaAuditEvent, ShariaPermit, ShariaRejection, ShariaTradeRequest


class PolicyAuditLogger:
    """Bounded append-only JSONL logger for sharia decisions."""

    def __init__(
        self,
        output_path: Path | str,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._output_path = Path(output_path)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def record(
        self,
        request: ShariaTradeRequest,
        decision: ShariaPermit | ShariaRejection,
    ) -> ShariaAuditEvent:
        event = ShariaAuditEvent(
            timestamp=self._now(),
            intent_id=request.intent_id,
            pair=request.pair,
            engine_id=request.engine_id,
            decision="permit" if decision.allowed else "reject",
            reason_code="" if decision.allowed else decision.reason_code,
            policy_version=decision.policy_version,
            detail=decision.detail,
        )
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=True))
            handle.write("\n")
        return event


__all__ = ["PolicyAuditLogger"]
