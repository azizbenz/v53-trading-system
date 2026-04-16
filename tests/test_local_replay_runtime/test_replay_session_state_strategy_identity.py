"""Focused tests for StrategyIdentity persistence in replay session state."""

from __future__ import annotations

import json
from pathlib import Path

from interface_contracts import (
    BetStructure,
    EngineId,
    ForecastTargetClass,
    ProfileId,
    StrategyIdentity,
    StrategyClassification,
)
from local_replay_runtime import (
    ReplayRunManifest,
    ReplaySessionStateStore,
    ReplaySessionStoreConfig,
    build_replay_session_config,
)


def _manifest_with_optional_strategy_identity() -> ReplayRunManifest:
    return ReplayRunManifest(
        run_id="run-state-identity-1",
        strategy_id="strategy-a",
        strategy_identity=StrategyIdentity(
            engine_id=EngineId.A,
            pair="BTCUSDT",
            regime_bucket="trend_up",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.BREAKOUT,
            calibration_version="calibration.v2",
        ),
        strategy_version="a.v2",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v2.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-state-identity-1",
        timeframe_scope="2026-03-01T00:00:00Z/2026-03-01T00:10:00Z",
        feature_set_version="2.0.0",
        transform_set_version="2.0.0",
        formula_set_version="formula.v2",
        scoring_version="score.v2",
        regime_version="regime.v2",
        risk_policy_version="risk.v2",
        cost_model_version="cost.v2",
        performance_mode="shadow_fidelity_mode",
        artifact_schema_version="2.0.0",
        artifact_hash="artifact-state-identity-1",
        clock_id="clock-state-identity-1",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_600_000,
        tick_count=10,
        record_count=10,
    )


def test_replay_session_state_store_persists_optional_strategy_identity(
    repo_tmp_path: Path,
) -> None:
    output_dir = repo_tmp_path / "session_state_identity"
    session_config = build_replay_session_config(
        _manifest_with_optional_strategy_identity(),
        input_kind="historical_dataset",
        input_path="E:/datasets/replay.json",
        input_record_count=10,
    )
    store = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
        )
    )

    store.initialize(session_config, output_dir=output_dir)

    persisted = json.loads((output_dir / "replay_session_state.json").read_text(encoding="utf-8"))
    reloaded = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
        )
    ).build_state()

    assert persisted["strategy_id"] == "strategy-a"
    assert persisted["strategy_identity"] == {
        "engine_id": "engine_a",
        "pair": "BTCUSDT",
        "regime_bucket": "trend_up",
        "forecast_target_class": "direction_plus_strength_plus_horizon",
        "bet_structure": "breakout",
        "calibration_version": "calibration.v2",
    }
    assert reloaded.strategy_identity is not None
    assert reloaded.strategy_identity.engine_id is EngineId.A
    assert reloaded.strategy_identity.canonical_key == (
        "engine_a:BTCUSDT:trend_up:"
        "direction_plus_strength_plus_horizon:breakout:calibration.v2"
    )


def test_replay_session_state_store_keeps_legacy_strategy_identity_none(
    repo_tmp_path: Path,
) -> None:
    manifest = ReplayRunManifest(
        run_id="run-state-legacy-1",
        strategy_id="strategy-a",
        strategy_version="a.v1",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v1.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-state-legacy-1",
        timeframe_scope="2026-03-01T00:00:00Z/2026-03-01T00:01:00Z",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        formula_set_version="formula.v1",
        scoring_version="score.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode="research_fast_mode",
        artifact_schema_version="1.0.0",
        artifact_hash="artifact-state-legacy-1",
        clock_id="clock-state-legacy-1",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_060_000,
        tick_count=1,
        record_count=1,
    )
    session_config = build_replay_session_config(
        manifest,
        input_kind="historical_dataset",
        input_path="E:/datasets/replay.json",
        input_record_count=1,
    )
    output_dir = repo_tmp_path / "session_state_legacy"
    store = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
        )
    )

    store.initialize(session_config, output_dir=output_dir)

    persisted = json.loads((output_dir / "replay_session_state.json").read_text(encoding="utf-8"))
    reloaded = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
        )
    ).build_state()

    assert persisted["strategy_id"] == "strategy-a"
    assert persisted["strategy_identity"] is None
    assert reloaded.strategy_identity is None
