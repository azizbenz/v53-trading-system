"""Canonical runtime composition for multiple artifact actions on the same hook."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from interface_contracts import (
    ActionUnit,
    ArtifactActionKind,
    ArtifactConflictPolicy,
    CANONICAL_ARTIFACT_CONFLICT_POLICY,
    DistilledRuleAction,
    HookId,
)


class ArtifactHookActionInput(BaseModel, frozen=True):
    """Single normalized artifact action to compose on a given runtime hook."""

    artifact_id: str = Field(..., min_length=1)
    hook_id: HookId
    rule_id: str = Field(..., min_length=1)
    action: DistilledRuleAction


class ComposedArtifactHookEffect(BaseModel, frozen=True):
    """Deterministic per-hook effect after canonical multi-artifact composition."""

    hook_id: HookId
    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    raw_score_multiplier_delta: float = 0.0
    raw_score_add: float = 0.0
    conviction_add: float = 0.0
    size_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    rank_delta: float = 0.0
    global_raw_score_cap: float | None = None
    contributing_artifact_ids: tuple[str, ...] = ()
    contributing_rule_ids: tuple[str, ...] = ()
    applied_action_count: int = Field(default=0, ge=0)


def compose_artifact_hook_actions(
    hook_id: HookId,
    actions: tuple[ArtifactHookActionInput, ...],
    *,
    conflict_policy: ArtifactConflictPolicy = CANONICAL_ARTIFACT_CONFLICT_POLICY,
) -> ComposedArtifactHookEffect:
    """Compose multiple actions for one hook using the canonical VPS policy."""

    if not actions:
        return ComposedArtifactHookEffect(hook_id=hook_id)

    artifact_ids: list[str] = []
    rule_ids: list[str] = []
    block_reason_codes: list[str] = []
    raw_score_multiplier_delta = 0.0
    raw_score_add = 0.0
    conviction_add = 0.0
    size_factor = 1.0
    rank_delta = 0.0
    raw_score_caps: list[float] = []

    for item in actions:
        if item.hook_id != hook_id:
            raise ValueError("compose_artifact_hook_actions requires a single hook_id")
        artifact_ids.append(item.artifact_id)
        rule_ids.append(item.rule_id)

        action = item.action
        action_value = float(action.action_value)
        if not math.isfinite(action_value):
            raise ValueError("artifact action_value must be finite")

        if action.action == conflict_policy.hard_veto_action:
            block_reason_codes.append(action.reason_code)
            continue

        if action.action in {ArtifactActionKind.SOFT_BOOST, ArtifactActionKind.SOFT_REDUCE}:
            if action_value < 0.0:
                raise ValueError("SOFT_BOOST/SOFT_REDUCE action_value must be >= 0")
            signed_value = action_value if action.action == ArtifactActionKind.SOFT_BOOST else -action_value
            if action.action_unit == ActionUnit.RAW_SCORE_MULTIPLIER:
                raw_score_multiplier_delta += signed_value
            elif action.action_unit == ActionUnit.RAW_SCORE_ADD:
                raw_score_add += signed_value
            elif action.action_unit == ActionUnit.CONVICTION_ADD:
                conviction_add += signed_value
            else:
                raise ValueError("unsupported score-oriented action_unit")
            if action.max_raw_score_cap is not None:
                raw_score_caps.append(float(action.max_raw_score_cap))
            continue

        if action.action == ArtifactActionKind.SIZE_REDUCE:
            if not 0.0 <= action_value <= 1.0:
                raise ValueError("SIZE_REDUCE action_value must stay within [0, 1]")
            size_factor = min(size_factor, action_value)
            continue

        if action.action == ArtifactActionKind.RANK_ADJUST:
            rank_delta += action_value
            continue

        raise ValueError(f"unsupported artifact action kind: {action.action}")

    if block_reason_codes:
        return ComposedArtifactHookEffect(
            hook_id=hook_id,
            blocked=True,
            block_reason_codes=tuple(block_reason_codes),
            size_factor=0.0,
            contributing_artifact_ids=tuple(artifact_ids),
            contributing_rule_ids=tuple(rule_ids),
            applied_action_count=len(actions),
        )

    return ComposedArtifactHookEffect(
        hook_id=hook_id,
        blocked=False,
        raw_score_multiplier_delta=raw_score_multiplier_delta,
        raw_score_add=raw_score_add,
        conviction_add=conviction_add,
        size_factor=size_factor,
        rank_delta=rank_delta,
        global_raw_score_cap=min(raw_score_caps) if raw_score_caps else None,
        contributing_artifact_ids=tuple(artifact_ids),
        contributing_rule_ids=tuple(rule_ids),
        applied_action_count=len(actions),
    )


__all__ = [
    "ArtifactHookActionInput",
    "ComposedArtifactHookEffect",
    "compose_artifact_hook_actions",
]
