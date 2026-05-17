"""Explainability and validation helpers for the Build-4 risk runtime."""

from __future__ import annotations

import math

from data_backbone.market_physics_math import (
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    toxicity_score_v1,
)

from .btc_factor_guard.beta_cap_guard import BetaCapResult, BetaCapVerdict
from .correlation_cluster_guard.cluster_cap_guard import (
    ClusterCapResult,
    ClusterCapVerdict,
)
from .loss_budgeter.drawdown_guard import DrawdownGuardResult, DrawdownVerdict
from .loss_budgeter.loss_cap_guard import LossCapResult, LossCapVerdict
from .exposure_budgeter.gross_cap_guard import GrossCapResult, GrossCapVerdict
from .risk_runtime_models import (
    RiskCandidate,
    RiskExplainability,
    RiskPhysicsScores,
    RiskReasonDetail,
    RiskRuntimeAction,
)


def _build_reason_details(
    *,
    gross_result: GrossCapResult,
    loss_result: LossCapResult,
    beta_result: BetaCapResult,
    cluster_results: tuple[ClusterCapResult, ...],
    drawdown_result: DrawdownGuardResult,
    beta_mapping_missing_pairs: tuple[str, ...] = (),
    beta_mapping_stale_pairs: tuple[str, ...] = (),
) -> tuple[RiskReasonDetail, ...]:
    details: list[RiskReasonDetail] = []

    if gross_result.verdict == GrossCapVerdict.REJECTED_POSITION_CAP:
        details.append(
            RiskReasonDetail(
                code="RISK_POSITION_CAP",
                category="gross_cap",
                verdict=gross_result.verdict.value,
                message=gross_result.reason,
            )
        )
    elif gross_result.verdict == GrossCapVerdict.REJECTED_GROSS_CAP:
        details.append(
            RiskReasonDetail(
                code="RISK_GROSS_CAP",
                category="gross_cap",
                verdict=gross_result.verdict.value,
                message=gross_result.reason,
            )
        )

    if loss_result.verdict == LossCapVerdict.REJECTED_NO_LOSS_ESTIMATE:
        details.append(
            RiskReasonDetail(
                code="RISK_NO_LOSS_ESTIMATE",
                category="loss_cap",
                verdict=loss_result.verdict.value,
                message=loss_result.reason,
            )
        )
    elif loss_result.verdict == LossCapVerdict.REJECTED_BUDGET_EXCEEDED:
        details.append(
            RiskReasonDetail(
                code="RISK_LOSS_CAP",
                category="loss_cap",
                verdict=loss_result.verdict.value,
                message=loss_result.reason,
            )
        )

    for pair in beta_mapping_missing_pairs:
        details.append(
            RiskReasonDetail(
                code="RISK_BETA_MAPPING_MISSING",
                category="beta_cap",
                verdict="rejected_missing_beta_mapping",
                message=f"missing explicit beta mapping for pair {pair}",
            )
        )

    for pair in beta_mapping_stale_pairs:
        details.append(
            RiskReasonDetail(
                code="RISK_BETA_MAPPING_STALE",
                category="beta_cap",
                verdict="rejected_stale_beta_mapping",
                message=f"stale beta mapping for pair {pair}",
            )
        )

    if beta_result.verdict == BetaCapVerdict.REJECTED:
        details.append(
            RiskReasonDetail(
                code="RISK_BETA_CAP",
                category="beta_cap",
                verdict=beta_result.verdict.value,
                message=beta_result.reason,
            )
        )

    for cluster_result in cluster_results:
        if cluster_result.verdict == ClusterCapVerdict.REJECTED:
            details.append(
                RiskReasonDetail(
                    code="RISK_CLUSTER_CAP",
                    category="cluster_cap",
                    verdict=cluster_result.verdict.value,
                    message=cluster_result.reason,
                )
            )
        elif cluster_result.verdict == ClusterCapVerdict.REJECTED_NO_CLUSTER:
            details.append(
                RiskReasonDetail(
                    code="RISK_CLUSTER_MAPPING_MISSING",
                    category="cluster_cap",
                    verdict=cluster_result.verdict.value,
                    message=cluster_result.reason,
                )
            )

    if drawdown_result.verdict == DrawdownVerdict.REDUCE_EXPOSURE:
        details.append(
            RiskReasonDetail(
                code="RISK_DRAWDOWN_REDUCE",
                category="drawdown_state",
                verdict=drawdown_result.verdict.value,
                message=drawdown_result.reason,
            )
        )
    elif drawdown_result.verdict == DrawdownVerdict.OBSERVE_ONLY:
        details.append(
            RiskReasonDetail(
                code="RISK_DRAWDOWN_OBSERVE",
                category="drawdown_state",
                verdict=drawdown_result.verdict.value,
                message=drawdown_result.reason,
            )
        )

    return tuple(details)


def _evaluate_candidate_physics(candidate: RiskCandidate) -> RiskPhysicsScores:
    fragility = fragility_score_v1(
        candidate.execution_fragility,
        spread_regime_penalty=candidate.spread_regime_penalty,
    )
    toxicity = toxicity_score_v1(
        candidate.market_toxicity,
        fragility_score=fragility,
        spread_regime_penalty=candidate.spread_regime_penalty,
    )
    execution_survivability = execution_survivability_score_v1(
        fragility_score=fragility,
        toxicity_score=toxicity,
        spread_regime_penalty=candidate.spread_regime_penalty,
        participation_penalty=candidate.participation_penalty,
    )
    micro_friction = micro_friction_score_v1(
        spread_regime_penalty=candidate.spread_regime_penalty,
        fragility_score=fragility,
        toxicity_score=toxicity,
        participation_penalty=candidate.participation_penalty,
    )
    pressure_state = "nominal"
    if execution_survivability <= 0.20 or micro_friction >= 0.80:
        pressure_state = "severe"
    elif (
        execution_survivability <= 0.40
        or micro_friction >= 0.60
        or toxicity >= 0.70
    ):
        pressure_state = "elevated"
    return RiskPhysicsScores(
        fragility_score=fragility,
        toxicity_score=toxicity,
        execution_survivability_score=execution_survivability,
        micro_friction_score=micro_friction,
        pressure_state=pressure_state,
    )


def _build_explain_summary(
    action: RiskRuntimeAction,
    reason_details: tuple[RiskReasonDetail, ...],
    physics_scores: RiskPhysicsScores,
) -> str:
    if not reason_details:
        if action == RiskRuntimeAction.ACCEPT and physics_scores.pressure_state != "nominal":
            return (
                f"risk={action.value} / physics={physics_scores.pressure_state} / "
                "no blocker triggered"
            )
        return f"risk={action.value} / no blocker triggered"
    dominant = reason_details[0]
    return (
        f"risk={action.value} / dominant={dominant.code} / "
        f"category={dominant.category} / total={len(reason_details)}"
    )


def _build_risk_explainability(
    *,
    candidate: RiskCandidate,
    action: RiskRuntimeAction,
    reason_details: tuple[RiskReasonDetail, ...],
    drawdown_result: DrawdownGuardResult,
    physics_scores: RiskPhysicsScores,
) -> RiskExplainability:
    blocked_guard_codes = tuple(detail.code for detail in reason_details)
    blocked_guard_categories = tuple(dict.fromkeys(detail.category for detail in reason_details))
    input_audit = _resolve_input_audit_surface(candidate)
    decision_severity = {
        RiskRuntimeAction.ACCEPT: "nominal",
        RiskRuntimeAction.REDUCE_EXPOSURE: "warning",
        RiskRuntimeAction.OBSERVE_ONLY: "critical",
        RiskRuntimeAction.REJECT: "critical",
    }[action]
    if action == RiskRuntimeAction.ACCEPT and physics_scores.pressure_state == "elevated":
        decision_severity = "warning"
    summary = _build_explain_summary(action, reason_details, physics_scores)
    return RiskExplainability(
        blocked_guard_codes=blocked_guard_codes,
        blocked_guard_categories=blocked_guard_categories,
        blocked_guard_count=len(blocked_guard_codes),
        carriage_statuses=candidate.carriage_statuses,
        carriage_reason_codes=candidate.carriage_reason_codes,
        shared_physics_mapping_status=candidate.shared_physics_mapping_status,
        engine_role=candidate.engine_role,
        execution_fragility_status=input_audit["execution_fragility_status"],
        market_toxicity_status=input_audit["market_toxicity_status"],
        spread_regime_penalty_status=input_audit["spread_regime_penalty_status"],
        participation_penalty_status=input_audit["participation_penalty_status"],
        micro_friction_source_status=input_audit["micro_friction_source_status"],
        risk_input_completeness_status=input_audit["risk_input_completeness_status"],
        cost_model_completeness_status=input_audit["cost_model_completeness_status"],
        fee_source_status=input_audit["fee_source_status"],
        impact_source_status=input_audit["impact_source_status"],
        fill_realism_status=input_audit["fill_realism_status"],
        realized_slippage_status=input_audit["realized_slippage_status"],
        risk_readiness_status=input_audit["risk_readiness_status"],
        input_reason_codes=input_audit["reason_codes"],
        execution_ready=input_audit["execution_ready"],
        promotion_ready=input_audit["promotion_ready"],
        drawdown_state_code=drawdown_result.verdict.value,
        decision_severity=decision_severity,
        physics_pressure_state=physics_scores.pressure_state,
        fragility_score=physics_scores.fragility_score,
        toxicity_score=physics_scores.toxicity_score,
        execution_survivability_score=physics_scores.execution_survivability_score,
        micro_friction_score=physics_scores.micro_friction_score,
        summary=summary,
    )


def _require_runtime_timestamp(now: float | None, *, context: str) -> float:
    """Reject implicit epoch timestamps on the open runtime rail."""

    if now is None:
        raise ValueError(f"{context} requires explicit now")
    if not math.isfinite(now):
        raise ValueError(f"{context} requires finite now")
    if now <= 0.0:
        raise ValueError(f"{context} requires now > 0")
    return now


def _resolve_input_audit_surface(candidate: RiskCandidate) -> dict[str, object]:
    execution_fragility_status = _normalize_status(
        candidate.execution_fragility_status,
        default="UNKNOWN",
    )
    market_toxicity_status = _normalize_status(
        candidate.market_toxicity_status,
        default="UNKNOWN",
    )
    spread_regime_penalty_status = _normalize_status(
        candidate.spread_regime_penalty_status,
        default="UNKNOWN",
    )
    participation_penalty_status = _normalize_status(
        candidate.participation_penalty_status,
        default="NOT_PROVEN",
    )
    micro_friction_source_status = _normalize_status(
        candidate.micro_friction_source_status,
        default="UNKNOWN",
    )
    cost_model_completeness_status = _normalize_status(
        candidate.cost_model_completeness_status,
        default="UNKNOWN",
    )
    fee_source_status = _normalize_status(candidate.fee_source_status, default="UNKNOWN")
    impact_source_status = _normalize_status(candidate.impact_source_status, default="UNKNOWN")
    fill_realism_status = _normalize_status(candidate.fill_realism_status, default="UNKNOWN")
    realized_slippage_status = _normalize_status(
        candidate.realized_slippage_status,
        default="UNKNOWN",
    )

    explicit_risk_input_status = _normalize_status(
        candidate.risk_input_completeness_status,
        default="UNKNOWN",
    )
    reason_codes: list[str] = []
    if execution_fragility_status == "UNKNOWN":
        reason_codes.append("RISK_EXECUTION_FRAGILITY_UNKNOWN")
    if market_toxicity_status == "UNKNOWN":
        reason_codes.append("RISK_MARKET_TOXICITY_UNKNOWN")
    if spread_regime_penalty_status == "UNKNOWN":
        reason_codes.append("RISK_SPREAD_REGIME_PENALTY_UNKNOWN")
    if participation_penalty_status in {"UNKNOWN", "NOT_PROVEN", "MISSING", "PARTIAL"}:
        reason_codes.append("RISK_PARTICIPATION_PENALTY_NOT_PROVEN")
    if micro_friction_source_status in {"UNKNOWN", "NOT_PROVEN", "MISSING", "PARTIAL"}:
        reason_codes.append("RISK_MICRO_FRICTION_SOURCE_UNKNOWN")
    if cost_model_completeness_status != "COMPLETE":
        reason_codes.append("COST_MODEL_INCOMPLETE")

    inferred_risk_input_status = explicit_risk_input_status
    if candidate.risk_input_completeness_status == "UNKNOWN":
        component_statuses = (
            execution_fragility_status,
            market_toxicity_status,
            spread_regime_penalty_status,
            participation_penalty_status,
            micro_friction_source_status,
        )
        if any(status in {"MISSING", "NOT_PROVEN", "PARTIAL"} for status in component_statuses):
            inferred_risk_input_status = "PARTIAL"
        elif any(status == "UNKNOWN" for status in component_statuses):
            inferred_risk_input_status = "UNKNOWN"
        else:
            inferred_risk_input_status = "GOVERNED_SOURCE"

    risk_ready = inferred_risk_input_status in {
        "MEASURED",
        "GOVERNED_SOURCE",
        "NEUTRAL_BY_DESIGN",
    }
    cost_ready = cost_model_completeness_status == "COMPLETE"
    execution_ready = risk_ready and cost_ready
    promotion_ready = execution_ready
    if execution_ready:
        risk_readiness_status = "READY"
    elif inferred_risk_input_status == "UNKNOWN":
        risk_readiness_status = "RISK_INPUTS_UNKNOWN"
    elif inferred_risk_input_status in {"PARTIAL", "MISSING", "NOT_PROVEN"}:
        risk_readiness_status = "RISK_INPUTS_PARTIAL"
    elif not cost_ready:
        risk_readiness_status = "SCORING_RISK_COST_COMPLETENESS_PARTIAL"
    else:
        risk_readiness_status = "UNKNOWN"

    return {
        "execution_fragility_status": execution_fragility_status,
        "market_toxicity_status": market_toxicity_status,
        "spread_regime_penalty_status": spread_regime_penalty_status,
        "participation_penalty_status": participation_penalty_status,
        "micro_friction_source_status": micro_friction_source_status,
        "risk_input_completeness_status": inferred_risk_input_status,
        "cost_model_completeness_status": cost_model_completeness_status,
        "fee_source_status": fee_source_status,
        "impact_source_status": impact_source_status,
        "fill_realism_status": fill_realism_status,
        "realized_slippage_status": realized_slippage_status,
        "risk_readiness_status": risk_readiness_status,
        "reason_codes": tuple(dict.fromkeys(reason_codes)),
        "execution_ready": execution_ready,
        "promotion_ready": promotion_ready,
    }


def _normalize_runtime_equity_state(
    current_equity: float,
    session_peak_equity: float,
    *,
    context: str,
    allow_uninitialized: bool = False,
) -> tuple[float, float]:
    """Normalize and validate governed equity state on the open risk rail."""

    if not math.isfinite(current_equity):
        raise ValueError(f"{context} requires finite current_equity")
    if not math.isfinite(session_peak_equity):
        raise ValueError(f"{context} requires finite session_peak_equity")
    if current_equity < 0.0:
        raise ValueError(f"{context} requires current_equity >= 0")
    if session_peak_equity < 0.0:
        raise ValueError(f"{context} requires session_peak_equity >= 0")

    if allow_uninitialized and current_equity == 0.0 and session_peak_equity == 0.0:
        return current_equity, session_peak_equity

    if current_equity <= 0.0:
        raise ValueError(f"{context} requires current_equity > 0")

    normalized_peak = session_peak_equity
    if normalized_peak <= 0.0:
        normalized_peak = current_equity
    elif normalized_peak < current_equity:
        normalized_peak = current_equity
    return current_equity, normalized_peak


def _normalize_status(value: str | None, *, default: str) -> str:
    normalized = "" if value is None else str(value).strip()
    return normalized or default


__all__ = [
    "_build_reason_details",
    "_build_risk_explainability",
    "_evaluate_candidate_physics",
    "_normalize_runtime_equity_state",
    "_require_runtime_timestamp",
]
