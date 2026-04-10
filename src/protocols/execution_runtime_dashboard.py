"""Monitoring projections for bounded compiled runtime hook bridges."""

from __future__ import annotations

from pathlib import Path

from interface_contracts import HookId, RUNTIME_OPEN_HOOK_IDS
from monitoring import ExecutionNoTradeBridgeProjection, RuntimeHookBridgeProjection

from .compiled_artifact_registry_store import CompiledArtifactRegistryStore
from .engine_a_pre_entry_confirmation_bridge import inspect_engine_a_pre_entry_confirmation_bridge
from .engine_b_sweep_validation_bridge import inspect_engine_b_sweep_validation_bridge
from .engine_c_void_validation_bridge import inspect_engine_c_void_validation_bridge
from .engine_d_reentry_validation_bridge import inspect_engine_d_reentry_validation_bridge
from .execution_runtime_bootstrap import inspect_execution_runtime_bootstrap
from .portfolio_relative_rank_adjustment_bridge import inspect_portfolio_relative_rank_adjustment_bridge
from .risk_micro_friction_precheck_bridge import inspect_risk_micro_friction_precheck_bridge
from .scoring_soft_penalty_layer_bridge import inspect_scoring_soft_penalty_layer_bridge


_HOOK_LABELS: dict[HookId, str] = {
    HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION: "Engine A pre-entry",
    HookId.ENGINE_B_SWEEP_VALIDATION: "Engine B sweep",
    HookId.ENGINE_C_VOID_VALIDATION: "Engine C void",
    HookId.ENGINE_D_REENTRY_VALIDATION: "Engine D re-entry",
    HookId.RISK_MICRO_FRICTION_PRECHECK: "Risk micro-friction",
    HookId.SCORING_SOFT_PENALTY_LAYER: "Scoring soft penalty",
    HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT: "Portfolio relative rank",
    HookId.EXECUTION_NO_TRADE_FILTER: "Execution no-trade",
}


def _status_from_bridge_status(status: object) -> str:
    if not status.configured:
        return "planned"
    if status.error_type:
        return "warning"
    if status.loaded:
        return "healthy"
    if status.selection_status.value == "binding_only":
        return "warning"
    if status.selection_status.value in {"no_binding", "no_snapshot"}:
        return "info"
    return "info"


def _detail_from_bridge_status(*, hook_id: HookId, status: object) -> str:
    detail = status.error_detail.strip()
    label = _HOOK_LABELS[hook_id].lower()
    if detail:
        return detail
    if not status.configured:
        return f"Compiled {label} bridge not configured"
    if status.loaded:
        return f"Compiled {label} bridge loaded from current snapshot"
    if status.binding_present:
        return f"Compiled {label} bridge binding published but plan not loaded"
    return f"Compiled {label} bridge configured without active binding"


def _build_runtime_hook_bridge_projection(
    *,
    hook_id: HookId,
    status: object,
) -> RuntimeHookBridgeProjection:
    return RuntimeHookBridgeProjection(
        hook_id=hook_id,
        label=_HOOK_LABELS[hook_id],
        status=_status_from_bridge_status(status),
        configured=status.configured,
        selection_status=status.selection_status.value,
        current_snapshot_id=status.current_snapshot_id,
        previous_snapshot_id=status.previous_snapshot_id,
        last_known_good_snapshot_id=status.last_known_good_snapshot_id,
        binding_present=status.binding_present,
        loaded=status.loaded,
        compiled_plan_ref=status.compiled_plan_ref,
        artifact_count=len(status.artifact_ids),
        action_kinds=tuple(item.value for item in status.action_kinds),
        failure_mode=status.failure_mode.value,
        error_stage="" if status.error_stage is None else status.error_stage.value,
        error_type=status.error_type,
        detail=_detail_from_bridge_status(hook_id=hook_id, status=status),
    )


def _default_runtime_hook_bridge_projection(hook_id: HookId) -> RuntimeHookBridgeProjection:
    return RuntimeHookBridgeProjection(
        hook_id=hook_id,
        label=_HOOK_LABELS[hook_id],
        status="planned",
        configured=False,
        selection_status="not_configured",
        detail=f"Compiled {_HOOK_LABELS[hook_id].lower()} bridge not configured",
    )


def build_runtime_hook_bridge_projections(
    *,
    compiled_registry_state_dir: str | Path | None = None,
) -> tuple[RuntimeHookBridgeProjection, ...]:
    """Project all runtime-open bounded hook bridges into monitoring-friendly truth."""

    if compiled_registry_state_dir is None:
        return tuple(
            _default_runtime_hook_bridge_projection(hook_id)
            for hook_id in RUNTIME_OPEN_HOOK_IDS
        )

    store = CompiledArtifactRegistryStore(Path(compiled_registry_state_dir))
    inspectors = {
        HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION: inspect_engine_a_pre_entry_confirmation_bridge,
        HookId.ENGINE_B_SWEEP_VALIDATION: inspect_engine_b_sweep_validation_bridge,
        HookId.ENGINE_C_VOID_VALIDATION: inspect_engine_c_void_validation_bridge,
        HookId.ENGINE_D_REENTRY_VALIDATION: inspect_engine_d_reentry_validation_bridge,
        HookId.RISK_MICRO_FRICTION_PRECHECK: inspect_risk_micro_friction_precheck_bridge,
        HookId.SCORING_SOFT_PENALTY_LAYER: inspect_scoring_soft_penalty_layer_bridge,
        HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT: inspect_portfolio_relative_rank_adjustment_bridge,
    }
    projections: list[RuntimeHookBridgeProjection] = []
    for hook_id in RUNTIME_OPEN_HOOK_IDS:
        if hook_id == HookId.EXECUTION_NO_TRADE_FILTER:
            execution_projection = build_execution_no_trade_bridge_projection(
                compiled_registry_state_dir=compiled_registry_state_dir
            )
            projections.append(
                RuntimeHookBridgeProjection(
                    hook_id=hook_id,
                    label=_HOOK_LABELS[hook_id],
                    status=execution_projection.status,
                    configured=execution_projection.configured,
                    selection_status=execution_projection.selection_status,
                    current_snapshot_id=execution_projection.current_snapshot_id,
                    previous_snapshot_id=execution_projection.previous_snapshot_id,
                    last_known_good_snapshot_id=execution_projection.last_known_good_snapshot_id,
                    binding_present=execution_projection.binding_present,
                    loaded=execution_projection.loaded,
                    compiled_plan_ref=execution_projection.compiled_plan_ref,
                    artifact_count=execution_projection.artifact_count,
                    failure_mode=execution_projection.failure_mode,
                    error_stage=execution_projection.error_stage,
                    error_type=execution_projection.error_type,
                    detail=execution_projection.detail,
                )
            )
            continue
        status = inspectors[hook_id](store)
        projections.append(
            _build_runtime_hook_bridge_projection(
                hook_id=hook_id,
                status=status,
            )
        )
    return tuple(projections)


def build_execution_no_trade_bridge_projection(
    *,
    compiled_registry_state_dir: str | Path | None = None,
) -> ExecutionNoTradeBridgeProjection:
    """Project the current execution bootstrap state into the governed monitoring surface."""

    status = inspect_execution_runtime_bootstrap(
        compiled_registry_state_dir=compiled_registry_state_dir
    )
    detail = _detail_from_bridge_status(
        hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
        status=status,
    )
    return ExecutionNoTradeBridgeProjection(
        status=_status_from_bridge_status(status),
        configured=status.configured,
        selection_status=status.selection_status.value,
        current_snapshot_id=status.current_snapshot_id,
        previous_snapshot_id=status.previous_snapshot_id,
        last_known_good_snapshot_id=status.last_known_good_snapshot_id,
        binding_present=status.binding_present,
        loaded=status.loaded,
        compiled_plan_ref=status.compiled_plan_ref,
        artifact_count=len(status.artifact_ids),
        failure_mode=status.failure_mode.value,
        error_stage="" if status.error_stage is None else status.error_stage.value,
        error_type=status.error_type,
        detail=detail,
    )


__all__ = [
    "build_execution_no_trade_bridge_projection",
    "build_runtime_hook_bridge_projections",
]
