"""
Build-3 / reconciliation_layer / recovery_trigger
Trigger controlled re-sync procedure when divergences require it.

Invariant: absence of recent reconciliation must be visible.
Δ_recon = t_now - t_last_recon
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .divergence_classifier import DivergenceSeverity


class RecoveryAction(StrEnum):
    NONE = "none"
    SOFT_RESYNC = "soft_resync"  # re-fetch state, compare again
    HARD_RESYNC = "hard_resync"  # cancel all local, re-bootstrap from exchange
    HALT_TRADING = "halt_trading"  # stop all new orders until resolved


class RecoveryDecision(BaseModel, frozen=True):
    """Decision about recovery action to take."""

    action: RecoveryAction
    reason: str
    severity: DivergenceSeverity
    stale_reconciliation: bool = False  # true if too long since last recon
    recon_age_s: float = 0.0


class RecoveryTrigger:
    """Decide and track recovery actions."""

    def __init__(self, max_recon_age_s: float = 60.0) -> None:
        self._max_recon_age = max_recon_age_s
        self._last_recon_time: float | None = None
        self._history: list[RecoveryDecision] = []

    def record_reconciliation(self, timestamp: float) -> None:
        self._last_recon_time = timestamp

    def evaluate(
        self,
        severity: DivergenceSeverity,
        now: float,
        divergence_count: int = 0,
    ) -> RecoveryDecision:
        """Evaluate whether recovery is needed based on divergence severity and recon age."""
        # Check reconciliation staleness
        stale = False
        recon_age = 0.0
        if self._last_recon_time is not None:
            recon_age = now - self._last_recon_time
            stale = recon_age > self._max_recon_age
        else:
            stale = True  # never reconciled

        if severity == DivergenceSeverity.CRITICAL:
            decision = RecoveryDecision(
                action=RecoveryAction.HALT_TRADING,
                reason=f"Critical divergence detected ({divergence_count} divergences)",
                severity=severity,
                stale_reconciliation=stale,
                recon_age_s=recon_age,
            )
        elif severity == DivergenceSeverity.BLOCKING:
            decision = RecoveryDecision(
                action=RecoveryAction.HARD_RESYNC,
                reason=f"Blocking divergence ({divergence_count} divergences) — hard resync required",
                severity=severity,
                stale_reconciliation=stale,
                recon_age_s=recon_age,
            )
        elif severity == DivergenceSeverity.WARNING or stale:
            decision = RecoveryDecision(
                action=RecoveryAction.SOFT_RESYNC,
                reason="Warning divergence or stale reconciliation — soft resync",
                severity=severity,
                stale_reconciliation=stale,
                recon_age_s=recon_age,
            )
        else:
            decision = RecoveryDecision(
                action=RecoveryAction.NONE,
                reason="No recovery needed",
                severity=severity,
                stale_reconciliation=stale,
                recon_age_s=recon_age,
            )

        self._history.append(decision)
        return decision

    def get_history(self) -> tuple[RecoveryDecision, ...]:
        return tuple(self._history)

    @property
    def last_recon_time(self) -> float | None:
        return self._last_recon_time
