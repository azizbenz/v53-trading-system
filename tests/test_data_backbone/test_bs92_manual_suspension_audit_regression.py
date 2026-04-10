"""
BS-92 regression — SuspensionReason.MANUAL was never returned by evaluate_suspension.

Blind spot: MANUAL is defined in SuspensionReason but the only way to issue a manual
suspension was to construct SuspensionDecision(reason=SuspensionReason.MANUAL) directly,
bypassing any audit trail. The operator_id and reason text were never captured. The
critical intervention path (manual emergency suspension) was the least audited path.

Fix: add suspend_manual(pair, *, operator_id, reason_text) — a dedicated audited function
that requires both fields and embeds them in the audit message. Callers cannot omit them.
"""

from __future__ import annotations

import pytest

from data_backbone.pair_health_scorer.suspension_decider import (
    SuspensionDecision,
    SuspensionReason,
    suspend_manual,
)


pytestmark = pytest.mark.build2


class TestBS92ManualSuspension:

    def test_suspend_manual_sets_should_suspend_true(self):
        """BS-92: manual suspension must always produce should_suspend=True."""
        result = suspend_manual("BTCUSDT", operator_id="ops-1", reason_text="emergency halt")

        assert result.should_suspend is True

    def test_suspend_manual_sets_reason_manual(self):
        """BS-92: manual suspension must carry reason=MANUAL."""
        result = suspend_manual("BTCUSDT", operator_id="ops-1", reason_text="flash crash")

        assert result.reason == SuspensionReason.MANUAL

    def test_suspend_manual_embeds_operator_id_in_message(self):
        """BS-92: operator_id must appear in message for audit trail."""
        result = suspend_manual("ETHUSDT", operator_id="trader-42", reason_text="test")

        assert "trader-42" in result.message

    def test_suspend_manual_embeds_reason_text_in_message(self):
        """BS-92: reason_text must appear in message for audit trail."""
        result = suspend_manual("BTCUSDT", operator_id="ops-1", reason_text="liquidity collapse")

        assert "liquidity collapse" in result.message

    def test_suspend_manual_sets_correct_pair(self):
        """BS-92: pair must be correctly propagated."""
        result = suspend_manual("NEARUSDT", operator_id="ops-1", reason_text="halt")

        assert result.pair == "NEARUSDT"

    # --- Guard: both fields are required ---

    def test_suspend_manual_rejects_empty_operator_id(self):
        """BS-92: empty operator_id must be rejected — no anonymous suspensions."""
        with pytest.raises(ValueError, match="operator_id"):
            suspend_manual("BTCUSDT", operator_id="", reason_text="valid reason")

    def test_suspend_manual_rejects_empty_reason_text(self):
        """BS-92: empty reason_text must be rejected — suspension must be documented."""
        with pytest.raises(ValueError, match="reason_text"):
            suspend_manual("BTCUSDT", operator_id="ops-1", reason_text="")

    # --- Verify evaluate_suspension still does not return MANUAL ---

    def test_evaluate_suspension_never_returns_manual(self):
        """BS-92: evaluate_suspension must not return MANUAL — that is reserved for suspend_manual."""
        from data_backbone.pair_health_scorer.suspension_decider import evaluate_suspension

        for health, stale, consistency in [
            (0.1, False, False),
            (0.9, True, False),
            (0.9, False, True),
            (0.9, False, False),
        ]:
            result = evaluate_suspension(
                "BTCUSDT",
                health_score=health,
                threshold=0.3,
                hard_stale=stale,
                consistency_failed=consistency,
            )
            assert result.reason != SuspensionReason.MANUAL
