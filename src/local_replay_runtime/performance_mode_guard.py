"""Guardrails for governed LOCAL_REPLAY performance modes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_session_config import ReplaySessionConfig


class PerformanceModeGuardReport(BaseModel, frozen=True):
    """Audit-ready summary of allowed vs forbidden behavior for the replay mode."""

    run_id: str = Field(..., min_length=1)
    performance_mode: str = Field(..., min_length=1)
    guard_passed: bool = False
    decision_invariance_required: bool = True
    log_detail_level: str = Field(..., min_length=1)
    monitoring_detail_level: str = Field(..., min_length=1)
    feature_set_version: str = Field(..., min_length=1)
    formula_set_version: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    regime_version: str = Field(..., min_length=1)
    risk_policy_version: str = Field(..., min_length=1)
    cost_model_version: str = Field(..., min_length=1)
    allowed_lightenings: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    summary: str = Field(..., min_length=1)


def build_performance_mode_guard_report(
    session_config: ReplaySessionConfig,
    run_manifest: ReplayRunManifest,
) -> PerformanceModeGuardReport:
    """Project the governed replay mode rules into an audit-ready report."""

    guard_passed = (
        session_config.performance_mode == run_manifest.performance_mode
        and session_config.expected_same_decisions
        and (
            (
                session_config.performance_mode == "shadow_fidelity_mode"
                and session_config.log_detail_level == "rich"
                and session_config.monitoring_detail_level == "rich"
            )
            or (
                session_config.performance_mode == "research_fast_mode"
                and session_config.log_detail_level in {"summary", "rich"}
                and session_config.monitoring_detail_level in {"summary", "rich"}
            )
        )
    )
    allowed_lightenings = (
        (
            "log_frequency",
            "intermediate_snapshots",
            "ui_live",
            "non_critical_monitoring_detail",
        )
        if session_config.performance_mode == "research_fast_mode"
        else ()
    )
    forbidden_changes = (
        "features",
        "equations",
        "hmm",
        "kills",
        "scoring",
        "risk",
        "allocation",
    )
    return PerformanceModeGuardReport(
        run_id=run_manifest.run_id,
        performance_mode=session_config.performance_mode,
        guard_passed=guard_passed,
        decision_invariance_required=session_config.expected_same_decisions,
        log_detail_level=session_config.log_detail_level,
        monitoring_detail_level=session_config.monitoring_detail_level,
        feature_set_version=run_manifest.feature_set_version,
        formula_set_version=run_manifest.formula_set_version,
        scoring_version=run_manifest.scoring_version,
        regime_version=run_manifest.regime_version,
        risk_policy_version=run_manifest.risk_policy_version,
        cost_model_version=run_manifest.cost_model_version,
        allowed_lightenings=allowed_lightenings,
        forbidden_changes=forbidden_changes,
        summary=(
            f"mode={session_config.performance_mode} / "
            f"decision_invariance={'yes' if session_config.expected_same_decisions else 'no'} / "
            f"log_detail={session_config.log_detail_level} / "
            f"monitoring_detail={session_config.monitoring_detail_level}"
        ),
    )


__all__ = [
    "PerformanceModeGuardReport",
    "build_performance_mode_guard_report",
]
