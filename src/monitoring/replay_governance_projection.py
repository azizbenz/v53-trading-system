"""Lower-layer replay governance projection shared by cockpit and protocols."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReplayGovernanceGateProjection(BaseModel, frozen=True):
    """Read-only gate summary for replay/backtest readiness."""

    gate_name: str
    passed: bool
    profile: str
    consecutive_days: int
    required_days: int = 30
    remaining_days: int
    total_resets: int = 0
    message: str = ""


def _default_gate(*, gate_name: str) -> "ReplayGovernanceGateProjection":
    return ReplayGovernanceGateProjection(
        gate_name=gate_name,
        passed=False,
        profile="complete",
        consecutive_days=0,
        remaining_days=30,
        total_resets=0,
        message="BLOCKED: shadow gate not started",
    )


class ReplayGovernanceProjection(BaseModel, frozen=True):
    """Read-only replay/backtest governance projection."""

    readiness_status: str = "REPLAY_PROTOCOL_PROOF_NOT_PROVEN"
    shadow_runtime_compatibility_status: str = "SHADOW_IMPORT_REQUIRES_REVIEW"
    blocking_reasons: tuple[str, ...] = ()
    micro_live_gate: ReplayGovernanceGateProjection = Field(
        default_factory=lambda: _default_gate(
            gate_name="complete_shadow_30j_for_micro_live"
        )
    )
    live_gate: ReplayGovernanceGateProjection = Field(
        default_factory=lambda: _default_gate(gate_name="complete_shadow_30j")
    )


def project_replay_governance(
    *,
    overall_backtest_proof_status: str,
    promotion_artifact_status: str,
    expected_edge_truth_status: str,
    execution_label_source: str,
    execution_fidelity_gap_codes: tuple[str, ...] = (),
) -> ReplayGovernanceProjection:
    """Project replay/backtest truth into gate-compatible vocabulary."""

    blocker_codes: list[str] = []
    if promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY":
        blocker_codes.append("PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY")
    blocker_codes.extend(
        str(code) for code in execution_fidelity_gap_codes if str(code).strip()
    )
    if expected_edge_truth_status != "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH":
        blocker_codes.append(expected_edge_truth_status or "EXPECTED_EDGE_TRUTH_NOT_PROVEN")
    if overall_backtest_proof_status in {
        "BACKTEST_PROOF_BLOCKED",
        "BACKTEST_PROOF_NOT_PROVEN",
    }:
        blocker_codes.append(overall_backtest_proof_status)
    if execution_label_source == "REPLAY_PROXY_EXECUTION":
        blocker_codes.append("EXECUTION_LABEL_REPLAY_PROXY")

    deduped_blockers = tuple(dict.fromkeys(code for code in blocker_codes if code))
    if overall_backtest_proof_status == "BACKTEST_PROOF_READY" and not deduped_blockers:
        readiness_status = "REPLAY_PROTOCOL_PROOF_READY_FOR_SHADOW"
        compatibility_status = "SHADOW_IMPORT_COMPATIBLE"
        micro_message = (
            "BLOCKED: 30 consecutive shadow days remain after accepted replay import"
        )
    elif deduped_blockers:
        readiness_status = "REPLAY_PROTOCOL_PROOF_BLOCKED"
        compatibility_status = "SHADOW_IMPORT_BLOCKED"
        micro_message = (
            "BLOCKED: replay/backtest proof unresolved ("
            + ", ".join(deduped_blockers)
            + ")"
        )
    else:
        readiness_status = "REPLAY_PROTOCOL_PROOF_PARTIAL"
        compatibility_status = "SHADOW_IMPORT_REQUIRES_REVIEW"
        micro_message = "BLOCKED: replay/backtest proof is partial and still requires review"

    micro_gate = ReplayGovernanceGateProjection(
        gate_name="complete_shadow_30j_for_micro_live",
        passed=False,
        profile="complete",
        consecutive_days=0,
        remaining_days=30,
        total_resets=0,
        message=micro_message,
    )
    live_gate = ReplayGovernanceGateProjection(
        gate_name="complete_shadow_30j",
        passed=False,
        profile="complete",
        consecutive_days=0,
        remaining_days=30,
        total_resets=0,
        message=f"BLOCKED: micro-live gate not passed - {micro_gate.message}",
    )
    return ReplayGovernanceProjection(
        readiness_status=readiness_status,
        shadow_runtime_compatibility_status=compatibility_status,
        blocking_reasons=deduped_blockers,
        micro_live_gate=micro_gate,
        live_gate=live_gate,
    )


__all__ = [
    "ReplayGovernanceGateProjection",
    "ReplayGovernanceProjection",
    "project_replay_governance",
]
