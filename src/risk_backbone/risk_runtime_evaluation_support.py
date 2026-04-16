"""Evaluation support for the stateful Build-4 risk runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .btc_factor_guard.beta_cap_guard import BetaCapVerdict, evaluate_beta_cap
from .btc_factor_guard.projected_beta_checker import ProjectedBeta, check_projected_beta
from .correlation_cluster_guard.cluster_cap_guard import (
    ClusterCapResult,
    ClusterCapVerdict,
    evaluate_cluster_cap,
)
from .correlation_cluster_guard.cluster_exposure_calculator import calculate_cluster_exposures
from .exposure_budgeter.gross_cap_guard import GrossCapVerdict, evaluate_gross_cap
from .exposure_budgeter.gross_exposure_calculator import Position, calculate_gross_exposure
from .loss_budgeter.drawdown_guard import DrawdownVerdict, evaluate_drawdown_guard
from .loss_budgeter.loss_cap_guard import LossCapVerdict, evaluate_loss_cap
from .risk_runtime_explainability import (
    _build_reason_details,
    _build_risk_explainability,
    _evaluate_candidate_physics,
    _normalize_runtime_equity_state,
    _require_runtime_timestamp,
)
from .risk_runtime_models import (
    RiskCandidate,
    RiskEvaluation,
    RiskPhysicsScores,
    RiskReasonDetail,
    RiskRuntimeAction,
)

if TYPE_CHECKING:
    from .btc_factor_guard.beta_cap_guard import BetaCapResult
    from .correlation_cluster_guard.cluster_registry import ClusterRegistry
    from .exposure_budgeter.gross_cap_guard import GrossCapResult
    from .loss_budgeter.drawdown_guard import DrawdownGuardResult
    from .loss_budgeter.loss_cap_guard import LossCapResult
    from .risk_runtime_runtime import RiskRuntime


@dataclass(frozen=True)
class _RiskGuardSnapshot:
    timestamp: float
    physics_scores: RiskPhysicsScores
    gross_result: GrossCapResult
    loss_result: LossCapResult
    pair_beta: float
    beta_projection: ProjectedBeta
    beta_result: BetaCapResult
    cluster_results: tuple[ClusterCapResult, ...]
    drawdown_result: DrawdownGuardResult
    reason_details: tuple[RiskReasonDetail, ...]
    dominant_reason_code: str
    daily_pnl_reason_details: tuple[RiskReasonDetail, ...]
    beta_mapping_missing_pairs: tuple[str, ...]
    beta_mapping_stale_pairs: tuple[str, ...]


def _planned_loss_amount(candidate: RiskCandidate) -> float:
    return 0.0 if candidate.planned_loss is None else candidate.planned_loss


def _build_hook_reason_details(
    *,
    reason_codes: tuple[str, ...] | None,
    fallback_code: str,
    detail: str,
    fallback_detail: str,
    category: str,
    verdict: str,
) -> tuple[tuple[str, ...], str, tuple[RiskReasonDetail, ...]]:
    normalized_codes = reason_codes or (fallback_code,)
    normalized_detail = detail.strip() or fallback_detail
    reason_details = tuple(
        RiskReasonDetail(
            code=reason_code,
            category=category,
            verdict=verdict,
            message=normalized_detail,
        )
        for reason_code in normalized_codes
    )
    return normalized_codes, normalized_detail, reason_details


def _build_daily_pnl_reason_details(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    *,
    timestamp: float,
    current_equity: float,
    session_peak_equity: float,
) -> tuple[RiskReasonDetail, ...]:
    outcome = runtime._run_daily_pnl_precheck_hook(
        candidate,
        timestamp,
        current_equity=current_equity,
        session_peak_equity=session_peak_equity,
    )
    if outcome is None or outcome.accepted:
        return ()
    _, _, reason_details = _build_hook_reason_details(
        reason_codes=outcome.reason_codes,
        fallback_code="RISK_DAILY_PNL_BREAKER_BLOCK",
        detail=outcome.detail,
        fallback_detail=(
            "compiled daily pnl breaker blocked "
            f"{candidate.pair} / {candidate.engine_id}"
        ),
        category="daily_pnl_breaker",
        verdict=outcome.verdict,
    )
    return reason_details


def _evaluate_cluster_results(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    current_positions: dict[str, float],
) -> tuple[ClusterCapResult, ...]:
    pair_to_clusters = {
        pair: runtime._cluster_registry.get_clusters_for_pair(pair)
        for pair in current_positions
    }
    current_cluster_exposures = calculate_cluster_exposures(current_positions, pair_to_clusters)
    exposure_by_cluster = {
        cluster.cluster_id: cluster.exposure
        for cluster in current_cluster_exposures.clusters
    }
    cluster_ids = runtime._cluster_registry.get_clusters_for_pair(candidate.pair)
    if not cluster_ids:
        return (
            evaluate_cluster_cap(
                pair=candidate.pair,
                cluster_id=None,
                current_exposure=0.0,
                candidate_size=candidate.size,
                cluster_cap=runtime._limits.cluster_cap,
            ),
        )
    return tuple(
        evaluate_cluster_cap(
            pair=candidate.pair,
            cluster_id=cluster_id,
            current_exposure=exposure_by_cluster.get(cluster_id, 0.0),
            candidate_size=candidate.size,
            cluster_cap=runtime._limits.cluster_cap,
        )
        for cluster_id in cluster_ids
    )


def _build_guard_snapshot(runtime: RiskRuntime, candidate: RiskCandidate, *, now: float | None) -> _RiskGuardSnapshot:
    timestamp = _require_runtime_timestamp(now, context="RiskRuntime.evaluate_candidate")
    current_equity, session_peak_equity = _normalize_runtime_equity_state(
        runtime._current_equity,
        runtime._session_peak_equity,
        context="RiskRuntime.evaluate_candidate",
    )
    runtime._current_equity = current_equity
    runtime._session_peak_equity = session_peak_equity
    physics_scores = _evaluate_candidate_physics(candidate)
    gross_snapshot = calculate_gross_exposure(tuple(runtime._positions))
    gross_result = evaluate_gross_cap(
        pair=candidate.pair,
        candidate_size=candidate.size,
        current_gross=gross_snapshot.gross_exposure,
        position_cap=runtime._limits.position_cap,
        gross_cap=runtime._limits.gross_cap,
        current_pair_exposure=gross_snapshot.by_pair.get(candidate.pair, 0.0),
    )
    loss_result = evaluate_loss_cap(
        pair=candidate.pair,
        candidate_loss=candidate.planned_loss,
        current_budget=runtime._current_loss_budget,
        loss_cap=runtime._limits.loss_cap,
    )
    current_positions = runtime._positions_by_pair()
    betas, pair_beta, missing_pairs, stale_pairs = runtime._resolve_governed_betas(
        candidate,
        current_positions,
        timestamp,
    )
    beta_projection = check_projected_beta(
        current_positions=current_positions,
        betas=betas,
        candidate_pair=candidate.pair,
        candidate_size=candidate.size,
        candidate_beta=pair_beta,
        beta_cap=runtime._limits.beta_cap,
    )
    beta_result = evaluate_beta_cap(
        pair=candidate.pair,
        current_beta=beta_projection.current_beta,
        projected_beta=beta_projection.projected_beta,
        beta_cap=runtime._limits.beta_cap,
    )
    cluster_results = _evaluate_cluster_results(runtime, candidate, current_positions)
    drawdown_result = evaluate_drawdown_guard(
        current_equity=current_equity,
        session_peak_equity=session_peak_equity,
        warning_threshold_pct=runtime._limits.drawdown_warning_threshold_pct,
        observe_threshold_pct=runtime._limits.drawdown_observe_threshold_pct,
    )
    reason_details = _build_reason_details(
        gross_result=gross_result,
        loss_result=loss_result,
        beta_result=beta_result,
        cluster_results=cluster_results,
        drawdown_result=drawdown_result,
        beta_mapping_missing_pairs=missing_pairs,
        beta_mapping_stale_pairs=stale_pairs,
    )
    return _RiskGuardSnapshot(
        timestamp=timestamp,
        physics_scores=physics_scores,
        gross_result=gross_result,
        loss_result=loss_result,
        pair_beta=pair_beta,
        beta_projection=beta_projection,
        beta_result=beta_result,
        cluster_results=cluster_results,
        drawdown_result=drawdown_result,
        reason_details=reason_details,
        dominant_reason_code=reason_details[0].code if reason_details else "",
        daily_pnl_reason_details=_build_daily_pnl_reason_details(
            runtime,
            candidate,
            timestamp=timestamp,
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
        ),
        beta_mapping_missing_pairs=missing_pairs,
        beta_mapping_stale_pairs=stale_pairs,
    )


def _build_rejected_components(snapshot: _RiskGuardSnapshot) -> tuple[str, ...]:
    rejected_components: list[str] = []
    if snapshot.gross_result.verdict != GrossCapVerdict.ACCEPTED:
        rejected_components.append(snapshot.gross_result.reason)
    if snapshot.loss_result.verdict != LossCapVerdict.ACCEPTED:
        rejected_components.append(snapshot.loss_result.reason)
    for pair in snapshot.beta_mapping_missing_pairs:
        rejected_components.append(f"missing explicit beta mapping for pair {pair}")
    for pair in snapshot.beta_mapping_stale_pairs:
        rejected_components.append(f"stale beta mapping for pair {pair}")
    if snapshot.beta_result.verdict != BetaCapVerdict.ACCEPTED:
        rejected_components.append(snapshot.beta_result.reason)
    for cluster_result in snapshot.cluster_results:
        if cluster_result.verdict != ClusterCapVerdict.ACCEPTED:
            rejected_components.append(cluster_result.reason)
    if snapshot.daily_pnl_reason_details:
        rejected_components.append(snapshot.daily_pnl_reason_details[0].message)
    return tuple(rejected_components)


def _build_evaluation(
    snapshot: _RiskGuardSnapshot,
    *,
    action: RiskRuntimeAction,
    accepted: bool,
    reasons: tuple[str, ...] = (),
    reason_details: tuple[RiskReasonDetail, ...] | None = None,
    dominant_reason_code: str | None = None,
) -> RiskEvaluation:
    resolved_reason_details = snapshot.reason_details if reason_details is None else reason_details
    resolved_dominant_code = (
        snapshot.dominant_reason_code
        if dominant_reason_code is None
        else dominant_reason_code
    )
    explainability = _build_risk_explainability(
        action=action,
        reason_details=resolved_reason_details,
        drawdown_result=snapshot.drawdown_result,
        physics_scores=snapshot.physics_scores,
    )
    return RiskEvaluation(
        action=action,
        accepted=accepted,
        reasons=reasons,
        reason_details=resolved_reason_details,
        dominant_reason_code=resolved_dominant_code,
        explain_summary=explainability.summary,
        explainability=explainability,
        gross_result=snapshot.gross_result,
        loss_result=snapshot.loss_result,
        beta_projection=snapshot.beta_projection,
        beta_result=snapshot.beta_result,
        cluster_results=snapshot.cluster_results,
        drawdown_result=snapshot.drawdown_result,
    )


def _record_and_build_block(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    snapshot: _RiskGuardSnapshot,
    *,
    action: RiskRuntimeAction,
    reasons: tuple[str, ...],
    reason_details: tuple[RiskReasonDetail, ...],
    dominant_reason_code: str,
) -> RiskEvaluation:
    runtime._record_refusals(
        candidate,
        snapshot.pair_beta,
        snapshot.cluster_results,
        reasons,
        snapshot.timestamp,
    )
    return _build_evaluation(
        snapshot,
        action=action,
        accepted=False,
        reasons=reasons,
        reason_details=reason_details,
        dominant_reason_code=dominant_reason_code,
    )


def _block_from_hook(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    snapshot: _RiskGuardSnapshot,
    *,
    action: RiskRuntimeAction,
    reason_codes: tuple[str, ...] | None,
    fallback_code: str,
    detail: str,
    fallback_detail: str,
    category: str,
    verdict: str,
) -> RiskEvaluation:
    normalized_codes, normalized_detail, reason_details = _build_hook_reason_details(
        reason_codes=reason_codes,
        fallback_code=fallback_code,
        detail=detail,
        fallback_detail=fallback_detail,
        category=category,
        verdict=verdict,
    )
    return _record_and_build_block(
        runtime,
        candidate,
        snapshot,
        action=action,
        reasons=(normalized_detail,),
        reason_details=snapshot.reason_details + reason_details,
        dominant_reason_code=normalized_codes[0],
    )


def _handle_drawdown_block(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    snapshot: _RiskGuardSnapshot,
    *,
    action: RiskRuntimeAction,
    fallback_reason: str,
) -> RiskEvaluation:
    reason = snapshot.drawdown_result.reason or fallback_reason
    return _record_and_build_block(
        runtime,
        candidate,
        snapshot,
        action=action,
        reasons=(reason,),
        reason_details=snapshot.reason_details,
        dominant_reason_code=snapshot.dominant_reason_code,
    )


def _handle_severe_pressure(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    snapshot: _RiskGuardSnapshot,
) -> RiskEvaluation:
    physics_reason_detail = RiskReasonDetail(
        code="RISK_EXECUTION_PRESSURE",
        category="execution_pressure",
        verdict=RiskRuntimeAction.REDUCE_EXPOSURE.value,
        message=(
            "microstructure execution pressure too high: "
            f"survivability={snapshot.physics_scores.execution_survivability_score:.3f}, "
            f"micro_friction={snapshot.physics_scores.micro_friction_score:.3f}"
        ),
    )
    return _record_and_build_block(
        runtime,
        candidate,
        snapshot,
        action=RiskRuntimeAction.REDUCE_EXPOSURE,
        reasons=(physics_reason_detail.message,),
        reason_details=snapshot.reason_details + (physics_reason_detail,),
        dominant_reason_code=physics_reason_detail.code,
    )


def _accept_candidate(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    snapshot: _RiskGuardSnapshot,
) -> RiskEvaluation:
    runtime._positions.append(
        Position(
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            size=candidate.size,
            side=candidate.side,
        )
    )
    runtime._current_loss_budget += _planned_loss_amount(candidate)
    runtime._exposure_reporter.record_accepted(
        candidate.pair,
        candidate.size,
        timestamp=snapshot.timestamp,
    )
    runtime._loss_reporter.record_accepted(
        candidate.pair,
        _planned_loss_amount(candidate),
        timestamp=snapshot.timestamp,
    )
    runtime._beta_reporter.record_accepted(
        candidate.pair,
        snapshot.pair_beta,
        snapshot.beta_projection.projected_beta,
        timestamp=snapshot.timestamp,
    )
    for cluster_result in snapshot.cluster_results:
        runtime._cluster_reporter.record_accepted(
            candidate.pair,
            cluster_result.cluster_id,
            size=candidate.size,
            timestamp=snapshot.timestamp,
        )
    return _build_evaluation(
        snapshot,
        action=RiskRuntimeAction.ACCEPT,
        accepted=True,
    )


def evaluate_candidate_support(
    runtime: RiskRuntime,
    candidate: RiskCandidate,
    *,
    now: float | None,
) -> RiskEvaluation:
    """Evaluate a candidate trade against the full Build-4 risk backbone."""

    snapshot = _build_guard_snapshot(runtime, candidate, now=now)
    rejected_components = _build_rejected_components(snapshot)
    if rejected_components:
        return _record_and_build_block(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.REJECT,
            reasons=rejected_components,
            reason_details=snapshot.reason_details + snapshot.daily_pnl_reason_details,
            dominant_reason_code=(
                (snapshot.reason_details + snapshot.daily_pnl_reason_details)[0].code
                if snapshot.reason_details or snapshot.daily_pnl_reason_details
                else ""
            ),
        )

    regime_outcome = runtime._run_regime_precheck_hook(candidate, snapshot.timestamp)
    if regime_outcome is not None and not regime_outcome.accepted:
        return _block_from_hook(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.REJECT,
            reason_codes=regime_outcome.reason_codes,
            fallback_code="RISK_REGIME_PRECHECK_BLOCK",
            detail=regime_outcome.detail,
            fallback_detail=(
                "compiled risk regime precheck blocked "
                f"{candidate.pair} / {candidate.engine_id}"
            ),
            category="regime_state",
            verdict="rejected_regime_precheck",
        )

    if snapshot.drawdown_result.verdict == DrawdownVerdict.OBSERVE_ONLY:
        return _handle_drawdown_block(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.OBSERVE_ONLY,
            fallback_reason="drawdown guard switched runtime to observe_only",
        )
    if snapshot.drawdown_result.verdict == DrawdownVerdict.REDUCE_EXPOSURE:
        return _handle_drawdown_block(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.REDUCE_EXPOSURE,
            fallback_reason="drawdown guard requested exposure reduction",
        )

    info_stress_outcome = runtime._run_info_stress_precheck_hook(candidate, snapshot.timestamp)
    if info_stress_outcome is not None and not info_stress_outcome.accepted:
        return _block_from_hook(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.REJECT,
            reason_codes=info_stress_outcome.reason_codes,
            fallback_code="RISK_INFO_STRESS_PRECHECK_BLOCK",
            detail=info_stress_outcome.detail,
            fallback_detail=(
                "compiled risk info-stress precheck blocked "
                f"{candidate.pair} / {candidate.engine_id}"
            ),
            category="info_stress",
            verdict="rejected_info_stress_precheck",
        )

    micro_friction_outcome = runtime._run_micro_friction_precheck_hook(
        candidate,
        snapshot.physics_scores,
        snapshot.timestamp,
    )
    if micro_friction_outcome is not None and not micro_friction_outcome.accepted:
        return _block_from_hook(
            runtime,
            candidate,
            snapshot,
            action=RiskRuntimeAction.REJECT,
            reason_codes=micro_friction_outcome.reason_codes,
            fallback_code="RISK_MICRO_FRICTION_PRECHECK_BLOCK",
            detail=micro_friction_outcome.detail,
            fallback_detail=(
                "compiled risk micro-friction precheck blocked "
                f"{candidate.pair} / {candidate.engine_id}"
            ),
            category="micro_friction_hook",
            verdict="rejected_micro_friction_precheck",
        )

    if snapshot.physics_scores.pressure_state == "severe":
        return _handle_severe_pressure(runtime, candidate, snapshot)
    return _accept_candidate(runtime, candidate, snapshot)


__all__ = ["evaluate_candidate_support"]
