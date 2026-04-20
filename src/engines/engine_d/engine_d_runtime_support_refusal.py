"""Runtime refusal / downstream annotation helpers extracted from `engine_d_runtime_support.py` on 2026-04-18."""

from __future__ import annotations

from interface_contracts import (
    ConditioningFamily,
    ConditioningRecord,
    ForecastSignalCandidate,
    RefusalCategory,
)
from interface_contracts.forecast_contracts import merge_reason_codes
from risk_backbone.risk_runtime import RiskEvaluation
from scoring_backbone.scoring_runtime import ScoringCandidateAudit

from .engine_d_runner import EngineDLogEntry, EngineDOutput


def _resolve_runtime_refusal_category(status: str) -> RefusalCategory | None:
    if status == "no_trade":
        return RefusalCategory.NO_TRADE
    if status in {
        "circuit_breaker_blocked",
        "hook_blocked",
        "hard_blocked",
        "risk_rejected",
    }:
        return RefusalCategory.HARD_BLOCK
    if status == "rejected_ranking":
        return RefusalCategory.NO_TRADE
    if status == "rejected_portfolio":
        return RefusalCategory.PORTFOLIO_REJECTED
    return None


def _resolve_runtime_refusal_reason_codes(
    *,
    status: str,
    engine_output: EngineDOutput,
    log_entries: tuple[EngineDLogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if status == "no_trade":
        if engine_output.reason_codes:
            return engine_output.reason_codes
        if engine_output.no_trade_reasons:
            return tuple(f"engine_d.no_trade.{reason.value}" for reason in engine_output.no_trade_reasons)
        return ("engine_d.runtime.no_trade",)
    if status == "hook_blocked":
        hook_reason_codes = _extract_log_reason_codes(log_entries, "engine_d_hook_blocked")
        if hook_reason_codes:
            return hook_reason_codes
        return ("engine_d.runtime.hook_blocked",)
    if status == "circuit_breaker_blocked":
        breaker_reason_codes = _extract_log_reason_codes(log_entries, "engine_d_circuit_breaker_blocked")
        if breaker_reason_codes:
            return breaker_reason_codes
        return ("engine_d.runtime.circuit_breaker_blocked",)
    if status == "hard_blocked":
        if scoring_audit is not None and scoring_audit.hard_block_decision.reasons:
            return merge_reason_codes(
                engine_output.reason_codes,
                (reason.code for reason in scoring_audit.hard_block_decision.reasons),
            )
        return merge_reason_codes(
            engine_output.reason_codes,
            ("hard_block.engine_d.runtime.hard_blocked", "engine_d.runtime.hard_blocked"),
        )
    if status == "rejected_ranking":
        return merge_reason_codes(
            engine_output.reason_codes,
            ("scoring.engine_d.runtime.rejected_ranking", "engine_d.runtime.rejected_ranking"),
        )
    if status == "rejected_portfolio":
        return merge_reason_codes(
            engine_output.reason_codes,
            ("portfolio.engine_d.runtime.rejected_portfolio", "engine_d.runtime.rejected_portfolio"),
        )
    if status == "risk_rejected":
        if risk_evaluation is not None:
            if risk_evaluation.reason_details:
                return merge_reason_codes(
                    engine_output.reason_codes,
                    (detail.code for detail in risk_evaluation.reason_details),
                )
            dominant_reason_code = (risk_evaluation.dominant_reason_code or "").strip()
            if dominant_reason_code:
                return merge_reason_codes(engine_output.reason_codes, (dominant_reason_code,))
        return merge_reason_codes(
            engine_output.reason_codes,
            ("hard_block.engine_d.runtime.risk_rejected", "engine_d.runtime.risk_rejected"),
        )
    return ("engine_d.runtime.unknown_refusal",)


def resolve_hook_blocked_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(code.strip() for code in reason_codes if code.strip())
    if normalized:
        return normalized
    return ("engine_d.runtime.hook_blocked",)


def annotate_forecast_signal_candidate_for_runtime_status(
    forecast_signal_candidate: ForecastSignalCandidate | None,
    *,
    timestamp_ms: int,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> ForecastSignalCandidate | None:
    if forecast_signal_candidate is None:
        return None
    downstream_reason_codes = _resolve_runtime_forecast_reason_codes(
        status=status,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
    )
    downstream_conditioning_state = _build_runtime_downstream_conditioning_records(
        timestamp_ms=timestamp_ms,
        status=status,
        scoring_audit=scoring_audit,
    )
    if not downstream_reason_codes and not downstream_conditioning_state:
        return forecast_signal_candidate
    return forecast_signal_candidate.model_copy(
        update={
            "reason_codes": merge_reason_codes(
                forecast_signal_candidate.reason_codes,
                downstream_reason_codes,
            ),
            "conditioning_state": (
                forecast_signal_candidate.conditioning_state + downstream_conditioning_state
            ),
        }
    )


def _resolve_runtime_forecast_reason_codes(
    *,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if status == "hard_blocked":
        return merge_reason_codes(
            ("hard_block.engine_d.runtime.hard_blocked", "engine_d.runtime.hard_blocked"),
            (
                reason.code
                for reason in (() if scoring_audit is None else scoring_audit.hard_block_decision.reasons)
                if reason.code.strip()
            ),
        )
    if status == "rejected_ranking":
        return ("scoring.engine_d.runtime.rejected_ranking", "engine_d.runtime.rejected_ranking")
    if status == "rejected_portfolio":
        if scoring_audit is not None and scoring_audit.portfolio_result is not None:
            return (
                "portfolio.engine_d.runtime.rejected_portfolio",
                "engine_d.runtime.rejected_portfolio",
                f"portfolio.engine_d.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
                f"engine_d.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
            )
        return ("portfolio.engine_d.runtime.rejected_portfolio", "engine_d.runtime.rejected_portfolio")
    if status == "risk_rejected":
        return merge_reason_codes(
            ("hard_block.engine_d.runtime.risk_rejected", "engine_d.runtime.risk_rejected"),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_reduced":
        return merge_reason_codes(
            ("engine_d.runtime.risk_reduced",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_observe_only":
        return merge_reason_codes(
            ("engine_d.runtime.risk_observe_only",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    return ()


def _resolve_runtime_risk_reason_codes(
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if risk_evaluation is None:
        return ()
    if risk_evaluation.reason_details:
        return tuple(detail.code for detail in risk_evaluation.reason_details if detail.code.strip())
    dominant_reason_code = (risk_evaluation.dominant_reason_code or "").strip()
    if dominant_reason_code:
        return (dominant_reason_code,)
    return ()


def _build_runtime_downstream_conditioning_records(
    *,
    timestamp_ms: int,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
) -> tuple[ConditioningRecord, ...]:
    if status == "hard_blocked":
        hard_block_count = 0.0 if scoring_audit is None else float(len(scoring_audit.hard_block_decision.reasons))
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.engine_d.runtime.hard_blocked",
                value=hard_block_count,
                triggered_no_trade=True,
            ),
        )
    if status == "rejected_ranking":
        ranking_score = None
        if scoring_audit is not None and scoring_audit.selection_entry is not None:
            ranking_score = scoring_audit.selection_entry.ranking_score
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.SCORING,
                code="scoring.engine_d.runtime.rejected_ranking",
                value=ranking_score,
                triggered_no_trade=True,
            ),
        )
    if status == "rejected_portfolio":
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.PORTFOLIO,
                code="portfolio.engine_d.runtime.rejected_portfolio",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_rejected":
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.engine_d.runtime.risk_rejected",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_reduced":
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_d.runtime.risk_reduced",
                triggered_no_trade=False,
            ),
        )
    if status == "risk_observe_only":
        return (
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_d.runtime.risk_observe_only",
                triggered_no_trade=False,
            ),
        )
    return ()


def _extract_log_reason_codes(log_entries: tuple[EngineDLogEntry, ...], event: str) -> tuple[str, ...]:
    for entry in reversed(log_entries):
        if entry.event != event:
            continue
        reason_codes = tuple(reason for reason in entry.reasons if reason.strip())
        if reason_codes:
            return reason_codes
    return ()
