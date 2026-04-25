"""Typed regression tests for Build-8 portfolio arbitration records."""

from __future__ import annotations

from portfolio_minimal.arbitration_record import PortfolioArbitrationVerdict
from portfolio_minimal.portfolio_orchestrator import run_portfolio_pipeline

from ._portfolio_support import build_candidate, build_config


def test_promoted_candidate_carries_portfolio_arbitration_record() -> None:
    result = run_portfolio_pipeline(
        (
            build_candidate(
                pair="BTC/USDT",
                score=0.9,
                ce=0.12,
                cluster="btc_cluster",
                holding_hours=2.0,
            ),
            build_candidate(
                pair="ETH/USDT",
                score=0.4,
                ce=0.05,
                cluster="eth_cluster",
                holding_hours=6.0,
            ),
        ),
        build_config(),
    )
    promoted = result.report.allocations[0].arbitration_record
    assert promoted is not None
    assert promoted.verdict == PortfolioArbitrationVerdict.PROMOTED
    assert "portfolio.promoted" in promoted.reason_codes
    assert promoted.best_net_score.passed


def test_selection_rejections_produce_rejected_arbitration_records() -> None:
    result = run_portfolio_pipeline(
        (
            build_candidate(pair="BTC/USDT", cluster="btc_cluster"),
            build_candidate(pair="XRP/USDT", cluster=""),
            build_candidate(pair="ADA/USDT", cluster="unknown"),
        ),
        build_config(),
    )
    rejected = tuple(
        record
        for record in result.arbitration_records
        if record.verdict == PortfolioArbitrationVerdict.REJECTED_SELECTION
    )
    assert len(rejected) == 2
    assert all("portfolio_rejected" in record.reason_codes for record in rejected)


def test_phantom_candidate_produces_rejected_allocation_record() -> None:
    result = run_portfolio_pipeline(
        (
            build_candidate(
                pair="BTC/USDT",
                score=0.8,
                size=100.0,
                cluster="btc_cluster",
                beta_impact=0.5,
            ),
        ),
        build_config(beta_cap=0.01),
    )
    assert result.report.count_phantom == 1
    phantom = result.report.phantoms[0].arbitration_record
    assert phantom is not None
    assert phantom.verdict == PortfolioArbitrationVerdict.REJECTED_ALLOCATION
    assert "portfolio_rejected" in phantom.reason_codes
