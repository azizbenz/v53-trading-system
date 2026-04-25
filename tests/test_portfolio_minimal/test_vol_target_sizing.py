"""Typed regression tests for Build-8 Carver-style vol-target sizing."""

from __future__ import annotations

import math

import pytest

from portfolio_minimal.allocation_router.vol_target_sizer import (
    VolTargetCandidateInput,
    VolTargetProfile,
    compute_vol_target_size,
)
from portfolio_minimal.portfolio_orchestrator import run_portfolio_pipeline

from ._portfolio_support import build_candidate, build_config


def test_compute_vol_target_size_matches_formula() -> None:
    result = compute_vol_target_size(
        VolTargetCandidateInput(
            pair="BTC/USDT",
            available_capital=10_000.0,
            forecast_strength=10.0,
            instrument_price=100.0,
            instrument_pct_vol=0.01,
        ),
        VolTargetProfile(annual_vol_target=0.16),
    )
    expected_daily_cash_vol_target = (10_000.0 * 0.16) / math.sqrt(252)
    assert result.instrument_value_vol == pytest.approx(1.0)
    assert result.daily_cash_vol_target == pytest.approx(expected_daily_cash_vol_target)
    assert result.vol_scalar == pytest.approx(expected_daily_cash_vol_target)
    assert result.position_size == pytest.approx(expected_daily_cash_vol_target)


def test_compute_vol_target_size_scales_with_forecast_strength() -> None:
    full = compute_vol_target_size(
        VolTargetCandidateInput(
            pair="BTC/USDT",
            available_capital=10_000.0,
            forecast_strength=10.0,
            instrument_price=100.0,
            instrument_pct_vol=0.01,
        ),
        VolTargetProfile(annual_vol_target=0.16),
    )
    half = compute_vol_target_size(
        VolTargetCandidateInput(
            pair="BTC/USDT",
            available_capital=10_000.0,
            forecast_strength=5.0,
            instrument_price=100.0,
            instrument_pct_vol=0.01,
        ),
        VolTargetProfile(annual_vol_target=0.16),
    )
    assert half.position_size == pytest.approx(full.position_size / 2.0)


def test_compute_vol_target_size_clips_when_max_position_set() -> None:
    result = compute_vol_target_size(
        VolTargetCandidateInput(
            pair="BTC/USDT",
            available_capital=10_000.0,
            forecast_strength=20.0,
            instrument_price=100.0,
            instrument_pct_vol=0.01,
        ),
        VolTargetProfile(
            annual_vol_target=0.16,
            max_position_size=50.0,
        ),
    )
    assert result.was_clipped
    assert result.position_size == 50.0


def test_orchestrator_uses_vol_target_sizing_when_profile_and_features_exist() -> None:
    result = run_portfolio_pipeline(
        (
            build_candidate(
                pair="BTC/USDT",
                cluster="btc_cluster",
                forecast_strength=10.0,
                instrument_price=100.0,
                instrument_pct_vol=0.01,
            ),
        ),
        build_config(
            capital=10_000.0,
            vol_target_profile=VolTargetProfile(annual_vol_target=0.16),
        ),
    )
    assert result.report.count_allocated == 1
    assert result.report.allocations[0].sizing_method == "carver_vol_target"
    assert result.report.allocations[0].vol_target_position_size is not None

