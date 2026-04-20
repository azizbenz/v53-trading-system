"""
Regression tests — BS-104
entry_price=0.0 must NOT raise Pydantic ValidationError.
Engine D must return NO_TRADE with INVALID_ENTRY_PRICE.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.engine_d import EngineDDecision, EngineDInput, run_engine_d
from engines.engine_d.engine_d_runner import NoTradeReasonD


def _base_inputs(**overrides: float | str) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=1.8 / 104.0,
        atr=1.8,
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def test_entry_price_zero_returns_no_trade_not_exception() -> None:
    """BS-104: entry_price=0.0 must NOT raise ValidationError."""
    result = run_engine_d(_base_inputs(entry_price=0.0))
    assert result.decision == EngineDDecision.NO_TRADE
    assert NoTradeReasonD.INVALID_ENTRY_PRICE in result.no_trade_reasons


def test_entry_price_negative_returns_no_trade_not_exception() -> None:
    """Negative entry_price is also invalid — must not reach invalidation builder."""
    result = run_engine_d(_base_inputs(entry_price=-1.0))
    assert result.decision == EngineDDecision.NO_TRADE
    assert NoTradeReasonD.INVALID_ENTRY_PRICE in result.no_trade_reasons


def test_entry_price_zero_produces_log_entry() -> None:
    """Log entry must be present explaining the rejection."""
    result = run_engine_d(_base_inputs(entry_price=0.0))
    assert len(result.log_entries) >= 1
    no_trade_log = next(
        (e for e in result.log_entries if e.event == "engine_d_no_trade"), None
    )
    assert no_trade_log is not None
    assert "entry_price" in no_trade_log.reasons[0]


def test_valid_entry_price_still_emits() -> None:
    """Regression: a valid entry_price must still reach EMIT."""
    result = run_engine_d(_base_inputs(entry_price=104.0))
    assert result.decision == EngineDDecision.EMIT


def test_entry_price_zero_never_raises_validation_error() -> None:
    """Core contract: ValidationError must never escape run_engine_d."""
    try:
        run_engine_d(_base_inputs(entry_price=0.0))
    except ValidationError as exc:
        pytest.fail(f"ValidationError escaped run_engine_d: {exc}")
