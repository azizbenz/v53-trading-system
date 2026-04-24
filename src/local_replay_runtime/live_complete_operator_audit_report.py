"""Operator-facing final Build-17 audit report for governed Complete supervision."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import DashboardCommandQueueStatus, VpsWarmupState
from local_replay_runtime.regime_detector_final_audit_report import (
    LocalLabRegimeDetectorFinalAuditReport,
)


LIVE_COMPLETE_VERDICT_BLOCKED = "blocked"
LIVE_COMPLETE_VERDICT_ALLOWED = "allowed_complete_supervision"


def _enum_value(value: object) -> str:
    """Return a stable string value without importing upstream protocol enums."""

    candidate = getattr(value, "value", value)
    return str(candidate)


class LiveCompleteOperatorAuditReport(BaseModel, frozen=True):
    """Persistent operator-facing proof surface for Build-17 Complete supervision."""

    correlation_id: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    operator_ready: bool = False
    live_complete_run_id: str = Field(..., min_length=1)
    live_complete_verdict: str = Field(..., min_length=1)
    live_complete_run_state: str = Field(..., min_length=1)
    deployment_state: str = Field(..., min_length=1)
    command_queue_status: str = "not_configured"
    recovery_eligible_to_trade: bool = False
    warmup_final_state: str = "cold_start"
    active_ml_artifact_hash: str = ""
    active_regime_detector_artifact_hash: str = ""
    regime_detector_audit_present: bool = False
    regime_detector_audit_status: str = "not_evaluated"
    final_recommendation: str = Field(default="not_evaluated", min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    live_complete_summary: BaseModel
    regime_detector_final_audit_report: LocalLabRegimeDetectorFinalAuditReport | None = None


def build_live_complete_operator_audit_report(
    *,
    live_complete_summary: BaseModel,
    regime_detector_final_audit_report: LocalLabRegimeDetectorFinalAuditReport | None = None,
) -> LiveCompleteOperatorAuditReport:
    """Join Build-17 readiness with the current RegimeDetector IA-Lab audit state."""

    queue_status = (
        "not_configured"
        if live_complete_summary.command_queue_snapshot is None
        else live_complete_summary.command_queue_snapshot.queue_status.value
    )
    recovery_eligible = (
        False
        if live_complete_summary.recovery_readiness_report is None
        else live_complete_summary.recovery_readiness_report.eligible_to_trade
    )
    warmup_state = (
        VpsWarmupState.COLD_START.value
        if live_complete_summary.warmup_run_summary is None
        else live_complete_summary.warmup_run_summary.final_state.value
    )
    blocking_reasons = list(live_complete_summary.decision.blocking_reasons)
    caution_flags: list[str] = []
    if live_complete_summary.command_queue_snapshot is None:
        caution_flags.append("LIVE_COMPLETE_COMMAND_QUEUE_NOT_ATTACHED")
    elif (
        live_complete_summary.command_queue_snapshot.queue_status
        != DashboardCommandQueueStatus.HEALTHY
    ):
        caution_flags.append("LIVE_COMPLETE_COMMAND_QUEUE_NOT_HEALTHY")
    if live_complete_summary.recovery_readiness_report is None:
        caution_flags.append("LIVE_COMPLETE_RECOVERY_REPORT_MISSING")
    if live_complete_summary.warmup_run_summary is None:
        caution_flags.append("LIVE_COMPLETE_WARMUP_SUMMARY_MISSING")
    if regime_detector_final_audit_report is None:
        caution_flags.append("REGIME_DETECTOR_FINAL_AUDIT_REPORT_MISSING")
    else:
        blocking_reasons.extend(regime_detector_final_audit_report.blocking_reasons)
        caution_flags.extend(regime_detector_final_audit_report.caution_flags)

    decision_verdict = _enum_value(live_complete_summary.decision.verdict)
    run_state = _enum_value(live_complete_summary.run_state)
    deployment_state = _enum_value(live_complete_summary.deployment_state)
    if decision_verdict == LIVE_COMPLETE_VERDICT_BLOCKED:
        status = "blocked"
        operator_ready = False
        final_recommendation = "investigate_live_complete_blockers"
    elif regime_detector_final_audit_report is None:
        status = "partial"
        operator_ready = False
        final_recommendation = "collect_regime_detector_final_audit_report"
    elif not regime_detector_final_audit_report.audit_ready:
        status = "partial" if regime_detector_final_audit_report.status != "blocked" else "blocked"
        operator_ready = False
        final_recommendation = regime_detector_final_audit_report.final_recommendation
    elif warmup_state != VpsWarmupState.ELIGIBLE_TO_TRADE.value:
        status = "partial"
        operator_ready = False
        final_recommendation = "complete_warmup_before_trading"
    elif queue_status != DashboardCommandQueueStatus.HEALTHY.value:
        status = "partial"
        operator_ready = False
        final_recommendation = "stabilize_dashboard_command_queue"
    elif decision_verdict != LIVE_COMPLETE_VERDICT_ALLOWED:
        status = "partial"
        operator_ready = False
        final_recommendation = "continue_complete_supervision_review"
    else:
        status = "ready"
        operator_ready = True
        final_recommendation = "operator_surface_ready_for_complete_supervision"

    return LiveCompleteOperatorAuditReport(
        correlation_id=live_complete_summary.correlation_id,
        status=status,
        operator_ready=operator_ready,
        live_complete_run_id=live_complete_summary.run_id,
        live_complete_verdict=decision_verdict,
        live_complete_run_state=run_state,
        deployment_state=deployment_state,
        command_queue_status=queue_status,
        recovery_eligible_to_trade=recovery_eligible,
        warmup_final_state=warmup_state,
        active_ml_artifact_hash=live_complete_summary.execution_envelope.active_ml_artifact_hash,
        active_regime_detector_artifact_hash=(
            live_complete_summary.execution_envelope.active_regime_detector_artifact_hash
        ),
        regime_detector_audit_present=regime_detector_final_audit_report is not None,
        regime_detector_audit_status=(
            "not_evaluated"
            if regime_detector_final_audit_report is None
            else regime_detector_final_audit_report.status
        ),
        final_recommendation=final_recommendation,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        live_complete_summary=live_complete_summary,
        regime_detector_final_audit_report=regime_detector_final_audit_report,
    )


def write_live_complete_operator_audit_report(
    report: LiveCompleteOperatorAuditReport,
    report_ref: str | Path,
) -> Path:
    """Persist the operator-facing Build-17 audit report as stable JSON."""

    path = Path(report_ref).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


__all__ = [
    "LiveCompleteOperatorAuditReport",
    "build_live_complete_operator_audit_report",
    "write_live_complete_operator_audit_report",
]
