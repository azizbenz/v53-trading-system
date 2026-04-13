from interface_contracts import OperatorSafingAction, RuntimeMode
from regime_classifier import RegimeLiteAssessment, RegimeLiteState
from risk_backbone import (
    RegimeLiteSafingSeverity,
    build_regime_lite_safing_recommendation,
)


def test_regime_lite_safing_recommends_halt_and_exit_all_when_extreme():
    recommendation = build_regime_lite_safing_recommendation(
        RegimeLiteAssessment(
            state=RegimeLiteState.EXTREME,
            candidate_state=RegimeLiteState.EXTREME,
            state_entered_ts=10_000,
            reason_codes=("RG_EXTREME_BTC_DROP_1H",),
        ),
        source_runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_726_000_000_000,
    )

    assert recommendation.severity == RegimeLiteSafingSeverity.HALT_RECOMMENDED
    assert recommendation.should_block_new_entries is True
    assert recommendation.should_exit_all is True
    assert recommendation.recommended_operator_action == OperatorSafingAction.SET_HALTED
    assert recommendation.operator_safing_request is not None
    assert recommendation.operator_safing_request.action == OperatorSafingAction.SET_HALTED
    assert recommendation.operator_safing_request.source_runtime_mode == RuntimeMode.SHADOW


def test_regime_lite_safing_keeps_entry_block_only_during_cooldown():
    recommendation = build_regime_lite_safing_recommendation(
        RegimeLiteAssessment(
            state=RegimeLiteState.STRESSED,
            candidate_state=RegimeLiteState.CALM,
            state_entered_ts=10_000,
            entries_blocked_until_ts=96_400,
            entries_blocked=True,
            reason_codes=("RG_EXTREME_COOLDOWN_ACTIVE",),
        ),
        source_runtime_mode=RuntimeMode.MICRO_LIVE,
        timestamp_ms=1_726_000_000_000,
    )

    assert recommendation.severity == RegimeLiteSafingSeverity.ENTRY_BLOCK_ONLY
    assert recommendation.should_block_new_entries is True
    assert recommendation.should_exit_all is False
    assert recommendation.recommended_operator_action is None
    assert recommendation.operator_safing_request is None
