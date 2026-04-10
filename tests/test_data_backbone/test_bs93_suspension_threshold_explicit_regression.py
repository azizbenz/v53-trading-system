"""
BS-93 regression — evaluate_suspension hid a universal 0.3 threshold default.

Blind spot: the default `threshold=0.3` silently encoded one global liquidity/health
policy into every health-based suspension decision, even when the caller did not
select a pair-specific threshold. Only `hard_stale` and `consistency_failed` are
threshold-free suspension reasons.

Fix: require an explicit threshold for health-based decisions while keeping the
hard-stale and consistency-failed paths threshold-independent.
"""

from __future__ import annotations

import pytest

from data_backbone.pair_health_scorer.suspension_decider import (
    SuspensionReason,
    evaluate_suspension,
)


pytestmark = pytest.mark.build2


class TestBS93SuspensionThresholdExplicit:

    def test_health_path_requires_explicit_threshold(self):
        with pytest.raises(ValueError, match="threshold"):
            evaluate_suspension("BTCUSDT", health_score=0.25)

    def test_hard_stale_path_remains_threshold_free(self):
        result = evaluate_suspension("BTCUSDT", health_score=0.90, hard_stale=True)

        assert result.should_suspend is True
        assert result.reason == SuspensionReason.HARD_STALE
        assert result.threshold is None

    def test_consistency_failure_path_remains_threshold_free(self):
        result = evaluate_suspension("BTCUSDT", health_score=0.90, consistency_failed=True)

        assert result.should_suspend is True
        assert result.reason == SuspensionReason.CONSISTENCY_FAILURE
        assert result.threshold is None

    def test_explicit_threshold_keeps_health_based_suspend_behavior(self):
        result = evaluate_suspension("BTCUSDT", health_score=0.25, threshold=0.30)

        assert result.should_suspend is True
        assert result.reason == SuspensionReason.HEALTH_BELOW_THRESHOLD
        assert result.threshold == pytest.approx(0.30)
