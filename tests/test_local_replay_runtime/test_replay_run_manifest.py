"""Focused tests for the governed replay run manifest contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    BetStructure,
    EngineId,
    ForecastTargetClass,
    ProfileId,
    StrategyIdentity,
    StrategyClassification,
)
from local_replay_runtime import ReplayRunManifest


def test_replay_run_manifest_accepts_optional_strategy_identity_for_single_scope() -> None:
    manifest = ReplayRunManifest(
        run_id="run-identity-1",
        strategy_id="strategy-a",
        strategy_identity=StrategyIdentity(
            engine_id=EngineId.A,
            pair="btcusdt",
            regime_bucket="vol_high",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.BREAKOUT,
            calibration_version="calibration.v1",
        ),
        strategy_version="a.v1",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v1.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-identity-1",
        timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        formula_set_version="formula.v1",
        scoring_version="score.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode="shadow_fidelity_mode",
        artifact_schema_version="1.0.0",
        artifact_hash="hash-identity-1",
        clock_id="clock-identity-1",
        start_timestamp_ms=1_700,
        end_timestamp_ms=2_000,
    )

    assert manifest.strategy_identity is not None
    assert manifest.strategy_identity.engine_id is EngineId.A
    assert manifest.strategy_identity.pair == "BTCUSDT"
    assert manifest.strategy_identity.canonical_key == (
        "engine_a:BTCUSDT:vol_high:"
        "direction_plus_strength_plus_horizon:breakout:calibration.v1"
    )


def test_replay_run_manifest_rejects_strategy_identity_scope_mismatch() -> None:
    strategy_identity = StrategyIdentity(
        engine_id=EngineId.A,
        pair="BTCUSDT",
        regime_bucket="vol_high",
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=BetStructure.BREAKOUT,
        calibration_version="calibration.v1",
    )

    with pytest.raises(ValidationError):
        ReplayRunManifest(
            run_id="run-identity-2",
            strategy_id="strategy-a",
            strategy_identity=strategy_identity,
            strategy_version="a.v1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v1.r1",
            profile_scope=ProfileId.LIGHT,
            engine_scope=("engine_a", "engine_b"),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-identity-2",
            timeframe_scope="2026-03-01/2026-03-31",
            feature_set_version="1.0.0",
            transform_set_version="1.0.0",
            formula_set_version="formula.v1",
            scoring_version="score.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_schema_version="1.0.0",
            artifact_hash="hash-identity-2",
            clock_id="clock-identity-2",
            start_timestamp_ms=1_700,
            end_timestamp_ms=2_000,
        )

    with pytest.raises(ValidationError):
        ReplayRunManifest(
            run_id="run-identity-3",
            strategy_id="strategy-a",
            strategy_identity=strategy_identity,
            strategy_version="a.v1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v1.r1",
            profile_scope=ProfileId.LIGHT,
            engine_scope=("engine_b",),
            tested_pairs=("ETHUSDT",),
            dataset_manifest_id="dataset-identity-3",
            timeframe_scope="2026-03-01/2026-03-31",
            feature_set_version="1.0.0",
            transform_set_version="1.0.0",
            formula_set_version="formula.v1",
            scoring_version="score.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_schema_version="1.0.0",
            artifact_hash="hash-identity-3",
            clock_id="clock-identity-3",
            start_timestamp_ms=1_700,
            end_timestamp_ms=2_000,
        )
