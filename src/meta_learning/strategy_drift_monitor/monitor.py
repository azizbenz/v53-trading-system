"""Minimal typed strategy drift monitor."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class StrategyDriftState(StrEnum):
    GREEN = "green"
    PAUSE = "pause"
    BLOCK = "block"
    INSUFFICIENT_DATA = "insufficient_data"


class StrategyDriftThresholds(BaseModel, frozen=True):
    min_samples: int = Field(default=30, ge=1)
    forecast_ks_floor: float = Field(default=0.05, ge=0.0, le=1.0)
    win_rate_delta_floor: float = -0.10
    ce_delta_floor: float = -0.05


class StrategyDriftSnapshot(BaseModel, frozen=True):
    sample_count: int = Field(default=0, ge=0)
    forecast_distribution_ks_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    win_rate_delta: float | None = None
    ce_delta: float | None = None


class StrategyDriftSignal(BaseModel, frozen=True):
    state: StrategyDriftState
    pause_signal: bool = False
    promotion_block: bool = False
    reasons: tuple[str, ...] = ()


def evaluate_strategy_drift(
    snapshot: StrategyDriftSnapshot,
    *,
    thresholds: StrategyDriftThresholds | None = None,
) -> StrategyDriftSignal:
    """Evaluate drift with explicit pause/block semantics."""

    resolved_thresholds = thresholds or StrategyDriftThresholds()
    if snapshot.sample_count < resolved_thresholds.min_samples:
        return StrategyDriftSignal(
            state=StrategyDriftState.INSUFFICIENT_DATA,
            promotion_block=True,
            reasons=("STRATEGY_DRIFT_INSUFFICIENT_DATA",),
        )
    if snapshot.forecast_distribution_ks_pvalue is not None and (
        snapshot.forecast_distribution_ks_pvalue <= resolved_thresholds.forecast_ks_floor
    ):
        return StrategyDriftSignal(
            state=StrategyDriftState.BLOCK,
            pause_signal=True,
            promotion_block=True,
            reasons=("FORECAST_DISTRIBUTION_DRIFT_BLOCK",),
        )
    pause_reasons: list[str] = []
    if snapshot.win_rate_delta is not None and (
        snapshot.win_rate_delta <= resolved_thresholds.win_rate_delta_floor
    ):
        pause_reasons.append("WIN_RATE_DRIFT_PAUSE")
    if snapshot.ce_delta is not None and snapshot.ce_delta <= resolved_thresholds.ce_delta_floor:
        pause_reasons.append("CE_DRIFT_PAUSE")
    if pause_reasons:
        return StrategyDriftSignal(
            state=StrategyDriftState.PAUSE,
            pause_signal=True,
            reasons=tuple(pause_reasons),
        )
    return StrategyDriftSignal(state=StrategyDriftState.GREEN)


__all__ = [
    "StrategyDriftState",
    "StrategyDriftThresholds",
    "StrategyDriftSnapshot",
    "StrategyDriftSignal",
    "evaluate_strategy_drift",
]
