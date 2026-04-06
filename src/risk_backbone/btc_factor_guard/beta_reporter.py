"""
Build-4 / btc_factor_guard / beta_reporter
Report BTC systemic exposure, refusals, concentration.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BetaEvent(BaseModel, frozen=True):
    pair: str
    pair_beta: float
    accepted: bool
    portfolio_beta_after: float = 0.0
    reason: str = ""
    timestamp: float = 0.0


class BetaStats(BaseModel, frozen=True):
    current_portfolio_beta: float = 0.0
    beta_cap: float = 0.0
    utilization: float = 0.0  # |β_port| / B_max
    total_accepted: int = 0
    total_refused: int = 0


class BetaReporter:
    """Track and report BTC factor guard events."""

    def __init__(self, beta_cap: float) -> None:
        self._beta_cap = beta_cap
        self._events: list[BetaEvent] = []
        self._current_beta: float = 0.0
        self._accepted: int = 0
        self._refused: int = 0

    def record_accepted(self, pair: str, pair_beta: float, portfolio_beta: float, timestamp: float = 0.0) -> None:
        self._current_beta = portfolio_beta
        self._accepted += 1
        self._events.append(BetaEvent(
            pair=pair, pair_beta=pair_beta, accepted=True,
            portfolio_beta_after=portfolio_beta, timestamp=timestamp,
        ))

    def record_refused(self, pair: str, pair_beta: float, reason: str, timestamp: float = 0.0) -> None:
        self._refused += 1
        self._events.append(BetaEvent(
            pair=pair, pair_beta=pair_beta, accepted=False,
            reason=reason, portfolio_beta_after=self._current_beta, timestamp=timestamp,
        ))

    def sync_current_beta(self, portfolio_beta: float) -> None:
        """Synchronize current beta from a governed portfolio snapshot."""

        self._current_beta = portfolio_beta

    def get_stats(self) -> BetaStats:
        return BetaStats(
            current_portfolio_beta=self._current_beta,
            beta_cap=self._beta_cap,
            utilization=abs(self._current_beta) / self._beta_cap if self._beta_cap > 0 else 0.0,
            total_accepted=self._accepted,
            total_refused=self._refused,
        )
