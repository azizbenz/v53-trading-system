"""Typed governed safing recommendation derived from a regime_lite assessment."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts import OperatorSafingAction, OperatorSafingRequest, RuntimeMode
from regime_classifier import RegimeLiteAssessment, RegimeLiteState


class RegimeLiteSafingSeverity(StrEnum):
    NONE = "none"
    ENTRY_BLOCK_ONLY = "entry_block_only"
    HALT_RECOMMENDED = "halt_recommended"


class RegimeLiteSafingRecommendation(BaseModel, frozen=True):
    """Explicit risk-rail recommendation; never auto-applied by this helper."""

    severity: RegimeLiteSafingSeverity = RegimeLiteSafingSeverity.NONE
    should_block_new_entries: bool = False
    should_exit_all: bool = False
    recommended_operator_action: OperatorSafingAction | None = None
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    operator_safing_request: OperatorSafingRequest | None = None


def build_regime_lite_safing_recommendation(
    assessment: RegimeLiteAssessment,
    *,
    source_runtime_mode: RuntimeMode,
    timestamp_ms: int,
    requested_by: str = "system_regime_guard",
    ui_channel: str = "regime_lite_guard",
) -> RegimeLiteSafingRecommendation:
    """Translate regime_lite state into a governed, opt-in safing recommendation."""

    if assessment.state == RegimeLiteState.EXTREME:
        reason_codes = tuple(
            dict.fromkeys(("RISK_REGIME_EXTREME_EXIT_ALL",) + assessment.reason_codes)
        )
        detail = (
            f"regime_lite reached EXTREME in {source_runtime_mode.value}; "
            "recommend set_halted and explicit position unwind"
        )
        operator_request = OperatorSafingRequest(
            timestamp_ms=timestamp_ms,
            request_id=f"regime-lite:{source_runtime_mode.value}:{timestamp_ms}",
            action=OperatorSafingAction.SET_HALTED,
            source_runtime_mode=source_runtime_mode,
            requested_by=requested_by,
            ui_channel=ui_channel,
            reason=detail,
        )
        return RegimeLiteSafingRecommendation(
            severity=RegimeLiteSafingSeverity.HALT_RECOMMENDED,
            should_block_new_entries=True,
            should_exit_all=True,
            recommended_operator_action=OperatorSafingAction.SET_HALTED,
            reason_codes=reason_codes,
            detail=detail,
            operator_safing_request=operator_request,
        )

    if assessment.entries_blocked:
        return RegimeLiteSafingRecommendation(
            severity=RegimeLiteSafingSeverity.ENTRY_BLOCK_ONLY,
            should_block_new_entries=True,
            should_exit_all=False,
            reason_codes=tuple(
                dict.fromkeys(
                    ("RISK_REGIME_EXTREME_COOLDOWN",) + assessment.reason_codes
                )
            ),
            detail=(
                "regime_lite cooldown remains active after EXTREME; "
                "keep new-entry block without forced exit-all"
            ),
        )

    return RegimeLiteSafingRecommendation(
        severity=RegimeLiteSafingSeverity.NONE,
        should_block_new_entries=False,
        should_exit_all=False,
        reason_codes=assessment.reason_codes,
        detail="regime_lite does not require additional safing",
    )


__all__ = [
    "RegimeLiteSafingRecommendation",
    "RegimeLiteSafingSeverity",
    "build_regime_lite_safing_recommendation",
]
