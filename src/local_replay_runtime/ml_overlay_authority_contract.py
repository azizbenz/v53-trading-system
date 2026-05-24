"""Authority contract for the Strategy Ladder governed ML overlay."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


ML_OVERLAY_AUTHORITY_CONTRACT_REPORT_FILENAME = (
    "ml_overlay_authority_contract_report.json"
)

ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED = (
    "ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED"
)
ML_OVERRIDE_SHARIA_BLOCKED = "ML_OVERRIDE_SHARIA_BLOCKED"
ML_OVERRIDE_COST_INFEASIBLE_BLOCKED = "ML_OVERRIDE_COST_INFEASIBLE_BLOCKED"
ML_OVERRIDE_EXPECTED_EDGE_PROXY_BLOCKED = "ML_OVERRIDE_EXPECTED_EDGE_PROXY_BLOCKED"
ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED = (
    "ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED"
)
ML_CHANGE_SIDE_BLOCKED = "ML_CHANGE_SIDE_BLOCKED"
ML_ARTIFACT_FEATURE_CONTRACT_MISMATCH_BLOCKED = (
    "ML_ARTIFACT_FEATURE_CONTRACT_MISMATCH_BLOCKED"
)


class MlOverlayAuthorityLevel(StrEnum):
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    RANKING_OVERLAY = "RANKING_OVERLAY"
    SOFT_VETO = "SOFT_VETO"
    SIZING_ASSIST = "SIZING_ASSIST"


class MlAuthorityAction(StrEnum):
    CREATE_CANDIDATE = "CREATE_CANDIDATE"
    CHANGE_SIDE = "CHANGE_SIDE"
    BYPASS_HARD_BLOCK = "BYPASS_HARD_BLOCK"
    SOFT_VETO = "SOFT_VETO"
    ADJUST_SIZE = "ADJUST_SIZE"
    RANK_CANDIDATE = "RANK_CANDIDATE"
    DIAGNOSTIC_SCORE = "DIAGNOSTIC_SCORE"


class MlAuthorityDecision(BaseModel, frozen=True):
    action: MlAuthorityAction
    allowed: bool = False
    blocker_reason: str = ""


class MlOverlayAuthorityContractReport(BaseModel, frozen=True):
    schema_version: str = "ml_overlay.authority_contract.v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    status: str = "ML_OVERLAY_AUTHORITY_CONTRACT_OK"
    ml_authority_level: MlOverlayAuthorityLevel = MlOverlayAuthorityLevel.DIAGNOSTIC_ONLY
    ml_can_create_candidate: bool = False
    ml_can_change_side: bool = False
    ml_can_bypass_hard_blocks: bool = False
    ml_can_veto: bool = False
    ml_can_adjust_size_after_hard_gates: bool = False
    hard_blockers_enforced: tuple[str, ...] = (
        "SHARIA",
        "SPOT_ONLY",
        "NO_SHORT",
        "COST_INFEASIBLE",
        "EXPECTED_EDGE_PROXY_BLOCKED",
        "FILL_REALISM_NOT_PROVEN",
    )
    blocked_override_reason_codes: tuple[str, ...] = (
        ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED,
        ML_OVERRIDE_SHARIA_BLOCKED,
        ML_OVERRIDE_COST_INFEASIBLE_BLOCKED,
        ML_OVERRIDE_EXPECTED_EDGE_PROXY_BLOCKED,
        ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED,
        ML_CHANGE_SIDE_BLOCKED,
        ML_ARTIFACT_FEATURE_CONTRACT_MISMATCH_BLOCKED,
    )


def build_ml_overlay_authority_contract_report(
    *,
    authority_level: MlOverlayAuthorityLevel | str = MlOverlayAuthorityLevel.DIAGNOSTIC_ONLY,
) -> MlOverlayAuthorityContractReport:
    level = MlOverlayAuthorityLevel(str(authority_level))
    return MlOverlayAuthorityContractReport(
        ml_authority_level=level,
        ml_can_veto=level in {
            MlOverlayAuthorityLevel.SOFT_VETO,
            MlOverlayAuthorityLevel.SIZING_ASSIST,
        },
        ml_can_adjust_size_after_hard_gates=level
        == MlOverlayAuthorityLevel.SIZING_ASSIST,
    )


def evaluate_ml_authority_action(
    action: MlAuthorityAction | str,
    *,
    authority_level: MlOverlayAuthorityLevel | str = MlOverlayAuthorityLevel.DIAGNOSTIC_ONLY,
    engine_candidate_present: bool = True,
    hard_gates_passed: bool = True,
    fill_realism_proven: bool = True,
) -> MlAuthorityDecision:
    resolved_action = MlAuthorityAction(str(action))
    level = MlOverlayAuthorityLevel(str(authority_level))
    if resolved_action == MlAuthorityAction.DIAGNOSTIC_SCORE:
        return MlAuthorityDecision(action=resolved_action, allowed=True)
    if resolved_action == MlAuthorityAction.RANK_CANDIDATE:
        if level in {
            MlOverlayAuthorityLevel.RANKING_OVERLAY,
            MlOverlayAuthorityLevel.SOFT_VETO,
            MlOverlayAuthorityLevel.SIZING_ASSIST,
        }:
            return MlAuthorityDecision(action=resolved_action, allowed=True)
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason="ML_RANKING_REQUIRES_RANKING_OVERLAY_AUTHORITY",
        )
    if resolved_action == MlAuthorityAction.CREATE_CANDIDATE:
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason=ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED,
        )
    if resolved_action == MlAuthorityAction.CHANGE_SIDE:
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason=ML_CHANGE_SIDE_BLOCKED,
        )
    if resolved_action == MlAuthorityAction.BYPASS_HARD_BLOCK:
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason=ML_OVERRIDE_COST_INFEASIBLE_BLOCKED,
        )
    if resolved_action == MlAuthorityAction.SOFT_VETO:
        if not engine_candidate_present:
            return MlAuthorityDecision(
                action=resolved_action,
                blocker_reason=ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED,
            )
        if level in {
            MlOverlayAuthorityLevel.SOFT_VETO,
            MlOverlayAuthorityLevel.SIZING_ASSIST,
        }:
            return MlAuthorityDecision(action=resolved_action, allowed=True)
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason="ML_SOFT_VETO_REQUIRES_SOFT_VETO_AUTHORITY",
        )
    if resolved_action == MlAuthorityAction.ADJUST_SIZE:
        if not hard_gates_passed:
            return MlAuthorityDecision(
                action=resolved_action,
                blocker_reason=ML_OVERRIDE_COST_INFEASIBLE_BLOCKED,
            )
        if not fill_realism_proven:
            return MlAuthorityDecision(
                action=resolved_action,
                blocker_reason=ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED,
            )
        if level == MlOverlayAuthorityLevel.SIZING_ASSIST:
            return MlAuthorityDecision(action=resolved_action, allowed=True)
        return MlAuthorityDecision(
            action=resolved_action,
            blocker_reason="ML_SIZING_REQUIRES_SIZING_ASSIST_AUTHORITY",
        )
    return MlAuthorityDecision(
        action=resolved_action,
        blocker_reason="ML_AUTHORITY_ACTION_UNKNOWN_BLOCKED",
    )


def write_ml_overlay_authority_contract_report(
    path: Path,
    report: MlOverlayAuthorityContractReport,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, report.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "ML_ARTIFACT_FEATURE_CONTRACT_MISMATCH_BLOCKED",
    "ML_CHANGE_SIDE_BLOCKED",
    "ML_CREATE_TRADE_WITHOUT_ENGINE_CANDIDATE_BLOCKED",
    "ML_OVERLAY_AUTHORITY_CONTRACT_REPORT_FILENAME",
    "ML_OVERRIDE_COST_INFEASIBLE_BLOCKED",
    "ML_OVERRIDE_EXPECTED_EDGE_PROXY_BLOCKED",
    "ML_OVERRIDE_FILL_REALISM_NOT_PROVEN_BLOCKED",
    "ML_OVERRIDE_SHARIA_BLOCKED",
    "MlAuthorityAction",
    "MlAuthorityDecision",
    "MlOverlayAuthorityContractReport",
    "MlOverlayAuthorityLevel",
    "build_ml_overlay_authority_contract_report",
    "evaluate_ml_authority_action",
    "write_ml_overlay_authority_contract_report",
]
