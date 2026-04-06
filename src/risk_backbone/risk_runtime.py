"""
Build-4 / risk_backbone / risk_runtime
Drive a real risk verdict path across gross exposure, loss budget, BTC beta,
cluster concentration and drawdown protection.
"""

from __future__ import annotations

from enum import StrEnum
import math

from pydantic import BaseModel, Field
from data_backbone.market_physics_math import (
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    toxicity_score_v1,
)

from .btc_factor_guard.beta_cap_guard import BetaCapResult, BetaCapVerdict, evaluate_beta_cap
from .btc_factor_guard.beta_reporter import BetaReporter, BetaStats
from .btc_factor_guard.pair_beta_registry import PairBetaRegistry
from .btc_factor_guard.portfolio_beta_calculator import calculate_portfolio_beta
from .btc_factor_guard.projected_beta_checker import ProjectedBeta, check_projected_beta
from .correlation_cluster_guard.cluster_cap_guard import (
    ClusterCapResult,
    ClusterCapVerdict,
    evaluate_cluster_cap,
)
from .correlation_cluster_guard.cluster_exposure_calculator import calculate_cluster_exposures
from .correlation_cluster_guard.cluster_registry import ClusterRegistry
from .correlation_cluster_guard.cluster_reporter import ClusterReporter, ClusterStats
from .exposure_budgeter.exposure_reporter import ExposureReporter, ExposureStats
from .exposure_budgeter.gross_cap_guard import GrossCapResult, GrossCapVerdict, evaluate_gross_cap
from .exposure_budgeter.gross_exposure_calculator import Position, calculate_gross_exposure
from .loss_budgeter.drawdown_guard import DrawdownGuardResult, DrawdownVerdict, evaluate_drawdown_guard
from .loss_budgeter.loss_cap_guard import LossCapResult, LossCapVerdict, evaluate_loss_cap
from .loss_budgeter.loss_reporter import LossReporter, LossStats


class RiskRuntimeAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    REDUCE_EXPOSURE = "reduce_exposure"
    OBSERVE_ONLY = "observe_only"


class RiskLimits(BaseModel, frozen=True):
    gross_cap: float
    position_cap: float
    loss_cap: float
    beta_cap: float
    cluster_cap: float
    drawdown_warning_threshold_pct: float = 0.02
    drawdown_observe_threshold_pct: float = 0.04


class RiskCandidate(BaseModel, frozen=True):
    pair: str
    engine_id: str
    size: float
    planned_loss: float | None
    pair_beta: float | None = None
    side: str = "buy"
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    participation_penalty: float = 0.0


class RiskReasonDetail(BaseModel, frozen=True):
    """Stable, audit-ready reason emitted by the Build-4 risk runtime."""

    code: str
    category: str
    verdict: str
    message: str


class RiskExplainability(BaseModel, frozen=True):
    """Structured Build-4 explainability summary for downstream monitoring/UI."""

    blocked_guard_codes: tuple[str, ...] = ()
    blocked_guard_categories: tuple[str, ...] = ()
    blocked_guard_count: int = 0
    drawdown_state_code: str = DrawdownVerdict.ACCEPTED.value
    decision_severity: str = "nominal"
    physics_pressure_state: str = "nominal"
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    summary: str = "risk=accept / no blocker triggered"


class PortfolioRiskSnapshot(BaseModel, frozen=True):
    positions: tuple[Position, ...] = ()
    current_loss_budget: float = 0.0
    current_equity: float = 0.0
    session_peak_equity: float = 0.0


class RiskPhysicsScores(BaseModel, frozen=True):
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    pressure_state: str = "nominal"


class RiskEvaluation(BaseModel, frozen=True):
    action: RiskRuntimeAction
    accepted: bool
    reasons: tuple[str, ...] = ()
    reason_details: tuple[RiskReasonDetail, ...] = ()
    dominant_reason_code: str = ""
    explain_summary: str = "risk=accepted"
    explainability: RiskExplainability = Field(default_factory=RiskExplainability)
    gross_result: GrossCapResult
    loss_result: LossCapResult
    beta_projection: ProjectedBeta
    beta_result: BetaCapResult
    cluster_results: tuple[ClusterCapResult, ...] = ()
    drawdown_result: DrawdownGuardResult


def _build_reason_details(
    *,
    gross_result: GrossCapResult,
    loss_result: LossCapResult,
    beta_result: BetaCapResult,
    cluster_results: tuple[ClusterCapResult, ...],
    drawdown_result: DrawdownGuardResult,
    beta_mapping_missing_pairs: tuple[str, ...] = (),
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


class RiskRuntime:
    """Stateful Build-4 runtime across all risk guards."""

    def __init__(
        self,
        limits: RiskLimits,
        *,
        pair_beta_registry: PairBetaRegistry | None = None,
        cluster_registry: ClusterRegistry | None = None,
        snapshot: PortfolioRiskSnapshot | None = None,
    ) -> None:
        self._limits = limits
        self._pair_beta_registry = pair_beta_registry or PairBetaRegistry()
        self._cluster_registry = cluster_registry or ClusterRegistry()
        initial_snapshot = snapshot or PortfolioRiskSnapshot()
        self._positions = list(initial_snapshot.positions)
        self._current_loss_budget = initial_snapshot.current_loss_budget
        (
            self._current_equity,
            self._session_peak_equity,
        ) = _normalize_runtime_equity_state(
            initial_snapshot.current_equity,
            initial_snapshot.session_peak_equity,
            context="RiskRuntime.__init__",
            allow_uninitialized=True,
        )
        self._exposure_reporter = ExposureReporter(gross_cap=limits.gross_cap)
        self._loss_reporter = LossReporter(loss_cap=limits.loss_cap)
        self._beta_reporter = BetaReporter(beta_cap=limits.beta_cap)
        self._cluster_reporter = ClusterReporter()
        self._seed_reporters_from_snapshot()

    def set_equity(self, *, current_equity: float, session_peak_equity: float) -> None:
        self._current_equity, self._session_peak_equity = _normalize_runtime_equity_state(
            current_equity,
            session_peak_equity,
            context="RiskRuntime.set_equity",
        )

    def replace_snapshot(self, snapshot: PortfolioRiskSnapshot) -> None:
        """Replace the managed state with a governed portfolio snapshot."""

        self._positions = list(snapshot.positions)
        self._current_loss_budget = snapshot.current_loss_budget
        self._current_equity, self._session_peak_equity = _normalize_runtime_equity_state(
            snapshot.current_equity,
            snapshot.session_peak_equity,
            context="RiskRuntime.replace_snapshot",
        )
        self._seed_reporters_from_snapshot()

    def register_position_closed(
        self,
        *,
        pair: str,
        engine_id: str,
        released_size: float,
        released_planned_loss: float = 0.0,
        side: str = "buy",
    ) -> None:
        """Release a tracked position from the runtime snapshot.

        This keeps the current Build-4 runtime stateful while making the release
        path explicit instead of append-only.
        """

        if released_size <= 0.0:
            raise ValueError("register_position_closed requires released_size > 0")
        if released_planned_loss < 0.0:
            raise ValueError("register_position_closed requires released_planned_loss >= 0")

        remaining_to_release = released_size
        updated_positions: list[Position] = []
        released_any = False

        for position in self._positions:
            matches = (
                position.pair == pair
                and position.engine_id == engine_id
                and position.side == side
            )
            if not matches or remaining_to_release <= 0.0:
                updated_positions.append(position)
                continue

            released_any = True
            if remaining_to_release >= position.size:
                remaining_to_release -= position.size
                continue

            updated_positions.append(
                position.model_copy(update={"size": position.size - remaining_to_release})
            )
            remaining_to_release = 0.0

        if not released_any:
            raise ValueError(
                f"register_position_closed found no matching position for {pair}/{engine_id}/{side}"
            )
        if remaining_to_release > 1e-12:
            raise ValueError(
                "register_position_closed cannot release more size than currently tracked"
            )

        self._positions = updated_positions
        self._current_loss_budget = max(
            0.0,
            self._current_loss_budget - released_planned_loss,
        )
        self._seed_reporters_from_snapshot()

    def get_snapshot(self) -> PortfolioRiskSnapshot:
        return PortfolioRiskSnapshot(
            positions=tuple(self._positions),
            current_loss_budget=self._current_loss_budget,
            current_equity=self._current_equity,
            session_peak_equity=self._session_peak_equity,
        )

    def evaluate_candidate(
        self,
        candidate: RiskCandidate,
        now: float | None = None,
    ) -> RiskEvaluation:
        """Evaluate a candidate trade against the full Build-4 risk backbone."""
        timestamp = _require_runtime_timestamp(now, context="RiskRuntime.evaluate_candidate")
        current_equity, session_peak_equity = _normalize_runtime_equity_state(
            self._current_equity,
            self._session_peak_equity,
            context="RiskRuntime.evaluate_candidate",
        )
        self._current_equity = current_equity
        self._session_peak_equity = session_peak_equity
        physics_scores = _evaluate_candidate_physics(candidate)
        gross_snapshot = calculate_gross_exposure(tuple(self._positions))
        current_pair_exposure = gross_snapshot.by_pair.get(candidate.pair, 0.0)
        gross_result = evaluate_gross_cap(
            pair=candidate.pair,
            candidate_size=candidate.size,
            current_gross=gross_snapshot.gross_exposure,
            position_cap=self._limits.position_cap,
            gross_cap=self._limits.gross_cap,
            current_pair_exposure=current_pair_exposure,
        )

        loss_result = evaluate_loss_cap(
            pair=candidate.pair,
            candidate_loss=candidate.planned_loss,
            current_budget=self._current_loss_budget,
            loss_cap=self._limits.loss_cap,
        )

        current_positions = self._positions_by_pair()
        betas, pair_beta, beta_mapping_missing_pairs = self._resolve_governed_betas(candidate, current_positions)
        beta_projection = check_projected_beta(
            current_positions=current_positions,
            betas=betas,
            candidate_pair=candidate.pair,
            candidate_size=candidate.size,
            candidate_beta=pair_beta,
            beta_cap=self._limits.beta_cap,
        )
        beta_result = evaluate_beta_cap(
            pair=candidate.pair,
            current_beta=beta_projection.current_beta,
            projected_beta=beta_projection.projected_beta,
            beta_cap=self._limits.beta_cap,
        )

        pair_to_clusters = {
            pair: self._cluster_registry.get_clusters_for_pair(pair)
            for pair in current_positions
        }
        current_cluster_exposures = calculate_cluster_exposures(current_positions, pair_to_clusters)
        exposure_by_cluster = {cluster.cluster_id: cluster.exposure for cluster in current_cluster_exposures.clusters}
        cluster_ids = self._cluster_registry.get_clusters_for_pair(candidate.pair)
        if not cluster_ids:
            cluster_results = (
                evaluate_cluster_cap(
                    pair=candidate.pair,
                    cluster_id=None,
                    current_exposure=0.0,
                    candidate_size=candidate.size,
                    cluster_cap=self._limits.cluster_cap,
                ),
            )
        else:
            cluster_results = tuple(
                evaluate_cluster_cap(
                    pair=candidate.pair,
                    cluster_id=cluster_id,
                    current_exposure=exposure_by_cluster.get(cluster_id, 0.0),
                    candidate_size=candidate.size,
                    cluster_cap=self._limits.cluster_cap,
                )
                for cluster_id in cluster_ids
            )

        drawdown_result = evaluate_drawdown_guard(
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
            warning_threshold_pct=self._limits.drawdown_warning_threshold_pct,
            observe_threshold_pct=self._limits.drawdown_observe_threshold_pct,
        )
        reason_details = _build_reason_details(
            gross_result=gross_result,
            loss_result=loss_result,
            beta_result=beta_result,
            cluster_results=cluster_results,
            drawdown_result=drawdown_result,
            beta_mapping_missing_pairs=beta_mapping_missing_pairs,
        )
        dominant_reason_code = reason_details[0].code if reason_details else ""

        rejected_components = []
        if gross_result.verdict != GrossCapVerdict.ACCEPTED:
            rejected_components.append(gross_result.reason)
        if loss_result.verdict != LossCapVerdict.ACCEPTED:
            rejected_components.append(loss_result.reason)
        for pair in beta_mapping_missing_pairs:
            rejected_components.append(f"missing explicit beta mapping for pair {pair}")
        if beta_result.verdict != BetaCapVerdict.ACCEPTED:
            rejected_components.append(beta_result.reason)
        for cluster_result in cluster_results:
            if cluster_result.verdict != ClusterCapVerdict.ACCEPTED:
                rejected_components.append(cluster_result.reason)

        if rejected_components:
            action = RiskRuntimeAction.REJECT
            self._record_refusals(
                candidate,
                pair_beta,
                cluster_results,
                tuple(rejected_components),
                timestamp,
            )
            explainability = _build_risk_explainability(
                action=action,
                reason_details=reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            )
            return RiskEvaluation(
                action=action,
                accepted=False,
                reasons=tuple(rejected_components),
                reason_details=reason_details,
                dominant_reason_code=dominant_reason_code,
                explain_summary=explainability.summary,
                explainability=explainability,
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        if drawdown_result.verdict == DrawdownVerdict.OBSERVE_ONLY:
            reason = drawdown_result.reason or "drawdown guard switched runtime to observe_only"
            self._record_refusals(candidate, pair_beta, cluster_results, (reason,), timestamp)
            explainability = _build_risk_explainability(
                action=RiskRuntimeAction.OBSERVE_ONLY,
                reason_details=reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            )
            return RiskEvaluation(
                action=RiskRuntimeAction.OBSERVE_ONLY,
                accepted=False,
                reasons=(reason,),
                reason_details=reason_details,
                dominant_reason_code=dominant_reason_code,
                explain_summary=explainability.summary,
                explainability=explainability,
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        if drawdown_result.verdict == DrawdownVerdict.REDUCE_EXPOSURE:
            reason = drawdown_result.reason or "drawdown guard requested exposure reduction"
            self._record_refusals(candidate, pair_beta, cluster_results, (reason,), timestamp)
            explainability = _build_risk_explainability(
                action=RiskRuntimeAction.REDUCE_EXPOSURE,
                reason_details=reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            )
            return RiskEvaluation(
                action=RiskRuntimeAction.REDUCE_EXPOSURE,
                accepted=False,
                reasons=(reason,),
                reason_details=reason_details,
                dominant_reason_code=dominant_reason_code,
                explain_summary=explainability.summary,
                explainability=explainability,
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        if physics_scores.pressure_state == "severe":
            physics_reason_detail = RiskReasonDetail(
                code="RISK_EXECUTION_PRESSURE",
                category="execution_pressure",
                verdict=RiskRuntimeAction.REDUCE_EXPOSURE.value,
                message=(
                    "microstructure execution pressure too high: "
                    f"survivability={physics_scores.execution_survivability_score:.3f}, "
                    f"micro_friction={physics_scores.micro_friction_score:.3f}"
                ),
            )
            severe_reason_details = reason_details + (physics_reason_detail,)
            severe_reason = physics_reason_detail.message
            self._record_refusals(
                candidate,
                pair_beta,
                cluster_results,
                (severe_reason,),
                timestamp,
            )
            explainability = _build_risk_explainability(
                action=RiskRuntimeAction.REDUCE_EXPOSURE,
                reason_details=severe_reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            )
            return RiskEvaluation(
                action=RiskRuntimeAction.REDUCE_EXPOSURE,
                accepted=False,
                reasons=(severe_reason,),
                reason_details=severe_reason_details,
                dominant_reason_code=physics_reason_detail.code,
                explain_summary=explainability.summary,
                explainability=explainability,
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        self._positions.append(
            Position(pair=candidate.pair, engine_id=candidate.engine_id, size=candidate.size, side=candidate.side),
        )
        self._current_loss_budget += 0.0 if candidate.planned_loss is None else candidate.planned_loss
        self._exposure_reporter.record_accepted(
            candidate.pair,
            candidate.size,
            timestamp=timestamp,
        )
        self._loss_reporter.record_accepted(
            candidate.pair,
            0.0 if candidate.planned_loss is None else candidate.planned_loss,
            timestamp=timestamp,
        )
        self._beta_reporter.record_accepted(
            candidate.pair,
            pair_beta,
            beta_projection.projected_beta,
            timestamp=timestamp,
        )
        for cluster_result in cluster_results:
            self._cluster_reporter.record_accepted(
                candidate.pair,
                cluster_result.cluster_id,
                size=candidate.size,
                timestamp=timestamp,
            )
        return RiskEvaluation(
            action=RiskRuntimeAction.ACCEPT,
            accepted=True,
            reason_details=reason_details,
            dominant_reason_code=dominant_reason_code,
            explain_summary=_build_risk_explainability(
                action=RiskRuntimeAction.ACCEPT,
                reason_details=reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            ).summary,
            explainability=_build_risk_explainability(
                action=RiskRuntimeAction.ACCEPT,
                reason_details=reason_details,
                drawdown_result=drawdown_result,
                physics_scores=physics_scores,
            ),
            gross_result=gross_result,
            loss_result=loss_result,
            beta_projection=beta_projection,
            beta_result=beta_result,
            cluster_results=cluster_results,
            drawdown_result=drawdown_result,
        )

    def get_exposure_stats(self) -> ExposureStats:
        return self._exposure_reporter.get_stats()

    def get_loss_stats(self) -> LossStats:
        return self._loss_reporter.get_stats()

    def get_beta_stats(self) -> BetaStats:
        return self._beta_reporter.get_stats()

    def get_cluster_stats(self) -> ClusterStats:
        return self._cluster_reporter.get_stats()

    def _positions_by_pair(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for position in self._positions:
            result[position.pair] = result.get(position.pair, 0.0) + position.size
        return result

    def _resolve_governed_betas(
        self,
        candidate: RiskCandidate,
        current_positions: dict[str, float],
    ) -> tuple[dict[str, float], float, tuple[str, ...]]:
        """Resolve beta inputs while rejecting implicit registry defaults on the open rail."""

        betas: dict[str, float] = {}
        missing_pairs: list[str] = []

        for pair in current_positions:
            if not self._pair_beta_registry.has_explicit_beta(pair):
                missing_pairs.append(pair)
            betas[pair] = self._pair_beta_registry.get_beta(pair).beta

        if candidate.pair_beta is not None:
            candidate_beta = candidate.pair_beta
        else:
            if not self._pair_beta_registry.has_explicit_beta(candidate.pair):
                missing_pairs.append(candidate.pair)
            candidate_beta = self._pair_beta_registry.get_beta(candidate.pair).beta

        return betas, candidate_beta, tuple(dict.fromkeys(missing_pairs))

    def _seed_reporters_from_snapshot(self) -> None:
        gross_snapshot = calculate_gross_exposure(tuple(self._positions))
        self._exposure_reporter.sync_current_gross(gross_snapshot.gross_exposure)
        self._loss_reporter.sync_current_budget(self._current_loss_budget)

        positions_by_pair = self._positions_by_pair()
        betas = {pair: self._pair_beta_registry.get_beta(pair).beta for pair in positions_by_pair}
        self._beta_reporter.sync_current_beta(
            calculate_portfolio_beta(positions_by_pair, betas).beta_port
        )

        pair_to_clusters = {
            pair: self._cluster_registry.get_clusters_for_pair(pair)
            for pair in positions_by_pair
        }
        current_cluster_exposures = calculate_cluster_exposures(positions_by_pair, pair_to_clusters)
        self._cluster_reporter.sync_cluster_exposures(
            {
                cluster.cluster_id: cluster.exposure
                for cluster in current_cluster_exposures.clusters
            }
        )

    def _record_refusals(
        self,
        candidate: RiskCandidate,
        pair_beta: float,
        cluster_results: tuple[ClusterCapResult, ...],
        reasons: tuple[str, ...],
        now: float,
    ) -> None:
        reason = "; ".join(reasons)
        self._exposure_reporter.record_refused(candidate.pair, candidate.size, reason, timestamp=now)
        self._loss_reporter.record_refused(
            candidate.pair,
            0.0 if candidate.planned_loss is None else candidate.planned_loss,
            reason,
            timestamp=now,
        )
        self._beta_reporter.record_refused(candidate.pair, pair_beta, reason, timestamp=now)
        for cluster_result in cluster_results:
            self._cluster_reporter.record_refused(
                candidate.pair,
                cluster_result.cluster_id,
                reason,
                timestamp=now,
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
