"""Tests for the governed LOCAL_REPLAY artifact exporter."""

from __future__ import annotations

import json
from pathlib import Path

from interface_contracts import (
    BetStructure,
    EngineId,
    ForecastTargetClass,
    ProfileId,
    StrategyClassification,
    StrategyIdentity,
)
from local_replay_runtime import (
    ReplayArtifactExportRequest,
    ReplayRunManifest,
    export_local_replay_artifact,
)


def _scratch_dir(repo_tmp_path: Path, name: str) -> Path:
    return repo_tmp_path / name


def _request() -> ReplayArtifactExportRequest:
    return ReplayArtifactExportRequest(
        run_manifest=ReplayRunManifest(
            run_id="run-exporter-1",
            strategy_id="strategy-a-exporter",
            strategy_version="a.v3.0",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v3.0.r1",
            profile_scope=ProfileId.LIGHT,
            engine_scope=("engine_a", "engine_b"),
            tested_pairs=("BTCUSDT", "ETHUSDT"),
            dataset_manifest_id="dataset-exporter-1",
            timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="3.0.0",
        transform_set_version="3.0.0",
        formula_set_version="formula.v3",
            scoring_version="score.v3",
            regime_version="regime.v3",
            risk_policy_version="risk.v3",
            cost_model_version="cost.v3",
            performance_mode="shadow_fidelity_mode",
        artifact_schema_version="3.0.0",
            artifact_hash="artifact-exporter-hash-1",
            clock_id="clock-exporter-1",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_600_000,
            tick_count=600,
            record_count=4096,
        ),
        review_export_markdown="# review\n",
        feature_bridge_payload={
            "bridge": "ok",
            "dataset_id": "dataset-exporter-1",
            "feature_set_version": "3.0.0",
            "transform_set_version": "3.0.0",
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "engines": ["engine_a", "engine_b"],
        },
        parity_diagnostics_payload={
            "parity": "ok",
            "dataset_id": "dataset-exporter-1",
            "decision_match_rate": 1.0,
        },
        replay_metrics_payload={"ce_net": 0.0012, "drawdown_pct": 0.03},
        replay_dtr_records=(
            {"dtr_id": "dtr-1", "pair": "BTCUSDT", "decision": "selected"},
            {"dtr_id": "dtr-2", "pair": "ETHUSDT", "decision": "rejected"},
        ),
    )


def test_export_local_replay_artifact_writes_canonical_export_directory(
    repo_tmp_path: Path,
) -> None:
    output_dir = _scratch_dir(repo_tmp_path, "artifact")
    result = export_local_replay_artifact(output_dir, _request())

    assert result.run_manifest_path.exists()
    assert result.review_export_path.exists()
    assert result.feature_bridge_path.exists()
    assert result.parity_diagnostics_path.exists()
    assert result.replay_metrics_path.exists()
    assert result.replay_dtr_path.exists()
    assert result.payload_refs == (
        str(result.review_export_path.resolve()),
        str(result.feature_bridge_path.resolve()),
        str(result.parity_diagnostics_path.resolve()),
        str(result.replay_metrics_path.resolve()),
        str(result.replay_dtr_path.resolve()),
    )

    run_manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    feature_bridge = json.loads(result.feature_bridge_path.read_text(encoding="utf-8"))
    replay_metrics = json.loads(result.replay_metrics_path.read_text(encoding="utf-8"))
    replay_dtr_lines = result.replay_dtr_path.read_text(encoding="utf-8").strip().splitlines()

    assert run_manifest["run_id"] == "run-exporter-1"
    assert run_manifest["artifact_hash"] == "artifact-exporter-hash-1"
    assert feature_bridge["bridge"] == "ok"
    assert replay_metrics["ce_net"] == 0.0012
    assert len(replay_dtr_lines) == 2


def test_export_local_replay_artifact_serializes_optional_strategy_identity(
    repo_tmp_path: Path,
) -> None:
    output_dir = _scratch_dir(repo_tmp_path, "artifact_with_strategy_identity")
    request = ReplayArtifactExportRequest(
        run_manifest=ReplayRunManifest(
            run_id="run-exporter-identity-1",
            strategy_id="strategy-a-exporter",
            strategy_identity=StrategyIdentity(
                engine_id=EngineId.A,
                pair="BTCUSDT",
                regime_bucket="trend_up",
                forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
                bet_structure=BetStructure.BREAKOUT,
                calibration_version="calibration.v3",
            ),
            strategy_version="a.v3.0",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v3.0.r1",
            profile_scope=ProfileId.LIGHT,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-exporter-identity-1",
            timeframe_scope="2026-03-01/2026-03-31",
            feature_set_version="3.0.0",
            transform_set_version="3.0.0",
            formula_set_version="formula.v3",
            scoring_version="score.v3",
            regime_version="regime.v3",
            risk_policy_version="risk.v3",
            cost_model_version="cost.v3",
            performance_mode="shadow_fidelity_mode",
            artifact_schema_version="3.0.0",
            artifact_hash="artifact-exporter-hash-identity-1",
            clock_id="clock-exporter-identity-1",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_600_000,
            tick_count=600,
            record_count=4096,
        ),
        review_export_markdown="# review\n",
        feature_bridge_payload={"bridge": "ok"},
        parity_diagnostics_payload={"parity": "ok"},
        replay_metrics_payload={"ce_net": 0.0012},
        replay_dtr_records=(),
    )

    result = export_local_replay_artifact(output_dir, request)
    run_manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))

    assert run_manifest["strategy_id"] == "strategy-a-exporter"
    assert run_manifest["strategy_identity"] == {
        "engine_id": "engine_a",
        "pair": "BTCUSDT",
        "regime_bucket": "trend_up",
        "forecast_target_class": "direction_plus_strength_plus_horizon",
        "bet_structure": "breakout",
        "calibration_version": "calibration.v3",
    }
