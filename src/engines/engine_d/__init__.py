"""Build-16 / engine_d.

Shadow-capable re-entry engine.
"""

from __future__ import annotations

from .engine_d_runner import (
    EngineDDecision,
    EngineDInput,
    EngineDInvalidation,
    EngineDLogEntry,
    EngineDOutput,
    run_engine_d,
)
from .cost_feasibility_d import (
    ENGINE_D_CE_MIN_THRESHOLD_FAMILY_ID,
    ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_D_COST_PROFILE_ID,
    ENGINE_D_DELTA_SAFE_THRESHOLD_FAMILY_ID,
    EngineDCostCallerThresholds,
)
from .marginal_value_estimator_d import (
    ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A,
    ENGINE_D_MARGINAL_VALUE_PROFILE_ID,
    ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID,
    EngineDMarginalValueCallerThresholds,
    marginal_value_floor_cleared,
)
from .engine_d_runtime import (
    EngineDReentryValidationHook,
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineDRuntime,
    EngineDRuntimeInput,
    EngineDRuntimeResult,
    EngineDRuntimeStatus,
)
from .first_episode_resolver_d import FirstEpisodeResolutionD, resolve_first_episode, resolve_first_episode_ref
from .first_episode_resolver_d import (
    ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_D_FIRST_EPISODE_PROFILE_ID,
    ENGINE_D_LOOKBACK_THRESHOLD_ID,
    ENGINE_D_MIN_GAP_REASON,
    ENGINE_D_MIN_GAP_THRESHOLD_ID,
    ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON,
    EngineDFirstEpisodeCallerThresholds,
    FirstEpisodeGapInspectionD,
    inspect_first_episode_gap,
)
from .historical_linkage_guard_d import build_engine_d_coordination_input, evaluate_engine_d_historical_linkage
from .consecutive_stop_counter_d import (
    ConsecutiveStopStateD,
    DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    DEFAULT_D_RESET_FAILSAFE_NS,
    EngineDResetStateInspection,
    EngineDResetStateStatus,
    inspect_engine_d_reset_state,
    record_engine_d_stop,
    record_fresh_a_detection,
    to_coordination_fields,
)
from .coordination_input_assembler_d import EngineDCoordinationAssembly, assemble_engine_d_coordination_input
from .engine_state_snapshot_d import (
    EngineDStateSnapshot,
    EngineDStateSnapshotManifest,
    EngineDStateSnapshotStore,
)
from .runtime_input_assembler_d import EngineDRuntimeInputAssembly, assemble_engine_d_runtime_input

ENGINE_D_BUILD_STAGE = 16
ENGINE_D_IMPLEMENTATION_STATUS = "shadow_capable"

__all__ = [
    "ENGINE_D_BUILD_STAGE",
    "ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_D_FIRST_EPISODE_PROFILE_ID",
    "ENGINE_D_CE_MIN_THRESHOLD_FAMILY_ID",
    "ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_D_COST_PROFILE_ID",
    "ENGINE_D_DELTA_SAFE_THRESHOLD_FAMILY_ID",
    "ENGINE_D_IMPLEMENTATION_STATUS",
    "ENGINE_D_LOOKBACK_THRESHOLD_ID",
    "ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A",
    "ENGINE_D_MARGINAL_VALUE_PROFILE_ID",
    "ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID",
    "ENGINE_D_MIN_GAP_REASON",
    "ENGINE_D_MIN_GAP_THRESHOLD_ID",
    "ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON",
    "EngineDDecision",
    "EngineDInput",
    "EngineDInvalidation",
    "EngineDLogEntry",
    "EngineDMarginalValueCallerThresholds",
    "EngineDOutput",
    "EngineDReentryValidationHook",
    "EngineDReentryValidationInput",
    "EngineDReentryValidationOutcome",
    "EngineDRuntime",
    "EngineDRuntimeInput",
    "EngineDRuntimeResult",
    "EngineDRuntimeStatus",
    "FirstEpisodeGapInspectionD",
    "FirstEpisodeResolutionD",
    "ConsecutiveStopStateD",
    "DEFAULT_D_CONSECUTIVE_STOP_LIMIT",
    "DEFAULT_D_RESET_FAILSAFE_NS",
    "EngineDResetStateInspection",
    "EngineDResetStateStatus",
    "EngineDCoordinationAssembly",
    "EngineDCostCallerThresholds",
    "EngineDFirstEpisodeCallerThresholds",
    "EngineDRuntimeInputAssembly",
    "EngineDStateSnapshot",
    "EngineDStateSnapshotManifest",
    "EngineDStateSnapshotStore",
    "assemble_engine_d_coordination_input",
    "assemble_engine_d_runtime_input",
    "build_engine_d_coordination_input",
    "evaluate_engine_d_historical_linkage",
    "inspect_engine_d_reset_state",
    "record_engine_d_stop",
    "record_fresh_a_detection",
    "inspect_first_episode_gap",
    "marginal_value_floor_cleared",
    "resolve_first_episode",
    "resolve_first_episode_ref",
    "to_coordination_fields",
    "run_engine_d",
]
