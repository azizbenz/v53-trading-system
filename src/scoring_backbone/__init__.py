"""Build-5 - scoring_backbone: auditable hard/soft/rank runtime."""

from __future__ import annotations

from .fee_aware_edge_gate import (
    FeeAwareEdgeDecision,
    FeeAwareEdgeGateConfig,
    FeeAwareEdgeThresholds,
    evaluate_fee_aware_edge,
    resolve_fee_aware_edge_thresholds,
)
from .forecast_normalizer import (
    ForecastNormalizationResult,
    ForecastNormalizerConfig,
    compute_raw_forecast,
    normalize_forecast,
    normalize_raw_forecast,
    resolve_forecast_scalar,
)
from .break_even_filter import (
    BreakEvenFilterConfig,
    BreakEvenFilterDecision,
    evaluate_break_even_filter,
)
from .ev_net_floor_thresholds import (
    ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID,
    EvNetFloorThresholdResolution,
    EvNetFloorThresholdResolverConfig,
    build_ev_net_floor_threshold_updates,
    resolve_ev_net_floor_threshold,
)
from .engine_a_cost_thresholds import (
    EngineACostThresholdResolution,
    EngineACostThresholdResolverConfig,
    build_engine_a_cost_threshold_updates,
    resolve_engine_a_cost_thresholds,
)
from .engine_b_cost_thresholds import (
    EngineBCostThresholdResolution,
    EngineBCostThresholdResolverConfig,
    build_engine_b_cost_threshold_updates,
    resolve_engine_b_cost_thresholds,
)
from .engine_b_breakout_thresholds import (
    EngineBBreakoutThresholdResolution,
    EngineBBreakoutThresholdResolverConfig,
    build_engine_b_breakout_threshold_updates,
    resolve_engine_b_breakout_thresholds,
)
from .engine_b_excess_thresholds import (
    EngineBExcessThresholdResolution,
    EngineBExcessThresholdResolverConfig,
    build_engine_b_excess_threshold_updates,
    resolve_engine_b_excess_thresholds,
)
from .engine_b_invalidation_thresholds import (
    EngineBInvalidationThresholdResolution,
    EngineBInvalidationThresholdResolverConfig,
    build_engine_b_invalidation_threshold_updates,
    resolve_engine_b_invalidation_thresholds,
)
from .engine_c_continuation_thresholds import (
    EngineCContinuationThresholdResolution,
    EngineCContinuationThresholdResolverConfig,
    build_engine_c_continuation_threshold_updates,
    resolve_engine_c_continuation_thresholds,
)
from .engine_c_cost_thresholds import (
    EngineCCostThresholdResolution,
    EngineCCostThresholdResolverConfig,
    build_engine_c_cost_threshold_updates,
    resolve_engine_c_cost_thresholds,
)
from .engine_d_coordination_thresholds import (
    EngineDCoordinationThresholdResolution,
    EngineDCoordinationThresholdResolverConfig,
    build_engine_d_coordination_threshold_updates,
    resolve_engine_d_coordination_thresholds,
)
from .engine_d_cost_thresholds import (
    EngineDCostThresholdResolution,
    EngineDCostThresholdResolverConfig,
    build_engine_d_cost_threshold_updates,
    resolve_engine_d_cost_thresholds,
)
from .engine_d_first_episode_thresholds import (
    EngineDFirstEpisodeThresholdResolution,
    EngineDFirstEpisodeThresholdResolverConfig,
    build_engine_d_first_episode_threshold_updates,
    resolve_engine_d_first_episode_thresholds,
)
from .scoring_runtime import (
    ScoringCandidateInput,
    ScoringCandidateAudit,
    ScoringRoundResult,
    ScoringSoftPenaltyLayerHook,
    ScoringSoftPenaltyLayerInput,
    ScoringSoftPenaltyLayerOutcome,
    ScoringRuntime,
)

__all__ = [
    "FeeAwareEdgeDecision",
    "FeeAwareEdgeGateConfig",
    "FeeAwareEdgeThresholds",
    "ForecastNormalizationResult",
    "ForecastNormalizerConfig",
    "BreakEvenFilterConfig",
    "BreakEvenFilterDecision",
    "ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID",
    "EngineACostThresholdResolution",
    "EngineACostThresholdResolverConfig",
    "EngineBBreakoutThresholdResolution",
    "EngineBBreakoutThresholdResolverConfig",
    "EngineBExcessThresholdResolution",
    "EngineBExcessThresholdResolverConfig",
    "EngineBInvalidationThresholdResolution",
    "EngineBInvalidationThresholdResolverConfig",
    "EngineBCostThresholdResolution",
    "EngineBCostThresholdResolverConfig",
    "EngineCContinuationThresholdResolution",
    "EngineCContinuationThresholdResolverConfig",
    "EngineCCostThresholdResolution",
    "EngineCCostThresholdResolverConfig",
    "EngineDCoordinationThresholdResolution",
    "EngineDCoordinationThresholdResolverConfig",
    "EngineDCostThresholdResolution",
    "EngineDCostThresholdResolverConfig",
    "EngineDFirstEpisodeThresholdResolution",
    "EngineDFirstEpisodeThresholdResolverConfig",
    "EvNetFloorThresholdResolution",
    "EvNetFloorThresholdResolverConfig",
    "ScoringCandidateAudit",
    "ScoringCandidateInput",
    "ScoringRoundResult",
    "ScoringSoftPenaltyLayerHook",
    "ScoringSoftPenaltyLayerInput",
    "ScoringSoftPenaltyLayerOutcome",
    "ScoringRuntime",
    "compute_raw_forecast",
    "normalize_forecast",
    "normalize_raw_forecast",
    "resolve_forecast_scalar",
    "evaluate_break_even_filter",
    "evaluate_fee_aware_edge",
    "build_engine_a_cost_threshold_updates",
    "build_engine_b_breakout_threshold_updates",
    "build_engine_b_excess_threshold_updates",
    "build_engine_b_invalidation_threshold_updates",
    "build_engine_b_cost_threshold_updates",
    "build_engine_c_continuation_threshold_updates",
    "build_engine_c_cost_threshold_updates",
    "build_engine_d_coordination_threshold_updates",
    "build_engine_d_cost_threshold_updates",
    "build_engine_d_first_episode_threshold_updates",
    "build_ev_net_floor_threshold_updates",
    "resolve_engine_a_cost_thresholds",
    "resolve_engine_b_breakout_thresholds",
    "resolve_engine_b_excess_thresholds",
    "resolve_engine_b_invalidation_thresholds",
    "resolve_engine_b_cost_thresholds",
    "resolve_engine_c_continuation_thresholds",
    "resolve_engine_c_cost_thresholds",
    "resolve_engine_d_coordination_thresholds",
    "resolve_engine_d_cost_thresholds",
    "resolve_engine_d_first_episode_thresholds",
    "resolve_ev_net_floor_threshold",
    "resolve_fee_aware_edge_thresholds",
]
