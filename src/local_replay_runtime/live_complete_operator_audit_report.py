"""Operator-facing final Build-17 audit report for governed Complete supervision."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from interface_contracts import DashboardCommandQueueStatus, VpsWarmupState
from local_replay_runtime.ml_final_audit_report import LocalLabMlFinalAuditReport
from local_replay_runtime.regime_detector_final_audit_report import (
    LocalLabRegimeDetectorFinalAuditReport,
)


LIVE_COMPLETE_VERDICT_BLOCKED = "blocked"
LIVE_COMPLETE_VERDICT_ALLOWED = "allowed_complete_supervision"


class RecentEventsSummaryLike(Protocol):
    """Minimal recent-log surface needed by the operator audit builder."""

    status: str
    parse_error_count: int
    latest_error: str
    latest_event_type: str


def _enum_value(value: object) -> str:
    """Return a stable string value without importing upstream protocol enums."""

    candidate = getattr(value, "value", value)
    return str(candidate)


def _resolve_recent_log_health(
    recent_events_summary: RecentEventsSummaryLike | None,
) -> tuple[str, tuple[str, ...]]:
    if recent_events_summary is None:
        return "not_available", ()
    caution_flags: list[str] = []
    if recent_events_summary.parse_error_count > 0:
        caution_flags.append("LIVE_COMPLETE_RECENT_LOG_PARSE_ERRORS_PRESENT")
    if recent_events_summary.latest_error:
        caution_flags.append("LIVE_COMPLETE_RECENT_LOG_ERROR_PRESENT")
    return recent_events_summary.status, tuple(caution_flags)


def _resolve_operator_outcome(
    *,
    decision_verdict: str,
    ml_final_audit_report: LocalLabMlFinalAuditReport | None,
    regime_detector_final_audit_report: LocalLabRegimeDetectorFinalAuditReport | None,
    warmup_state: str,
    queue_status: str,
) -> tuple[str, bool, str]:
    if decision_verdict == LIVE_COMPLETE_VERDICT_BLOCKED:
        return "blocked", False, "investigate_live_complete_blockers"
    if ml_final_audit_report is None:
        return "partial", False, "collect_ml_final_audit_report"
    if not ml_final_audit_report.audit_ready:
        status = "partial" if ml_final_audit_report.status != "blocked" else "blocked"
        return status, False, ml_final_audit_report.final_recommendation
    if regime_detector_final_audit_report is None:
        return "partial", False, "collect_regime_detector_final_audit_report"
    if not regime_detector_final_audit_report.audit_ready:
        status = (
            "partial"
            if regime_detector_final_audit_report.status != "blocked"
            else "blocked"
        )
        return status, False, regime_detector_final_audit_report.final_recommendation
    if warmup_state != VpsWarmupState.ELIGIBLE_TO_TRADE.value:
        return "partial", False, "complete_warmup_before_trading"
    if queue_status != DashboardCommandQueueStatus.HEALTHY.value:
        return "partial", False, "stabilize_dashboard_command_queue"
    if decision_verdict != LIVE_COMPLETE_VERDICT_ALLOWED:
        return "partial", False, "continue_complete_supervision_review"
    return "ready", True, "operator_surface_ready_for_complete_supervision"


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
    ml_audit_present: bool = False
    ml_audit_status: str = "not_evaluated"
    regime_detector_audit_present: bool = False
    regime_detector_audit_status: str = "not_evaluated"
    recent_log_status: str = "not_available"
    recent_log_summary_ref: str = ""
    recent_log_latest_event_type: str = ""
    recent_log_latest_error: str = ""
    recent_log_parse_error_count: int = 0
    final_recommendation: str = Field(default="not_evaluated", min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    live_complete_summary: BaseModel
    ml_final_audit_report: LocalLabMlFinalAuditReport | None = None
    regime_detector_final_audit_report: LocalLabRegimeDetectorFinalAuditReport | None = None


def build_live_complete_operator_audit_report(
    *,
    live_complete_summary: BaseModel,
    ml_final_audit_report: LocalLabMlFinalAuditReport | None = None,
    regime_detector_final_audit_report: LocalLabRegimeDetectorFinalAuditReport | None = None,
    recent_events_summary: RecentEventsSummaryLike | None = None,
    recent_events_summary_ref: str = "",
) -> LiveCompleteOperatorAuditReport:
    """Join Build-17 readiness with governed artifact audits and recent-log health."""

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
    if ml_final_audit_report is None:
        caution_flags.append("ML_FINAL_AUDIT_REPORT_MISSING")
    else:
        blocking_reasons.extend(ml_final_audit_report.blocking_reasons)
        caution_flags.extend(ml_final_audit_report.caution_flags)
    if regime_detector_final_audit_report is None:
        caution_flags.append("REGIME_DETECTOR_FINAL_AUDIT_REPORT_MISSING")
    else:
        blocking_reasons.extend(regime_detector_final_audit_report.blocking_reasons)
        caution_flags.extend(regime_detector_final_audit_report.caution_flags)
    recent_log_status, recent_log_flags = _resolve_recent_log_health(
        recent_events_summary
    )
    caution_flags.extend(recent_log_flags)

    decision_verdict = _enum_value(live_complete_summary.decision.verdict)
    run_state = _enum_value(live_complete_summary.run_state)
    deployment_state = _enum_value(live_complete_summary.deployment_state)
    status, operator_ready, final_recommendation = _resolve_operator_outcome(
        decision_verdict=decision_verdict,
        ml_final_audit_report=ml_final_audit_report,
        regime_detector_final_audit_report=regime_detector_final_audit_report,
        warmup_state=warmup_state,
        queue_status=queue_status,
    )

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
        ml_audit_present=ml_final_audit_report is not None,
        ml_audit_status=(
            "not_evaluated"
            if ml_final_audit_report is None
            else ml_final_audit_report.status
        ),
        regime_detector_audit_present=regime_detector_final_audit_report is not None,
        regime_detector_audit_status=(
            "not_evaluated"
            if regime_detector_final_audit_report is None
            else regime_detector_final_audit_report.status
        ),
        recent_log_status=recent_log_status,
        recent_log_summary_ref=recent_events_summary_ref,
        recent_log_latest_event_type=(
            ""
            if recent_events_summary is None
            else recent_events_summary.latest_event_type
        ),
        recent_log_latest_error=(
            "" if recent_events_summary is None else recent_events_summary.latest_error
        ),
        recent_log_parse_error_count=(
            0
            if recent_events_summary is None
            else recent_events_summary.parse_error_count
        ),
        final_recommendation=final_recommendation,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        live_complete_summary=live_complete_summary,
        ml_final_audit_report=ml_final_audit_report,
        regime_detector_final_audit_report=regime_detector_final_audit_report,
    )


def write_live_complete_operator_audit_report(
    report: LiveCompleteOperatorAuditReport,
    report_ref: str | Path,
) -> Path:
    """Persist the operator-facing Build-17 audit report as stable JSON."""

    path = Path(report_ref).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, report.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "LiveCompleteOperatorAuditReport",
    "build_live_complete_operator_audit_report",
    "write_live_complete_operator_audit_report",
]
