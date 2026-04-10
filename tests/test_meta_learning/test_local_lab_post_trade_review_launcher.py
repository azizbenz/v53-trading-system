from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from interface_contracts.domain_types import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    export_local_replay_artifact,
)
from local_replay_runtime.replay_metrics_collector import build_replay_metrics_summary
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.shadow_execution_simulator import ReplayParityDiagnosticsSummary
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from scripts.run_local_lab_post_trade_review import main


def _write_replay_dtr_jsonl(path, records) -> None:
    payload = "\n".join(record.model_dump_json() for record in records)
    path.write_text(payload + "\n", encoding="utf-8")


def _build_review_export_markdown(
    *,
    run_id: str,
    strategy_id: str,
    strategy_version: str,
    lineage_version: str,
    profile_scope: str,
    runtime_mode: str,
    performance_mode: str,
    total_opportunities: int,
    total_records: int,
    dtr_coverage: float,
    status: str,
    decision_match_rate: float,
) -> str:
    return "\n".join(
        [
            "# Governed Review Export",
            f"- run_id: {run_id}",
            f"- strategy_id: {strategy_id}",
            f"- strategy_version: {strategy_version}",
            f"- lineage_version: {lineage_version}",
            f"- profile_scope: {profile_scope}",
            f"- runtime_mode: {runtime_mode}",
            f"- performance_mode: {performance_mode}",
            f"- total_opportunities: {total_opportunities}",
            f"- total_records: {total_records}",
            f"- dtr_coverage: {dtr_coverage:.3f}",
            f"- status: {status}",
            f"- decision_match_rate: {decision_match_rate}",
            "",
        ]
    )


def test_run_local_lab_post_trade_review_generates_governed_outputs(repo_tmp_path):
    replay_dtr_path = repo_tmp_path / "replay_dtr.jsonl"
    output_dir = repo_tmp_path / "out"
    records = (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0040,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0042,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_100.0,
        ),
    )
    _write_replay_dtr_jsonl(replay_dtr_path, records)

    exit_code = main(
        [
            "--replay-dtr",
            str(replay_dtr_path),
            "--correlation-id",
            "corr-local-lab",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    meta_runtime = json.loads((output_dir / "meta_runtime_result.json").read_text(encoding="utf-8"))
    bundle = json.loads((output_dir / "meta_learning_review.bundle.json").read_text(encoding="utf-8"))
    projection = json.loads((output_dir / "meta_learning_projection.json").read_text(encoding="utf-8"))
    loss_attribution = json.loads((output_dir / "trade_loss_attribution.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "meta_learning_review.md").read_text(encoding="utf-8")

    assert meta_runtime["dtr_summary"]["total_records"] == 2
    assert bundle["correlation_id"] == "corr-local-lab"
    assert bundle["review_export"]["correlation_id"] == "corr-local-lab"
    assert projection["diagnostics_count"] == len(bundle["diagnostics"])
    assert loss_attribution["correlation_id"] == "corr-local-lab"
    assert loss_attribution["attribution_ready"] is True
    assert "corr-local-lab" in markdown


def test_run_local_lab_post_trade_review_can_scope_by_pair_and_engine(repo_tmp_path):
    replay_dtr_path = repo_tmp_path / "replay_dtr.jsonl"
    output_dir = repo_tmp_path / "scoped"
    records = (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0040,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-b-1",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0012,
            realized_cost=0.0011,
            gross_return=0.0045,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_100.0,
        ),
    )
    _write_replay_dtr_jsonl(replay_dtr_path, records)

    exit_code = main(
        [
            "--replay-dtr",
            str(replay_dtr_path),
            "--correlation-id",
            "corr-local-lab-filtered",
            "--pair",
            "ETHUSDT",
            "--engine-id",
            "engine_b",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    bundle = json.loads((output_dir / "meta_learning_review.bundle.json").read_text(encoding="utf-8"))
    meta_runtime = json.loads((output_dir / "meta_runtime_result.json").read_text(encoding="utf-8"))
    loss_attribution = json.loads((output_dir / "trade_loss_attribution.json").read_text(encoding="utf-8"))
    assert bundle["review_export"]["correlation_id"] == "corr-local-lab-filtered"
    assert bundle["memory_record"]["correlation_id"] == "corr-local-lab-filtered"
    assert len(meta_runtime["records"]) == 1
    assert meta_runtime["records"][0]["pair"] == "ETHUSDT"
    assert meta_runtime["records"][0]["engine_id"] == "engine_b"
    assert loss_attribution["total_records"] == 1
    assert loss_attribution["attributions"][0]["pair"] == "ETHUSDT"


def test_run_local_lab_post_trade_review_direct_script_execution_bootstraps_src(repo_tmp_path):
    replay_dtr_path = repo_tmp_path / "replay_dtr.jsonl"
    output_dir = repo_tmp_path / "direct"
    records = (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0040,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    _write_replay_dtr_jsonl(replay_dtr_path, records)

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_lab_post_trade_review.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--replay-dtr",
            str(replay_dtr_path),
            "--correlation-id",
            "corr-local-lab-direct",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    bundle = json.loads((output_dir / "meta_learning_review.bundle.json").read_text(encoding="utf-8"))
    loss_attribution = json.loads((output_dir / "trade_loss_attribution.json").read_text(encoding="utf-8"))
    assert bundle["correlation_id"] == "corr-local-lab-direct"
    assert loss_attribution["correlation_id"] == "corr-local-lab-direct"


def test_run_local_lab_post_trade_review_can_consume_governed_export_dir(repo_tmp_path):
    export_dir = repo_tmp_path / "export_dir"
    output_dir = repo_tmp_path / "export_review"
    records = (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0040,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0042,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_100.0,
        ),
    )
    metrics = build_replay_metrics_summary(records, total_opportunities=2)
    parity = ReplayParityDiagnosticsSummary(
        parity_status="passed",
        dataset_id="dataset-btc-01",
        decision_match_rate=1.0,
        score_match_rate=1.0,
        baseline_status="available",
        score_alignment="aligned",
        cost_alignment="aligned",
        compared_records=2,
        shared_core_match=True,
        parity_policy={"kind": "test"},
    )
    run_manifest = ReplayRunManifest(
        run_id="run-btc-01",
        strategy_id="strat-btc",
        strategy_version="v5.3",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="v5.3.lineage",
        profile_scope=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        engine_scope=("engine_a",),
        tested_pairs=("BTCUSDT",),
        dataset_manifest_id="dataset-btc-01",
        timeframe_scope="2026-04-01/2026-04-02",
        formula_set_version="formula.v1",
        scoring_version="scoring.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode="shadow_fidelity_mode",
        artifact_hash="artifact-run-btc-01",
        clock_id="clock-run-btc-01",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_000_100_000,
        tick_count=2,
        record_count=2,
    )
    export_local_replay_artifact(
        export_dir,
        ReplayArtifactExportRequest(
            run_manifest=run_manifest,
            review_export_markdown=_build_review_export_markdown(
                run_id=run_manifest.run_id,
                strategy_id=run_manifest.strategy_id,
                strategy_version=run_manifest.strategy_version,
                lineage_version=run_manifest.lineage_version,
                profile_scope=run_manifest.profile_scope.value,
                runtime_mode=run_manifest.runtime_mode.value,
                performance_mode=run_manifest.performance_mode,
                total_opportunities=metrics.total_opportunities,
                total_records=metrics.total_records,
                dtr_coverage=metrics.dtr_coverage,
                status=parity.parity_status,
                decision_match_rate=parity.decision_match_rate,
            ),
            feature_bridge_payload={
                "dataset_id": run_manifest.dataset_manifest_id,
                "feature_set_version": run_manifest.feature_set_version,
                "transform_set_version": run_manifest.transform_set_version,
                "pairs": list(run_manifest.tested_pairs),
                "engines": list(run_manifest.engine_scope),
            },
            parity_diagnostics_payload=parity.model_dump(mode="json"),
            replay_metrics_payload=metrics.model_dump(mode="json"),
            replay_dtr_records=tuple(record.model_dump(mode="json") for record in records),
        ),
    )

    exit_code = main(
        [
            "--export-dir",
            str(export_dir),
            "--correlation-id",
            "corr-local-lab-export-dir",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    bundle = json.loads((output_dir / "meta_learning_review.bundle.json").read_text(encoding="utf-8"))
    input_summary = json.loads((output_dir / "governed_input_summary.json").read_text(encoding="utf-8"))
    meta_runtime = json.loads((output_dir / "meta_runtime_result.json").read_text(encoding="utf-8"))
    loss_attribution = json.loads((output_dir / "trade_loss_attribution.json").read_text(encoding="utf-8"))

    assert bundle["correlation_id"] == "corr-local-lab-export-dir"
    assert input_summary["source_kind"] == "export_dir"
    assert input_summary["run_id"] == "run-btc-01"
    assert input_summary["dataset_manifest_id"] == "dataset-btc-01"
    assert input_summary["selected_pair"] == "BTCUSDT"
    assert input_summary["selected_engine_id"] == "engine_a"
    assert input_summary["filtered_record_count"] == 2
    assert input_summary["total_opportunities"] == 2
    assert meta_runtime["dtr_summary"]["total_records"] == 2
    assert loss_attribution["attribution_ready"] is True
