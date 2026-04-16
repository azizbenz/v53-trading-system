"""Stateful Build-4 risk runtime implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from .btc_factor_guard.beta_reporter import BetaReporter, BetaStats
from .btc_factor_guard.pair_beta_registry import PairBetaRegistry
from .btc_factor_guard.portfolio_beta_calculator import calculate_portfolio_beta
from .correlation_cluster_guard.cluster_cap_guard import ClusterCapResult
from .correlation_cluster_guard.cluster_exposure_calculator import calculate_cluster_exposures
from .correlation_cluster_guard.cluster_registry import ClusterRegistry
from .correlation_cluster_guard.cluster_reporter import ClusterReporter, ClusterStats
from .exposure_budgeter.exposure_reporter import ExposureReporter, ExposureStats
from .exposure_budgeter.gross_exposure_calculator import Position, calculate_gross_exposure
from .loss_budgeter.loss_reporter import LossReporter, LossStats
from .risk_runtime_evaluation_support import evaluate_candidate_support
from .risk_runtime_explainability import _normalize_runtime_equity_state
from .risk_runtime_models import (
    PortfolioRiskSnapshot,
    RiskCandidate,
    RiskDailyPnlPrecheckHook,
    RiskDailyPnlPrecheckInput,
    RiskDailyPnlPrecheckOutcome,
    RiskEvaluation,
    RiskInfoStressPrecheckHook,
    RiskInfoStressPrecheckInput,
    RiskInfoStressPrecheckOutcome,
    RiskLimits,
    RiskMicroFrictionPrecheckHook,
    RiskMicroFrictionPrecheckInput,
    RiskMicroFrictionPrecheckOutcome,
    RiskPhysicsScores,
    RiskRegimePrecheckHook,
    RiskRegimePrecheckInput,
    RiskRegimePrecheckOutcome,
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
        daily_pnl_precheck_hook: RiskDailyPnlPrecheckHook | None = None,
        regime_precheck_hook: RiskRegimePrecheckHook | None = None,
        info_stress_precheck_hook: RiskInfoStressPrecheckHook | None = None,
        micro_friction_precheck_hook: RiskMicroFrictionPrecheckHook | None = None,
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
        self._daily_pnl_precheck_hook = daily_pnl_precheck_hook
        self._regime_precheck_hook = regime_precheck_hook
        self._info_stress_precheck_hook = info_stress_precheck_hook
        self._micro_friction_precheck_hook = micro_friction_precheck_hook
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
        """Release a tracked position from the runtime snapshot."""

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
        return evaluate_candidate_support(self, candidate, now=now)

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
        now: float,
    ) -> tuple[dict[str, float], float, tuple[str, ...], tuple[str, ...]]:
        """Resolve beta inputs while rejecting implicit or stale registry mappings."""

        betas: dict[str, float] = {}
        missing_pairs: list[str] = []
        stale_pairs: list[str] = []
        for pair in current_positions:
            if not self._pair_beta_registry.has_explicit_beta(pair):
                missing_pairs.append(pair)
                betas[pair] = 0.0
                continue
            if not self._pair_beta_registry.is_fresh(
                pair,
                now=now,
                max_age_s=self._limits.beta_mapping_max_age_s,
            ):
                stale_pairs.append(pair)
            betas[pair] = self._pair_beta_registry.get_beta(pair).beta

        if candidate.pair_beta is not None:
            candidate_beta = candidate.pair_beta
        else:
            if not self._pair_beta_registry.has_explicit_beta(candidate.pair):
                missing_pairs.append(candidate.pair)
                candidate_beta = 0.0
            else:
                if not self._pair_beta_registry.is_fresh(
                    candidate.pair,
                    now=now,
                    max_age_s=self._limits.beta_mapping_max_age_s,
                ):
                    stale_pairs.append(candidate.pair)
                candidate_beta = self._pair_beta_registry.get_beta(candidate.pair).beta

        return (
            betas,
            candidate_beta,
            tuple(dict.fromkeys(missing_pairs)),
            tuple(dict.fromkeys(stale_pairs)),
        )

    def _seed_reporters_from_snapshot(self) -> None:
        gross_snapshot = calculate_gross_exposure(tuple(self._positions))
        self._exposure_reporter.sync_current_gross(gross_snapshot.gross_exposure)
        self._loss_reporter.sync_current_budget(self._current_loss_budget)

        positions_by_pair = self._positions_by_pair()
        betas = {
            pair: (
                self._pair_beta_registry.get_beta(pair).beta
                if self._pair_beta_registry.has_explicit_beta(pair)
                else 0.0
            )
            for pair in positions_by_pair
        }
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
        planned_loss = 0.0 if candidate.planned_loss is None else candidate.planned_loss
        self._exposure_reporter.record_refused(candidate.pair, candidate.size, reason, timestamp=now)
        self._loss_reporter.record_refused(
            candidate.pair,
            planned_loss,
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

    def _run_daily_pnl_precheck_hook(
        self,
        candidate: RiskCandidate,
        now: float,
        *,
        current_equity: float,
        session_peak_equity: float,
    ) -> RiskDailyPnlPrecheckOutcome | None:
        if self._daily_pnl_precheck_hook is None:
            return None
        session_date = datetime.fromtimestamp(now, tz=UTC).date().isoformat()
        return self._daily_pnl_precheck_hook(
            RiskDailyPnlPrecheckInput(
                context_id=f"{candidate.pair}:{candidate.engine_id}:{now:.6f}",
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                size=candidate.size,
                planned_loss=candidate.planned_loss,
                session_date=session_date,
                current_equity=current_equity,
                session_peak_equity=session_peak_equity,
            )
        )

    def _run_micro_friction_precheck_hook(
        self,
        candidate: RiskCandidate,
        physics_scores: RiskPhysicsScores,
        now: float,
    ) -> RiskMicroFrictionPrecheckOutcome | None:
        if self._micro_friction_precheck_hook is None:
            return None
        return self._micro_friction_precheck_hook(
            RiskMicroFrictionPrecheckInput(
                context_id=f"{candidate.pair}:{candidate.engine_id}:{now:.6f}",
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                size=candidate.size,
                planned_loss=candidate.planned_loss,
                fragility_score=physics_scores.fragility_score,
                toxicity_score=physics_scores.toxicity_score,
                execution_survivability_score=physics_scores.execution_survivability_score,
                micro_friction_score=physics_scores.micro_friction_score,
                pressure_state=physics_scores.pressure_state,
            )
        )

    def _run_info_stress_precheck_hook(
        self,
        candidate: RiskCandidate,
        now: float,
    ) -> RiskInfoStressPrecheckOutcome | None:
        if self._info_stress_precheck_hook is None:
            return None
        return self._info_stress_precheck_hook(
            RiskInfoStressPrecheckInput(
                context_id=f"{candidate.pair}:{candidate.engine_id}:{now:.6f}",
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                size=candidate.size,
                planned_loss=candidate.planned_loss,
                now_ts=now,
                spread_bps=candidate.spread_bps,
                reference_spread_bps=candidate.reference_spread_bps,
                depth_ratio=candidate.depth_ratio,
                order_cancellation_rate=candidate.order_cancellation_rate,
                taker_imbalance=candidate.taker_imbalance,
                micro_vol_divergence=candidate.micro_vol_divergence,
            )
        )

    def _run_regime_precheck_hook(
        self,
        candidate: RiskCandidate,
        now: float,
    ) -> RiskRegimePrecheckOutcome | None:
        if self._regime_precheck_hook is None:
            return None
        return self._regime_precheck_hook(
            RiskRegimePrecheckInput(
                context_id=f"{candidate.pair}:{candidate.engine_id}:{now}",
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                size=candidate.size,
                planned_loss=candidate.planned_loss,
            )
        )


__all__ = ["RiskRuntime"]
