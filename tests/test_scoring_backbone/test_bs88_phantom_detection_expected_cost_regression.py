"""
BS-88 regression — phantom detection silently disabled when expected_cost=0.0.

Blind spot: evaluate_penalty_cap used `is_phantom = effective_value <= expected_cost`.
When expected_cost=0.0 (the default), this reduces to `effective_value <= 0.0`, which
only triggers on zero-or-negative effective values. A genuinely unprofitable trade
(effective_value=0.05, expected_cost=0.10) would escape the phantom check because
0.05 <= 0.0 is False.

Fix: guard with `expected_cost > 0.0` before evaluating phantom condition.
When expected_cost is not provided (zero), phantom detection is skipped — the caller
has not supplied a cost baseline, so the comparison is meaningless.
"""

from __future__ import annotations

import pytest

from scoring_backbone.penalty_aggregator.penalty_cap_guard import (
    PenaltyCapVerdict,
    evaluate_penalty_cap,
)


class TestBS88PhantomDetectionExpectedCost:

    # --- Core BS-88 regression ---

    def test_zero_expected_cost_does_not_trigger_phantom(self):
        """BS-88: effective_value=0.05 with expected_cost=0.0 must NOT be PHANTOM_RISK.

        Before fix: 0.05 <= 0.0 is False → NORMAL (accidentally correct but wrong semantics).
        The real problem is a trade that earns less than it costs must be phantom,
        but we cannot determine that without a positive cost baseline.
        """
        result = evaluate_penalty_cap(
            score_penalty=2.8,
            size_multiplier=0.1,
            max_score_penalty=3.0,
            min_size_multiplier=0.05,
            raw_score=3.0,
            expected_cost=0.0,  # no cost baseline provided
        )
        # Without a positive expected_cost we cannot claim phantom — must be NORMAL or CAPPED
        assert result.verdict != PenaltyCapVerdict.PHANTOM_RISK

    def test_negative_expected_cost_does_not_trigger_phantom(self):
        """BS-88: negative expected_cost is also an invalid baseline — no phantom."""
        result = evaluate_penalty_cap(
            score_penalty=0.5,
            size_multiplier=0.9,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=1.0,
            expected_cost=-0.5,
        )
        assert result.verdict != PenaltyCapVerdict.PHANTOM_RISK

    def test_positive_expected_cost_triggers_phantom_when_unprofitable(self):
        """BS-88: with a real cost baseline, phantom detection must still work."""
        # adjusted = 3.0 - 2.8 = 0.2, effective = 0.2 * 0.1 = 0.02 <= 0.5 → PHANTOM
        result = evaluate_penalty_cap(
            score_penalty=2.8,
            size_multiplier=0.1,
            max_score_penalty=3.0,
            min_size_multiplier=0.05,
            raw_score=3.0,
            expected_cost=0.5,
        )
        assert result.verdict == PenaltyCapVerdict.PHANTOM_RISK

    def test_positive_expected_cost_no_phantom_when_profitable(self):
        """BS-88: profitable trade with positive expected_cost must be NORMAL."""
        # adjusted = 3.0 - 0.5 = 2.5, effective = 2.5 * 0.9 = 2.25 > 0.5 → not phantom
        result = evaluate_penalty_cap(
            score_penalty=0.5,
            size_multiplier=0.9,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=3.0,
            expected_cost=0.5,
        )
        assert result.verdict == PenaltyCapVerdict.NORMAL

    def test_default_expected_cost_is_zero(self):
        """BS-88: calling without expected_cost uses 0.0 — phantom check disabled."""
        # Any trade with raw_score > 0 and positive effective_value should not be phantom
        result = evaluate_penalty_cap(
            score_penalty=0.1,
            size_multiplier=0.9,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=1.0,
            # expected_cost omitted — defaults to 0.0
        )
        assert result.verdict == PenaltyCapVerdict.NORMAL

    # --- Boundary cases ---

    def test_exact_zero_effective_value_with_positive_cost_is_phantom(self):
        """effective_value=0.0 with expected_cost=0.1 must be PHANTOM_RISK."""
        # adjusted = 1.0 - 1.0 = 0.0, effective = 0.0 * 1.0 = 0.0 <= 0.1
        result = evaluate_penalty_cap(
            score_penalty=1.0,
            size_multiplier=1.0,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=1.0,
            expected_cost=0.1,
        )
        assert result.verdict == PenaltyCapVerdict.PHANTOM_RISK

    def test_exact_zero_effective_value_with_zero_cost_is_not_phantom(self):
        """effective_value=0.0, expected_cost=0.0 → no baseline, must not be PHANTOM_RISK."""
        result = evaluate_penalty_cap(
            score_penalty=1.0,
            size_multiplier=1.0,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=1.0,
            expected_cost=0.0,
        )
        # No positive cost baseline — cannot claim phantom
        assert result.verdict != PenaltyCapVerdict.PHANTOM_RISK

    def test_raw_score_zero_never_phantom(self):
        """BS-88: raw_score=0 means no signal — phantom guard must not trigger."""
        result = evaluate_penalty_cap(
            score_penalty=0.0,
            size_multiplier=1.0,
            max_score_penalty=2.0,
            min_size_multiplier=0.1,
            raw_score=0.0,
            expected_cost=0.5,
        )
        assert result.verdict != PenaltyCapVerdict.PHANTOM_RISK
