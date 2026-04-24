"""Typed Local-Lab ML inputs projected from governed backtest/replay data."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator

ML_BACKTEST_TARGET_POLICY = "net_return_bps_after_route_cost_bps.v1"
ML_BACKTEST_REALIZED_TARGET_POLICY = "net_return_bps_after_replay_realized_cost.v1"
ML_BACKTEST_ROUTE_FEATURE_NAMES = (
    "route_raw_score",
    "route_penalized_score",
    "route_final_score",
    "route_expected_edge_bps",
    "route_spread_bps",
    "route_slippage_bps",
    "route_latency_penalty_bps",
    "route_fill_ratio",
    "route_ranking_position",
    "route_candidate_size",
    "route_final_size",
)


class MlBacktestRouteFeatures(BaseModel, frozen=True):
    """No-lookahead route metrics carried from replay/backtest into ML training."""

    raw_score: float = 0.0
    penalized_score: float = 0.0
    final_score: float = 0.0
    expected_edge_bps: float = 0.0
    spread_bps: float = Field(default=0.0, ge=0.0)
    slippage_bps: float = Field(default=0.0, ge=0.0)
    latency_penalty_bps: float = Field(default=0.0, ge=0.0)
    fill_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    ranking_position: int = Field(default=0, ge=0)
    candidate_size: float = Field(default=0.0, ge=0.0)
    final_size: float = Field(default=0.0, ge=0.0)

    @field_validator("raw_score", "penalized_score", "final_score", "expected_edge_bps")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("MlBacktestRouteFeatures values must be finite")
        return float(value)

    @property
    def route_cost_bps_total(self) -> float:
        return self.spread_bps + self.slippage_bps + self.latency_penalty_bps

    def as_prefixed_feature_map(self) -> dict[str, float]:
        return {
            "route_raw_score": self.raw_score,
            "route_penalized_score": self.penalized_score,
            "route_final_score": self.final_score,
            "route_expected_edge_bps": self.expected_edge_bps,
            "route_spread_bps": self.spread_bps,
            "route_slippage_bps": self.slippage_bps,
            "route_latency_penalty_bps": self.latency_penalty_bps,
            "route_fill_ratio": self.fill_ratio,
            "route_ranking_position": float(self.ranking_position),
            "route_candidate_size": self.candidate_size,
            "route_final_size": self.final_size,
        }


class MlBacktestOutcomeContext(BaseModel, frozen=True):
    """Outcome supervision projected from replay/backtest into ML training."""

    gross_return_bps: float = 0.0
    projected_net_return_bps: float = 0.0
    realized_net_return_bps: float | None = None
    target_decision_state: str | None = None
    production_decision_state: str | None = None
    replay_decision_state: str | None = None
    production_final_score: float | None = None
    production_expected_cost: float | None = Field(default=None, ge=0.0)
    replay_dtr_id: str | None = None
    replay_expected_cost_fraction: float | None = None
    replay_realized_cost_fraction: float | None = None
    replay_gross_return_fraction: float | None = None
    replay_ce_expected_fraction: float | None = None
    primary_reason: str = ""
    hard_block_reasons: tuple[str, ...] = ()

    @field_validator(
        "gross_return_bps",
        "projected_net_return_bps",
        "realized_net_return_bps",
        "production_final_score",
        "replay_expected_cost_fraction",
        "replay_realized_cost_fraction",
        "replay_gross_return_fraction",
        "replay_ce_expected_fraction",
    )
    @classmethod
    def _validate_finite_optional(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("MlBacktestOutcomeContext values must be finite")
        return float(value)


class MlBacktestTrainingSample(BaseModel, frozen=True):
    """Single audit-ready training sample derived from governed replay/backtest."""

    dataset_id: str = Field(..., min_length=1)
    opportunity_id: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    regime: str = ""
    tier: str = ""
    shared_core_match: bool = True
    target_policy: str = Field(default=ML_BACKTEST_TARGET_POLICY, min_length=1)
    recognized_feature_values: dict[str, float]
    route_features: MlBacktestRouteFeatures
    outcome: MlBacktestOutcomeContext

    @field_validator("recognized_feature_values")
    @classmethod
    def _validate_feature_values(cls, value: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for key, item in value.items():
            if not key.strip():
                raise ValueError("MlBacktestTrainingSample feature names must not be blank")
            if not math.isfinite(item):
                raise ValueError("MlBacktestTrainingSample feature values must be finite")
            normalized[key] = float(item)
        return normalized

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.recognized_feature_values))

    @property
    def target_return_fraction(self) -> float:
        if self.outcome.realized_net_return_bps is not None:
            return self.outcome.realized_net_return_bps / 10_000.0
        return self.outcome.projected_net_return_bps / 10_000.0

    def trainer_feature_values(self, *, include_route_features: bool = True) -> dict[str, float]:
        payload = dict(self.recognized_feature_values)
        if include_route_features:
            payload.update(self.route_features.as_prefixed_feature_map())
        return payload


class MlBacktestTrainingDataset(BaseModel, frozen=True):
    """Dataset-level audit-ready projection used before ML artifact training."""

    dataset_id: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    target_policy: str = Field(default=ML_BACKTEST_TARGET_POLICY, min_length=1)
    samples: tuple[MlBacktestTrainingSample, ...] = Field(..., min_length=1)
    pair_scope: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    recognized_feature_keys: tuple[str, ...] = ()
    route_feature_names: tuple[str, ...] = ML_BACKTEST_ROUTE_FEATURE_NAMES
    shared_core_match: bool = True

    @property
    def sample_count(self) -> int:
        return len(self.samples)


__all__ = [
    "ML_BACKTEST_TARGET_POLICY",
    "ML_BACKTEST_REALIZED_TARGET_POLICY",
    "ML_BACKTEST_ROUTE_FEATURE_NAMES",
    "MlBacktestRouteFeatures",
    "MlBacktestOutcomeContext",
    "MlBacktestTrainingSample",
    "MlBacktestTrainingDataset",
]
