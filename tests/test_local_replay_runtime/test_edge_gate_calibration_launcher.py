from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import yaml

from calibration_loader import CalibrationArtifact
from interface_contracts.domain_types import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import export_replay_dtr_records
from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    export_local_replay_artifact,
)
from local_replay_runtime.replay_metrics_collector import build_replay_metrics_summary
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.shadow_execution_simulator import ReplayParityDiagnosticsSummary
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from scripts.run_edge_gate_calibration import main


def _scratch_dir() -> Path:
    return Path("build/pytest-edge-gate-launcher") / uuid4().hex


def _records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0008,
            gross_return=0.0038,
            ce_expected=0.0028,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0009,
            gross_return=0.0041,
            ce_expected=0.0030,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-3",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0012,
            realized_cost=0.0010,
            gross_return=0.0040,
            ce_expected=0.0028,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="dtr-4",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0013,
            realized_cost=0.0011,
            gross_return=0.0047,
            ce_expected=0.0034,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
        build_dtr(
            dtr_id="dtr-5",
            pair="SOLUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0014,
            realized_cost=0.0012,
            gross_return=0.0048,
            ce_expected=0.0034,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_240.0,
        ),
        build_dtr(
            dtr_id="dtr-6",
            pair="SOLUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0015,
            realized_cost=0.0013,
            gross_return=0.0050,
            ce_expected=0.0035,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_300.0,
        ),
    )


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


def test_run_edge_gate_calibration_generates_signed_yaml_artifact():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        replay_dtr_path = scratch / "replay_dtr.jsonl"
        replay_dtr_path.write_text(
            "\n".join(json.dumps(item) for item in export_replay_dtr_records(_records())),
            encoding="utf-8",
        )
        output_path = scratch / "edge_gate.yml"

        exit_code = main(
            [
                "--replay-dtr-path",
                str(replay_dtr_path),
                "--output-path",
                str(output_path),
                "--signed-by",
                "operator.aziz",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "5",
                "--min-cost-observations",
                "6",
            ]
        )

        payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        artifact = CalibrationArtifact.model_validate(payload)
        report = json.loads(output_path.with_suffix(".report.json").read_text(encoding="utf-8"))

        assert exit_code == 0
        assert artifact.thresholds[0].threshold_id == "THR-E01"
        assert artifact.thresholds[1].threshold_id == "THR-E02"
        assert artifact.signature.signed_by == "operator.aziz"
        assert report["thresholds"][0]["threshold_id"] == "THR-E01"
        assert report["thresholds"][0]["method_version"] == "stationary_block_bootstrap_v1"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_edge_gate_calibration_can_consume_governed_export_dir():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        output_path = scratch / "edge_gate.yml"
        recalibration_plan_path = scratch / "local_lab_recalibration_plan.json"
        records = _records()
        metrics = build_replay_metrics_summary(records, total_opportunities=len(records))
        parity = ReplayParityDiagnosticsSummary(
            parity_status="passed",
            dataset_id="dataset-edge-01",
            decision_match_rate=1.0,
            score_match_rate=1.0,
            baseline_status="available",
            score_alignment="aligned",
            cost_alignment="aligned",
            compared_records=len(records),
            shared_core_match=True,
            parity_policy={"kind": "test"},
        )
        run_manifest = ReplayRunManifest(
            run_id="run-edge-01",
            strategy_id="strat-edge",
            strategy_version="v5.3",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="v5.3.lineage",
            profile_scope=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            engine_scope=("engine_a", "engine_b", "engine_c"),
            tested_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
            dataset_manifest_id="dataset-edge-01",
            timeframe_scope="2026-04-01/2026-04-02",
            formula_set_version="formula.v1",
            scoring_version="scoring.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_hash="artifact-edge-01",
            clock_id="clock-edge-01",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_300_000,
            tick_count=len(records),
            record_count=len(records),
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
        recalibration_plan_path.write_text(
            json.dumps(
                {
                    "correlation_id": "corr-edge-01",
                    "export_dir": str(export_dir.resolve()),
                    "report_count": 1,
                    "scope_count": 0,
                    "ready_scope_count": 0,
                    "blocked_scope_count": 0,
                    "executed_records": len(records),
                    "losing_trade_count": 0,
                    "dominant_failure_modes": [],
                    "recommended_threshold_ids": [],
                    "action_count": 0,
                    "calibration_candidate_ready": False,
                    "blocking_reasons": ["NO_LOSING_TRADES_TO_RECALIBRATE"],
                    "actions": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--output-path",
                str(output_path),
                "--signed-by",
                "operator.aziz",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "5",
                "--min-cost-observations",
                "6",
                "--recalibration-plan-path",
                str(recalibration_plan_path),
            ]
        )

        payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        artifact = CalibrationArtifact.model_validate(payload)
        input_summary = json.loads(output_path.with_suffix(".input_summary.json").read_text(encoding="utf-8"))
        report = json.loads(output_path.with_suffix(".report.json").read_text(encoding="utf-8"))

        assert exit_code == 0
        assert artifact.thresholds[0].threshold_id == "THR-E01"
        assert report["thresholds"][1]["threshold_id"] == "THR-E02"
        assert input_summary["source_kind"] == "export_dir"
        assert input_summary["run_id"] == "run-edge-01"
        assert input_summary["dataset_manifest_id"] == "dataset-edge-01"
        assert input_summary["record_count"] == len(records)
        assert input_summary["recalibration_plan_ref"].endswith("local_lab_recalibration_plan.json")
        assert input_summary["recalibration_candidate_ready"] is False
        assert input_summary["recalibration_blocking_reasons"] == [
            "NO_LOSING_TRADES_TO_RECALIBRATE"
        ]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
