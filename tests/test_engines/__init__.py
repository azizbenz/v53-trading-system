"""
BS-86 regression â€” EngineXRuntimeInput.timestamp_ms lacked the millisecond range constraint.

Blind spot: all four EngineXRuntimeInput models defined `timestamp_ms: int` with no
lower-bound guard. Passing a Unix timestamp in *seconds* (e.g. 1_700_000_000) instead
of *milliseconds* (e.g. 1_700_000_000_000) silently produced a ~year-1970 `now` value
inside `_resolve_runtime_now`, corrupting every time-dependent guard downstream.

Fix: `timestamp_ms: int = Field(..., ge=1_000_000_000_000)` on all four models,
matching the constraint on `TimestampedModel.timestamp_ms` in `interface_contracts`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.engine_a import EngineARuntimeInput
from engines.engine_b import EngineBRuntimeInput
from engines.engine_c import EngineCRuntimeInput
from engines.engine_d import EngineDRuntimeInput
from engines.engine_a.engine_a_runner import EngineAInput
from engines.engine_b.engine_b_runner import EngineBInput
from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_d.engine_d_runner import EngineDInput
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState


_VALID_TIMESTAMP_MS = 1_700_000_000_000   # Nov 2023 in milliseconds
_SECONDS_TIMESTAMP = 1_700_000_000        # same instant in *seconds* â€” must be rejected


def _portfolio() -> PortfolioState:
    return PortfolioState(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )


def _engine_a_inputs() -> EngineAInput:
    return EngineAInput(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.9,
        structure_quality=0.85,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.9,
        regime_confidence=0.8,
        pair_health=0.9,
        data_freshness=0.95,
        flow_coherence=0.8,
        flow_score=0.4,
        cost_preference_score=0.5,
        expected_gain=0.005,
        expected_cost=0.001,
        candidate_size=1000.0,
        holding_period=4.0,
        entry_price=50000.0,
        atr=500.0,
        scoring_version="v1.0",
    )


def _engine_b_inputs() -> EngineBInput:
    return EngineBInput(
        pair="BTCUSDT",
        current_price=97.0,
        local_mean=100.0,
        local_std=1.5,
        structure_is_range=0.7,
        recent_expansion=0.1,
        regime="range",
        regime_trend_strength=0.1,
        volume_anomaly=0.1,
        structural_break=0.0,
        continuation_momentum=0.1,
        microstructure_breakout_confirmation=0.0,
        regime_favorability=0.7,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        expected_gain=0.003,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=2.0,
        scoring_version="B_v1",
    )


def _engine_c_inputs() -> EngineCInput:
    return EngineCInput(
        pair="BTCUSDT",
        breakout_strength=0.88,
        range_quality=0.78,
        compression_quality=0.74,
        volume_confirmation=0.81,
        followthrough_room=0.76,
        extension_pct=0.24,
        retrace_risk=0.18,
        rejection_wick_ratio=0.12,
        regime="breakout",
        regime_favorability=0.80,
        pair_health=0.92,
        data_freshness=0.95,
        flow_coherence=0.79,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        atr=2.0,
        engine_a_overlap_ratio=0.28,
        marginal_portfolio_gain=9.2,
        covered_share_by_engine_a=0.22,
        keff_contribution=0.31,
        scoring_version="engine_c.v1",
    )


def _engine_d_inputs() -> EngineDInput:
    return EngineDInput(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        structure_reformed_detected=True,
        regime="trending_up",
        regime_favorability=0.78,
        pair_health=0.90,
        data_freshness=0.94,
        flow_coherence=0.81,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )


def _base_kwargs(engine_inputs, timestamp_ms: int) -> dict:
    return dict(
        engine_inputs=engine_inputs,
        timestamp_ms=timestamp_ms,
        portfolio=_portfolio(),
        projected_size=1000.0,
        projected_loss=50.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.8,
        cluster_id="btc_majors",
    )


class TestBS86TimestampMsUnitConstraint:
    # --- Engine A ---

    def test_engine_a_rejects_seconds_timestamp(self):
        """BS-86: EngineARuntimeInput must reject Unix seconds (< 1e12)."""
        with pytest.raises(ValidationError):
            EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), _SECONDS_TIMESTAMP))

    def test_engine_a_accepts_milliseconds_timestamp(self):
        """BS-86: EngineARuntimeInput must accept a valid millisecond timestamp."""
        inp = EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), _VALID_TIMESTAMP_MS))
        assert inp.timestamp_ms == _VALID_TIMESTAMP_MS

    # --- Engine B ---

    def test_engine_b_rejects_seconds_timestamp(self):
        """BS-86: EngineBRuntimeInput must reject Unix seconds (< 1e12)."""
        with pytest.raises(ValidationError):
            EngineBRuntimeInput(**_base_kwargs(_engine_b_inputs(), _SECONDS_TIMESTAMP))

    def test_engine_b_accepts_milliseconds_timestamp(self):
        """BS-86: EngineBRuntimeInput must accept a valid millisecond timestamp."""
        inp = EngineBRuntimeInput(**_base_kwargs(_engine_b_inputs(), _VALID_TIMESTAMP_MS))
        assert inp.timestamp_ms == _VALID_TIMESTAMP_MS

    # --- Engine C ---

    def test_engine_c_rejects_seconds_timestamp(self):
        """BS-86: EngineCRuntimeInput must reject Unix seconds (< 1e12)."""
        with pytest.raises(ValidationError):
            EngineCRuntimeInput(**_base_kwargs(_engine_c_inputs(), _SECONDS_TIMESTAMP))

    def test_engine_c_accepts_milliseconds_timestamp(self):
        """BS-86: EngineCRuntimeInput must accept a valid millisecond timestamp."""
        inp = EngineCRuntimeInput(**_base_kwargs(_engine_c_inputs(), _VALID_TIMESTAMP_MS))
        assert inp.timestamp_ms == _VALID_TIMESTAMP_MS

    # --- Engine D ---

    def test_engine_d_rejects_seconds_timestamp(self):
        """BS-86: EngineDRuntimeInput must reject Unix seconds (< 1e12)."""
        with pytest.raises(ValidationError):
            EngineDRuntimeInput(**_base_kwargs(_engine_d_inputs(), _SECONDS_TIMESTAMP))

    def test_engine_d_accepts_milliseconds_timestamp(self):
        """BS-86: EngineDRuntimeInput must accept a valid millisecond timestamp."""
        inp = EngineDRuntimeInput(**_base_kwargs(_engine_d_inputs(), _VALID_TIMESTAMP_MS))
        assert inp.timestamp_ms == _VALID_TIMESTAMP_MS

    # --- Zero / negative boundary ---

    def test_engine_a_rejects_zero_timestamp(self):
        """Zero is also below the millisecond threshold â€” must be rejected."""
        with pytest.raises(ValidationError):
            EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), 0))

    def test_engine_a_rejects_negative_timestamp(self):
        """Negative timestamp must be rejected."""
        with pytest.raises(ValidationError):
            EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), -1_700_000_000_000))

    def test_engine_a_rejects_boundary_below_ms(self):
        """999_999_999_999 is one below the threshold â€” must be rejected."""
        with pytest.raises(ValidationError):
            EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), 999_999_999_999))

    def test_engine_a_accepts_exact_threshold(self):
        """1_000_000_000_000 is the exact lower bound â€” must be accepted."""
        inp = EngineARuntimeInput(**_base_kwargs(_engine_a_inputs(), 1_000_000_000_000))
        assert inp.timestamp_ms == 1_000_000_000_000
