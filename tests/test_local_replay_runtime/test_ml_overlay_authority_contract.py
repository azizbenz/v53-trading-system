from __future__ import annotations

from local_replay_runtime.ml_overlay_authority_contract import (
    ML_CHANGE_SIDE_BLOCKED,
    ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED,
    ML_OVERRIDE_COST_INFEASIBLE_BLOCKED,
    ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED,
    MlAuthorityAction,
    MlOverlayAuthorityLevel,
    build_ml_overlay_authority_contract_report,
    evaluate_ml_authority_action,
)


def test_default_authority_contract_is_diagnostic_only() -> None:
    report = build_ml_overlay_authority_contract_report()

    assert report.ml_authority_level == MlOverlayAuthorityLevel.DIAGNOSTIC_ONLY
    assert report.ml_can_create_candidate is False
    assert report.ml_can_change_side is False
    assert report.ml_can_bypass_hard_blocks is False
    assert report.ml_can_veto is False


def test_ml_cannot_create_candidate_without_engine_candidate() -> None:
    decision = evaluate_ml_authority_action(MlAuthorityAction.CREATE_CANDIDATE)

    assert decision.allowed is False
    assert decision.blocker_reason == ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED


def test_ml_cannot_change_side() -> None:
    decision = evaluate_ml_authority_action(MlAuthorityAction.CHANGE_SIDE)

    assert decision.allowed is False
    assert decision.blocker_reason == ML_CHANGE_SIDE_BLOCKED


def test_ml_cannot_bypass_hard_blocks() -> None:
    decision = evaluate_ml_authority_action(MlAuthorityAction.BYPASS_HARD_BLOCK)

    assert decision.allowed is False
    assert decision.blocker_reason == ML_OVERRIDE_COST_INFEASIBLE_BLOCKED


def test_soft_veto_requires_authority_and_engine_candidate() -> None:
    blocked = evaluate_ml_authority_action(
        MlAuthorityAction.SOFT_VETO,
        authority_level=MlOverlayAuthorityLevel.RANKING_OVERLAY,
    )
    allowed = evaluate_ml_authority_action(
        MlAuthorityAction.SOFT_VETO,
        authority_level=MlOverlayAuthorityLevel.SOFT_VETO,
    )

    assert blocked.allowed is False
    assert allowed.allowed is True


def test_sizing_assist_after_hard_gates_still_requires_fill_realism() -> None:
    decision = evaluate_ml_authority_action(
        MlAuthorityAction.ADJUST_SIZE,
        authority_level=MlOverlayAuthorityLevel.SIZING_ASSIST,
        hard_gates_passed=True,
        fill_realism_proven=False,
    )

    assert decision.allowed is False
    assert decision.blocker_reason == ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED
