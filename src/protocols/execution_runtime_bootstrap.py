"""Bootstrap helpers for wiring compiled execution hooks into the execution runtime."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

import httpx

from execution_backbone import (
    ExecutionRuntime,
    ExecutionVenueAdapter,
    VenueConstraintProvider,
)
from scoring_backbone import FeeAwareEdgeGateConfig
from interface_contracts.binance_contracts import BinanceCredentials
from venue_adapters.binance_spot import (
    BinanceAdapterConfig,
    build_binance_spot_execution_adapter,
)
from venue_adapters.binance_spot.user_data_ws_client import UserDataSocketFactory

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
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
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
        fee_aware_edge_gate_config=fee_aware_edge_gate_config,
    )


def build_binance_execution_runtime(
    *,
    credentials: BinanceCredentials,
    config: BinanceAdapterConfig,
    default_fee_rate: float = 0.001,
    max_recon_age_s: float = 60.0,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    compiled_registry_state_dir: str | Path | None = None,
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
    user_data_stream_enabled: bool = False,
    user_data_socket_factory: UserDataSocketFactory | None = None,
    clock_ms: Callable[[], int] | None = None,
) -> ExecutionRuntime:
    """Build the execution runtime on the bounded Binance Spot adapter rail."""

    adapter = build_binance_spot_execution_adapter(
        credentials=credentials,
        config=config,
        venue_constraint_provider=venue_constraint_provider,
        http_client=http_client,
        user_data_stream_enabled=user_data_stream_enabled,
        user_data_socket_factory=user_data_socket_factory,
        clock_ms=clock_ms,
    )
    resolved_fee_aware_edge_gate_config = fee_aware_edge_gate_config
    if resolved_fee_aware_edge_gate_config is None and config.fee_aware_edge_gate_enabled:
        resolved_fee_aware_edge_gate_config = FeeAwareEdgeGateConfig(
            calibration_root=config.calibration_root,
            calibration_version=config.calibration_version,
        )
    return build_execution_runtime(
        adapter,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        compiled_registry_state_dir=compiled_registry_state_dir,
        fee_aware_edge_gate_config=resolved_fee_aware_edge_gate_config,
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
    "build_binance_execution_runtime",
    "build_execution_runtime",
    "inspect_execution_runtime_bootstrap",
]
