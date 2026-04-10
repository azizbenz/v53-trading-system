"""Bounded runtime facade for halal trade authorization."""

from __future__ import annotations

from .contracts import ShariaPermit, ShariaPolicy, ShariaRejection, ShariaTradeRequest
from .policy_audit_logger import PolicyAuditLogger
from .trade_type_guard import authorize_trade_type


class ShariaRuntime:
    """Versioned halal policy gate used before execution submit."""

    def __init__(
        self,
        policy: ShariaPolicy,
        *,
        audit_logger: PolicyAuditLogger | None = None,
    ) -> None:
        self._policy = policy
        self._audit_logger = audit_logger

    @property
    def policy_version(self) -> str:
        return self._policy.policy_version

    def authorize_trade(self, request: ShariaTradeRequest) -> ShariaPermit | ShariaRejection:
        decision = authorize_trade_type(request, self._policy)
        if self._audit_logger is not None:
            self._audit_logger.record(request, decision)
        return decision


__all__ = ["ShariaRuntime"]
