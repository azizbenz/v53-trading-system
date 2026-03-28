"""Minimal real Build-11 Shadow runtime surface."""

from protocols.contracts import (
    ShadowComparison,
    ShadowDecision,
    ShadowInput,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.enums import (
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import (
    ShadowGateError,
    ShadowInputError,
    ShadowLineageError,
    ShadowProtocolError,
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
