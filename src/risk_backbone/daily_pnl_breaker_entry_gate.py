"""Opt-in risk precheck built from the typed daily PnL breaker seam."""

from __future__ import annotations

from risk_backbone.loss_budgeter import DailyPnlBreaker, DailyPnlBreakerThresholds

from .risk_runtime import (
    RiskDailyPnlPrecheckHook,
    RiskDailyPnlPrecheckInput,
    RiskDailyPnlPrecheckOutcome,
)


def build_daily_pnl_breaker_entry_gate(
    breaker: DailyPnlBreaker,
    *,
    thresholds: DailyPnlBreakerThresholds | None = None,
) -> RiskDailyPnlPrecheckHook:
    """Build a bounded risk precheck from the persistent daily breaker state."""

    def _hook(hook_input: RiskDailyPnlPrecheckInput) -> RiskDailyPnlPrecheckOutcome:
        assessment = breaker.evaluate(
            session_date=hook_input.session_date,
            current_equity=hook_input.current_equity,
            session_peak_equity=hook_input.session_peak_equity,
            thresholds=thresholds,
        )
        if assessment.should_force_shadow:
            return RiskDailyPnlPrecheckOutcome(
                accepted=False,
                verdict=assessment.verdict.value,
                should_force_shadow=True,
                reason_codes=assessment.reason_codes or ("RISK_DAILY_PNL_BREAKER",),
                detail=assessment.detail,
            )
        return RiskDailyPnlPrecheckOutcome(
            accepted=True,
            verdict=assessment.verdict.value,
            should_force_shadow=False,
            reason_codes=assessment.reason_codes,
            detail=assessment.detail,
        )

    return _hook


__all__ = ["build_daily_pnl_breaker_entry_gate"]
