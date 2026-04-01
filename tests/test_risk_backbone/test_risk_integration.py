"""Integration tests for risk_backbone Build-4."""

import pytest

from risk_backbone.btc_factor_guard.beta_cap_guard import BetaCapVerdict, evaluate_beta_cap
from risk_backbone.btc_factor_guard.projected_beta_checker import check_projected_beta
from risk_backbone.correlation_cluster_guard.cluster_cap_guard import (
    ClusterCapVerdict,
    evaluate_cluster_cap,
)
from risk_backbone.correlation_cluster_guard.cluster_registry import ClusterRegistry
from risk_backbone.exposure_budgeter.gross_cap_guard import GrossCapVerdict, evaluate_gross_cap
from risk_backbone.loss_budgeter.drawdown_guard import DrawdownVerdict, evaluate_drawdown_guard
from risk_backbone.loss_budgeter.loss_cap_guard import LossCapVerdict, evaluate_loss_cap


class TestRiskBackboneIntegration:
    def test_candidate_trade_passes_all_primary_guards(self):
        gross = evaluate_gross_cap(
            pair="ETHUSDT",
            candidate_size=100.0,
            current_gross=200.0,
            position_cap=250.0,
            gross_cap=500.0,
            current_pair_exposure=50.0,
        )
        assert gross.verdict == GrossCapVerdict.ACCEPTED

        loss = evaluate_loss_cap(
            pair="ETHUSDT",
            candidate_loss=20.0,
            current_budget=40.0,
            loss_cap=100.0,
        )
        assert loss.verdict == LossCapVerdict.ACCEPTED

        beta_projection = check_projected_beta(
            current_positions={"BTCUSDT": 100.0},
            betas={"BTCUSDT": 1.0, "ETHUSDT": 0.6},
            candidate_pair="ETHUSDT",
            candidate_size=100.0,
            candidate_beta=0.6,
            beta_cap=1.0,
        )
        beta = evaluate_beta_cap(
            pair="ETHUSDT",
            current_beta=beta_projection.current_beta,
            projected_beta=beta_projection.projected_beta,
            beta_cap=1.0,
        )
        assert beta.verdict == BetaCapVerdict.ACCEPTED

        registry = ClusterRegistry()
        cluster_ids = registry.get_clusters_for_pair("ETHUSDT")
        cluster = evaluate_cluster_cap(
            pair="ETHUSDT",
            cluster_id=cluster_ids[0],
            current_exposure=50.0,
            candidate_size=50.0,
            cluster_cap=200.0,
        )
        assert cluster.verdict == ClusterCapVerdict.ACCEPTED

        drawdown = evaluate_drawdown_guard(
            current_equity=995.0,
            session_peak_equity=1000.0,
            warning_threshold_pct=0.02,
            observe_threshold_pct=0.04,
        )
        assert drawdown.verdict == DrawdownVerdict.ACCEPTED

    def test_drawdown_guard_blocks_even_when_other_caps_pass(self):
        gross = evaluate_gross_cap(
            pair="ETHUSDT",
            candidate_size=50.0,
            current_gross=100.0,
            position_cap=250.0,
            gross_cap=500.0,
            current_pair_exposure=0.0,
        )
        loss = evaluate_loss_cap(
            pair="ETHUSDT",
            candidate_loss=10.0,
            current_budget=20.0,
            loss_cap=100.0,
        )
        registry = ClusterRegistry()
        cluster = evaluate_cluster_cap(
            pair="ETHUSDT",
            cluster_id=registry.get_clusters_for_pair("ETHUSDT")[0],
            current_exposure=25.0,
            candidate_size=25.0,
            cluster_cap=200.0,
        )

        assert gross.verdict == GrossCapVerdict.ACCEPTED
        assert loss.verdict == LossCapVerdict.ACCEPTED
        assert cluster.verdict == ClusterCapVerdict.ACCEPTED

        drawdown = evaluate_drawdown_guard(
            current_equity=955.0,
            session_peak_equity=1000.0,
            warning_threshold_pct=0.02,
            observe_threshold_pct=0.04,
        )
        assert drawdown.verdict == DrawdownVerdict.OBSERVE_ONLY
