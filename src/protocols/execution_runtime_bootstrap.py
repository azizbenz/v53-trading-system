"""Bootstrap helpers for wiring compiled execution hooks into the execution runtime."""

from __future__ import annotations

from pathlib import Path

from execution_backbone import (
    ExecutionRuntime,
    ExecutionVenueAdapter,
    VenueConstraintProvider,
)

from .compiled_artifact_registry_store import CompiledArtifactRegistryStore
from .execution_no_trade_filter_bridge import (
    ExecutionNoTradeFilterBridge,
    ExecutionNoTradeFilterBridgeStatus,
    inspect_execution_no_trade_filter_bridge,
)


def build_execution_runtime(
    adapter: ExecutionVenueAdapter,
    *,
    default_fee_rate: float = 0.001,
    max_recon_age_s: float = 60.0,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    compiled_registry_state_dir: str | Path | None = None,
) -> ExecutionRuntime:
    """Build an ExecutionRuntime with the bounded compiled no-trade bridge when configured."""

    execution_no_trade_filter = None
    if compiled_registry_state_dir is not None:
        store = CompiledArtifactRegistryStore(Path(compiled_registry_state_dir))
        execution_no_trade_filter = ExecutionNoTradeFilterBridge(store)
    return ExecutionRuntime(
        adapter,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        execution_no_trade_filter=execution_no_trade_filter,
    )


def inspect_execution_runtime_bootstrap(
    *,
    compiled_registry_state_dir: str | Path | None = None,
) -> ExecutionNoTradeFilterBridgeStatus:
    """Inspect the configured execution runtime bootstrap state outside the hot path."""

    if compiled_registry_state_dir is None:
        return ExecutionNoTradeFilterBridgeStatus(configured=False)
    store = CompiledArtifactRegistryStore(Path(compiled_registry_state_dir))
    return inspect_execution_no_trade_filter_bridge(store)


__all__ = [
    "build_execution_runtime",
    "inspect_execution_runtime_bootstrap",
]
