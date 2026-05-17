"""Protocol-facing replay governance projection without live/runtime coupling."""

from __future__ import annotations

from pydantic import BaseModel, Field

from monitoring.replay_governance_projection import (
    ReplayGovernanceGateProjection as MonitoringReplayGovernanceGateProjection,
)
from monitoring.replay_governance_projection import (
    ReplayGovernanceProjection as MonitoringReplayGovernanceProjection,
)
from monitoring.replay_governance_projection import (
    project_replay_governance as project_monitoring_replay_governance,
)
from protocols.promotion_gates import PromotionGateResult


def _default_gate(*, gate_name: str) -> PromotionGateResult:
    return PromotionGateResult(
        gate_name=gate_name,
        passed=False,
        profile="complete",
        consecutive_days=0,
        remaining_days=30,
        total_resets=0,
        message="BLOCKED: shadow gate not started",
    )


class ReplayGovernanceProjection(BaseModel, frozen=True):
    """Read-only protocol projection for replay/backtest outputs."""

    readiness_status: str = "REPLAY_PROTOCOL_PROOF_NOT_PROVEN"
    shadow_runtime_compatibility_status: str = "SHADOW_IMPORT_REQUIRES_REVIEW"
    blocking_reasons: tuple[str, ...] = ()
    micro_live_gate: PromotionGateResult = Field(
        default_factory=lambda: _default_gate(
            gate_name="complete_shadow_30j_for_micro_live"
        )
    )
    live_gate: PromotionGateResult = Field(
        default_factory=lambda: _default_gate(gate_name="complete_shadow_30j")
    )


def _materialize_gate(
    gate: MonitoringReplayGovernanceGateProjection,
) -> PromotionGateResult:
    return PromotionGateResult(
        gate_name=gate.gate_name,
        passed=gate.passed,
        profile=gate.profile,
        consecutive_days=gate.consecutive_days,
        required_days=gate.required_days,
        remaining_days=gate.remaining_days,
        total_resets=gate.total_resets,
        message=gate.message,
    )


def _materialize_projection(
    projection: MonitoringReplayGovernanceProjection,
) -> ReplayGovernanceProjection:
    return ReplayGovernanceProjection(
        readiness_status=projection.readiness_status,
        shadow_runtime_compatibility_status=(
            projection.shadow_runtime_compatibility_status
        ),
        blocking_reasons=projection.blocking_reasons,
        micro_live_gate=_materialize_gate(projection.micro_live_gate),
        live_gate=_materialize_gate(projection.live_gate),
    )


def project_replay_governance(
    *,
    overall_backtest_proof_status: str,
    promotion_artifact_status: str,
    expected_edge_truth_status: str,
    execution_label_source: str,
    execution_fidelity_gap_codes: tuple[str, ...] = (),
) -> ReplayGovernanceProjection:
    """Project replay/backtest truth into protocol-style promotion vocabulary."""

    return _materialize_projection(
        project_monitoring_replay_governance(
            overall_backtest_proof_status=overall_backtest_proof_status,
            promotion_artifact_status=promotion_artifact_status,
            expected_edge_truth_status=expected_edge_truth_status,
            execution_label_source=execution_label_source,
            execution_fidelity_gap_codes=execution_fidelity_gap_codes,
        )
    )


__all__ = ["ReplayGovernanceProjection", "project_replay_governance"]
