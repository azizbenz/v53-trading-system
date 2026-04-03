"""Shadow readiness preflight without opening the Build-11 runtime."""

from __future__ import annotations

import importlib
from typing import Iterable

from pydantic import BaseModel, Field

from interface_contracts import ProfileId
from manifest_registry.profile_registry import is_module_active_in_profile


class ShadowReadinessReport(BaseModel, frozen=True):
    """Deterministic preflight report for opening Build-11 later on."""

    core_green: bool
    build10_supervision_ready: bool
    build9x_governed_ready: bool
    replay_import_ready: bool
    onboarding_ready: bool
    build14_shadow_governance_ready: bool
    missing_items: tuple[str, ...] = ()
    final_verdict: str = Field(..., min_length=1)


def _has_exports(module_name: str, required_exports: Iterable[str]) -> bool:
    module = importlib.import_module(module_name)
    module_exports = set(getattr(module, "__all__", ()))
    return set(required_exports).issubset(module_exports)


def evaluate_shadow_readiness(
    *,
    core_green: bool,
    build10_supervision_ready: bool | None = None,
    build9x_governed_ready: bool | None = None,
    replay_import_ready: bool | None = None,
    onboarding_ready: bool | None = None,
    build14_shadow_governance_ready: bool | None = None,
) -> ShadowReadinessReport:
    """Evaluate whether Shadow opening is credible without creating the runtime."""

    if build10_supervision_ready is None:
        build10_supervision_ready = (
            _has_exports("monitoring", {"build_technical_dashboard_payload", "build_observability_export"})
            and _has_exports("ui", {"build_technical_dashboard_view"})
        )
    if build9x_governed_ready is None:
        build9x_governed_ready = _has_exports(
            "meta_learning",
            {"run_meta_learning_review", "MetaLearningReviewBundle"},
        )
    if replay_import_ready is None:
        replay_import_ready = (
            _has_exports(
                "local_replay_runtime",
                {"ReplayExecutionPlan", "LocalReplayOrchestrator"},
            )
            and _has_exports(
                "backtest_artifact_import",
                {"ArtifactImportSummary", "validate_import_request"},
            )
        )
    if onboarding_ready is None:
        onboarding_ready = _has_exports(
            "backtest_artifact_import",
            {"StrategyOnboardingRequest", "validate_strategy_onboarding_request"},
        )
    if build14_shadow_governance_ready is None:
        build14_shadow_governance_ready = (
            _has_exports(
                "complete_enablers",
                {"build_market_toxicity_snapshot", "build_execution_fragility_score"},
            )
            and is_module_active_in_profile("complete_enablers", ProfileId.LIGHT)
        )

    missing_items: list[str] = []
    if not core_green:
        missing_items.append("core baseline must stay green")
    if not build10_supervision_ready:
        missing_items.append("Build-10 supervision layer is not ready")
    if not build9x_governed_ready:
        missing_items.append("Build-9X governed review flow is not ready")
    if not replay_import_ready:
        missing_items.append("LOCAL_REPLAY / import governed MVP is not ready")
    if not onboarding_ready:
        missing_items.append("strategy onboarding governance is not ready")
    if not build14_shadow_governance_ready:
        missing_items.append("Build-14 Shadow governance is not ready")

    return ShadowReadinessReport(
        core_green=core_green,
        build10_supervision_ready=build10_supervision_ready,
        build9x_governed_ready=build9x_governed_ready,
        replay_import_ready=replay_import_ready,
        onboarding_ready=onboarding_ready,
        build14_shadow_governance_ready=build14_shadow_governance_ready,
        missing_items=tuple(missing_items),
        final_verdict="ready_for_shadow" if not missing_items else "not_ready_for_shadow",
    )


__all__ = [
    "ShadowReadinessReport",
    "evaluate_shadow_readiness",
]
