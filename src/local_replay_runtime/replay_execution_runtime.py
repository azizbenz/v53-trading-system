"""Execution-realism seam for governed LOCAL_REPLAY."""

from __future__ import annotations

from local_replay_runtime.enums import ReplayExecutionProviderKind
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.replay_execution_contracts import (
    ReplayExecutionEvaluationRequest,
    ReplayExecutionEvaluationResult,
    ReplayParityDiagnosticsSummary,
    ShadowExecutionSimulatorConfig,
)
from local_replay_runtime.replay_execution_projection_loader import (
    load_replay_execution_projection_models,
)
from local_replay_runtime.shadow_execution_simulator import (
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


def build_replay_parity_diagnostics(
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    *,
    simulator_config: ShadowExecutionSimulatorConfig | None = None,
) -> ReplayParityDiagnosticsSummary:
    """Build typed replay parity diagnostics for artifact serialization."""

    return ReplayParityDiagnosticsSummary.model_validate(
        build_parity_diagnostics_payload(
            dataset,
            dtr_records,
            config=simulator_config,
        )
    )


def _resolve_simulator_config(
    request: ReplayExecutionEvaluationRequest,
) -> ShadowExecutionSimulatorConfig:
    config = request.simulator_config
    if request.execution_runtime_projection_path is None:
        return config
    spread_guard_model, slippage_model = load_replay_execution_projection_models(
        request.execution_runtime_projection_path
    )
    return config.model_copy(
        update={
            "spread_guard_model": spread_guard_model,
            "slippage_model": slippage_model,
            "execution_runtime_projection_ref": request.execution_runtime_projection_path,
        }
    )


def evaluate_replay_execution(
    request: ReplayExecutionEvaluationRequest,
) -> ReplayExecutionEvaluationResult:
    """Evaluate replay execution realism through the configured provider seam."""

    if request.provider.provider_kind != ReplayExecutionProviderKind.SHADOW_SIMULATOR:
        raise ValueError(
            "LOCAL_REPLAY replay execution provider is unsupported: "
            f"{request.provider.provider_kind}"
        )
    effective_config = _resolve_simulator_config(request)
    dtr_records = simulate_shadow_compatible_dtrs(
        request.dataset,
        config=effective_config,
    )
    return ReplayExecutionEvaluationResult(
        request=request,
        dtr_records=dtr_records,
        parity_diagnostics=build_replay_parity_diagnostics(
            request.dataset,
            dtr_records,
            simulator_config=effective_config,
        ),
    )


__all__ = [
    "build_replay_parity_diagnostics",
    "evaluate_replay_execution",
]
