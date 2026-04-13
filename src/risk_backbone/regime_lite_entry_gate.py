"""Opt-in risk precheck built from a typed regime_lite assessment."""

from __future__ import annotations

from regime_classifier import RegimeLiteAssessment, RegimeLiteState

from .risk_runtime import (
    RiskRegimePrecheckHook,
    RiskRegimePrecheckInput,
    RiskRegimePrecheckOutcome,
)


def build_regime_lite_entry_gate(
    assessment: RegimeLiteAssessment,
) -> RiskRegimePrecheckHook:
    """Build a bounded risk precheck from the current regime_lite assessment."""

    def _hook(_hook_input: RiskRegimePrecheckInput) -> RiskRegimePrecheckOutcome:
        if assessment.entries_blocked:
            return RiskRegimePrecheckOutcome(
                accepted=False,
                reason_codes=("RISK_REGIME_EXTREME_COOLDOWN",),
                detail=(
                    "regime_lite blocked new entries during EXTREME cooldown "
                    f"until {assessment.entries_blocked_until_ts}"
                ),
            )
        if assessment.state == RegimeLiteState.EXTREME:
            return RiskRegimePrecheckOutcome(
                accepted=False,
                reason_codes=("RISK_REGIME_EXTREME",),
                detail="regime_lite blocked new entries while state=extreme",
            )
        return RiskRegimePrecheckOutcome()

    return _hook


__all__ = ["build_regime_lite_entry_gate"]
