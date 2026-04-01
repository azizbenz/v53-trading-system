"""
Build-4 / loss_budgeter / drawdown_guard
Minimal Light trajectory drawdown protection.

Guardrail: if intraday drawdown exceeds a configurable threshold,
the system reduces exposure or switches to observation mode.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class DrawdownVerdict(StrEnum):
    ACCEPTED = "accepted"
    REDUCE_EXPOSURE = "reduce_exposure"
    OBSERVE_ONLY = "observe_only"


class DrawdownGuardResult(BaseModel, frozen=True):
    current_equity: float
    session_peak_equity: float
    drawdown_pct: float
    warning_threshold_pct: float
    observe_threshold_pct: float
    verdict: DrawdownVerdict
    reason: str = ""


def evaluate_drawdown_guard(
    current_equity: float,
    session_peak_equity: float,
    warning_threshold_pct: float = 0.02,
    observe_threshold_pct: float = 0.04,
) -> DrawdownGuardResult:
    """Evaluate minimal intraday drawdown protection.

    - warning threshold -> reduce exposure
    - observe threshold -> switch to observation mode
    """
    if session_peak_equity <= 0:
        raise ValueError("session_peak_equity must be positive")
    if warning_threshold_pct < 0 or observe_threshold_pct < 0:
        raise ValueError("drawdown thresholds must be non-negative")
    if observe_threshold_pct < warning_threshold_pct:
        raise ValueError("observe_threshold_pct must be >= warning_threshold_pct")

    drawdown_pct = max(0.0, (session_peak_equity - current_equity) / session_peak_equity)

    if drawdown_pct >= observe_threshold_pct:
        return DrawdownGuardResult(
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
            drawdown_pct=drawdown_pct,
            warning_threshold_pct=warning_threshold_pct,
            observe_threshold_pct=observe_threshold_pct,
            verdict=DrawdownVerdict.OBSERVE_ONLY,
            reason=f"intraday drawdown {drawdown_pct:.4f} >= observe threshold {observe_threshold_pct:.4f}",
        )

    if drawdown_pct >= warning_threshold_pct:
        return DrawdownGuardResult(
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
            drawdown_pct=drawdown_pct,
            warning_threshold_pct=warning_threshold_pct,
            observe_threshold_pct=observe_threshold_pct,
            verdict=DrawdownVerdict.REDUCE_EXPOSURE,
            reason=f"intraday drawdown {drawdown_pct:.4f} >= warning threshold {warning_threshold_pct:.4f}",
        )

    return DrawdownGuardResult(
        current_equity=current_equity,
        session_peak_equity=session_peak_equity,
        drawdown_pct=drawdown_pct,
        warning_threshold_pct=warning_threshold_pct,
        observe_threshold_pct=observe_threshold_pct,
        verdict=DrawdownVerdict.ACCEPTED,
    )
