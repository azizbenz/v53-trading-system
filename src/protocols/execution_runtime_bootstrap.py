"""Bootstrap helpers for wiring compiled execution hooks into the execution runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from execution_backbone.execution_runtime import ExecutionRuntime
from execution_backbone.execution_runtime_models import ExecutionVenueAdapter, RemoteExecutionState
from execution_backbone.gatekeeper import GatekeeperAuditLogger
from execution_backbone.reconciliation_layer.scheduler import (
    ReconciliationScheduler,
    ReconciliationSchedulerCalibrationConfig,
    ReconciliationSchedulerRunResult,
    ReconciliationSchedulerThresholds,
    resolve_reconciliation_scheduler_thresholds,
)
from execution_backbone.venue_constraints_provider import VenueConstraintProvider
from interface_contracts.binance_contracts import BinanceCredentials
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from scoring_backbone import FeeAwareEdgeGateConfig
from venue_adapters.binance_spot.bootstrap import build_binance_spot_execution_adapter
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig
from venue_adapters.binance_spot.user_data_ws_client import UserDataSocketFactory

from .compiled_artifact_registry_store import CompiledArtifactRegistryStore
from .execution_no_trade_filter_bridge import (
    ExecutionNoTradeFilterBridge,
    ExecutionNoTradeFilterBridgeStatus,
    inspect_execution_no_trade_filter_bridge,
)
from .execution_runtime_projection_bridge import (
    load_execution_runtime_consumer_models,
)


@dataclass(frozen=True)
class ExecutionRuntimeBootstrapBundle:
    """Typed operated bootstrap output for the canonical Build-3 runtime."""

    runtime: ExecutionRuntime
    reconciliation_scheduler: ReconciliationScheduler | None = None
    reconciliation_boot_result: ReconciliationSchedulerRunResult | None = None
    remote_state_snapshot: RemoteExecutionState | None = None


def build_execution_runtime_bootstrap_bundle(
    adapter: ExecutionVenueAdapter,
    *,
    default_fee_rate: float = 0.001,
    max_recon_age_s: float = 60.0,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    compiled_registry_state_dir: str | Path | None = None,
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
    execution_runtime_projection_path: str | Path | None = None,
    gatekeeper_audit_path: str | Path | None = None,
    reconciliation_scheduler_calibration_config: (
        ReconciliationSchedulerCalibrationConfig | None
    ) = None,
    reconciliation_boot_now: float | None = None,
    reconciliation_circuit_breaker: EmergencyCircuitBreaker | None = None,
    trip_reconciliation_circuit_breaker_on_unresolved: bool = True,
    capture_remote_state_snapshot: bool = False,
) -> ExecutionRuntimeBootstrapBundle:
    """Build an execution runtime plus optional bounded reconciliation bootstrap state."""

    if reconciliation_circuit_breaker is not None and reconciliation_boot_now is None:
        raise ValueError(
            "reconciliation_circuit_breaker requires reconciliation_boot_now"
        )

    execution_no_trade_filter = None
    if compiled_registry_state_dir is not None:
        store = CompiledArtifactRegistryStore(Path(compiled_registry_state_dir))
        execution_no_trade_filter = ExecutionNoTradeFilterBridge(store)

    rate_limit_model = None
    spread_guard_model = None
    slippage_model = None
    if execution_runtime_projection_path is not None:
        (
            rate_limit_model,
            spread_guard_model,
            slippage_model,
        ) = load_execution_runtime_consumer_models(
            execution_runtime_projection_path
        )
    gatekeeper_audit_logger = (
        GatekeeperAuditLogger(Path(gatekeeper_audit_path))
        if gatekeeper_audit_path is not None
        else None
    )

    runtime = ExecutionRuntime(
        adapter,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        execution_no_trade_filter=execution_no_trade_filter,
        fee_aware_edge_gate_config=fee_aware_edge_gate_config,
        rate_limit_model=rate_limit_model,
        spread_guard_model=spread_guard_model,
        slippage_model=slippage_model,
        gatekeeper_audit_logger=gatekeeper_audit_logger,
    )

    reconciliation_scheduler = _build_reconciliation_scheduler(
        calibration_config=reconciliation_scheduler_calibration_config,
        reconciliation_boot_now=reconciliation_boot_now,
    )
    reconciliation_boot_result = None
    if reconciliation_scheduler is not None and reconciliation_boot_now is not None:
        reconciliation_boot_result = reconciliation_scheduler.boot_reconcile(
            runtime,
            now=reconciliation_boot_now,
            circuit_breaker=reconciliation_circuit_breaker,
            trip_circuit_breaker_on_unresolved=(
                trip_reconciliation_circuit_breaker_on_unresolved
            ),
        )
    remote_state_snapshot = (
        adapter.fetch_remote_state() if capture_remote_state_snapshot else None
    )

    return ExecutionRuntimeBootstrapBundle(
        runtime=runtime,
        reconciliation_scheduler=reconciliation_scheduler,
        reconciliation_boot_result=reconciliation_boot_result,
        remote_state_snapshot=remote_state_snapshot,
    )


def build_execution_runtime(
    adapter: ExecutionVenueAdapter,
    *,
    default_fee_rate: float = 0.001,
    max_recon_age_s: float = 60.0,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    compiled_registry_state_dir: str | Path | None = None,
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
    execution_runtime_projection_path: str | Path | None = None,
    gatekeeper_audit_path: str | Path | None = None,
) -> ExecutionRuntime:
    """Build an ExecutionRuntime with the bounded compiled no-trade bridge when configured."""

    return build_execution_runtime_bootstrap_bundle(
        adapter,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        compiled_registry_state_dir=compiled_registry_state_dir,
        fee_aware_edge_gate_config=fee_aware_edge_gate_config,
        execution_runtime_projection_path=execution_runtime_projection_path,
        gatekeeper_audit_path=gatekeeper_audit_path,
    ).runtime


def build_binance_execution_runtime_bootstrap_bundle(
    *,
    credentials: BinanceCredentials,
    config: BinanceAdapterConfig,
    default_fee_rate: float = 0.001,
    max_recon_age_s: float = 60.0,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    compiled_registry_state_dir: str | Path | None = None,
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None,
    execution_runtime_projection_path: str | Path | None = None,
    gatekeeper_audit_path: str | Path | None = None,
    reconciliation_scheduler_calibration_config: (
        ReconciliationSchedulerCalibrationConfig | None
    ) = None,
    reconciliation_boot_now: float | None = None,
    reconciliation_circuit_breaker: EmergencyCircuitBreaker | None = None,
    trip_reconciliation_circuit_breaker_on_unresolved: bool = True,
    http_client: httpx.AsyncClient | None = None,
    user_data_stream_enabled: bool = False,
    user_data_socket_factory: UserDataSocketFactory | None = None,
    clock_ms: Callable[[], int] | None = None,
    capture_remote_state_snapshot: bool = False,
) -> ExecutionRuntimeBootstrapBundle:
    """Build the bounded Binance execution runtime plus optional reconciliation bootstrap state."""

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
    return build_execution_runtime_bootstrap_bundle(
        adapter,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        compiled_registry_state_dir=compiled_registry_state_dir,
        fee_aware_edge_gate_config=resolved_fee_aware_edge_gate_config,
        execution_runtime_projection_path=execution_runtime_projection_path,
        gatekeeper_audit_path=gatekeeper_audit_path,
        reconciliation_scheduler_calibration_config=(
            reconciliation_scheduler_calibration_config
        ),
        reconciliation_boot_now=reconciliation_boot_now,
        reconciliation_circuit_breaker=reconciliation_circuit_breaker,
        trip_reconciliation_circuit_breaker_on_unresolved=(
            trip_reconciliation_circuit_breaker_on_unresolved
        ),
        capture_remote_state_snapshot=capture_remote_state_snapshot,
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
    execution_runtime_projection_path: str | Path | None = None,
    gatekeeper_audit_path: str | Path | None = None,
    http_client: httpx.AsyncClient | None = None,
    user_data_stream_enabled: bool = False,
    user_data_socket_factory: UserDataSocketFactory | None = None,
    clock_ms: Callable[[], int] | None = None,
) -> ExecutionRuntime:
    """Build the execution runtime on the bounded Binance Spot adapter rail."""

    return build_binance_execution_runtime_bootstrap_bundle(
        credentials=credentials,
        config=config,
        default_fee_rate=default_fee_rate,
        max_recon_age_s=max_recon_age_s,
        venue_constraint_provider=venue_constraint_provider,
        compiled_registry_state_dir=compiled_registry_state_dir,
        fee_aware_edge_gate_config=fee_aware_edge_gate_config,
        execution_runtime_projection_path=execution_runtime_projection_path,
        gatekeeper_audit_path=gatekeeper_audit_path,
        http_client=http_client,
        user_data_stream_enabled=user_data_stream_enabled,
        user_data_socket_factory=user_data_socket_factory,
        clock_ms=clock_ms,
    ).runtime


def _build_reconciliation_scheduler(
    *,
    calibration_config: ReconciliationSchedulerCalibrationConfig | None,
    reconciliation_boot_now: float | None,
) -> ReconciliationScheduler | None:
    if calibration_config is None and reconciliation_boot_now is None:
        return None
    thresholds = (
        resolve_reconciliation_scheduler_thresholds(calibration_config)
        if calibration_config is not None
        else ReconciliationSchedulerThresholds.from_documented_defaults()
    )
    return ReconciliationScheduler(thresholds=thresholds)


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
    "ExecutionRuntimeBootstrapBundle",
    "build_binance_execution_runtime_bootstrap_bundle",
    "build_binance_execution_runtime",
    "build_execution_runtime_bootstrap_bundle",
    "build_execution_runtime",
    "inspect_execution_runtime_bootstrap",
]
