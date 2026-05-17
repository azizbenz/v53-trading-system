"""Tests for protocol-facing replay governance projection."""

from __future__ import annotations

from protocols import project_replay_governance


def test_project_replay_governance_blocks_fidelity_gaps() -> None:
    projection = project_replay_governance(
        overall_backtest_proof_status="BACKTEST_PROOF_RESEARCH_ONLY",
        promotion_artifact_status="PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
        expected_edge_truth_status="EXPECTED_EDGE_PROXY_BLOCKED",
        execution_label_source="PARTIAL_CANONICAL_EXECUTION",
        execution_fidelity_gap_codes=("PARTIAL_FILL_PROXY", "VENUE_CONSTRAINTS_PROXY"),
    )

    assert projection.readiness_status == "REPLAY_PROTOCOL_PROOF_BLOCKED"
    assert projection.shadow_runtime_compatibility_status == "SHADOW_IMPORT_BLOCKED"
    assert projection.blocking_reasons == (
        "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
        "PARTIAL_FILL_PROXY",
        "VENUE_CONSTRAINTS_PROXY",
        "EXPECTED_EDGE_PROXY_BLOCKED",
    )
    assert "PARTIAL_FILL_PROXY" in projection.micro_live_gate.message
    assert "micro-live gate not passed" in projection.live_gate.message


def test_project_replay_governance_can_be_ready_for_shadow_without_passing_shadow_days() -> None:
    projection = project_replay_governance(
        overall_backtest_proof_status="BACKTEST_PROOF_READY",
        promotion_artifact_status="PROMOTION_ARTIFACTS_READY",
        expected_edge_truth_status="EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
        execution_label_source="PARTIAL_CANONICAL_EXECUTION",
        execution_fidelity_gap_codes=(),
    )

    assert projection.readiness_status == "REPLAY_PROTOCOL_PROOF_READY_FOR_SHADOW"
    assert projection.shadow_runtime_compatibility_status == "SHADOW_IMPORT_COMPATIBLE"
    assert projection.blocking_reasons == ()
    assert projection.micro_live_gate.passed is False
    assert projection.micro_live_gate.remaining_days == 30
    assert "accepted replay import" in projection.micro_live_gate.message
