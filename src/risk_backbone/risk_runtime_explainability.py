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
    action: RiskRuntimeAction,
    reason_details: tuple[RiskReasonDetail, ...],
    drawdown_result: DrawdownGuardResult,
    physics_scores: RiskPhysicsScores,
) -> RiskExplainability:
    blocked_guard_codes = tuple(detail.code for detail in reason_details)
    blocked_guard_categories = tuple(dict.fromkeys(detail.category for detail in reason_details))
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


__all__ = [
    "_build_reason_details",
    "_build_risk_explainability",
    "_evaluate_candidate_physics",
    "_normalize_runtime_equity_state",
    "_require_runtime_timestamp",
]
