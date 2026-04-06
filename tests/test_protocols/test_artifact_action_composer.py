from __future__ import annotations

import pytest

from interface_contracts import (
    ActionUnit,
    ArtifactActionKind,
    DistilledRuleAction,
    HookId,
)
from protocols import (
    ArtifactHookActionInput,
    compose_artifact_hook_actions,
)


def _rule_action(
    *,
    action: ArtifactActionKind,
    action_value: float,
    action_unit: ActionUnit | None,
    reason_code: str,
    max_raw_score_cap: float | None = None,
) -> DistilledRuleAction:
    return DistilledRuleAction(
        action=action,
        action_value=action_value,
        action_unit=action_unit,
        max_raw_score_cap=max_raw_score_cap,
        reason_code=reason_code,
    )


def test_compose_artifact_hook_actions_no_trade_wins_over_other_actions():
    effect = compose_artifact_hook_actions(
        HookId.ENGINE_B_SWEEP_VALIDATION,
        (
            ArtifactHookActionInput(
                artifact_id="art-1",
                hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                rule_id="rule-1",
                action=_rule_action(
                    action=ArtifactActionKind.SOFT_BOOST,
                    action_value=0.15,
                    action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                    max_raw_score_cap=2.5,
                    reason_code="BOOST",
                ),
            ),
            ArtifactHookActionInput(
                artifact_id="art-2",
                hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                rule_id="rule-2",
                action=_rule_action(
                    action=ArtifactActionKind.NO_TRADE,
                    action_value=0.0,
                    action_unit=None,
                    reason_code="TOXICITY_BLOCK",
                ),
            ),
        ),
    )

    assert effect.blocked is True
    assert effect.block_reason_codes == ("TOXICITY_BLOCK",)
    assert effect.size_factor == pytest.approx(0.0)
    assert effect.raw_score_multiplier_delta == pytest.approx(0.0)


def test_compose_artifact_hook_actions_adds_score_actions_and_uses_strictest_cap():
    effect = compose_artifact_hook_actions(
        HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        (
            ArtifactHookActionInput(
                artifact_id="art-1",
                hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                rule_id="rule-1",
                action=_rule_action(
                    action=ArtifactActionKind.SOFT_BOOST,
                    action_value=0.20,
                    action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                    max_raw_score_cap=2.5,
                    reason_code="BOOST_A",
                ),
            ),
            ArtifactHookActionInput(
                artifact_id="art-2",
                hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                rule_id="rule-2",
                action=_rule_action(
                    action=ArtifactActionKind.SOFT_REDUCE,
                    action_value=0.05,
                    action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                    max_raw_score_cap=1.8,
                    reason_code="REDUCE_A",
                ),
            ),
            ArtifactHookActionInput(
                artifact_id="art-3",
                hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                rule_id="rule-3",
                action=_rule_action(
                    action=ArtifactActionKind.SOFT_BOOST,
                    action_value=0.12,
                    action_unit=ActionUnit.RAW_SCORE_ADD,
                    reason_code="BOOST_ADD",
                ),
            ),
        ),
    )

    assert effect.blocked is False
    assert effect.raw_score_multiplier_delta == pytest.approx(0.15)
    assert effect.raw_score_add == pytest.approx(0.12)
    assert effect.global_raw_score_cap == pytest.approx(1.8)


def test_compose_artifact_hook_actions_uses_min_factor_for_size_reduce_and_sums_rank_delta():
    effect = compose_artifact_hook_actions(
        HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
        (
            ArtifactHookActionInput(
                artifact_id="art-1",
                hook_id=HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
                rule_id="rule-1",
                action=_rule_action(
                    action=ArtifactActionKind.SIZE_REDUCE,
                    action_value=0.75,
                    action_unit=ActionUnit.SIZE_FACTOR,
                    reason_code="SIZE_1",
                ),
            ),
            ArtifactHookActionInput(
                artifact_id="art-2",
                hook_id=HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
                rule_id="rule-2",
                action=_rule_action(
                    action=ArtifactActionKind.SIZE_REDUCE,
                    action_value=0.60,
                    action_unit=ActionUnit.SIZE_FACTOR,
                    reason_code="SIZE_2",
                ),
            ),
            ArtifactHookActionInput(
                artifact_id="art-3",
                hook_id=HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
                rule_id="rule-3",
                action=_rule_action(
                    action=ArtifactActionKind.RANK_ADJUST,
                    action_value=-1.5,
                    action_unit=ActionUnit.RANK_DELTA,
                    reason_code="RANK_DOWN",
                ),
            ),
        ),
    )

    assert effect.size_factor == pytest.approx(0.60)
    assert effect.rank_delta == pytest.approx(-1.5)


def test_compose_artifact_hook_actions_rejects_mixed_hook_ids():
    with pytest.raises(ValueError):
        compose_artifact_hook_actions(
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
            (
                ArtifactHookActionInput(
                    artifact_id="art-1",
                    hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                    rule_id="rule-1",
                    action=_rule_action(
                        action=ArtifactActionKind.SOFT_BOOST,
                        action_value=0.15,
                        action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                        reason_code="BOOST",
                    ),
                ),
                ArtifactHookActionInput(
                    artifact_id="art-2",
                    hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                    rule_id="rule-2",
                    action=_rule_action(
                        action=ArtifactActionKind.SOFT_BOOST,
                        action_value=0.10,
                        action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                        reason_code="BOOST_2",
                    ),
                ),
            ),
        )


def test_compose_artifact_hook_actions_rejects_invalid_size_reduce_factor():
    with pytest.raises(ValueError):
        compose_artifact_hook_actions(
            HookId.EXECUTION_NO_TRADE_FILTER,
            (
                ArtifactHookActionInput(
                    artifact_id="art-1",
                    hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                    rule_id="rule-1",
                    action=_rule_action(
                        action=ArtifactActionKind.SIZE_REDUCE,
                        action_value=1.2,
                        action_unit=ActionUnit.SIZE_FACTOR,
                        reason_code="BAD_SIZE",
                    ),
                ),
            ),
        )
