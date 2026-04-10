"""
BS-89 regression — evaluate_gap_fill accepted negative gaps silently.

Blind spot: gap_size = gap_end - gap_start is computed but not validated for sign.
If gap_end < gap_start (clock reversal, inverted timestamps), gap_size is negative.
Condition `gap_size > max_gap_s` is False for any negative value → verdict FILL.
A REST fetch is triggered for a gap that does not exist in the correct time direction.

Fix: reject immediately when gap_size <= 0.0 with REJECT_TOO_LARGE verdict
and a message identifying the inversion.
"""

from __future__ import annotations

import pytest

from data_backbone.rest_bootstrap.gap_fill_controller import GapFillDecision, evaluate_gap_fill


pytestmark = pytest.mark.build2


class TestBS89GapFillNegativeGap:

    def test_negative_gap_is_rejected(self):
        """BS-89: gap_end < gap_start (clock reversal) must be rejected, not filled."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=1000.0, gap_end=500.0, max_gap_s=300.0)

        assert result.decision == GapFillDecision.REJECT_TOO_LARGE

    def test_negative_gap_message_identifies_inversion(self):
        """BS-89: rejection message must name the inversion, not just 'too large'."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=2000.0, gap_end=1000.0)

        assert "non-positive" in result.message or "clock" in result.message or "inverted" in result.message

    def test_zero_gap_is_rejected(self):
        """BS-89: gap_start == gap_end → zero-size gap must be rejected."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=1000.0, gap_end=1000.0)

        assert result.decision == GapFillDecision.REJECT_TOO_LARGE

    def test_large_negative_gap_is_rejected(self):
        """BS-89: deeply inverted timestamps must be rejected regardless of max_gap_s."""
        result = evaluate_gap_fill(
            "BTCUSDT", gap_start=9_999_999.0, gap_end=0.0, max_gap_s=999_999_999.0
        )

        assert result.decision == GapFillDecision.REJECT_TOO_LARGE

    def test_negative_gap_request_records_correct_gap_size(self):
        """BS-89: gap_size_s in request must reflect the actual (negative) computed size."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=500.0, gap_end=200.0)

        assert result.request.gap_size_s == pytest.approx(-300.0)

    def test_small_positive_gap_still_fills(self):
        """BS-89: normal positive gap must not be affected by the fix."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=100.0, gap_end=200.0, max_gap_s=300.0)

        assert result.decision == GapFillDecision.FILL

    def test_positive_gap_at_boundary_fills(self):
        """BS-89: gap exactly equal to max_gap_s must still fill (> check, not >=)."""
        result = evaluate_gap_fill("BTCUSDT", gap_start=0.0, gap_end=300.0, max_gap_s=300.0)

        assert result.decision == GapFillDecision.FILL

    def test_rate_limited_positive_gap_still_rejected(self):
        """BS-89: rate-limit path for positive gaps must be unaffected."""
        result = evaluate_gap_fill(
            "BTCUSDT", gap_start=100.0, gap_end=200.0, max_gap_s=300.0, rate_limited=True
        )

        assert result.decision == GapFillDecision.REJECT_RATE_LIMITED
