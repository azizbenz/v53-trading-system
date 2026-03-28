"""Minimal real Build-11/12 protocol runtime surface."""

from protocols.contracts import (
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveInput,
    MicroLiveRunSummary,
    ShadowComparison,
    ShadowDecision,
    ShadowInput,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.enums import (
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import (
    MicroLiveBudgetError,
    MicroLiveGateError,
    MicroLiveInputError,
    MicroLiveProtocolError,
    ShadowGateError,
    ShadowInputError,
    ShadowLineageError,
    ShadowProtocolError,
)
from protocols.micro_live_dashboard import (
    build_micro_live_dashboard_section,
    build_micro_live_projection,
)
from protocols.micro_live_runtime import (
    build_micro_live_input_from_shadow,
    run_micro_live_gate,
)
from protocols.shadow_dashboard import (
    build_shadow_dashboard_section,
    build_shadow_projection,
)
from protocols.shadow_runtime import (
    build_shadow_input_from_payloads,
    compare_shadow_candidate,
    run_shadow_validation,
)

__all__ = [
    "MicroLiveInput",
    "MicroLiveDecision",
    "MicroLiveExecutionPlan",
    "MicroLiveRunSummary",
    "MicroLiveRunState",
    "MicroLiveVerdict",
    "MicroLiveProtocolError",
    "MicroLiveInputError",
    "MicroLiveGateError",
    "MicroLiveBudgetError",
    "build_micro_live_input_from_shadow",
    "run_micro_live_gate",
    "build_micro_live_projection",
    "build_micro_live_dashboard_section",
    "ShadowTruthSet",
    "ShadowValidationSet",
    "ShadowInput",
    "ShadowComparison",
    "ShadowDecision",
    "ShadowRunSummary",
    "ShadowRunState",
    "ShadowVerdict",
    "ShadowComparisonStatus",
    "ShadowDivergenceSeverity",
    "ShadowProtocolError",
    "ShadowInputError",
    "ShadowLineageError",
    "ShadowGateError",
    "build_shadow_input_from_payloads",
    "compare_shadow_candidate",
    "run_shadow_validation",
    "build_shadow_projection",
    "build_shadow_dashboard_section",
]
