"""
Build-7 / engine_b / signal_reporter_B
Track and report Engine B signal events and statistics.

Status:
- `NoTradeReasonB` is canonical and consumed by `engine_b_runner`.
- `SignalCandidateB`, `SignalStatsB`, and `SignalReporterB` remain
  secondary audit helpers outside the canonical runner/runtime flow.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from engines.engine_b.conviction_builder_b import ConvictionLevelB, TierSuggestionB

ENGINE_B_SIGNAL_REPORTER_STATUS = "secondary_helper_non_canonical_flow"
ENGINE_B_SIGNAL_REPORTER_STATUS_DETAIL = (
    "NoTradeReasonB is canonical and imported by engine_b_runner; "
    "SignalCandidateB/SignalStatsB/SignalReporterB remain secondary audit helpers "
    "outside the canonical runner/runtime path."
)


class SignalDecisionB(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonB(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_INVALIDATION = "invalid_invalidation"
    NON_LONG_DIRECTION = "non_long_direction"
    NO_EXCESS = "no_excess"
    BREAKOUT_BLOCKED = "breakout_blocked"
    COST_INFEASIBLE = "cost_infeasible"
    COST_MARGINAL = "cost_marginal"
    CONVICTION_LOW = "conviction_low"
    CONVICTION_NONE = "conviction_none"
    INVALID_DISPERSION = "invalid_dispersion"


class SignalCandidateB(BaseModel, frozen=True):
    """Complete Engine B signal output — typed for downstream consumption."""

    pair: str
    engine_id: str = "engine_b"
    decision: SignalDecisionB
    raw_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelB = ConvictionLevelB.NONE
    tier_suggestion: TierSuggestionB = TierSuggestionB.NO_TRADE
    z_score: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    expected_holding_hours: float = 0.0
    invalidation: str = ""
    scoring_version: str = ""
    no_trade_reasons: tuple[NoTradeReasonB, ...] = ()


class SignalStatsB(BaseModel, frozen=True):
    total_evaluated: int = 0
    total_emitted: int = 0
    total_no_trade: int = 0
    emission_rate: float = 0.0
    no_trade_by_reason: dict[str, int] = Field(default_factory=dict)
    mean_raw_score: float = 0.0
    mean_z_score: float = 0.0


class SignalReporterB:
    """Track Engine B audit stats outside the canonical runner/runtime path."""

    def __init__(self) -> None:
        self._total: int = 0
        self._emitted: int = 0
        self._scores: list[float] = []
        self._z_scores: list[float] = []
        self._no_trade_reasons: dict[str, int] = {}

    def record_emit(self, raw_score: float, z_score: float = 0.0) -> None:
        self._total += 1
        self._emitted += 1
        self._scores.append(raw_score)
        self._z_scores.append(z_score)

    def record_no_trade(self, reasons: tuple[str, ...]) -> None:
        self._total += 1
        for r in reasons:
            self._no_trade_reasons[r] = self._no_trade_reasons.get(r, 0) + 1

    def get_stats(self) -> SignalStatsB:
        n = self._total
        rate = self._emitted / n if n > 0 else 0.0
        mean_score = sum(self._scores) / len(self._scores) if self._scores else 0.0
        mean_z = sum(self._z_scores) / len(self._z_scores) if self._z_scores else 0.0

        return SignalStatsB(
            total_evaluated=n,
            total_emitted=self._emitted,
            total_no_trade=n - self._emitted,
            emission_rate=rate,
            no_trade_by_reason=dict(self._no_trade_reasons),
            mean_raw_score=mean_score,
            mean_z_score=mean_z,
        )


__all__ = [
    "ENGINE_B_SIGNAL_REPORTER_STATUS",
    "ENGINE_B_SIGNAL_REPORTER_STATUS_DETAIL",
    "NoTradeReasonB",
    "SignalCandidateB",
    "SignalDecisionB",
    "SignalReporterB",
    "SignalStatsB",
]
