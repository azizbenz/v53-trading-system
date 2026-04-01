"""Runtime tests for risk_backbone Build-4."""

import pytest

from risk_backbone import PortfolioRiskSnapshot, RiskCandidate, RiskLimits, RiskRuntime, RiskRuntimeAction
from risk_backbone.btc_factor_guard.pair_beta_registry import PairBetaRegistry
from risk_backbone.correlation_cluster_guard.cluster_registry import ClusterRegistry
from risk_backbone.exposure_budgeter.gross_exposure_calculator import Position


pytestmark = pytest.mark.build4


def _limits() -> RiskLimits:
    return RiskLimits(
        gross_cap=500.0,
        position_cap=250.0,
        loss_cap=100.0,
        beta_cap=1.0,
        cluster_cap=200.0,
        drawdown_warning_threshold_pct=0.02,
        drawdown_observe_threshold_pct=0.04,
    )


def _runtime(snapshot: PortfolioRiskSnapshot | None = None) -> RiskRuntime:
    beta_registry = PairBetaRegistry()
    beta_registry.set_beta("BTCUSDT", 1.0)
    beta_registry.set_beta("ETHUSDT", 0.6)
    beta_registry.set_beta("LINKUSDT", 0.55)
    beta_registry.set_beta("SOLUSDT", 0.7)
    return RiskRuntime(
        _limits(),
        pair_beta_registry=beta_registry,
        cluster_registry=ClusterRegistry(),
        snapshot=snapshot,
    )


class TestRiskRuntime:
    def test_runtime_accepts_candidate_and_updates_stateful_reporters(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                positions=(Position(pair="BTCUSDT", engine_id="eng-a", size=100.0),),
                current_loss_budget=20.0,
                current_equity=995.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=100.0,
                planned_loss=20.0,
            ),
            now=10.0,
        )
        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert evaluation.accepted is True
        assert evaluation.gross_result.projected_gross == pytest.approx(200.0)
        assert evaluation.beta_projection.projected_beta == pytest.approx(0.8)
        assert runtime.get_snapshot().current_loss_budget == pytest.approx(40.0)
        assert runtime.get_exposure_stats().current_gross == pytest.approx(200.0)
        assert runtime.get_loss_stats().current_budget == pytest.approx(40.0)
        assert runtime.get_beta_stats().current_portfolio_beta == pytest.approx(0.8)
        assert runtime.get_cluster_stats().cluster_exposures["eth_ecosystem"] == pytest.approx(100.0)

    def test_runtime_rejects_missing_loss_estimate(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=50.0,
                planned_loss=None,
            ),
            now=20.0,
        )
        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.loss_result.verdict.value == "rejected_no_loss_estimate"
        assert runtime.get_loss_stats().total_refused == 1

    def test_runtime_blocks_multiple_small_correlated_trades(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        first = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=120.0,
                planned_loss=15.0,
            ),
            now=30.0,
        )
        second = runtime.evaluate_candidate(
            RiskCandidate(
                pair="LINKUSDT",
                engine_id="eng-b",
                size=100.0,
                planned_loss=15.0,
            ),
            now=31.0,
        )
        assert first.action == RiskRuntimeAction.ACCEPT
        assert second.action == RiskRuntimeAction.REJECT
        assert second.accepted is False
        assert any(result.verdict.value == "rejected" for result in second.cluster_results)
        assert "eth_ecosystem" in second.reasons[0]

    def test_runtime_drawdown_observe_only_blocks_even_if_other_guards_pass(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=950.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=50.0,
                planned_loss=10.0,
            ),
            now=40.0,
        )
        assert evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
        assert evaluation.accepted is False
        assert "drawdown" in evaluation.reasons[0]

    def test_runtime_fail_closed_when_pair_has_no_cluster(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="DOGEUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                pair_beta=0.9,
            ),
            now=50.0,
        )
        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.cluster_results[0].verdict.value == "rejected_no_cluster"
