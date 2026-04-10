"""
Build-8 / portfolio_minimal — Portfolio Minimal Pack.

Transforms surviving Engine A/B opportunities into a coherent Light portfolio:
- opportunity_selector: rank, compare, select candidates under budget constraints
- allocation_router: allocate capital, apply caps, detect phantom trades
"""

from .portfolio_orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    PortfolioRelativeRankAdjustmentHook,
    PortfolioRelativeRankAdjustmentInput,
    PortfolioRelativeRankAdjustmentOutcome,
    run_portfolio_pipeline,
)

__all__ = [
    "OrchestratorConfig",
    "OrchestratorResult",
    "PortfolioRelativeRankAdjustmentHook",
    "PortfolioRelativeRankAdjustmentInput",
    "PortfolioRelativeRankAdjustmentOutcome",
    "run_portfolio_pipeline",
]
