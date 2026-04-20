"""
Build-6 / engine_a / signal_reporter_A
Produce complete, audit-able signal output and track statistics.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from engines.engine_a.conviction_builder_a import ConvictionLevel, TierSuggestion

ENGINE_A_SIGNAL_REPORTER_STATUS = "secondary_helper_non_canonical_flow"
ENGINE_A_SIGNAL_REPORTER_STATUS_DETAIL = (
    "NoTradeReason is canonical and imported by engine_a_runner; "
    "SignalCandidateA/SignalStats/SignalReporterA remain secondary audit helpers "
    "outside the canonical runner/runtime path."
)


class SignalDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReason(StrEnum):
    NON_LONG_DIRECTION = "non_long_direction"
    INVALID_CANDIDATE_SIZE = "invalid_candidate_size"
    INVALID_HOLDING_PERIOD = "invalid_holding_period"
    INVALID_ENTRY_PRICE = "invalid_entry_price"
    INVALID_ATR = "invalid_atr"
    INVALID_INVALIDATION = "invalid_invalidation"
    STRUCTURE_UNFAVORABLE = "structure_unfavorable"
    CONTEXT_FATAL = "context_fatal"
    COST_INFEASIBLE = "cost_infeasible"
    COST_MARGINAL = "cost_marginal"
    LOW_CONVICTION = "low_conviction"
    CONVICTION_NONE = "conviction_none"


class SignalCandidateA(BaseModel, frozen=True):
    """Complete Engine A signal output — typed for downstream consumption."""

    pair: str
    engine_id: str = "engine_a"
    decision: SignalDecision
    raw_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevel = ConvictionLevel.NONE
    tier_suggestion: TierSuggestion = TierSuggestion.NO_TRADE
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    invalidation: str = ""
    holding_hours: float = 0.0
    scoring_version: str = ""
    no_trade_reasons: tuple[NoTradeReason, ...] = ()


class SignalStats(BaseModel, frozen=True):
    total_evaluated: int = 0
    total_emitted: int = 0
    total_no_trade: int = 0
    emission_rate: float = 0.0
    no_trade_by_reason: dict[str, int] = Field(default_factory=dict)
    mean_raw_score: float = 0.0


class SignalReporterA:
    """Track and report Engine A signal events."""

    def __init__(self) -> None:
        self._total: int = 0
        self._emitted: int = 0
        self._scores: list[float] = []
        self._no_trade_reasons: dict[str, int] = {}

    def record_emit(self, raw_score: float) -> None:
        self._total += 1
        self._emitted += 1
        self._scores.append(raw_score)

    def record_no_trade(self, reasons: tuple[str, ...]) -> None:
        self._total += 1
        for r in reasons:
            self._no_trade_reasons[r] = self._no_trade_reasons.get(r, 0) + 1

    def get_stats(self) -> SignalStats:
        n = self._total
        rate = self._emitted / n if n > 0 else 0.0
        mean = sum(self._scores) / len(self._scores) if self._scores else 0.0

        return SignalStats(
            total_evaluated=n,
            total_emitted=self._emitted,
            total_no_trade=n - self._emitted,
            emission_rate=rate,
            no_trade_by_reason=dict(self._no_trade_reasons),
            mean_raw_score=mean,
        )


__all__ = [
    "ENGINE_A_SIGNAL_REPORTER_STATUS",
    "ENGINE_A_SIGNAL_REPORTER_STATUS_DETAIL",
    "NoTradeReason",
    "SignalCandidateA",
    "SignalDecision",
    "SignalReporterA",
    "SignalStats",
]
