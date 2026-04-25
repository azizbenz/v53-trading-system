"""
Build-8 / portfolio_minimal — Portfolio Minimal Pack.

Transforms surviving Engine A/B opportunities into a coherent Light portfolio:
- opportunity_selector: rank, compare, select candidates under budget constraints
- allocation_router: allocate capital, apply caps, detect phantom trades
"""

from __future__ import annotations

from .portfolio_orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    PortfolioRelativeRankAdjustmentHook,
    PortfolioRelativeRankAdjustmentInput,
    PortfolioRelativeRankAdjustmentOutcome,
    run_portfolio_pipeline,
)
from .arbitration_record import (
    PortfolioArbitrationRecord,
    PortfolioArbitrationVerdict,
)
from .allocation_router.vol_target_sizer import (
    VolTargetProfile,
    VolTargetSizeResult,
)

__all__ = [
    "OrchestratorConfig",
    "OrchestratorResult",
    "PortfolioArbitrationRecord",
    "PortfolioArbitrationVerdict",
    "PortfolioRelativeRankAdjustmentHook",
    "PortfolioRelativeRankAdjustmentInput",
    "PortfolioRelativeRankAdjustmentOutcome",
    "VolTargetProfile",
    "VolTargetSizeResult",
    "run_portfolio_pipeline",
]
