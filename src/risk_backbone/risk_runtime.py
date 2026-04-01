"""
Build-4 / risk_backbone / risk_runtime
Drive a real risk verdict path across gross exposure, loss budget, BTC beta,
cluster concentration and drawdown protection.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

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


class PortfolioRiskSnapshot(BaseModel, frozen=True):
    positions: tuple[Position, ...] = ()
    current_loss_budget: float = 0.0
    current_equity: float = 0.0
    session_peak_equity: float = 0.0


class RiskEvaluation(BaseModel, frozen=True):
    action: RiskRuntimeAction
    accepted: bool
    reasons: tuple[str, ...] = ()
    gross_result: GrossCapResult
    loss_result: LossCapResult
    beta_projection: ProjectedBeta
    beta_result: BetaCapResult
    cluster_results: tuple[ClusterCapResult, ...] = ()
    drawdown_result: DrawdownGuardResult


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
        self._current_equity = initial_snapshot.current_equity
        self._session_peak_equity = initial_snapshot.session_peak_equity
        self._exposure_reporter = ExposureReporter(gross_cap=limits.gross_cap)
        self._loss_reporter = LossReporter(loss_cap=limits.loss_cap)
        self._beta_reporter = BetaReporter(beta_cap=limits.beta_cap)
        self._cluster_reporter = ClusterReporter()
        self._seed_reporters_from_snapshot()

    def set_equity(self, *, current_equity: float, session_peak_equity: float) -> None:
        self._current_equity = current_equity
        self._session_peak_equity = session_peak_equity

    def get_snapshot(self) -> PortfolioRiskSnapshot:
        return PortfolioRiskSnapshot(
            positions=tuple(self._positions),
            current_loss_budget=self._current_loss_budget,
            current_equity=self._current_equity,
            session_peak_equity=self._session_peak_equity,
        )

    def evaluate_candidate(self, candidate: RiskCandidate, now: float = 0.0) -> RiskEvaluation:
        """Evaluate a candidate trade against the full Build-4 risk backbone."""
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
        betas = {pair: self._pair_beta_registry.get_beta(pair).beta for pair in current_positions}
        pair_beta = candidate.pair_beta
        if pair_beta is None:
            pair_beta = self._pair_beta_registry.get_beta(candidate.pair).beta
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
            current_equity=self._current_equity,
            session_peak_equity=self._session_peak_equity,
            warning_threshold_pct=self._limits.drawdown_warning_threshold_pct,
            observe_threshold_pct=self._limits.drawdown_observe_threshold_pct,
        )

        rejected_components = []
        if gross_result.verdict != GrossCapVerdict.ACCEPTED:
            rejected_components.append(gross_result.reason)
        if loss_result.verdict != LossCapVerdict.ACCEPTED:
            rejected_components.append(loss_result.reason)
        if beta_result.verdict != BetaCapVerdict.ACCEPTED:
            rejected_components.append(beta_result.reason)
        for cluster_result in cluster_results:
            if cluster_result.verdict != ClusterCapVerdict.ACCEPTED:
                rejected_components.append(cluster_result.reason)

        if rejected_components:
            action = RiskRuntimeAction.REJECT
            self._record_refusals(candidate, pair_beta, cluster_results, tuple(rejected_components), now)
            return RiskEvaluation(
                action=action,
                accepted=False,
                reasons=tuple(rejected_components),
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        if drawdown_result.verdict == DrawdownVerdict.OBSERVE_ONLY:
            reason = drawdown_result.reason or "drawdown guard switched runtime to observe_only"
            self._record_refusals(candidate, pair_beta, cluster_results, (reason,), now)
            return RiskEvaluation(
                action=RiskRuntimeAction.OBSERVE_ONLY,
                accepted=False,
                reasons=(reason,),
                gross_result=gross_result,
                loss_result=loss_result,
                beta_projection=beta_projection,
                beta_result=beta_result,
                cluster_results=cluster_results,
                drawdown_result=drawdown_result,
            )

        if drawdown_result.verdict == DrawdownVerdict.REDUCE_EXPOSURE:
            reason = drawdown_result.reason or "drawdown guard requested exposure reduction"
            self._record_refusals(candidate, pair_beta, cluster_results, (reason,), now)
            return RiskEvaluation(
                action=RiskRuntimeAction.REDUCE_EXPOSURE,
                accepted=False,
                reasons=(reason,),
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
        self._exposure_reporter.record_accepted(candidate.pair, candidate.size, timestamp=now)
        self._loss_reporter.record_accepted(candidate.pair, 0.0 if candidate.planned_loss is None else candidate.planned_loss, timestamp=now)
        self._beta_reporter.record_accepted(candidate.pair, pair_beta, beta_projection.projected_beta, timestamp=now)
        for cluster_result in cluster_results:
            self._cluster_reporter.record_accepted(
                candidate.pair,
                cluster_result.cluster_id,
                size=candidate.size,
                timestamp=now,
            )
        return RiskEvaluation(
            action=RiskRuntimeAction.ACCEPT,
            accepted=True,
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

    def _seed_reporters_from_snapshot(self) -> None:
        gross_snapshot = calculate_gross_exposure(tuple(self._positions))
        self._exposure_reporter._current_gross = gross_snapshot.gross_exposure
        self._loss_reporter._current_budget = self._current_loss_budget

        positions_by_pair = self._positions_by_pair()
        betas = {pair: self._pair_beta_registry.get_beta(pair).beta for pair in positions_by_pair}
        self._beta_reporter._current_beta = calculate_portfolio_beta(positions_by_pair, betas).beta_port

        pair_to_clusters = {
            pair: self._cluster_registry.get_clusters_for_pair(pair)
            for pair in positions_by_pair
        }
        current_cluster_exposures = calculate_cluster_exposures(positions_by_pair, pair_to_clusters)
        self._cluster_reporter._cluster_sizes = {
            cluster.cluster_id: cluster.exposure
            for cluster in current_cluster_exposures.clusters
        }

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
