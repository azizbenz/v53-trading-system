"""
Build-3 / fill_tracker / fill_reporter
Order tracking and fill reporting.

Metrics: PFR = N_partial/N_orders, RejectRate = N_reject/N_orders, FullFillRate = N_full/N_orders
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from .order_state_tracker import OrderState, TERMINAL_STATES


logger = logging.getLogger(__name__)


class FillStats(BaseModel, frozen=True):
    """Aggregate fill statistics."""

    total_orders: int = 0
    full_fills: int = 0
    partial_fills: int = 0
    cancellations: int = 0
    rejections: int = 0
    expirations: int = 0
    open_orders: int = 0
    full_fill_rate: float = 0.0
    partial_fill_rate: float = 0.0
    reject_rate: float = 0.0


class FillReporter:
    """Track and report fill statistics."""

    def __init__(self) -> None:
        self._full: int = 0
        self._partial: int = 0
        self._cancelled: int = 0
        self._rejected: int = 0
        self._expired: int = 0
        self._open: int = 0
        self._total: int = 0

    def record_order_created(self) -> None:
        self._total += 1
        self._open += 1
        logger.info(
            "execution_order_created",
            extra={"total_orders": self._total, "open_orders": self._open},
        )

    def record_terminal(self, state: OrderState, had_partial_fills: bool = False) -> None:
        if self._open > 0:
            self._open -= 1

        if state == OrderState.FILLED:
            self._full += 1
        elif state == OrderState.CANCELLED:
            if had_partial_fills:
                self._partial += 1
            else:
                self._cancelled += 1
        elif state == OrderState.EXPIRED:
            if had_partial_fills:
                self._partial += 1
            else:
                self._expired += 1
        elif state == OrderState.REJECTED:
            self._rejected += 1

        level = logging.WARNING if state in {OrderState.CANCELLED, OrderState.EXPIRED, OrderState.REJECTED} else logging.INFO
        logger.log(
            level,
            "execution_order_terminal",
            extra={
                "state": state.value,
                "had_partial_fills": had_partial_fills,
                "open_orders": self._open,
                "full_fills": self._full,
                "partial_fills": self._partial,
                "cancellations": self._cancelled,
                "rejections": self._rejected,
                "expirations": self._expired,
            },
        )

    def get_stats(self) -> FillStats:
        total = self._total if self._total > 0 else 1  # avoid div/0

        return FillStats(
            total_orders=self._total,
            full_fills=self._full,
            partial_fills=self._partial,
            cancellations=self._cancelled,
            rejections=self._rejected,
            expirations=self._expired,
            open_orders=self._open,
            full_fill_rate=self._full / total,
            partial_fill_rate=self._partial / total,
            reject_rate=self._rejected / total,
        )
