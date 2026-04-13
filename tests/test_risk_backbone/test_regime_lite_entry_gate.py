from regime_classifier import RegimeLiteAssessment, RegimeLiteState
from risk_backbone import (
    RiskRegimePrecheckInput,
    build_regime_lite_entry_gate,
)


def test_regime_lite_entry_gate_blocks_entries_during_extreme_cooldown():
    hook = build_regime_lite_entry_gate(
        RegimeLiteAssessment(
            state=RegimeLiteState.EXTREME,
            candidate_state=RegimeLiteState.EXTREME,
            state_entered_ts=10_000,
            entries_blocked_until_ts=96_400,
            entries_blocked=True,
            reason_codes=("RG_EXTREME_COOLDOWN_ACTIVE",),
        )
    )

    outcome = hook(
        RiskRegimePrecheckInput(
            context_id="ETHUSDT:engine-a:10",
            pair="ETHUSDT",
            engine_id="engine-a",
            size=10.0,
        )
    )

    assert outcome.accepted is False
    assert outcome.reason_codes == ("RISK_REGIME_EXTREME_COOLDOWN",)


def test_regime_lite_entry_gate_allows_entries_when_regime_is_not_blocked():
    hook = build_regime_lite_entry_gate(
        RegimeLiteAssessment(
            state=RegimeLiteState.STRESSED,
            candidate_state=RegimeLiteState.STRESSED,
            state_entered_ts=10_000,
            reason_codes=("RG_STRESSED_VOL_24H",),
        )
    )

    outcome = hook(
        RiskRegimePrecheckInput(
            context_id="ETHUSDT:engine-a:10",
            pair="ETHUSDT",
            engine_id="engine-a",
            size=10.0,
        )
    )

    assert outcome.accepted is True
    assert outcome.reason_codes == ()
