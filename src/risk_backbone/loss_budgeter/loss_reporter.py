"""
Build-4 / loss_budgeter / loss_reporter
Report loss budget consumption, refusals, remaining capacity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LossEvent(BaseModel, frozen=True):
    pair: str
    loss_amount: float
    accepted: bool
    reason: str = ""
    budget_after: float = 0.0
    timestamp: float = 0.0


class LossStats(BaseModel, frozen=True):
    current_budget: float = 0.0
    loss_cap: float = 0.0
    utilization: float = 0.0
    remaining_capacity: float = 0.0
    total_accepted: int = 0
    total_refused: int = 0


class LossReporter:
    """Track and report loss budget events."""

    def __init__(self, loss_cap: float) -> None:
        self._loss_cap = loss_cap
        self._events: list[LossEvent] = []
        self._current_budget: float = 0.0
        self._accepted: int = 0
        self._refused: int = 0

    def record_accepted(self, pair: str, loss_amount: float, timestamp: float = 0.0) -> None:
        self._current_budget += loss_amount
        self._accepted += 1
        self._events.append(LossEvent(
            pair=pair, loss_amount=loss_amount, accepted=True,
            budget_after=self._current_budget, timestamp=timestamp,
        ))

    def record_refused(self, pair: str, loss_amount: float, reason: str, timestamp: float = 0.0) -> None:
        self._refused += 1
        self._events.append(LossEvent(
            pair=pair, loss_amount=loss_amount, accepted=False,
            reason=reason, budget_after=self._current_budget, timestamp=timestamp,
        ))

    def record_position_closed(self, loss_amount: float) -> None:
        self._current_budget = max(0.0, self._current_budget - loss_amount)

    def sync_current_budget(self, budget: float) -> None:
        """Synchronize current budget from a governed portfolio snapshot."""

        self._current_budget = max(0.0, budget)

    def get_stats(self) -> LossStats:
        return LossStats(
            current_budget=self._current_budget,
            loss_cap=self._loss_cap,
            utilization=self._current_budget / self._loss_cap if self._loss_cap > 0 else 0.0,
            remaining_capacity=max(0.0, self._loss_cap - self._current_budget),
            total_accepted=self._accepted,
            total_refused=self._refused,
        )
