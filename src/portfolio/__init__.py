"""
V5.3 - Canonical portfolio facade.

The manifest module name is `portfolio`; the current Build-8 implementation
resides in `portfolio_minimal`. This facade keeps the canonical import surface
stable while the implementation remains split into subpackages.
"""

from __future__ import annotations

from portfolio_minimal import allocation_router, opportunity_selector
from portfolio_minimal.allocation_router.allocation_reporter import (
    AllocationEntry,
    AllocationReport,
)
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    OpportunityCandidate,
)
from portfolio_minimal.opportunity_selector.selection_resolver import (
    SelectionEntry,
    SelectionResult,
    SelectionVerdict,
)
from portfolio_minimal.portfolio_orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    run_portfolio_pipeline,
)

__all__ = [
    "allocation_router",
    "opportunity_selector",
    "AllocationEntry",
    "AllocationReport",
    "OrchestratorConfig",
    "OrchestratorResult",
    "OpportunityCandidate",
    "SelectionEntry",
    "SelectionResult",
    "SelectionVerdict",
    "run_portfolio_pipeline",
]
