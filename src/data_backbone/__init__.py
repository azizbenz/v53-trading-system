"""
V5.3 — Data Backbone: reliable, observable data ingestion pipeline.

Sub-modules (in build order):
1. websocket_gateway — connection, subscription, heartbeat, reconnect, raw messages
2. rest_bootstrap — snapshots, rate limiting, gap fill, reporting
3. event_normalizer — schema mapping, timestamps, classification, validation
4. internal_router — consumer registry, priority dispatch, queues, backpressure
5. freshness_checker — age tracking, stale penalties, hard blocks
6. consistency_checker — sequences, gaps, duplicates, contradictions
7. pair_health_scorer — quality aggregation, suspension, recovery, health state
"""

from data_backbone.market_physics_math import (
    Float64,
    TO_CALIBRATE,
    DeltaProxyVariant,
    PHYSICS_FEATURE_ALIASES,
    PhysicsFeatureFamily,
    as_float64,
    require_finite_float64,
    round_float64,
    capratio,
    clip01,
    delta_proxy_sign,
    delta_proxy_soft,
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    participation_ratio,
    sweep_score_v1,
    toxicity_score_v1,
    void_score_discrete,
    zplus,
)

__all__ = [
    "Float64",
    "TO_CALIBRATE",
    "PhysicsFeatureFamily",
    "DeltaProxyVariant",
    "PHYSICS_FEATURE_ALIASES",
    "as_float64",
    "require_finite_float64",
    "round_float64",
    "clip01",
    "zplus",
    "capratio",
    "delta_proxy_soft",
    "delta_proxy_sign",
    "fragility_score_v1",
    "toxicity_score_v1",
    "execution_survivability_score_v1",
    "micro_friction_score_v1",
    "participation_ratio",
    "void_score_discrete",
    "sweep_score_v1",
]
