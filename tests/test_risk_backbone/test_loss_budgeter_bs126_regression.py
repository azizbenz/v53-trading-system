"""
Regression tests — BS-126
stop_price=0.0 must raise ValueError (was silently accepted before fix).
stop_price=0.0 would produce loss_pct=1.0 (100% loss guarantee).
"""
from __future__ import annotations

import pytest

from risk_backbone.loss_budgeter.position_loss_estimator import estimate_position_loss


def test_stop_price_zero_raises():
    """BS-126: stop_price=0.0 must be rejected — was silently accepted before."""
    with pytest.raises(ValueError, match="stop_price must be positive"):
        estimate_position_loss(
            pair="BTCUSDT",
            engine_id="engine_a",
            size=1000.0,
            entry_price=50000.0,
            stop_price=0.0,
        )


def test_stop_price_negative_still_raises():
    """Pre-existing behaviour preserved: negative stop must also raise."""
    with pytest.raises(ValueError):
        estimate_position_loss(
            pair="BTCUSDT",
            engine_id="engine_a",
            size=1000.0,
            entry_price=50000.0,
            stop_price=-100.0,
        )


def test_stop_price_small_positive_accepted():
    """A small but positive stop_price is valid (e.g., micro-cap at 0.0001)."""
    result = estimate_position_loss(
        pair="XRPUSDT",
        engine_id="engine_b",
        size=500.0,
        entry_price=0.50,
        stop_price=0.0001,
    )
    assert result.loss_amount > 0.0
    assert result.loss_pct < 1.0


def test_stop_price_one_accepted():
    """Sanity: normal stop_price=1.0 on entry=100.0 must work."""
    result = estimate_position_loss(
        pair="BTCUSDT",
        engine_id="engine_a",
        size=100.0,
        entry_price=100.0,
        stop_price=95.0,
    )
    assert result.loss_pct == pytest.approx(0.05)
    assert result.loss_amount == pytest.approx(5.0)
