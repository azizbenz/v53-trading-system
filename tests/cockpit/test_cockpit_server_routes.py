from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
import shutil
import time
from uuid import uuid4
import zipfile

import pytest
from fastapi.testclient import TestClient

from cockpit.action_support import (
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
    PAIR_ARG_INVALID_PATH,
    PAIR_UNIVERSE_AMBIGUOUS,
    RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE,
    estimate_job_progress,
    harvest_manifest_blockers,
    infer_pair_symbol_from_path,
    infer_pair_universe_from_paths,
    is_path_like_pair_token,
    is_valid_raw_source_manifest_path,
    load_backtest_job_records,
)
from cockpit.backtest_preflight import build_patch6_preflight_preview
from cockpit.form_state_support import (
    BacktestFormState,
    LabMlHandoffFormState,
    read_backtest_form_state,
    write_lab_ml_handoff_form_state,
    write_backtest_form_state,
)
from cockpit.backtest_state_support import (
    CockpitPatch6State,
    build_state_consistency,
    read_current_form_state,
    read_launch_request_state,
    write_launch_request_state,
    write_source_preview_state,
)
from cockpit.queue_support import (
    build_dashboard_command_queue_snapshot,
    initialize_dashboard_command_queue,
    resolve_dashboard_command_queue_paths,
)
from cockpit.runtime_support import _read_strategy_ladder_summary, read_runtime_surfaces
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A1,
    PHASE_A2,
    PHASE_B1,
    PHASE_B2,
    ensure_workflow_manifest,
    read_workflow_manifest,
    upsert_workflow_phase,
    workflow_manifest_path,
)
from cockpit import action_support as action_support_module
from cockpit import server as server_module
from cockpit.server import create_app
from cockpit.state import CockpitPaths, build_dashboard_view_model
from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    ProfileId,
    RuntimeMode,
)
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsServiceEvent,
    ShadowVpsServiceState,
)
from local_replay_runtime.governed_audit_evidence_index import (
    build_governed_audit_evidence_entry,
    build_governed_audit_evidence_index,
)
from local_replay_runtime.ml_governance_sidecars import (
    build_ml_anti_leakage_proof_artifact,
    build_ml_live_drift_snapshot,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    build_fixture_expected_edge_artifact,
)
from local_replay_runtime.strategy_ladder_rolling_ml_window_planner import (
    StrategyLadderRollingMlWindowPlannerRequest,
    write_strategy_ladder_rolling_ml_window_plan,
)
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.contracts_artifacts import (
    ArtifactShadowComparisonEvidence,
    ArtifactShadowVerdictBundle,
)
from monitoring.local_observability_stack import LocalObservabilityStackSummary


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _write_ml_handoff_run_fixture(run_root: Path) -> tuple[Path, Path, str]:
    run_root.mkdir(parents=True, exist_ok=True)
    artifact_path = run_root / "strategy_ladder_expected_edge_ml_model_bundle.json"
    artifact_path.write_text("{}", encoding="utf-8")
    rolling_plan_path = run_root / "rolling_ml_window_plan.json"
    rolling_plan_path.write_text("{}", encoding="utf-8")
    (run_root / "rolling_ml_window_plan.md").write_text("# rolling plan", encoding="utf-8")
    artifact_hash = "3df347bc6f5338117e585c5c9c6d802c8ab605def5521fd8fffc953edb4a072d"
    _write_json(
        run_root / "strategy_ladder_backtest_ml_input.json",
        {
            "status": "STRATEGY_LADDER_BACKTEST_ML_INPUT_READY",
            "ml_mode": "ML_MODE_OVERLAY_FROZEN",
            "pair": "BTCUSDT",
            "timeframe": "1m,5m,10m,15m",
            "timeframe_scope": ["1m", "5m", "10m", "15m"],
            "frozen_ml_artifact_path": str(artifact_path),
            "frozen_ml_artifact_hash": artifact_hash,
            "rolling_ml_window_plan_ref": str(rolling_plan_path),
            "requested_backtest_start": "2025-07-18",
            "requested_backtest_end": "2025-08-01",
            "artifact_stale_after": "2025-08-16T23:00:00+00:00",
            "max_valid_backtest_end": "2025-08-16",
            "train_days": 180,
            "validation_days": 30,
            "freshness_days": 30,
            "chunk_days": 15,
        },
    )
    _write_json(
        run_root / "strategy_ladder_ml_lab_handoff_report.json",
        {
            "status": "STRATEGY_LADDER_ML_LAB_HANDOFF_READY",
            "ready": True,
            "pair": "BTCUSDT",
            "timeframe": "1m,5m,10m,15m",
            "feature_names": ["close_return", "high_low_range", "volume"],
            "train_start": "2025-05-02",
            "train_end": "2025-07-17",
            "requested_backtest_start": "2025-07-18",
            "requested_backtest_end": "2025-08-01",
            "artifact_stale_after": "2025-08-16T23:00:00+00:00",
            "max_valid_backtest_end": "2025-08-16",
            "artifact_hash": artifact_hash,
            "rolling_ml_window_plan_ref": str(rolling_plan_path),
            "rolling_ml_window_plan_markdown_ref": str(run_root / "rolling_ml_window_plan.md"),
            "rolling_ml_window_plan_status": "ROLLING_PLAN_READY",
            "rolling_ml_required_artifact_count": 1,
            "train_days": 180,
            "validation_days": 30,
            "freshness_days": 30,
            "chunk_days": 15,
            "blocking_reasons": [],
        },
    )
    _write_json(
        run_root / "strategy_ladder_expected_edge_ml_model_bundle.summary.json",
        {
            "pair": "BTCUSDT",
            "timeframe_scope": ["1m", "5m", "10m", "15m"],
            "feature_names": ["close_return", "high_low_range", "volume"],
        },
    )
    return artifact_path, rolling_plan_path, artifact_hash


def _build_paths(tmp_path: Path) -> CockpitPaths:
    service_dir = tmp_path / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    auto_exports_root = tmp_path / "auto_exports"
    export_dir = auto_exports_root / "2026-04-27"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "analysis.bundle.json").write_text(
        "{}",
        encoding="utf-8",
    )
    _write_json(
        export_dir / "feature_bridge.json",
        {
            "bridge_status": "ok",
            "feature_set_version": "fs-v1",
            "record_count": 40,
            "rows_with_features": 40,
            "missing_feature_rows": 0,
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "engines": ["engine_a", "engine_b", "engine_c", "engine_d"],
            "feature_keys": [
                "snapshot_last_price",
                "snapshot_spread_bps",
                "trade_notional_usdt",
                "trade_is_maker",
            ],
            "recognized_feature_keys": ["snapshot_last_price", "trade_notional_usdt"],
            "unrecognized_feature_keys": ["snapshot_spread_bps", "trade_is_maker"],
            "lineage_lock_status": "missing",
            "lineage_lock_reasons": ["feature_lock_missing"],
            "feature_to_engine_path": "snapshot -> scoring -> engine_a",
        },
    )
    _write_json(
        export_dir / "replay_metrics.json",
        {
            "total_records": 40,
            "total_opportunities": 40,
            "selected_count": 20,
            "executed_count": 20,
            "hard_blocked_count": 4,
            "ce_net": 0.12,
            "pair_aggregates": [
                {"pair": "BTCUSDT", "record_count": 20, "selected_count": 12, "ce_net": 0.08},
                {"pair": "ETHUSDT", "record_count": 20, "selected_count": 8, "ce_net": 0.04},
            ],
            "engine_aggregates": [
                {"engine_id": "engine_a", "record_count": 20, "selected_count": 10, "ce_net": 0.07},
                {"engine_id": "engine_b", "record_count": 20, "selected_count": 10, "ce_net": 0.05},
                {"engine_id": "engine_c", "record_count": 0, "selected_count": 0, "ce_net": 0.0},
                {"engine_id": "engine_d", "record_count": 0, "selected_count": 0, "ce_net": 0.0},
            ],
        },
    )
    live_websocket_config = tmp_path / "live_websocket_config.json"
    _write_json(live_websocket_config, {"pairs": ["BTCUSDT", "ETHUSDT"]})
    _write_json(
        service_dir / "vps_warmup_run.summary.json",
        {
            "runtime_mode": "shadow",
            "final_state": "warmup_ready",
            "eligible_to_trade": True,
            "blocking_reasons": [],
            "report": {
                "checks": [
                    {"check_id": "time_sync", "status": "passed", "reasons": []},
                ]
            },
        },
    )
    active_ml = DashboardArtifactTransferManifest(
        artifact_hash="ml-hash",
        artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
        artifact_id="ml-a1",
        source_ref=str((tmp_path / "artifacts" / "ml-a1.bundle").resolve()),
    )
    shadow_ml = DashboardArtifactTransferManifest(
        artifact_hash="ml-shadow-hash",
        artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
        artifact_id="ml-a2",
        source_ref=str((tmp_path / "artifacts" / "ml-a2.bundle").resolve()),
    )
    active_regime = DashboardArtifactTransferManifest(
        artifact_hash="regime-hash",
        artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
        artifact_id="regime-a1",
        source_ref=str((tmp_path / "artifacts" / "regime-a1.bundle").resolve()),
    )
    shadow_regime = DashboardArtifactTransferManifest(
        artifact_hash="regime-shadow-hash",
        artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
        artifact_id="regime-a2",
        source_ref=str((tmp_path / "artifacts" / "regime-a2.bundle").resolve()),
    )
    ml_evidence_path = tmp_path / "comparisons" / "ml.json"
    regime_evidence_path = tmp_path / "comparisons" / "regime.json"
    verdict_bundle_path = tmp_path / "comparisons" / "verdict.json"
    _write_json(
        ml_evidence_path,
        ArtifactShadowComparisonEvidence(
            artifact_family="ml",
            champion_artifact_id="ml-a1",
            challenger_artifact_id="ml-a2",
            event_count=12,
            decision_diff_rate=0.25,
            expected_ce_delta_mean=0.12,
            comparison_status="shadow_ready",
            sharia_policy_version="policy_v1",
            halal_eligible_event_count=10,
            halal_excluded_event_count=2,
        ).model_dump(mode="json"),
    )
    _write_json(
        regime_evidence_path,
        ArtifactShadowComparisonEvidence(
            artifact_family="regime_detector",
            champion_artifact_id="regime-a1",
            challenger_artifact_id="regime-a2",
            event_count=8,
            decision_diff_rate=0.1,
            comparison_status="shadow_ready",
            sharia_policy_version="policy_v1",
            halal_eligible_event_count=8,
            halal_excluded_event_count=0,
        ).model_dump(mode="json"),
    )
    _write_json(
        verdict_bundle_path,
        ArtifactShadowVerdictBundle(
            session_date="2026-04-27",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=2,
            ready_family_count=2,
            ml_comparison_status="shadow_ready",
            regime_detector_comparison_status="shadow_ready",
            ml_comparison_ref=str(ml_evidence_path.resolve()),
            regime_detector_comparison_ref=str(regime_evidence_path.resolve()),
            sharia_policy_version="policy_v1",
        ).model_dump(mode="json"),
    )
    service_state = ShadowVpsServiceState(
        service_status="running",
        last_completed_session_date="2026-04-27",
        active_ml_artifact=active_ml,
        active_regime_detector_artifact=active_regime,
        shadow_ml_challenger_artifact=shadow_ml,
        shadow_regime_detector_challenger_artifact=shadow_regime,
        last_shadow_ml_artifact_comparison_ref=str(ml_evidence_path.resolve()),
        last_shadow_ml_artifact_comparison_status="shadow_ready",
        last_shadow_regime_detector_artifact_comparison_ref=str(
            regime_evidence_path.resolve()
        ),
        last_shadow_regime_detector_artifact_comparison_status="shadow_ready",
        last_shadow_challenger_verdict_bundle_ref=str(verdict_bundle_path.resolve()),
        last_shadow_challenger_verdict_bundle_status="shadow_ready",
    )
    (service_dir / "shadow_vps_service.state.json").write_text(
        service_state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    monitoring_payload = ShadowVpsServiceMonitoringPayload(
        timestamp_ms=1_714_200_000_000,
        correlation_id="cockpit-test",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status="healthy",
        detail="ok",
        service_status="running",
        loop_count=7,
        last_completed_session_date="2026-04-27",
        last_live_complete_status="shadow_ready",
        last_live_complete_verdict="operator_ready",
        last_live_complete_run_state="steady",
        last_live_complete_operator_report_recommendation="keep_shadow",
        process=ProcessMetricsSample(
            pid=4242,
            cpu_pct=96.0,
            ram_pct=91.0,
            rss_mb=512.0,
            thread_count=11,
            sampling_mode="local_sampler",
        ),
        disk=DiskUsageSample(
            path=str(service_dir.resolve()),
            total_gb=100.0,
            free_gb=9.0,
            used_pct=91.0,
            sampling_mode="local_sampler",
        ),
    )
    (service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
        monitoring_payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    events_path = service_dir / "shadow_vps_service.events.jsonl"
    events = [
        ShadowVpsServiceEvent(
            event_type="service_started",
            message="shadow ready",
            session_date="2026-04-27",
        ),
        ShadowVpsServiceEvent(
            event_type="resource_ram_heartbeat",
            message="heartbeat",
            session_date="2026-04-27",
        ),
    ]
    events_path.write_text(
        "\n".join(event.model_dump_json() for event in events) + "\n",
        encoding="utf-8",
    )
    observability_output_dir = tmp_path / ".local_observability_stack"
    observability_output_dir.mkdir(parents=True, exist_ok=True)
    prom_text_path = observability_output_dir / "shadow.prom"
    prom_text_path.write_text("v53_shadow_vps_process_cpu_pct 96\n", encoding="utf-8")
    dashboard_json_path = observability_output_dir / "shadow.dashboard.json"
    dashboard_json_path.write_text("{}", encoding="utf-8")
    dashboard_summary_path = observability_output_dir / "shadow.summary.json"
    dashboard_summary_path.write_text("{}", encoding="utf-8")
    bootstrap_summary_path = observability_output_dir / "local_grafana_bootstrap.summary.json"
    _write_json(
        bootstrap_summary_path,
        {
            "shadow_vps": {"dashboard_status_code": 200, "dashboard_uid": "shadow-vps"},
            "lab": {"dashboard_status_code": 200, "dashboard_uid": "lab"},
            "build17": {"dashboard_status_code": 200, "dashboard_uid": "build17"},
        },
    )
    local_summary = LocalObservabilityStackSummary(
        output_dir=str(observability_output_dir.resolve()),
        prom_text_path=str(prom_text_path.resolve()),
        dashboard_json_path=str(dashboard_json_path.resolve()),
        dashboard_summary_path=str(dashboard_summary_path.resolve()),
        bootstrap_summary_path=str(bootstrap_summary_path.resolve()),
        prometheus_config_path=str((observability_output_dir / "prom.yml").resolve()),
        bridge_url="http://127.0.0.1:19100/metrics",
        prometheus_url="http://127.0.0.1:9090",
        grafana_url="http://127.0.0.1:3000",
        bridge_status="started",
        prometheus_status="started",
        grafana_status="started",
        bridge_log_path=str((observability_output_dir / "bridge.log").resolve()),
        prometheus_log_path=str((observability_output_dir / "prometheus.log").resolve()),
        grafana_log_path=str((observability_output_dir / "grafana.log").resolve()),
    )
    (observability_output_dir / "local_observability_stack.summary.json").write_text(
        local_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    queue_root = tmp_path / "dashboard_command_queue"
    initialize_dashboard_command_queue(queue_root)
    backtest_jobs_root = tmp_path / "backtest_jobs"
    artifact_ingress_root = tmp_path / "artifact_ingress"
    backtest_jobs_root.mkdir(parents=True, exist_ok=True)
    artifact_ingress_root.mkdir(parents=True, exist_ok=True)
    return CockpitPaths(
        service_dir=service_dir,
        pid_file=tmp_path / "cockpit.pid",
        log_file=service_dir / "shadow_service.log",
        auto_exports_root=auto_exports_root,
        live_websocket_config=live_websocket_config,
        calibration_thresholds=tmp_path / "thresholds.yml",
        build_root=tmp_path / "build_root",
        dashboard_command_queue_root=queue_root,
        observability_output_dir=observability_output_dir,
        backtest_jobs_root=backtest_jobs_root,
        artifact_ingress_root=artifact_ingress_root,
    )


def _build_client(tmp_path: Path) -> TestClient:
    paths = _build_paths(tmp_path)
    app = create_app(
        paths=paths,
        grafana_url="http://127.0.0.1:3000",
        prometheus_url="http://127.0.0.1:9090",
    )
    return TestClient(app)


def _wait_for_path(path: Path, *, timeout_s: float = 5.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path}")


def _wait_for_glob(root: Path, pattern: str, *, timeout_s: float = 5.0) -> Path:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        matches = tuple(root.glob(pattern))
        if matches:
            return matches[0]
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {pattern} under {root}")


def _wait_for_terminal_job(
    jobs_root: Path,
    *,
    timeout_s: float = 5.0,
) -> CockpitBacktestJobRecord:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        records = load_backtest_job_records(jobs_root)
        if records and records[0].status not in {
            CockpitBacktestJobStatus.JOB_CREATED,
            CockpitBacktestJobStatus.JOB_RUNNING,
            CockpitBacktestJobStatus.REQUESTED,
            CockpitBacktestJobStatus.RUNNING,
        }:
            return records[0]
        time.sleep(0.05)
    raise AssertionError("timed out waiting for terminal job status")


def test_cockpit_pages_render_full_navigation_and_logs() -> None:
    scratch = _scratch_dir("cockpit_pages")
    try:
        client = _build_client(scratch)

        response = client.get("/shadow")
        assert response.status_code == 200
        assert 'href="/shadow"' in response.text
        assert 'href="/vps"' in response.text
        assert 'href="/lab"' in response.text
        assert 'href="/backtest"' in response.text
        assert 'href="/observability"' in response.text
        assert 'href="/logs"' in response.text
        assert "Shadow Runtime" in response.text
        assert "Pair Universe Control" in response.text

        assert client.get("/vps").status_code == 200
        lab = client.get("/lab")
        assert lab.status_code == 200
        assert "Feature Families Used" in lab.text
        assert "Artifact Families Visible on VPS" in lab.text
        assert "Strategy Ladder ML Handoff" in lab.text
        assert "ML train window" in lab.text
        assert "active_ml" in lab.text
        backtest = client.get("/backtest")
        assert backtest.status_code == 200
        assert "Launch Local Job" in backtest.text
        assert "Backtest Progress" in backtest.text
        trading = client.get("/trading")
        assert trading.status_code == 200
        assert "Engines active" in trading.text
        assert "Dormant" in trading.text
        observability = client.get("/observability")
        assert observability.status_code == 200
        assert "http://127.0.0.1:9090" in observability.text
        logs = client.get("/logs")
        assert logs.status_code == 200
        assert "shadow ready" in logs.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_surfaces_strategy_ladder_ml_handoff_dates() -> None:
    scratch = _scratch_dir("cockpit_lab_ml_handoff_dates")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        output_root = jobs_root / "strategy_ladder_ml_lab_handoff-1" / "output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "strategy_ladder_ml_lab_handoff_report.json",
            {
                "artifact_id": "edge-handoff",
                "status": "STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
                "ready": False,
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "export_dir": str(output_root),
                "train_start": "2025-01-01",
                "train_end": "2025-04-30",
                "trainer_train_row_count": 180,
                "trainer_validation_row_count": 30,
                "requested_backtest_start": "2025-05-01",
                "requested_backtest_end": "2025-09-07",
                "artifact_stale_after": "2025-05-30T00:00:00Z",
                "max_valid_backtest_end": "2025-05-30",
                "blocking_reasons": ["BACKTEST_WINDOW_EXCEEDS_ARTIFACT_STALE_AFTER"],
                "artifact_hash": "a" * 64,
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-1",
            correlation_id="cockpit-backtest-1",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-08T00:00:00Z",
            output_root=str(output_root),
            record_path=str((jobs_root / "strategy_ladder_ml_lab_handoff-1" / "job.json")),
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))

        lab = client.get("/lab")

        assert lab.status_code == 200
        assert "2025-01-01 → 2025-04-30" in lab.text
        assert "2025-05-01 → 2025-09-07" in lab.text
        assert "2025-05-30" in lab.text
        assert "BACKTEST_WINDOW_EXCEEDS_ARTIFACT_STALE_AFTER" in lab.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_strategy_ladder_ml_handoff_launch_builds_dated_command() -> None:
    scratch = _scratch_dir("cockpit_lab_ml_handoff_launch")
    try:
        client = _build_client(scratch)
        kline_root = scratch / "klines"
        kline_root.mkdir(parents=True, exist_ok=True)

        response = client.post(
            "/lab/strategy-ladder-ml-handoff",
            data={
                "kline_root": str(kline_root),
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "train_start": "2025-01-01",
                "train_end": "2025-04-30",
                "requested_backtest_start": "2025-05-01",
                "requested_backtest_days": "130",
            },
            follow_redirects=False,
        )

        assert response.status_code in {302, 303, 307}
        jobs = load_backtest_job_records(client.app.state.paths.backtest_jobs_root)
        latest = jobs[0]
        command = " ".join(latest.command)
        assert latest.job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF
        assert "run_strategy_ladder_ml_lab_handoff.py" in command
        assert "--train-start 2025-01-01" in command
        assert "--train-end 2025-04-30" in command
        assert "--requested-backtest-start 2025-05-01" in command
        assert "--requested-backtest-days 130" in command
        assert "--train-days 180" in command
        assert "--validation-days 30" in command
        assert "--freshness-days 30" in command
        assert "--chunk-days 30" in command
        assert "--feature-names close_return,high_low_range,volume" in command
        assert "--sample-stride-minutes 60" in command
        assert "--target-horizon-minutes 1" in command
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_surfaces_ml_scientific_provenance_panels() -> None:
    scratch = _scratch_dir("cockpit_lab_ml_scientific_panels")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        output_root = jobs_root / "strategy_ladder_ml_lab_handoff-2" / "output"
        output_root.mkdir(parents=True, exist_ok=True)

        artifact = build_fixture_expected_edge_artifact(
            feature_names=("close_return", "high_low_range", "volume")
        )
        artifact_path = output_root / "strategy_ladder_expected_edge_training" / "strategy_ladder_ml_lab_handoff-2.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(artifact_path, artifact.model_dump(mode="json"))

        training_report_path = artifact_path.parent / "strategy_ladder_ml_lab_handoff-2.training_report.json"
        _write_json(
            training_report_path,
            {
                "artifact_id": "strategy_ladder_ml_lab_handoff-2",
                "status": "STRATEGY_LADDER_EXPECTED_EDGE_ARTIFACT_READY",
                "ready": True,
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "kline_root": "L:\\klines",
                "output_dir": str(artifact_path.parent),
                "artifact_path": str(artifact_path),
                "artifact_hash": artifact.artifact_hash,
                "feature_hash": artifact.feature_hash,
                "dataset_hash": artifact.dataset_hash,
                "feature_names": ["close_return", "high_low_range", "volume"],
                "train_start": "2025-01-01",
                "train_end": "2025-04-30",
                "target_horizon_minutes": 1,
                "sample_stride_minutes": 60,
                "kline_file_count": 120,
                "training_row_count": 480,
                "trainer_train_row_count": 360,
                "trainer_validation_row_count": 120,
                "optuna_trials_used": 0,
                "bagging_folds_used": 5,
                "first_training_timestamp": "2025-01-01T00:00:00+00:00",
                "last_training_timestamp": "2025-04-30T23:59:00+00:00",
                "artifact_stale_after": "2025-05-30T00:00:00+00:00",
                "calibration_version": "strategy_ladder_expected_edge.v1",
                "training_seed": 5307,
                "best_params": {"learning_rate": 0.05, "num_leaves": 31},
                "blocking_reasons": [],
            },
        )

        anti_leakage = build_ml_anti_leakage_proof_artifact(
            artifact,
            test_start=date(2025, 5, 1),
            test_end=date(2025, 5, 30),
        )
        anti_leakage_path = artifact_path.parent / "ml_anti_leakage_proof_artifact.json"
        _write_json(anti_leakage_path, anti_leakage.model_dump(mode="json"))

        live_drift = build_ml_live_drift_snapshot(artifact)
        live_drift_path = artifact_path.parent / "ml_live_drift_snapshot.json"
        _write_json(live_drift_path, live_drift.model_dump(mode="json"))
        rolling_plan = write_strategy_ladder_rolling_ml_window_plan(
            output_root,
            StrategyLadderRollingMlWindowPlannerRequest(
                backtest_start_date="2025-05-01",
                backtest_days=30,
            ),
        )

        _write_json(
            output_root / "strategy_ladder_ml_lab_handoff_report.json",
            {
                "artifact_id": "strategy_ladder_ml_lab_handoff-2",
                "status": "STRATEGY_LADDER_ML_LAB_HANDOFF_READY",
                "ready": True,
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "export_dir": str(output_root),
                "source_artifact_ref": str(artifact_path),
                "transport_artifact_ref": str(output_root / "strategy_ladder_expected_edge_ml_model_artifact.json"),
                "transport_summary_ref": str(output_root / "strategy_ladder_expected_edge_ml_model_artifact.summary.json"),
                "training_report_ref": str(training_report_path),
                "handoff_report_ref": str(output_root / "strategy_ladder_ml_lab_handoff_report.json"),
                "backtest_input_ref": str(output_root / "strategy_ladder_backtest_ml_input.json"),
                "anti_leakage_proof_ref": str(anti_leakage_path),
                "live_drift_snapshot_ref": str(live_drift_path),
                "artifact_hash": artifact.artifact_hash,
                "feature_hash": artifact.feature_hash,
                "dataset_hash": artifact.dataset_hash,
                "feature_names": ["close_return", "high_low_range", "volume"],
                "train_start": "2025-01-01",
                "train_end": "2025-04-30",
                "trainer_train_row_count": 360,
                "trainer_validation_row_count": 120,
                "requested_backtest_start": "2025-05-01",
                "requested_backtest_end": "2025-05-30",
                "artifact_stale_after": "2025-05-30T00:00:00+00:00",
                "max_valid_backtest_end": "2025-05-30",
                "rolling_ml_window_plan_ref": rolling_plan.json_ref,
                "rolling_ml_window_plan_markdown_ref": rolling_plan.markdown_ref,
                "rolling_ml_window_plan_status": rolling_plan.status,
                "rolling_ml_required_artifact_count": rolling_plan.required_artifact_count,
                "train_days": 180,
                "validation_days": 30,
                "freshness_days": 30,
                "chunk_days": 30,
                "backtest_cli_args": ["--ml-mode", "ML_MODE_OVERLAY_FROZEN"],
                "blocking_reasons": [],
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-2",
            correlation_id="cockpit-backtest-2",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-08T00:00:00Z",
            output_root=str(output_root),
            record_path=str((jobs_root / "strategy_ladder_ml_lab_handoff-2" / "job.json")),
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))

        lab = client.get("/lab")

        assert lab.status_code == 200
        assert "Training identity and scientific controls" in lab.text
        assert "Features and Equations" in lab.text
        assert "close_return" in lab.text
        assert "strategy_ladder.expected_edge.target.abs_forward_close_return.v1" in lab.text
        assert "src/local_replay_runtime/strategy_ladder_expected_edge_training.py" in lab.text
        assert "strategy_ladder_expected_edge.v1" in lab.text
        assert "NO_FUTURE_DATA_LEAK_PROVEN" in lab.text
        assert "Rolling ML coverage plan" in lab.text
        assert "ROLLING_PLAN_READY" in lab.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_strategy_ladder_ml_handoff_preview_reuses_backtest_source_scope() -> None:
    scratch = _scratch_dir("cockpit_lab_ml_handoff_preview")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        orderbook_root = scratch / "orderbook" / "BTCUSDT"
        trades_root = scratch / "trades" / "BTCUSDT"
        klines_root = scratch / "klines" / "BTCUSDT" / "1" / "2025"
        metadata_root = scratch / "metadata" / "bybit" / "spot"

        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "2025-04-29_BTCUSDT.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_json(
            metadata_root / "symbol_filters.json",
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "tickSize": "0.01",
                        "stepSize": "0.0001",
                        "minNotional": "5.0",
                    }
                ]
            },
        )

        response = client.post(
            "/lab/strategy-ladder-ml-handoff",
            data={
                "intent": "preview",
                "kline_root": str(scratch / "klines"),
                "orderbook_root": str(scratch / "orderbook"),
                "trades_root": str(scratch / "trades"),
                "metadata_root": str(metadata_root),
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "train_start": "2025-04-29",
                "train_end": "2025-04-29",
                "requested_backtest_days": "30",
            },
            follow_redirects=False,
        )

        assert response.status_code in {302, 303, 307}
        updated_form = read_backtest_form_state(jobs_root)
        assert updated_form.klines_path == str(scratch / "klines")
        assert updated_form.orderbook_path == str(scratch / "orderbook")
        assert updated_form.trades_path == str(scratch / "trades")
        assert updated_form.start == "2025-04-29"
        assert updated_form.end == "2025-04-29"
        preview_payload = _latest_preview_payload(jobs_root)
        assert preview_payload["inspection_status"] == "PHASE_A1_PREVIEW_READY"
        assert preview_payload["matched_files_by_type"]["klines"] >= 1
        assert preview_payload["matched_files_by_type"]["trades"] >= 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_surfaces_preview_rolling_ml_plan_without_handoff_run() -> None:
    scratch = _scratch_dir("cockpit_lab_preview_rolling_plan")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        write_lab_ml_handoff_form_state(
            jobs_root,
            LabMlHandoffFormState(
                pair="BTCUSDT",
                timeframe="1m",
                requested_backtest_start="2025-05-01",
                requested_backtest_days=130,
                train_days=180,
                validation_days=30,
                freshness_days=30,
                chunk_days=30,
            ),
        )

        lab = client.get("/lab")

        assert lab.status_code == 200
        assert "Rolling ML coverage plan" in lab.text
        assert "ROLLING_PLAN_REQUIRES_5_ARTIFACTS" in lab.text
        assert "strategy_ladder_expected_edge.chunk01" in lab.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_status_json_returns_ml_job_progress_without_final_report() -> None:
    scratch = _scratch_dir("lab_status_running_job_only")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_root = jobs_root / "strategy_ladder_ml_lab_handoff-running"
        output_root = scratch / "ml_running_output"
        output_root.mkdir(parents=True, exist_ok=True)
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-running",
            correlation_id="corr-ml-running",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            requested_at_iso="2026-05-17T10:00:00+00:00",
            started_at_iso="2026-05-17T10:00:05+00:00",
            output_root=str(output_root),
            record_path=str((job_root / "job.json").resolve()),
            stdout_log_path=str((job_root / "stdout.log").resolve()),
            pid=os.getpid(),
        )
        _write_json(job_root / "job.json", record.model_dump(mode="json"))

        response = client.get("/lab/status.json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["requested_count"] == 1
        assert payload["summary"]["running_count"] == 1
        assert payload["latest_job"]["job_id"] == "strategy_ladder_ml_lab_handoff-running"
        assert payload["latest_job"]["status"] == "JOB_RUNNING"
        assert payload["handoff"]["job_id"] == "strategy_ladder_ml_lab_handoff-running"
        assert payload["handoff"]["latest_job_status"] == "JOB_RUNNING"
        assert payload["handoff"]["source_status"] == "job_only"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_status_json_reconciles_ml_outputs_into_refs() -> None:
    scratch = _scratch_dir("lab_status_reconcile_outputs")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_root = jobs_root / "strategy_ladder_ml_lab_handoff-stale"
        output_root = scratch / "ml_stale_output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "strategy_ladder_ml_lab_handoff_report.json",
            {
                "artifact_id": "edge-stale",
                "status": "STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
                "ready": False,
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "export_dir": str(output_root),
                "train_start": "2025-01-01",
                "train_end": "2025-01-31",
                "blocking_reasons": ["INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS"],
            },
        )
        _write_json(
            output_root / "strategy_ladder_backtest_ml_input.json",
            {
                "status": "STRATEGY_LADDER_ML_BACKTEST_INPUT_READY",
                "ml_mode": "ML_MODE_OVERLAY_FROZEN",
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-stale",
            correlation_id="corr-ml-stale",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            requested_at_iso="2026-05-17T10:00:00+00:00",
            started_at_iso="2026-05-17T10:00:05+00:00",
            output_root=str(output_root),
            record_path=str((job_root / "job.json").resolve()),
            stdout_log_path=str((job_root / "stdout.log").resolve()),
            pid=999999,
        )
        _write_json(job_root / "job.json", record.model_dump(mode="json"))

        response = client.get("/lab/status.json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["latest_job"]["job_id"] == "strategy_ladder_ml_lab_handoff-stale"
        assert payload["latest_job"]["output_ref_count"] >= 2
        assert payload["latest_job"]["produced_file_count"] >= 2
        assert payload["handoff"]["latest_job_status"] in {
            "JOB_COMPLETED_WITH_BLOCKERS",
            "JOB_FAILED",
        }
        assert "INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS" in payload["handoff"]["latest_job_blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_surfaces_ml_training_progress_panel() -> None:
    scratch = _scratch_dir("lab_page_progress_panel")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_root = jobs_root / "strategy_ladder_ml_lab_handoff-ui"
        output_root = scratch / "ml_ui_output"
        output_root.mkdir(parents=True, exist_ok=True)
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-ui",
            correlation_id="corr-ml-ui",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            requested_at_iso="2026-05-17T10:00:00+00:00",
            started_at_iso="2026-05-17T10:00:05+00:00",
            output_root=str(output_root),
            record_path=str((job_root / "job.json").resolve()),
            stdout_log_path=str((job_root / "stdout.log").resolve()),
            pid=os.getpid(),
        )
        _write_json(job_root / "job.json", record.model_dump(mode="json"))

        response = client.get("/lab")

        assert response.status_code == 200
        assert "ML Training Progress" in response.text
        assert "ML Runner Coverage" in response.text
        assert "Latest job status" in response.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_trading_page_labels_expected_ce_exec_rate_and_proxy_caveat() -> None:
    scratch = _scratch_dir("cockpit_replay_labels")
    try:
        client = _build_client(scratch)

        trading = client.get("/trading")

        assert trading.status_code == 200
        assert "Expected CE net" in trading.text
        assert "Exec rate (executed / total records)" in trading.text
        assert "Gross-return proxy; not net-equity max drawdown and not promotion-grade." in trading.text
        assert "artifact: ARTIFACT_PRESENT_ONLY" in trading.text
        assert "runtime: NOT_PROVEN" in trading.text
        assert "feature-bridge artifact presence is not runtime-consumption proof" in trading.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_trading_page_marks_zero_record_replay_as_not_measured() -> None:
    scratch = _scratch_dir("cockpit_replay_zero_record")
    try:
        paths = _build_paths(scratch)
        replay_path = paths.auto_exports_root / "2026-04-27" / "replay_metrics.json"
        _write_json(
            replay_path,
            {
                "total_records": 0,
                "total_opportunities": 0,
                "selected_count": 0,
                "executed_count": 0,
                "hard_blocked_count": 0,
                "rejected_ranking_count": 0,
                "phantom_count": 0,
                "ce_net": 0.12,
                "pair_aggregates": (),
                "engine_aggregates": (),
            },
        )
        client = TestClient(
            create_app(
                paths=paths,
                grafana_url="http://127.0.0.1:3000",
                prometheus_url="http://127.0.0.1:9090",
            )
        )

        trading = client.get("/trading")

        assert trading.status_code == 200
        assert "not measured yet" in trading.text
        assert "value-warn" in trading.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_trading_page_marks_stale_replay_metrics_as_non_green() -> None:
    scratch = _scratch_dir("cockpit_replay_stale")
    try:
        paths = _build_paths(scratch)
        replay_path = paths.auto_exports_root / "2026-04-27" / "replay_metrics.json"
        stale_epoch = time.time() - 900.0
        os.utime(replay_path, (stale_epoch, stale_epoch))
        client = TestClient(
            create_app(
                paths=paths,
                grafana_url="http://127.0.0.1:3000",
                prometheus_url="http://127.0.0.1:9090",
            )
        )

        trading = client.get("/trading")

        assert trading.status_code == 200
        assert "must not be treated as green" in trading.text
        assert "value-warn" in trading.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_observability_page_falls_back_to_embedded_build17_status() -> None:
    scratch = _scratch_dir("cockpit_observability_build17_embedded")
    try:
        client = _build_client(scratch)
        bootstrap_summary_path = (
            client.app.state.paths.observability_output_dir
            / "local_grafana_bootstrap.summary.json"
        )
        bootstrap_payload = json.loads(
            bootstrap_summary_path.read_text(encoding="utf-8")
        )
        bootstrap_payload.pop("build17", None)
        bootstrap_summary_path.write_text(
            json.dumps(bootstrap_payload, indent=2),
            encoding="utf-8",
        )

        observability = client.get("/observability")
        assert observability.status_code == 200
        assert "Build-17 (embedded in Shadow VPS)" in observability.text
        assert "shadow-vps" in observability.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_import_and_export_actions_enqueue_governed_requests() -> None:
    scratch = _scratch_dir("cockpit_lab_actions")
    try:
        client = _build_client(scratch)
        queue_root = client.app.state.paths.dashboard_command_queue_root
        assert queue_root is not None

        import_response = client.post(
            "/lab/import/ml",
            files={"artifact_file": ("ml.bundle", b"artifact-payload")},
            follow_redirects=False,
        )
        assert import_response.status_code == 303

        export_response = client.post(
            "/lab/export/shadow-verdict",
            follow_redirects=False,
        )
        assert export_response.status_code == 303

        snapshot = build_dashboard_command_queue_snapshot(queue_root)
        assert snapshot.pending_request_count == 2
        assert snapshot.writable is True

        request_dir = resolve_dashboard_command_queue_paths(queue_root).requests_dir
        request_payloads = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(request_dir.glob("*.json"))
        ]
        assert request_payloads[0]["command_kind"] == "request_upload_ml_artifact"
        assert (
            request_payloads[1]["command_kind"]
            == "request_export_shadow_challenger_verdict_bundle"
        )
        ingress_files = list(
            client.app.state.paths.artifact_ingress_root.rglob("ml.bundle")
        )
        assert ingress_files
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_shadow_pair_universe_apply_enqueues_governed_suspend_resume_requests() -> None:
    scratch = _scratch_dir("cockpit_shadow_pair_control")
    try:
        client = _build_client(scratch)
        queue_root = client.app.state.paths.dashboard_command_queue_root
        assert queue_root is not None

        state_path = client.app.state.paths.service_dir / "shadow_vps_service.state.json"
        state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        state_payload["dashboard_control_suspended_pairs"] = ["BTCUSDT"]
        state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")

        response = client.post(
            "/shadow/pairs/apply",
            data={"active_pairs": ["BTCUSDT"], "operator_reason": "study btc only"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        snapshot = build_dashboard_command_queue_snapshot(queue_root)
        assert snapshot.pending_request_count == 2

        request_dir = resolve_dashboard_command_queue_paths(queue_root).requests_dir
        request_payloads = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(request_dir.glob("*.json"))
        ]
        command_pairs = {
            (payload["command_kind"], payload["target_pair"])
            for payload in request_payloads
        }
        assert ("request_pair_resume", "BTCUSDT") in command_pairs
        assert ("suspend_pair", "ETHUSDT") in command_pairs
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_launch_records_audited_job_summary() -> None:
    scratch = _scratch_dir("cockpit_backtest")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        from cockpit.action_support import launch_backtest_job

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.LOCAL_LAB_ANALYSIS_BUNDLE,
            export_dir=scratch / "candidate_export",
            signed_by="tester",
            blocked_reason="MANUAL_AUDITED_JOB_SUMMARY_TEST",
        )
        bundle_path = Path(record.output_root) / "bundle.json"
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text("{}", encoding="utf-8")
        stdout_log_path = Path(record.stdout_log_path)
        stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_log_path.write_text("job completed\n", encoding="utf-8")
        payload = json.loads(Path(record.record_path).read_text(encoding="utf-8"))
        payload["status"] = CockpitBacktestJobStatus.JOB_COMPLETED.value
        payload["finished_at_iso"] = "2026-04-27T12:05:00+00:00"
        payload["output_refs"] = [str(bundle_path.resolve())]
        _write_json(Path(record.record_path), payload)

        page = client.get("/backtest")
        assert page.status_code == 200
        assert record.job_id in page.text
        assert "1 refs" in page.text
        assert "stdout.log" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_strategy_ladder_summary() -> None:
    scratch = _scratch_dir("cockpit_strategy_ladder")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        from cockpit.action_support import launch_backtest_job

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            export_dir=scratch / "strategy_ladder_input",
            signed_by="tester",
            action_name="PHASE_B2_DETAILED_REPLAY",
            phase_id=PHASE_B2,
            workflow_run_id="strategy_ladder_workflow-summary-page",
            operator_output_root=str(scratch / "summary_base"),
            blocked_reason="PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
        )
        stdout_log_path = Path(record.stdout_log_path)
        stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_log_path.write_text("strategy ladder completed with blockers\n", encoding="utf-8")
        summary_path = (
            Path(record.output_root)
            / "backtest_strategy_ladder"
            / record.workflow_run_id
            / "reports"
            / "strategy_ladder_summary.json"
        )
        _write_json(
            summary_path,
            {
                "run_id": record.workflow_run_id,
                "final_status": "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE",
                "feature_store_status": "FEATURE_STORE_READY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_extraction_status": "RAW_WINDOW_PARTIAL",
                "detailed_replay_status": "DETAILED_REPLAY_PARTIAL",
                "capital_profile_generation_status": "CAPITAL_PROFILE_GENERATION_PARTIAL",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
                "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                "statistical_validation_status": "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED",
                "statistical_validation_observation_count": 24,
                "statistical_validation_trial_count": 4,
                "statistical_validation_stationary_block_length": 3,
                "statistical_validation_effective_sample_size": 8.0,
                "statistical_validation_min_trl_required": 31.75,
                "statistical_validation_min_trl_satisfied": False,
                "statistical_validation_sample_sharpe": 0.42,
                "statistical_validation_psr": 0.8123,
                "statistical_validation_psr_passes_floor": False,
                "statistical_validation_dsr": 0.7012,
                "statistical_validation_dsr_passes_floor": False,
                "statistical_validation_blocker_codes": [
                    "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED"
                ],
                "executed_count": 24,
                "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
                "execution_label_source": "PARTIAL_CANONICAL_EXECUTION",
                "spread_model_source": "CANONICAL_SPREAD_GUARD",
                "slippage_model_source": "CANONICAL_EXECUTION_BACKBONE",
                "execution_fidelity_gap_codes": ["PARTIAL_FILL_PROXY"],
                "promotion_blockers": ["PROMOTION_BLOCKED_BY_SAMPLE_SIZE"],
            },
        )
        evidence_index_path = summary_path.parent / "governed_audit_evidence_index.json"
        _write_json(
            evidence_index_path,
            build_governed_audit_evidence_index(
                run_id=record.workflow_run_id,
                source_root=summary_path.parent.parent,
                entries=(
                    build_governed_audit_evidence_entry(
                        rail_id=f"{record.workflow_run_id}:run_manifest",
                        artifact_kind="run_manifest",
                        artifact_ref=str(
                            (summary_path.parent.parent / "run_manifest.json").resolve()
                        ),
                    ),
                    build_governed_audit_evidence_entry(
                        rail_id=f"{record.workflow_run_id}:operator:refusal_ledger",
                        artifact_kind="refusal_ledger",
                        artifact_ref=str(
                            (summary_path.parent.parent / "refusal_ledger.jsonl").resolve()
                        ),
                    ),
                ),
            ).model_dump(mode="json"),
        )
        _write_json(
            Path(record.output_root) / "backtest_proof_matrix.json",
            {
                "overall_backtest_proof_status": "REPLAY_PROTOCOL_PROOF_BLOCKED",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
                "execution_fidelity_gap_codes": ["PARTIAL_FILL_PROXY"],
            },
        )
        payload = json.loads(Path(record.record_path).read_text(encoding="utf-8"))
        payload["status"] = CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS.value
        payload["finished_at_iso"] = "2026-05-03T12:05:00+00:00"
        _write_json(Path(record.record_path), payload)

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Strategy Ladder runner" in page.text
        assert "Strategy Ladder Status" in page.text
        assert "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE" in page.text
        assert "PROMOTION_BLOCKED_BY_SAMPLE_SIZE" in page.text
        assert "REPLAY_PROTOCOL_PROOF_BLOCKED" in page.text
        assert "PARTIAL_FILL_PROXY" in page.text
        assert "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED" in page.text
        assert "Effective sample size" in page.text
        assert "31.75" in page.text
        assert "Governed Audit Evidence" in page.text
        assert "EVIDENCE_AUDIT_NOT_CONFIRMED" in page.text
        assert "run_manifest" in page.text
        assert "refusal_ledger" in page.text
        assert "SCRATCH_ONLY" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_research_only_provenance_alert() -> None:
    scratch = _scratch_dir("cockpit_provenance_alert")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        from cockpit.action_support import launch_backtest_job

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            export_dir=scratch / "strategy_ladder_input",
            signed_by="tester",
            action_name="PHASE_B2_DETAILED_REPLAY",
            phase_id=PHASE_B2,
            workflow_run_id="strategy_ladder_workflow-provenance-alert",
            operator_output_root=str(scratch / "summary_base"),
            blocked_reason="CURRENT_METADATA_PROXY",
        )
        output_root = Path(record.output_root)
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "run_id": record.workflow_run_id,
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "raw_source_provenance_status": "RAW_SOURCE_MANIFEST_GENERATED",
                "raw_source_typing_status": "RAW_SOURCE_TYPE_INFERRED",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_NOT_READY",
                "trade_schema_status": "TRADE_SCHEMA_READY",
                "kline_schema_status": "KLINE_SCHEMA_READY",
                "historical_metadata_status": "BYBIT_HISTORICAL_METADATA_READY",
                "metadata_source_mode": "LOCAL_METADATA_CACHE",
                "metadata_temporal_status": "CURRENT_METADATA_PROXY",
                "metadata_temporal_drift_days": 281.0,
                "fee_provenance_status": "CONFIGURED_FEE_PROVENANCE_READY",
                "blocker_codes": [
                    "RAW_SOURCE_TYPE_INFERRED",
                    "CURRENT_METADATA_PROXY",
                ],
            },
        )
        _write_json(
            output_root / "raw_source_report.json",
            {
                "raw_source_typing_status": "RAW_SOURCE_TYPE_INFERRED",
                "raw_source_provenance_status": "RAW_SOURCE_MANIFEST_GENERATED",
            },
        )
        _write_json(
            output_root / "data_quality_report.json",
            {
                "metadata_temporal_status": "CURRENT_METADATA_PROXY",
                "metadata_fetched_at_utc": "2026-05-05T00:00:00+00:00",
                "metadata_temporal_drift_days": 281.0,
                "raw_source_typing_status": "RAW_SOURCE_TYPE_INFERRED",
            },
        )
        _write_json(
            output_root / "backtest_proof_matrix.json",
            {
                "run_id": record.workflow_run_id,
                "overall_backtest_proof_status": "BACKTEST_PROOF_RESEARCH_ONLY",
                "raw_source_provenance_status": "RAW_SOURCE_MANIFEST_GENERATED",
                "raw_source_typing_status": "RAW_SOURCE_TYPE_INFERRED",
                "metadata_temporal_status": "CURRENT_METADATA_PROXY",
                "metadata_temporal_drift_days": 281.0,
            },
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Research-only provenance alert" in page.text
        assert "RAW_SOURCE_TYPE_INFERRED" in page.text
        assert "temporal drift=281.0 days" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_data_factory_dry_run_action_creates_job_request_and_status() -> None:
    scratch = _scratch_dir("cockpit_patch6_df_dry")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
        )
        assert response.status_code == 303

        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        status_path = request_path.parent / "job_status.json"
        _wait_for_path(request_path)
        _wait_for_path(status_path)
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))

        assert request_payload["job_kind"] == "strategy_ladder_data_factory"
        assert "run_strategy_ladder_data_factory.py" in request_payload["command_preview"]
        assert status_payload["status"] in {
            "JOB_CREATED",
            "JOB_RUNNING",
            "JOB_COMPLETED",
            "JOB_FAILED",
            "JOB_BLOCKED",
        }
        assert not any((request_path.parent / "output").rglob("capital_profiles/*.json"))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_first_controlled_run_dry_run_stays_non_green() -> None:
    scratch = _scratch_dir("cockpit_patch6_first_run_dry")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        response = client.post(
            "/backtest/run",
            data={
                "action_name": "FIRST_CONTROLLED_RUN_DRY_RUN",
                "intent": "preview",
                "export_dir": str(scratch / "patch6_root"),
                "signed_by": "tester",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Patch 6 Controls" in page.text
        assert "PREVIEW_NOT_LAUNCHABLE" in page.text
        assert "ML_MODE_OFF" in page.text
        assert not any(jobs_root.glob("*/job_status.json"))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_dashboard_accepts_checkbox_only_broad_run_confirmation() -> None:
    scratch = _scratch_dir("cockpit_patch6_broad_checkbox_only")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        response = _post_patch6(
            client,
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            export_dir=str(scratch / "patch6_root"),
            allow_broad_run="true",
        )
        assert response.status_code == 303

        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        _wait_for_path(request_path)
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert request_payload["allow_broad_run"] is True
        assert "--allow-broad-run" in request_payload["command_preview"]

        status_path = _wait_for_glob(jobs_root, "*/job_status.json")
        _wait_for_path(status_path)
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert "BROAD_RUN_REQUIRES_ALLOW_BROAD_RUN_CONFIRMATION" not in status_payload["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_dashboard_blocks_ml_training_mode() -> None:
    scratch = _scratch_dir("cockpit_patch6_ml_block")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            ml_mode="ML_MODE_TRAINING_LAB_ONLY",
        )
        assert response.status_code == 303

        status_path = _wait_for_glob(jobs_root, "*/job_status.json")
        _wait_for_path(status_path)
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_payload["status"] == "JOB_BLOCKED"
        assert "ML_TRAINING_DISABLED_FOR_BASELINE" in status_payload["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_sync_does_not_copy_handoff_export_root_into_backtest_output_root() -> None:
    current_form = BacktestFormState(
        export_dir="K:/v5.3 backtest/output2/backtests",
        output_root="K:/v5.3 backtest/output2/backtests",
    )
    lab_form = LabMlHandoffFormState(
        kline_root="L:/klines/BTCUSDT",
        handoff_export_dir="K:/v5.3 backtest/output2/ml_handoffstrategy",
        pair="BTCUSDT",
        train_start="2025-01-01",
        train_end="2025-01-31",
    )

    synced = server_module._sync_lab_handoff_into_backtest_form(current_form, lab_form)

    assert synced.export_dir == "K:/v5.3 backtest/output2/ml_handoffstrategy"
    assert synced.output_root == "K:/v5.3 backtest/output2/backtests"


def test_lab_sync_clears_contaminated_backtest_output_root_when_it_matches_handoff_export_root() -> None:
    current_form = BacktestFormState(
        export_dir="K:/v5.3 backtest/output2/ml_handoffstrategy",
        output_root="K:/v5.3 backtest/output2/ml_handoffstrategy",
    )
    lab_form = LabMlHandoffFormState(
        kline_root="L:/klines/BTCUSDT",
        handoff_export_dir="K:/v5.3 backtest/output2/ml_handoffstrategy",
        pair="BTCUSDT",
        train_start="2025-01-01",
        train_end="2025-01-31",
    )

    synced = server_module._sync_lab_handoff_into_backtest_form(current_form, lab_form)

    assert synced.export_dir == "K:/v5.3 backtest/output2/ml_handoffstrategy"
    assert synced.output_root == ""


def test_patch6_dashboard_blocks_frozen_ml_overlay_for_data_factory() -> None:
    scratch = _scratch_dir("cockpit_patch6_overlay_data_factory_block")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        artifact_path = scratch / "edge_artifact.json"
        artifact_path.write_text("{}", encoding="utf-8")

        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            frozen_ml_artifact_path=str(artifact_path),
            frozen_ml_artifact_hash="deadbeef",
        )
        assert response.status_code == 303

        status_path = _wait_for_glob(jobs_root, "*/job_status.json")
        _wait_for_path(status_path)
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_payload["status"] == "JOB_BLOCKED"
        assert "ML_OVERLAY_UNSUPPORTED_FOR_DATA_FACTORY" in status_payload["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_dashboard_allows_frozen_ml_overlay_for_first_controlled_run() -> None:
    scratch = _scratch_dir("cockpit_patch6_overlay_first_run")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        klines_root = scratch / "klines" / "BTCUSDT" / "1" / "2025"
        klines_root.mkdir(parents=True, exist_ok=True)
        (klines_root / "BTCUSDT_1_2025-01-17.csv").write_text(
            "timestamp,open,high,low,close,volume\n1,1,1,1,1,1\n",
            encoding="utf-8",
        )
        artifact_path = scratch / "edge_artifact.json"
        artifact_path.write_text("{}", encoding="utf-8")

        response = _post_patch6(
            client,
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            export_dir=str(scratch / "patch6_root"),
            klines_path=str(scratch / "klines"),
            pairs="BTCUSDT",
            start="2025-01-17",
            end="2025-01-17",
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            frozen_ml_artifact_path=str(artifact_path),
            frozen_ml_artifact_hash="deadbeef",
        )
        assert response.status_code == 303

        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        _wait_for_path(request_path)
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert request_payload["ml_mode_status"] == "ML_MODE_OVERLAY_FROZEN"
        assert request_payload["frozen_ml_artifact_path"] == str(artifact_path.resolve())
        assert request_payload["frozen_ml_artifact_hash"] == "deadbeef"
        assert "--ml-mode ML_MODE_OVERLAY_FROZEN" in request_payload["command_preview"]
        assert "--frozen-ml-artifact-path" in request_payload["command_preview"]
        assert "--frozen-ml-artifact-hash deadbeef" in request_payload["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_patch6_non_green_summary() -> None:
    scratch = _scratch_dir("cockpit_patch6_summary")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_dir = jobs_root / "strategy_ladder_first_controlled_run-1"
        output_root = job_dir / "output"
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_first_controlled_run-1",
            correlation_id="cockpit-first-run-1",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-03T12:00:00+00:00",
            export_dir=str((scratch / "patch6_root").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_strategy_ladder_first_controlled_run.py"),
            action_name="FIRST_CONTROLLED_RUN_DRY_RUN",
            command_preview="python run_strategy_ladder_first_controlled_run.py --dry-run",
            job_request_path=str((job_dir / "job_request.json").resolve()),
            job_status_path=str((job_dir / "job_status.json").resolve()),
            artifact_inventory_path=str((output_root / "first_run_artifact_inventory.json").resolve()),
            stage_summary_path=str((output_root / "first_run_stage_summary.json").resolve()),
            ml_mode_status="ML_MODE_OFF",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_PARTIAL",
                "raw_source_status": "RAW_SOURCE_MISSING",
                "pair_universe_status": "PAIR_UNIVERSE_PARTIAL",
                "silver_index_status": "SILVER_INDEX_NOT_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_NOT_READY",
                "compression_status": "COMPRESSION_NOT_PROVEN",
                "trade_schema_status": "TRADE_SCHEMA_NOT_PROVEN",
                "kline_schema_status": "KLINE_SCHEMA_NOT_PROVEN",
                "orderbook_schema_status": "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
                "blocker_codes": ["RAW_SOURCE_MISSING"],
            },
        )
        _write_json(
            output_root / "pair_universe_report.json",
            {
                "requested_pairs": ["BTCUSDT", "ETHUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": ["ETHUSDT"],
            },
        )
        _write_json(
            output_root / "first_run_manifest.json",
            {
                "run_id": "strategy_ladder_first_controlled_run-1",
                "first_run_status": "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE",
                "ml_mode_status": "ML_MODE_OFF",
                "blocker_codes": ["GOLD_FEATURE_STORE_NOT_READY"],
            },
        )
        _write_json(
            output_root / "first_run_stage_summary.json",
            {
                "run_id": "strategy_ladder_first_controlled_run-1",
                "stage_statuses": {
                    "first_run_status": "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE",
                    "silver_index_status": "SILVER_INDEX_NOT_READY",
                },
                "blockers": ["ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"],
            },
        )
        _write_json(
            output_root / "first_run_artifact_inventory.json",
            {"run_id": "strategy_ladder_first_controlled_run-1", "artifact_refs": {}},
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Cockpit State Consistency" in page.text
        assert "SILVER_INDEX_NOT_READY" in page.text
        assert "GOLD_FEATURE_STORE_NOT_READY" in page.text
        assert "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN" in page.text
        assert "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_runtime_surfaces_derive_host_and_observability_alerts() -> None:
    scratch = _scratch_dir("cockpit_runtime_surfaces")
    try:
        paths = _build_paths(scratch)
        surfaces = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        alert_ids = {alert.alert_id for alert in surfaces.alerts}
        assert "cockpit:host_cpu_high" in alert_ids
        assert "cockpit:host_ram_high" in alert_ids
        assert "cockpit:host_disk_high" in alert_ids
        assert "cockpit:observability_missing_refs" not in alert_ids
        assert surfaces.observability.source_status == "ok"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Patch 6.6 — pair/path routing, form-state persistence, blocker propagation
# ---------------------------------------------------------------------------


def test_is_path_like_pair_token_classifies_correctly() -> None:
    assert is_path_like_pair_token("L:\\klines\\BTCUSDT\\")
    assert is_path_like_pair_token("C:\\data\\BTCUSDT")
    assert is_path_like_pair_token("/home/data/BTCUSDT")
    assert is_path_like_pair_token("L:/klines/BTCUSDT")
    assert is_path_like_pair_token("./relative/path")
    assert not is_path_like_pair_token("BTCUSDT")
    assert not is_path_like_pair_token("ETHUSDT")
    assert not is_path_like_pair_token("")


def test_infer_pair_symbol_from_path_extracts_leaf_symbol() -> None:
    assert infer_pair_symbol_from_path("L:\\klines\\BTCUSDT\\") == "BTCUSDT"
    assert infer_pair_symbol_from_path("L:/klines/BTCUSDT") == "BTCUSDT"
    assert infer_pair_symbol_from_path(
        "L:\\ordre book part 1\\BTCUSDT\\2025-04-29_BTCUSDT_ob200.data"
    ) == "BTCUSDT"
    assert infer_pair_symbol_from_path("/home/x/ETHUSDT/") == "ETHUSDT"
    assert infer_pair_symbol_from_path("") == ""


def test_command_builder_hard_guard_rejects_path_in_pairs() -> None:
    from cockpit import action_support as action_support_module

    scratch = _scratch_dir("cockpit_hard_guard")
    try:
        jobs_root = scratch / "backtest_jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError, match=PAIR_ARG_INVALID_PATH):
            action_support_module._build_backtest_command(
                job_id="x",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
                export_dir=scratch / "export",
                output_root=scratch / "out",
                baseline_export_dir=None,
                signed_by="tester",
                python_executable="python",
                action_name="DATA_FACTORY_DRY_RUN",
                raw_source_manifest_path=None,
                raw_roots=(),
                pairs=("L:\\klines\\BTCUSDT\\",),
                start="",
                end="",
                allow_broad_run=False,
                ml_mode_status="ML_MODE_OFF",
                engine_native_mode=False,
                engine_native_sample_size=10,
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_reroutes_path_in_pairs_field_to_raw_roots() -> None:
    scratch = _scratch_dir("cockpit_pair_path_block")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            pairs="L:\\klines\\BTCUSDT\\,/home/data/ETHUSDT",
        )
        assert response.status_code == 303
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        _wait_for_path(request_path)
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        # UI rerouting: paths must move to raw_roots, symbols inferred onto pairs
        assert "BTCUSDT" in request_payload["pairs"]
        assert "ETHUSDT" in request_payload["pairs"]
        assert any("klines" in r for r in request_payload["raw_roots"])
        # Hard-guard: --pairs must NEVER receive a path
        preview = request_payload["command_preview"]
        if "--pairs" in preview:
            after_pairs = preview.split("--pairs", 1)[1].split(" --", 1)[0]
            assert ":\\" not in after_pairs
            assert "/" not in after_pairs
            assert "\\" not in after_pairs
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_routes_kline_folder_to_raw_root_not_pairs() -> None:
    scratch = _scratch_dir("cockpit_kline_routing")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            raw_roots="L:\\klines\\BTCUSDT\\",
            pairs="BTCUSDT",
        )
        assert response.status_code == 303
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        _wait_for_path(request_path)
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        preview = payload["command_preview"]
        assert "--raw-root" in preview
        assert "klines" in preview
        # --pairs token must be the symbol, not the path
        if "--pairs" in preview:
            after_pairs = preview.split("--pairs", 1)[1].lstrip().split(" ", 1)[0]
            assert "BTCUSDT" in after_pairs
            assert ":\\" not in after_pairs
            assert "/" not in after_pairs
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_routes_trade_folder_to_raw_root_not_pairs() -> None:
    scratch = _scratch_dir("cockpit_trade_routing")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            raw_roots="L:\\trades\\BTCUSDT\\",
            pairs="BTCUSDT",
        )
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert any("trades" in r for r in payload["raw_roots"])
        preview = payload["command_preview"]
        assert "--raw-root" in preview
        assert "trades" in preview
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_routes_orderbook_data_file_to_raw_root_not_manifest() -> None:
    scratch = _scratch_dir("cockpit_ob_routing")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        ob_path = "L:\\ordre book part 1\\BTCUSDT\\2025-04-29_BTCUSDT_ob200.data"
        _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            raw_roots=ob_path,
            pairs="BTCUSDT",
        )
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert any("ob200" in r or "BTCUSDT" in r for r in payload["raw_roots"])
        # raw-source-manifest must remain empty for an .data orderbook file
        assert payload["raw_source_manifest_path"] == ""
        preview = payload["command_preview"]
        assert "--raw-source-manifest" not in preview
        assert "--raw-root" in preview
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_routes_btcusdt_symbol_to_pairs() -> None:
    scratch = _scratch_dir("cockpit_pair_symbol")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            pairs="BTCUSDT,ETHUSDT",
        )
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert payload["pairs"] == ["BTCUSDT", "ETHUSDT"]
        assert "--pairs BTCUSDT,ETHUSDT" in payload["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_pair_inferred_from_path_but_path_never_in_pairs_arg() -> None:
    scratch = _scratch_dir("cockpit_pair_infer")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        _post_patch6(
            client,
            action_name="DATA_FACTORY_DRY_RUN",
            export_dir=str(scratch / "patch6_root"),
            # operator put the path in the pair field by mistake
            pairs="L:\\klines\\BTCUSDT\\",
        )
        request_path = _wait_for_glob(jobs_root, "*/job_request.json")
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert payload["pairs"] == ["BTCUSDT"]
        assert any("klines" in r for r in payload["raw_roots"])
        preview = payload["command_preview"]
        assert "--pairs BTCUSDT" in preview
        # Path must never appear after --pairs
        if "--pairs" in preview:
            after_pairs = preview.split("--pairs", 1)[1]
            assert "L:\\" not in after_pairs.split(" --")[0]
            assert "L:/" not in after_pairs.split(" --")[0]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_form_persists_raw_roots_after_redirect() -> None:
    scratch = _scratch_dir("cockpit_form_persist_raw")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        client.post(
            "/backtest/run",
            data={
                "action_name": "DATA_FACTORY_DRY_RUN",
                "export_dir": str(scratch / "patch6_root"),
                "raw_roots": "L:\\klines\\BTCUSDT\\,L:\\trades\\BTCUSDT\\",
                "pairs": "BTCUSDT",
                "signed_by": "tester",
            },
            follow_redirects=False,
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "L:\\klines\\BTCUSDT\\" in page.text
        assert "L:\\trades\\BTCUSDT\\" in page.text
        # Sidecar must contain it
        state = read_backtest_form_state(jobs_root)
        assert "L:\\klines\\BTCUSDT\\" in state.raw_roots
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_form_persists_pairs_after_redirect() -> None:
    scratch = _scratch_dir("cockpit_form_persist_pairs")
    try:
        client = _build_client(scratch)
        client.post(
            "/backtest/run",
            data={
                "action_name": "DATA_FACTORY_DRY_RUN",
                "export_dir": str(scratch / "patch6_root"),
                "pairs": "BTCUSDT,ETHUSDT",
                "signed_by": "tester",
            },
            follow_redirects=False,
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert 'value="BTCUSDT,ETHUSDT"' in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_template_keeps_action_name_selection_after_redirect() -> None:
    scratch = _scratch_dir("cockpit_form_persist_action")
    try:
        client = _build_client(scratch)
        client.post(
            "/backtest/run",
            data={
                "action_name": "FIRST_CONTROLLED_RUN_DRY_RUN",
                "export_dir": str(scratch / "patch6_root"),
                "signed_by": "tester",
            },
            follow_redirects=False,
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert (
            'value="PHASE_A1_PREVIEW" selected' in page.text
            or 'value="PHASE_A1_PREVIEW"selected' in page.text
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_manifest_blockers_propagate_via_harvest() -> None:
    scratch = _scratch_dir("cockpit_blocker_harvest_df")
    try:
        output_root = scratch / "output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_BLOCKED_BY_RAW_DATA",
                "blocker_codes": [
                    "DATA_FACTORY_BLOCKED_BY_RAW_DATA",
                    "SILVER_INDEX_NOT_READY",
                ],
            },
        )
        _write_json(
            output_root / "pair_universe_report.json",
            {
                "available_pairs": [],
                "missing_pairs": ["BTCUSDT"],
            },
        )
        blockers, stages = harvest_manifest_blockers(output_root)
        assert "DATA_FACTORY_BLOCKED_BY_RAW_DATA" in blockers
        assert "SILVER_INDEX_NOT_READY" in blockers
        assert "PAIR_UNIVERSE_EMPTY" in blockers
        assert "PAIR_UNIVERSE_MISSING_REQUESTED" in blockers
        assert stages.get("data_factory_status") == "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_first_run_blockers_and_stage_statuses_propagate_via_harvest() -> None:
    scratch = _scratch_dir("cockpit_blocker_harvest_first_run")
    try:
        output_root = scratch / "output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "first_run_manifest.json",
            {
                "first_run_status": "FIRST_RUN_BLOCKED",
                "blocker_codes": ["GOLD_FEATURE_STORE_NOT_READY"],
            },
        )
        _write_json(
            output_root / "first_run_stage_summary.json",
            {
                "stage_statuses": {
                    "first_run_status": "FIRST_RUN_BLOCKED",
                    "silver_index_status": "SILVER_INDEX_NOT_READY",
                },
                "blockers": ["ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"],
            },
        )
        blockers, stages = harvest_manifest_blockers(output_root)
        assert "GOLD_FEATURE_STORE_NOT_READY" in blockers
        assert "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN" in blockers
        assert stages["first_run_status"] == "FIRST_RUN_BLOCKED"
        assert stages["silver_index_status"] == "SILVER_INDEX_NOT_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_job_completed_with_blockers_status_when_manifests_have_blockers(
    monkeypatch,
) -> None:
    from cockpit import action_support as action_support_module

    scratch = _scratch_dir("cockpit_completed_with_blockers")
    try:
        jobs_root = scratch / "backtest_jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)

        class _FakePopen:
            def __init__(self, cmd, **kwargs):  # noqa: ANN001
                self.pid = 43210
                args = list(cmd)
                for idx, token in enumerate(args):
                    if token == "--silver-root" and idx + 1 < len(args):
                        out = Path(args[idx + 1]).parent
                        out.mkdir(parents=True, exist_ok=True)
                        _write_json(
                            out / "data_factory_manifest.json",
                            {
                                "data_factory_status": "DATA_FACTORY_BLOCKED_BY_RAW_DATA",
                                "blocker_codes": ["DATA_FACTORY_BLOCKED_BY_RAW_DATA"],
                            },
                        )
                        break
                kwargs["stdout"].write("ok\n")

            def wait(self, timeout=None):  # noqa: ANN001
                return 0

            def terminate(self) -> None:
                return None

            def kill(self) -> None:
                return None

        monkeypatch.setattr(action_support_module.subprocess, "Popen", _FakePopen)

        record = action_support_module.launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=scratch / "export",
            action_name="DATA_FACTORY_DRY_RUN",
            raw_roots=(Path("L:\\klines\\BTCUSDT\\"),),
            pairs=("BTCUSDT",),
            ml_mode_status="ML_MODE_OFF",
        )
        # wait until subprocess thread completes
        deadline = time.time() + 5.0
        status_path = Path(record.job_status_path)
        while time.time() < deadline:
            try:
                payload = json.loads(status_path.read_text(encoding="utf-8"))
                if payload.get("status") in {
                    "JOB_COMPLETED",
                    "JOB_COMPLETED_WITH_BLOCKERS",
                    "JOB_FAILED",
                }:
                    break
            except (OSError, json.JSONDecodeError):
                pass
            time.sleep(0.05)
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert payload["status"] == "JOB_COMPLETED_WITH_BLOCKERS"
        assert "DATA_FACTORY_BLOCKED_BY_RAW_DATA" in payload["blockers"]
        assert payload["stage_statuses"].get("data_factory_status") == (
            "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_does_not_mix_strategy_ladder_roots() -> None:
    scratch = _scratch_dir("cockpit_strategy_ladder_root_scope")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        older_job_dir = jobs_root / "strategy_ladder_data_factory-older"
        older_output_root = older_job_dir / "output"
        older_record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_data_factory-older",
            correlation_id="cockpit-df-older",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-03T12:00:00+00:00",
            finished_at_iso="2026-05-03T12:05:00+00:00",
            export_dir=str((scratch / "older_export").resolve()),
            output_root=str(older_output_root.resolve()),
            record_path=str((older_job_dir / "job.json").resolve()),
            stdout_log_path=str((older_job_dir / "stdout.log").resolve()),
            command=("python", "run_strategy_ladder_data_factory.py"),
            action_name="DATA_FACTORY_DRY_RUN",
            command_preview="python run_strategy_ladder_data_factory.py --dry-run",
        )
        _write_json(Path(older_record.record_path), older_record.model_dump(mode="json"))
        _write_json(
            older_output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_PARTIAL",
                "raw_source_status": "RAW_SOURCE_MISSING",
                "pair_universe_status": "PAIR_UNIVERSE_PARTIAL",
                "silver_index_status": "SILVER_INDEX_NOT_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_NOT_READY",
                "compression_status": "COMPRESSION_NOT_PROVEN",
                "trade_schema_status": "TRADE_SCHEMA_NOT_PROVEN",
                "kline_schema_status": "KLINE_SCHEMA_NOT_PROVEN",
                "orderbook_schema_status": "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
                "blocker_codes": ["RAW_SOURCE_MISSING"],
            },
        )

        newer_job_dir = jobs_root / "strategy_ladder_runner-newer"
        newer_output_root = newer_job_dir / "output"
        newer_record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_runner-newer",
            correlation_id="cockpit-ladder-newer",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.COMPLETED,
            requested_at_iso="2026-05-03T13:00:00+00:00",
            finished_at_iso="2026-05-03T13:05:00+00:00",
            export_dir=str((scratch / "newer_export").resolve()),
            output_root=str(newer_output_root.resolve()),
            record_path=str((newer_job_dir / "job.json").resolve()),
            stdout_log_path=str((newer_job_dir / "stdout.log").resolve()),
            command=("python", "run_backtest_strategy_ladder.py"),
            command_preview="python run_backtest_strategy_ladder.py",
        )
        _write_json(Path(newer_record.record_path), newer_record.model_dump(mode="json"))
        _write_json(
            newer_output_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_runner-newer"
            / "reports"
            / "strategy_ladder_summary.json",
            {
                "run_id": "strategy_ladder_runner-newer",
                "final_status": "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE",
                "feature_store_status": "FEATURE_STORE_READY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_extraction_status": "RAW_WINDOW_PARTIAL",
                "detailed_replay_status": "DETAILED_REPLAY_PARTIAL",
                "capital_profile_generation_status": "CAPITAL_PROFILE_GENERATION_PARTIAL",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_PARTIAL",
                "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
            },
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE" in page.text
        assert "RAW_SOURCE_MISSING" not in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_prefers_proof_matrix_orderbook_reconstruction_status() -> None:
    scratch = _scratch_dir("cockpit_strategy_ladder_orderbook_precedence")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        job_dir = jobs_root / "strategy_ladder_data_factory-proof"
        output_root = job_dir / "output"
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_data_factory-proof",
            correlation_id="cockpit-df-proof",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-03T12:00:00+00:00",
            finished_at_iso="2026-05-03T12:05:00+00:00",
            export_dir=str((scratch / "export").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_strategy_ladder_data_factory.py"),
            action_name="DATA_FACTORY_DRY_RUN",
            command_preview="python run_strategy_ladder_data_factory.py --dry-run",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_PARTIAL",
                "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
            },
        )
        _write_json(
            output_root / "backtest_proof_matrix.json",
            {
                "overall_backtest_proof_status": "BACKTEST_PROOF_PARTIAL",
                "orderbook_snapshot_status": "READY",
                "orderbook_delta_status": "READY",
                "orderbook_reconstruction_status": "ORDERBOOK_SEQUENCE_GAP",
                "depth20_proof_status": "BOOK_DEPTH_STALE",
            },
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "ORDERBOOK_SEQUENCE_GAP" in page.text
        assert "ORDERBOOK_SCHEMA_READY" not in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_shows_candidate_explorer_and_model_only_warning() -> None:
    scratch = _scratch_dir("cockpit_operator_grade_candidate")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        job_dir = jobs_root / "strategy_ladder_first_controlled_run-operator"
        output_root = job_dir / "output"
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_first_controlled_run-operator",
            correlation_id="cockpit-ladder-operator",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.COMPLETED,
            requested_at_iso="2026-05-03T13:00:00+00:00",
            finished_at_iso="2026-05-03T13:05:00+00:00",
            export_dir=str((scratch / "operator_export").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_strategy_ladder_first_controlled_run.py"),
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            command_preview="python run_strategy_ladder_first_controlled_run.py",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            output_root / "backtest_proof_matrix.json",
            {
                "overall_backtest_proof_status": "BACKTEST_PROOF_RESEARCH_ONLY",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
                "candidate_count": 1,
                "raw_window_count": 1,
                "detailed_replay_count": 1,
                "executed_count": 0,
                "reduced_count": 0,
                "no_fill_count": 1,
                "replay_fee_source_status": "FEE_SOURCE_NOT_PROVEN",
                "replay_impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
                "replay_fill_realism_status": "FILL_REALISM_MODEL_ONLY",
                "replay_cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                "replay_executed_only_net_return_status": "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                "replay_true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS",
                "historical_replay_venue": "BYBIT",
                "execution_target_venue": "BINANCE",
                "backtest_class": "BYBIT_PROXY_BACKTEST",
                "venue_transfer_status": "BINANCE_SHADOW_REQUIRED",
                "live_trading_eligibility_status": "BLOCKED",
                "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
                "execution_label_source": "PARTIAL_CANONICAL_EXECUTION",
                "fee_model_source": "REPLAY_PROXY",
                "spread_model_source": "CANONICAL_SPREAD_GUARD",
                "slippage_model_source": "CANONICAL_EXECUTION_BACKBONE",
                "partial_fill_model_source": "REPLAY_PROXY",
                "adverse_selection_source": "REPLAY_PROXY",
                "order_type_selection_source": "REPLAY_PROXY",
                "venue_constraints_source": "REPLAY_PROXY",
                "execution_fidelity_gap_codes": [
                    "PARTIAL_FILL_PROXY",
                    "VENUE_CONSTRAINTS_PROXY",
                ],
                "ready_metrics": [{"metric_name": "candidate_export_status", "status": "READY"}],
                "metric_gaps": [{"metric_name": "fill_realism_status", "status": "NOT_PROVEN"}],
            },
        )
        run_dir = (
            output_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_first_controlled_run-operator"
        )
        _write_json(
            run_dir / "reports" / "strategy_ladder_summary.json",
            {
                "run_id": "strategy_ladder_first_controlled_run-operator",
                "final_status": "FIRST_RUN_MEASURED_ARTIFACTS_PRODUCED",
                "feature_store_status": "FEATURE_STORE_READY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "capital_profile_generation_status": "CAPITAL_PROFILE_READY",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_READY",
                "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                "expected_edge_label_source": "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
                "expected_edge_label_fidelity": "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
                "expected_edge_anti_leakage_status": "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
                "expected_edge_walkforward_status": "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED",
                "expected_edge_blocker_codes": [
                    "EXPECTED_EDGE_PROXY_BLOCKED",
                    "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH",
                ],
            },
        )
        _write_json(
            run_dir / "run_manifest.json",
            {
                "run_id": "strategy_ladder_first_controlled_run-operator",
                "feature_row_count": 10,
                "expected_edge_proxy_count": 1,
                "expected_edge_governed_count": 0,
                "candidate_engine_native_count": 0,
                "candidate_proxy_count": 1,
                "engine_native_records_built": 0,
            },
        )
        _write_json(
            output_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 10,
                "feature_groups": ["ofi_features"],
                "feature_groups_declared": ["ofi_features"],
                "feature_groups_generated": ["ofi_features"],
                "feature_groups_ready": ["ofi_features"],
            },
        )
        _write_json(
            output_root / "feature_threshold_manifest.json",
            {
                "thresholds_used": [
                    {
                        "threshold_name": "ev_net_floor_bps",
                        "threshold_status": "THRESHOLD_DEFAULT",
                        "calibration_status": "CALIBRATION_NOT_PROVEN",
                    },
                    {
                        "threshold_name": "spread_guard_max_spread_bps",
                        "threshold_status": "THRESHOLD_DEFAULT",
                        "calibration_status": "CALIBRATION_NOT_PROVEN",
                    },
                ]
            },
        )
        _write_json(
            run_dir / "reports" / "pair_matrix.json",
            [
                {
                    "pair": "BTCUSDT",
                    "record_count": 1,
                    "executed_count": 0,
                    "reduced_count": 0,
                    "no_fill_count": 1,
                    "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
                    "impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
                    "fill_realism_status": "FILL_REALISM_MODEL_ONLY",
                    "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                    "executed_only_net_return_status": "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                    "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS",
                    "promotion_status": "PAIR_BLOCKED_COST_COMPLETENESS",
                }
            ],
        )
        _write_json(
            run_dir / "reports" / "engine_matrix.json",
            [
                {
                    "engine_id": "engine_c",
                    "candidate_count": 1,
                    "no_fill_count": 1,
                    "promotion_status": "ENGINE_PROMOTION_BLOCKED_BY_SAMPLE_SIZE",
                }
            ],
        )
        (run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        (run_dir / "fast_candidates" / "candidate_events.jsonl").write_text(
            json.dumps(
                {
                    "candidate_id": "cand-1",
                    "timestamp_ms": 1745884800000,
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "engine_id": "engine_c",
                    "strategy_id": "strategy_ladder",
                    "candidate_source": "COMPAT_FEATURE_DISCOVERY",
                    "preliminary_score": 0.73,
                    "preliminary_reason_codes": ["c.continuation.ofi_persistence"],
                    "feature_refs": ["ofi"],
                    "compatibility_payload": {
                        "feature_values": {"ofi": 0.73},
                        "raw_score": 0.81,
                        "penalized_score": 0.77,
                        "final_score": 0.73,
                        "spread_bps": 4.0,
                        "slippage_bps": 3.0,
                        "expected_edge_bps": 12.0,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        _write_json(
            run_dir / "detailed_replay" / "cand-1.json",
            {
                "candidate_id": "cand-1",
                "pair": "BTCUSDT",
                "engine_id": "engine_c",
                "strategy_id": "strategy_ladder",
                "timestamp_ms": 1745884800000,
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "bucket_results": [
                    {
                        "candidate_id": "cand-1",
                        "pair": "BTCUSDT",
                        "engine_id": "engine_c",
                        "strategy_id": "strategy_ladder",
                        "capital_bucket": 400,
                        "timestamp_ms": 1745884800000,
                        "execution_state": "phantom",
                        "no_fill_flag": True,
                        "expected_ce_net": -0.00023,
                        "executed_only_net_return_status": "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                        "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
                        "impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
                        "fill_realism_status": "FILL_REALISM_MODEL_ONLY",
                        "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        "reason_codes": ["economically_absurd"],
                    }
                ],
            },
        )
        _write_json(
            run_dir / "candidate_replay_windows" / "cand-1.json",
            {
                "candidate_id": "cand-1",
                "raw_window_status": "RAW_WINDOW_READY",
                "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                "source_coverage_status": "RAW_WINDOW_SOURCE_READY",
                "raw_trade_path": "K:/run/trades.jsonl",
                "raw_book_path": "K:/run/orderbook.jsonl",
                "raw_ohlcv_path": "K:/run/ohlcv.jsonl",
                "replay_artifact_path": "K:/run/detailed_replay/cand-1.json",
            },
        )

        page = client.get("/backtest?candidate_id=cand-1")
        assert page.status_code == 200
        assert "Candidate Explorer" in page.text
        assert "cand-1" in page.text
        assert "Replay/fill/cost remains model-only, not proven live." in page.text
        assert "Bybit backtest does not imply Binance live readiness." in page.text
        assert "PIPELINE_READY_ONLY" in page.text
        assert "NOT_PROVEN_SMALL_SAMPLE" in page.text
        assert "EXPECTED_EDGE_NOT_GOVERNED" in page.text
        assert "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY" in page.text
        assert "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN" in page.text
        assert "EXECUTION_FIDELITY_PARTIAL" in page.text
        assert "THRESHOLDS_DEFAULT_NOT_CALIBRATED" in page.text
        assert "default=2, calibrated=0, calibration_not_proven=2" in page.text
        assert "BINANCE_SHADOW_REQUIRED" in page.text
        assert "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY" in page.text
        assert "PROMOTION_ARTIFACTS_READY" not in page.text
        assert "PARTIAL_CANONICAL_EXECUTION" in page.text
        assert "REPLAY_PROTOCOL_PROOF_BLOCKED" in page.text
        assert "VENUE_CONSTRAINTS_PROXY" in page.text
        assert "Selected Candidate Detail" in page.text
        assert "/backtest/candidate-detail.json" in page.text
        assert "data-candidate-select-form" in page.text
        assert 'action="/backtest#candidate-workspace"' in page.text
        detail = client.get("/backtest/candidate-detail.json", params={"candidate_id": "cand-1"})
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["found"] is True
        assert payload["selected_candidate_id"] == "cand-1"
        assert payload["detail"]["engine_id"] == "engine_c"
        assert payload["replay"]["execution_state"] == "phantom"
        assert payload["window"]["raw_window_status"] == "RAW_WINDOW_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_shows_cancelled_partial_artifact_banner() -> None:
    scratch = _scratch_dir("cockpit_operator_grade_cancelled")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        job_dir = jobs_root / "strategy_ladder_first_controlled_run-cancelled"
        output_root = job_dir / "output"
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_first_controlled_run-cancelled",
            correlation_id="cockpit-ladder-cancelled",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_CANCELLED,
            requested_at_iso="2026-05-03T13:00:00+00:00",
            finished_at_iso="2026-05-03T13:05:00+00:00",
            export_dir=str((scratch / "cancelled_export").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_strategy_ladder_first_controlled_run.py"),
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            command_preview="python run_strategy_ladder_first_controlled_run.py",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "trade_schema_status": "TRADE_SCHEMA_READY",
                "kline_schema_status": "KLINE_SCHEMA_READY",
                "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
                "metadata_schema_status": "METADATA_SCHEMA_NOT_PROVEN",
                "compression_status": "COMPRESSION_READY",
                "blocker_codes": [],
            },
        )
        _write_json(
            output_root / "backtest_proof_matrix.json",
            {
                "overall_backtest_proof_status": "BACKTEST_PROOF_RESEARCH_ONLY",
                "candidate_count": 4,
                "raw_window_count": 3,
                "detailed_replay_count": 2,
            },
        )
        _write_json(
            output_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_first_controlled_run-cancelled"
            / "fast_candidates"
            / "candidate_summary.json",
            {
                "candidate_count": 4,
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
            },
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Cancelled after partial artifact production." in page.text
        assert "candidate_count=4" in page.text
        assert "raw_window_count=3" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_lists_temporal_stratified_candidate_mode() -> None:
    scratch = _scratch_dir("backtest_temporal_stratified_mode")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        client = _build_client(scratch)
        page = client.get("/backtest")
        assert page.status_code == 200
        assert 'value="TEMPORAL_STRATIFIED"' in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_ml_handoff_run_folder_check() -> None:
    scratch = _scratch_dir("backtest_ml_handoff_stage3")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        run_root = scratch / "ml_handoffstrategy" / "runs" / "strategy_ladder_ml_lab_handoff-stage3"
        _write_ml_handoff_run_fixture(run_root)
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                phase_id=PHASE_B2,
                workflow_phase=PHASE_B2,
                ml_mode="ML_MODE_OVERLAY_FROZEN",
                ml_handoff_run_root=str(run_root),
            ),
        )

        page = client.get("/backtest")

        assert page.status_code == 200
        assert "IA Lab handoff run folder (preferred)" in page.text
        assert "ML_CHECK_OK" in page.text
        assert "2025-08-16" in page.text
        assert "1m, 5m, 10m, 15m" in page.text
        assert "strategy_ladder_expected_edge_ml_model_bundle.json" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_path_like_pairs_classifier_unit_examples() -> None:
    # Examples from the patch spec
    rejected = [
        "L:\\klines\\BTCUSDT\\",
        "C:\\data\\BTCUSDT",
        "/home/data/BTCUSDT",
    ]
    for token in rejected:
        assert is_path_like_pair_token(token), token
    accepted = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
    for token in accepted:
        assert not is_path_like_pair_token(token), token


# =============================================================================
# Patch 6 Dashboard Redesign — explicit per-data-type fields, manifest typing,
# pair-universe inference, start/end propagation, form persistence, progress.
# =============================================================================


def _post_patch6(
    client: TestClient,
    *,
    action_name: str = "DATA_FACTORY_DRY_RUN",
    intent: str = "launch",
    preview_id: str = "",
    request_hash: str = "",
    workflow_run_id: str = "",
    export_dir: str | None = None,
    baseline_export_dir: str = "",
    orderbook_path: str = "",
    klines_path: str = "",
    trades_path: str = "",
    metadata_path: str = "",
    raw_source_manifest_path: str = "",
    raw_roots: str = "",
    pairs: str = "",
    start: str = "",
    end: str = "",
    output_root: str = "",
    ml_mode: str = "ML_MODE_OFF",
    frozen_ml_artifact_path: str = "",
    frozen_ml_artifact_hash: str = "",
    rolling_ml_window_plan_path: str = "",
    ml_artifact_freshness_days: int = 30,
    confirm_broad_run: str = "",
    allow_broad_run: str = "false",
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG",
    engine_native_sample_size: int = 10,
    b1_5_policy_mode: str = "conservative_hard_only",
    small_scope_enabled: str = "",
    full_scan_enabled: str = "",
    preselected_only: str = "true",
    diagnostic_full_replay: str = "",
    silver_storage_mode: str = "jsonl_gz",
    debug_storage_override: str = "",
):
    def _build_data(
        *,
        request_intent: str,
        request_preview_id: str,
        request_hash_value: str,
        request_workflow_run_id: str,
    ) -> dict[str, str]:
        return {
            "action_name": action_name,
            "intent": request_intent,
            "preview_id": request_preview_id,
            "request_hash": request_hash_value,
            "workflow_run_id": request_workflow_run_id,
            "export_dir": export_dir or "/tmp/redesign_root",
            "baseline_export_dir": baseline_export_dir,
            "orderbook_path": orderbook_path,
            "klines_path": klines_path,
            "trades_path": trades_path,
            "metadata_path": metadata_path,
            "raw_source_manifest_path": raw_source_manifest_path,
            "raw_roots": raw_roots,
            "pairs": pairs,
            "start": start,
            "end": end,
            "output_root": output_root,
            "ml_mode": ml_mode,
            "frozen_ml_artifact_path": frozen_ml_artifact_path,
            "frozen_ml_artifact_hash": frozen_ml_artifact_hash,
            "rolling_ml_window_plan_path": rolling_ml_window_plan_path,
            "ml_artifact_freshness_days": str(ml_artifact_freshness_days),
            "confirm_broad_run": confirm_broad_run,
            "allow_broad_run": allow_broad_run,
            "candidate_discovery_mode": candidate_discovery_mode,
            "engine_native_sample_size": str(engine_native_sample_size),
            "b1_5_policy_mode": b1_5_policy_mode,
            "small_scope_enabled": small_scope_enabled,
            "full_scan_enabled": full_scan_enabled,
            "preselected_only": preselected_only,
            "diagnostic_full_replay": diagnostic_full_replay,
            "silver_storage_mode": silver_storage_mode,
            "debug_storage_override": debug_storage_override,
            "signed_by": "tester",
        }

    request_preview_id = preview_id
    request_hash_value = request_hash
    request_workflow_run_id = workflow_run_id
    if (
        intent == "launch"
        and action_name != "PHASE_A1_PREVIEW"
        and not request_preview_id
        and not request_hash_value
    ):
        preview_response = client.post(
            "/backtest/run",
            data=_build_data(
                request_intent="preview",
                request_preview_id="",
                request_hash_value="",
                request_workflow_run_id=request_workflow_run_id,
            ),
            follow_redirects=False,
        )
        assert preview_response.status_code == 303
        preview_payload = _latest_preview_payload(client.app.state.paths.backtest_jobs_root)
        request_preview_id = str(preview_payload["preview_id"])
        request_hash_value = str(preview_payload["request_hash"])
        request_workflow_run_id = str(preview_payload["workflow_run_id"])

    data = _build_data(
        request_intent=intent,
        request_preview_id=request_preview_id,
        request_hash_value=request_hash_value,
        request_workflow_run_id=request_workflow_run_id,
    )
    return client.post("/backtest/run", data=data, follow_redirects=False)


def _read_latest_job_request(jobs_root: Path) -> dict:
    request_path = _wait_for_glob(jobs_root, "*/job_request.json")
    _wait_for_path(request_path)
    return json.loads(request_path.read_text(encoding="utf-8"))


def _read_latest_job_status(jobs_root: Path) -> dict:
    status_path = _wait_for_glob(jobs_root, "*/job_status.json")
    _wait_for_path(status_path)
    return json.loads(status_path.read_text(encoding="utf-8"))


def _latest_preview_payload(jobs_root: Path) -> dict[str, object]:
    previews_root = jobs_root / "previews"
    manifests = sorted(
        previews_root.glob("*/source_date_preview_manifest.json"),
        key=lambda path: path.stat().st_mtime,
    )
    assert manifests, "expected at least one preview manifest"
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _write_trade_fixture(path: Path, *, timestamp_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "id,timestamp,price,volume,side\n"
        f"1,{timestamp_ms},100.0,1.0,buy\n",
        encoding="utf-8",
    )


def _write_kline_fixture(path: Path, *, timestamp_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "startTime,open,high,low,close,volume,turnover\n"
        f"{timestamp_ms},100,101,99,100.5,10,1005\n",
        encoding="utf-8",
    )


def _copy_orderbook_fixture(target: Path, fixture_name: str = "2025-04-29_BTCUSDT_ob200.data") -> Path:
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "orderbook" / "BTCUSDT"
    source = fixture_root / fixture_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_orderbook_data_field_routes_to_raw_root() -> None:
    scratch = _scratch_dir("redesign_orderbook_data")
    try:
        client = _build_client(scratch)
        ob = "L:\\ordre book part 1\\BTCUSDT\\2025-04-29_BTCUSDT_ob200.data"
        response = _post_patch6(client, orderbook_path=ob)
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert any("ob200.data" in p.lower() for p in request["raw_roots"]), request["raw_roots"]
        assert request.get("raw_source_manifest_path", "") == ""
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_folder_field_routes_to_raw_root() -> None:
    scratch = _scratch_dir("redesign_orderbook_folder")
    try:
        client = _build_client(scratch)
        response = _post_patch6(client, orderbook_path="L:\\orderbook\\BTCUSDT\\")
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert any("orderbook" in p.lower() and "BTCUSDT" in p for p in request["raw_roots"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_kline_folder_field_routes_to_raw_root() -> None:
    scratch = _scratch_dir("redesign_klines")
    try:
        client = _build_client(scratch)
        response = _post_patch6(client, klines_path="L:\\klines\\BTCUSDT\\1")
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert any("klines" in p.lower() and "BTCUSDT" in p for p in request["raw_roots"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_trades_folder_field_routes_to_raw_root() -> None:
    scratch = _scratch_dir("redesign_trades")
    try:
        client = _build_client(scratch)
        response = _post_patch6(client, trades_path="L:\\trades\\BTCUSDT\\")
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert any("trades" in p.lower() and "BTCUSDT" in p for p in request["raw_roots"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_metadata_field_routes_to_historical_metadata_root() -> None:
    scratch = _scratch_dir("redesign_metadata")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            metadata_path="L:\\metadata\\bybit\\spot",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request["historical_metadata_root"].lower().endswith(
            "metadata\\bybit\\spot"
        )
        assert not any("metadata" in p.lower() for p in request["raw_roots"])
        assert request.get("raw_source_manifest_path", "") == ""
        assert "--historical-metadata-root" in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_raw_sources_json_routes_to_raw_source_manifest() -> None:
    scratch = _scratch_dir("redesign_manifest_json")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            klines_path="L:\\klines\\BTCUSDT\\1",
            raw_source_manifest_path="L:\\raw_sources.json",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert "raw_sources.json" in request["raw_source_manifest_path"].lower()
        assert "--raw-source-manifest" in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_in_manifest_field_rejected_with_typed_blocker() -> None:
    scratch = _scratch_dir("redesign_manifest_data_rejected")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            raw_source_manifest_path="L:\\ordre book part 1\\BTCUSDT\\ob200.data",
        )
        assert response.status_code == 303
        status = _read_latest_job_status(client.app.state.paths.backtest_jobs_root)
        assert status["status"] == "JOB_BLOCKED"
        assert RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE in status["blockers"]
        assert "--raw-source-manifest" not in status["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_folder_in_manifest_field_rejected_with_typed_blocker() -> None:
    scratch = _scratch_dir("redesign_manifest_folder_rejected")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            raw_source_manifest_path="L:\\raw_sources\\",
        )
        assert response.status_code == 303
        status = _read_latest_job_status(client.app.state.paths.backtest_jobs_root)
        assert status["status"] == "JOB_BLOCKED"
        assert RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE in status["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_btcusdt_remains_pairs_arg() -> None:
    scratch = _scratch_dir("redesign_btc_pairs")
    try:
        client = _build_client(scratch)
        response = _post_patch6(client, klines_path="L:\\klines\\BTCUSDT\\1", pairs="BTCUSDT")
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert "BTCUSDT" in request["pairs"]
        assert "--pairs" in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_path_in_pairs_never_emitted_as_pairs_flag() -> None:
    scratch = _scratch_dir("redesign_path_in_pairs")
    try:
        client = _build_client(scratch)
        response = _post_patch6(client, pairs="C:\\some\\garbage\\")
        assert response.status_code == 303
        status = _read_latest_job_status(client.app.state.paths.backtest_jobs_root)
        # Hard guarantee: no path appears in the command preview as --pairs argument.
        assert "--pairs C:" not in status["command_preview"]
        assert "--pairs L:" not in status["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_pair_inferred_from_orderbook_or_kline_paths() -> None:
    scratch = _scratch_dir("redesign_infer_pair")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            orderbook_path="L:\\ordre book part 1\\ETHUSDT\\2025-04-29_ETHUSDT_ob200.data",
            klines_path="L:\\klines\\ETHUSDT\\1",
            pairs="",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert "ETHUSDT" in request["pairs"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_ambiguous_inferred_pair_emits_PAIR_UNIVERSE_AMBIGUOUS_blocker() -> None:
    scratch = _scratch_dir("redesign_ambiguous")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            orderbook_path="L:\\ordre book part 1\\BTCUSDT\\ob200.data",
            klines_path="L:\\klines\\ETHUSDT\\1",
            pairs="",
        )
        assert response.status_code == 303
        status = _read_latest_job_status(client.app.state.paths.backtest_jobs_root)
        assert status["status"] == "JOB_BLOCKED"
        assert PAIR_UNIVERSE_AMBIGUOUS in status["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_start_end_propagate_to_job_request_and_command_preview() -> None:
    scratch = _scratch_dir("redesign_start_end")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            klines_path="L:\\klines\\BTCUSDT\\1",
            start="2026-01-01",
            end="2026-01-31",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request["start"] == "2026-01-01"
        assert request["end"] == "2026-01-31"
        assert "--start 2026-01-01" in request["command_preview"]
        assert "--end 2026-01-31" in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_klines_trades_paths_visible_after_submit() -> None:
    scratch = _scratch_dir("redesign_persist_paths")
    try:
        client = _build_client(scratch)
        ob = "L:\\ordre book part 1\\BTCUSDT\\ob200.data"
        kl = "L:\\klines\\BTCUSDT\\1"
        td = "L:\\trades\\BTCUSDT\\"
        _post_patch6(client, orderbook_path=ob, klines_path=kl, trades_path=td)
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "ob200.data" in page.text
        assert "klines" in page.text and "BTCUSDT" in page.text
        assert "trades" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_start_end_visible_after_submit() -> None:
    scratch = _scratch_dir("redesign_persist_dates")
    try:
        client = _build_client(scratch)
        _post_patch6(
            client,
            klines_path="L:\\klines\\BTCUSDT\\1",
            start="2026-03-01",
            end="2026-03-31",
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "2026-03-01" in page.text
        assert "2026-03-31" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_preview_shows_matched_files_before_launch() -> None:
    scratch = _scratch_dir("redesign_preview_before_launch")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "PAIR_DATE_INTERSECTION_READY" in page.text
        assert "Matched files total" in page.text
        assert "2025-04-29" in page.text
        assert "python scripts/run_strategy_ladder_data_factory.py" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_is_blocked_when_no_common_data_intersection_exists() -> None:
    scratch = _scratch_dir("redesign_no_common_intersection")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2023-01-01.csv", timestamp_ms=1_672_531_200_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2023-01-01.csv", timestamp_ms=1_672_531_200_000)
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        status = _read_latest_job_status(client.app.state.paths.backtest_jobs_root)
        assert status["status"] == "JOB_BLOCKED"
        assert "NO_COMMON_DATA_INTERSECTION" in status["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_output_root_collision_is_surfaced_clearly_on_dashboard() -> None:
    scratch = _scratch_dir("redesign_output_root_collision")
    try:
        client = _build_client(scratch)
        collision = scratch / "existing_out"
        collision.mkdir(parents=True, exist_ok=True)
        preview_collision = collision / "runs" / "__preview__"
        preview_collision.mkdir(parents=True, exist_ok=True)
        (preview_collision / "already_here.json").write_text("{}", encoding="utf-8")
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(collision),
        )
        assert response.status_code == 303
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "OUTPUT_ROOT_EXISTS_NON_EMPTY" in page.text
        assert "create timestamped subfolder" in page.text
        assert str(collision) in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_trades_klines_availability_is_shown_separately() -> None:
    scratch = _scratch_dir("redesign_separate_availability")
    try:
        client = _build_client(scratch)
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "ORDERBOOK_NO_FILES_IN_DATE_RANGE" not in page.text
        assert "trades" in page.text
        assert "klines" in page.text
        assert "metadata" in page.text
        assert "SOURCE_PREVIEW_READY" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_pair_auto_detection_ignores_timeframe_folder_and_autofills_pair() -> None:
    scratch = _scratch_dir("redesign_pair_autodetect_timeframe")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            klines_path="L:\\klines\\BTCUSDT\\1",
            pairs="",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request["pairs"] == ["BTCUSDT"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_status_refresh_does_not_wipe_form_values() -> None:
    scratch = _scratch_dir("redesign_persist_refresh")
    try:
        client = _build_client(scratch)
        ob = "L:\\ordre book part 1\\BTCUSDT\\ob200.data"
        _post_patch6(client, orderbook_path=ob, pairs="BTCUSDT")
        for _ in range(3):
            page = client.get("/backtest")
            assert page.status_code == 200
            assert "ob200.data" in page.text
            assert "BTCUSDT" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_pair_mismatch_preview_is_not_launchable() -> None:
    scratch = _scratch_dir("patch6_pair_mismatch_preview")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "ADAUSDT"
        trades_root = scratch / "raw" / "trades" / "ADAUSDT"
        klines_root = scratch / "raw" / "klines" / "ADAUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_ADAUSDT_ob200.data")
        _write_trade_fixture(trades_root / "ADAUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "ADAUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            pairs="BTCUSDT",
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        page = client.get("/backtest")
        assert "PREVIEW_BLOCKED_BY_PAIR_MISMATCH" in page.text
        assert "REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_preview_hash_matches_job_request_for_valid_launch() -> None:
    scratch = _scratch_dir("patch6_preview_hash_launch")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "venue,exchange,market_type,symbol,base_coin,quote_coin,status,tick_size,qty_step,min_order_qty,min_notional,maker_fee_rate,taker_fee_rate,fee_source,metadata_purpose,proof_level,source,fetched_at_utc,raw_payload_hash\n"
            "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.1,0.001,0.001,5,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-06T00:00:00+00:00,abc\n",
            encoding="utf-8",
        )
        _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        # Read the latest generated manifest without assuming the hash in advance.
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        preview_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="launch",
            preview_id=preview_payload["preview_id"],
            request_hash=preview_payload["request_hash"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        request_payload = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request_payload["request_hash"] == preview_payload["request_hash"]
        assert request_payload["preview_id"] == preview_payload["preview_id"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_blocks_when_dates_change_after_preview() -> None:
    scratch = _scratch_dir("patch6_preview_launch_mismatch_dates")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        preview_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="launch",
            preview_id=preview_payload["preview_id"],
            request_hash=preview_payload["request_hash"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-30",
        )
        assert response.status_code == 303
        launch_state = read_launch_request_state(client.app.state.paths.backtest_jobs_root)
        assert launch_state is not None
        assert launch_state.status == "PREVIEW_LAUNCH_MISMATCH"
        assert "end" in launch_state.mismatch_fields
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_preview_date_change_rekeys_workflow_parent_even_with_stale_hidden_id() -> None:
    scratch = _scratch_dir("patch6_preview_date_change_rekeys_workflow")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _copy_orderbook_fixture(orderbook_root / "2025-04-30_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-30.csv",
            timestamp_ms=1_745_971_200_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-30.csv",
            timestamp_ms=1_745_971_200_000,
        )

        _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        first_manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        first_payload = json.loads(first_manifest_path.read_text(encoding="utf-8"))

        _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="preview",
            workflow_run_id=first_payload["workflow_run_id"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-30",
            end="2025-04-30",
        )
        form_state = read_backtest_form_state(client.app.state.paths.backtest_jobs_root)
        source_preview = json.loads(
            (
                client.app.state.paths.backtest_jobs_root / "_source_preview_state.json"
            ).read_text(encoding="utf-8")
        )
        second_manifest = (
            previews_root
            / str(source_preview["preview_id"])
            / "source_date_preview_manifest.json"
        )
        second_payload = json.loads(second_manifest.read_text(encoding="utf-8"))
        assert second_payload["workflow_request_hash"] != first_payload["workflow_request_hash"]
        assert second_payload["workflow_run_id"] == (
            f"strategy_ladder_workflow-{second_payload['workflow_request_hash'][:16]}"
        )
        assert second_payload["workflow_run_id"] != first_payload["workflow_run_id"]
        assert form_state.workflow_run_id == second_payload["workflow_run_id"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_a1_preview_from_scratch_always_creates_new_workflow_id() -> None:
    scratch = _scratch_dir("patch6_a1_preview_always_creates_new_workflow")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )

        _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        first_manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        first_payload = json.loads(first_manifest_path.read_text(encoding="utf-8"))

        _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            workflow_run_id=first_payload["workflow_run_id"],
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        form_state = read_backtest_form_state(client.app.state.paths.backtest_jobs_root)
        source_preview = json.loads(
            (
                client.app.state.paths.backtest_jobs_root / "_source_preview_state.json"
            ).read_text(encoding="utf-8")
        )
        second_manifest = (
            previews_root
            / str(source_preview["preview_id"])
            / "source_date_preview_manifest.json"
        )
        second_payload = json.loads(second_manifest.read_text(encoding="utf-8"))
        assert second_payload["workflow_request_hash"] == first_payload["workflow_request_hash"]
        assert second_payload["workflow_run_id"] != first_payload["workflow_run_id"]
        assert form_state.workflow_run_id == second_payload["workflow_run_id"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_allows_phase_a2_from_matching_phase_a1_preview(monkeypatch) -> None:
    scratch = _scratch_dir("patch6_preview_launch_a1_to_a2")
    try:
        client = _build_client(scratch)
        captured: dict[str, object] = {}
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)

        def _fake_launch_backtest_job(**kwargs):
            captured.update(kwargs)
            return CockpitBacktestJobRecord(
                job_id="strategy_ladder_data_factory-a2-test",
                correlation_id="corr-a2-test",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
                status=CockpitBacktestJobStatus.JOB_CREATED,
                requested_at_iso="2026-05-12T14:10:00+00:00",
                output_root=str(scratch / "out" / "phase_a2_data_factory"),
                record_path=str(scratch / "jobs" / "a2" / "job.json"),
                stdout_log_path=str(scratch / "jobs" / "a2" / "stdout.log"),
                command=("python", "stub.py"),
                action_name=str(kwargs["action_name"]),
                phase_id=str(kwargs["phase_id"]),
                workflow_run_id=str(kwargs["workflow_run_id"]),
                phase_run_id="phase_a2-test",
                preview_id=str(kwargs["preview_id"]),
                request_hash=str(kwargs["request_hash"]),
            )

        monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)
        _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        preview_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        response = _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="launch",
            preview_id=preview_payload["preview_id"],
            request_hash=preview_payload["request_hash"],
            workflow_run_id=preview_payload["workflow_run_id"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        launch_state = read_launch_request_state(client.app.state.paths.backtest_jobs_root)
        assert launch_state is not None
        assert launch_state.status == "JOB_CREATED"
        assert captured["phase_id"] == PHASE_A2
        assert captured["action_name"] == "PHASE_A2_DATA_FACTORY"
        assert captured["workflow_run_id"] == preview_payload["workflow_run_id"]
        assert str(captured["preview_id"]).startswith("preview-")
        assert captured["request_hash"] != preview_payload["request_hash"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_a2_preview_reuses_phase_a1_workflow_when_form_workflow_missing() -> None:
    scratch = _scratch_dir("patch6_phase_a2_preview_reuses_a1_workflow")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(client.app.state.paths.backtest_jobs_root)

        response = _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        a2_preview = _latest_preview_payload(client.app.state.paths.backtest_jobs_root)
        assert a2_preview["workflow_run_id"] == a1_preview["workflow_run_id"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_reuses_workflow_parent_with_mixed_path_separators() -> None:
    scratch = _scratch_dir("patch6_b1_mixed_path_workflow_parent")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=100,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(jobs_root)
        workflow_run_id = str(a1_preview["workflow_run_id"])
        workflow_root = scratch / "export" / "runs" / workflow_run_id
        phase_a2_root = workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export").replace("\\", "/"),
            orderbook_path=str(orderbook_root).replace("\\", "/"),
            trades_path=str(trades_root).replace("\\", "/"),
            klines_path=str(klines_root).replace("\\", "/"),
            metadata_path=str(metadata_root).replace("\\", "/"),
            output_root=str(scratch / "export").replace("\\", "/"),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=100,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
        )
        assert response.status_code == 303
        b1_preview = _latest_preview_payload(jobs_root)
        assert b1_preview["workflow_run_id"] == workflow_run_id
        assert "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS" not in b1_preview["blockers"]
        assert "FEATURE_STORE_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
        assert "SILVER_INDEX_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_reuses_existing_workflow_parent_when_hash_recipe_changes() -> None:
    scratch = _scratch_dir("patch6_b1_existing_workflow_parent_compat")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=100,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(jobs_root)
        original_workflow_root = scratch / "export" / "runs" / str(a1_preview["workflow_run_id"])
        legacy_workflow_run_id = "strategy_ladder_workflow-legacycompat"
        legacy_workflow_root = scratch / "export" / "runs" / legacy_workflow_run_id
        shutil.move(str(original_workflow_root), str(legacy_workflow_root))

        phase_a2_root = legacy_workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=legacy_workflow_run_id,
            export_dir=str(scratch / "export").replace("\\", "/"),
            orderbook_path=str(orderbook_root).replace("\\", "/"),
            trades_path=str(trades_root).replace("\\", "/"),
            klines_path=str(klines_root).replace("\\", "/"),
            metadata_path=str(metadata_root).replace("\\", "/"),
            output_root=str(scratch / "export").replace("\\", "/"),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=100,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
        )
        assert response.status_code == 303
        b1_preview = _latest_preview_payload(jobs_root)
        assert b1_preview["workflow_run_id"] == legacy_workflow_run_id
        assert "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS" not in b1_preview["blockers"]
        assert "FEATURE_STORE_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
        assert "SILVER_INDEX_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_reuses_existing_workflow_when_ml_mode_changes() -> None:
    scratch = _scratch_dir("patch6_b1_reuses_workflow_when_ml_mode_changes")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(jobs_root)
        workflow_run_id = str(a1_preview["workflow_run_id"])
        workflow_root = scratch / "export" / "runs" / workflow_run_id
        phase_a2_root = workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export").replace("\\", "/"),
            orderbook_path=str(orderbook_root).replace("\\", "/"),
            trades_path=str(trades_root).replace("\\", "/"),
            klines_path=str(klines_root).replace("\\", "/"),
            metadata_path=str(metadata_root).replace("\\", "/"),
            output_root=str(scratch / "export").replace("\\", "/"),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            frozen_ml_artifact_hash="abc123",
        )
        assert response.status_code == 303
        b1_preview = _latest_preview_payload(jobs_root)
        assert b1_preview["workflow_run_id"] == workflow_run_id
        assert "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS" not in b1_preview["blockers"]
        assert "FEATURE_STORE_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
        assert "SILVER_INDEX_NOT_MATERIALIZED_FOR_B1" not in b1_preview["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_blocks_when_a2_manifest_is_critically_blocked() -> None:
    scratch = _scratch_dir("patch6_b1_blocks_on_a2_critical")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text("symbol\nBTCUSDT\n", encoding="utf-8")

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        workflow_run_id = str(_latest_preview_payload(jobs_root)["workflow_run_id"])
        phase_a2_root = scratch / "export" / "runs" / workflow_run_id / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS",
                "blocker_codes": ["OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED"],
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        preview = _latest_preview_payload(jobs_root)
        assert "A2_BLOCKED_UPSTREAM:DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS" in preview["blockers"]
        assert preview["inspection_status"] == "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_allows_a2_research_only_blockers() -> None:
    scratch = _scratch_dir("patch6_b1_allows_a2_research_only")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text("symbol\nBTCUSDT\n", encoding="utf-8")

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        workflow_run_id = str(_latest_preview_payload(jobs_root)["workflow_run_id"])
        phase_a2_root = scratch / "export" / "runs" / workflow_run_id / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "blocker_codes": [
                    "RAW_SOURCE_TYPE_INFERRED",
                    "CURRENT_METADATA_PROXY",
                    "SINGLE_PAIR_RESEARCH_ONLY",
                    "OHLCV_1M_PARTIAL_DAY_ACCEPTED",
                ],
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        preview = _latest_preview_payload(jobs_root)
        assert not any(str(code).startswith("A2_") for code in preview["blockers"])
        assert preview["inspection_status"] == "PHASE_B1_CANDIDATE_DISCOVERY_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b1_preview_does_not_borrow_a2_from_sibling_workflow() -> None:
    scratch = _scratch_dir("patch6_b1_no_sibling_borrow")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            output_root=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OFF",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(jobs_root)
        ready_workflow_run_id = str(a1_preview["workflow_run_id"])
        ready_workflow_root = scratch / "export" / "runs" / ready_workflow_run_id
        phase_a2_root = ready_workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        stale_workflow_run_id = "strategy_ladder_workflow-staleb1"
        stale_workflow_root = scratch / "export" / "runs" / stale_workflow_run_id
        shutil.copytree(ready_workflow_root, stale_workflow_root)
        stale_manifest = json.loads(
            (stale_workflow_root / "workflow_manifest.json").read_text(encoding="utf-8")
        )
        stale_manifest["workflow_run_id"] = stale_workflow_run_id
        stale_manifest["workflow_root"] = str(stale_workflow_root)
        stale_manifest["phase_id"] = PHASE_A1
        stale_manifest["current_phase_id"] = PHASE_A1
        stale_manifest["phase_sequence"] = ["PHASE_A1"]
        stale_manifest["ml_mode"] = "ML_MODE_OVERLAY_FROZEN"
        stale_manifest["phases"] = {
            "PHASE_A1": stale_manifest["phases"]["PHASE_A1"]
        }
        (stale_workflow_root / "phase_a2_data_factory").rename(
            stale_workflow_root / "_phase_a2_removed"
        )
        _write_json(stale_workflow_root / "workflow_manifest.json", stale_manifest)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=stale_workflow_run_id,
            export_dir=str(scratch / "export").replace("\\", "/"),
            orderbook_path=str(orderbook_root).replace("\\", "/"),
            trades_path=str(trades_root).replace("\\", "/"),
            klines_path=str(klines_root).replace("\\", "/"),
            metadata_path=str(metadata_root).replace("\\", "/"),
            output_root=str(scratch / "export").replace("\\", "/"),
            start="2025-04-29",
            end="2025-04-29",
            candidate_discovery_mode="TEMPORAL_STRATIFIED",
            engine_native_sample_size=250,
            small_scope_enabled="false",
            full_scan_enabled="true",
            silver_storage_mode="jsonl_gz",
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            frozen_ml_artifact_hash="abc123",
        )
        assert response.status_code == 303
        b1_preview = _latest_preview_payload(jobs_root)
        assert b1_preview["workflow_run_id"] == stale_workflow_run_id
        assert b1_preview["workflow_run_id"] != ready_workflow_run_id
        assert "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS" in b1_preview["blockers"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_blocks_b1_when_reusing_phase_a1_preview() -> None:
    scratch = _scratch_dir("patch6_preview_launch_a1_to_b1_blocked")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(trades_root / "BTCUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "BTCUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        preview_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="launch",
            preview_id=preview_payload["preview_id"],
            request_hash=preview_payload["request_hash"],
            workflow_run_id=preview_payload["workflow_run_id"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        launch_state = read_launch_request_state(client.app.state.paths.backtest_jobs_root)
        assert launch_state is not None
        assert launch_state.status == "PREVIEW_LAUNCH_MISMATCH"
        assert "phase_id" in launch_state.mismatch_fields
        assert "action_name" in launch_state.mismatch_fields
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_small_scope_launch_ignores_legacy_raw_roots_when_dedicated_roots_selected(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("patch6_ignore_legacy_raw_roots")
    try:
        client = _build_client(scratch)
        captured: dict[str, object] = {}

        def _fake_launch_backtest_job(**kwargs):
            captured.update(kwargs)
            return CockpitBacktestJobRecord(
                job_id="strategy_ladder_data_factory-test",
                correlation_id="corr-test",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
                status=CockpitBacktestJobStatus.JOB_CREATED,
                requested_at_iso="2026-05-06T00:00:00+00:00",
                output_root=str(scratch / "out"),
                record_path=str(scratch / "job.json"),
                stdout_log_path=str(scratch / "stdout.log"),
                command=("python", "scripts/run_strategy_ladder_data_factory.py"),
                action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
                phase_id="PHASE_1B",
                preview_id="preview-test",
                request_hash="hash-test",
            )

        monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)
        orderbook_root = scratch / "raw" / "orderbook" / "ADAUSDT"
        trades_root = scratch / "raw" / "trades" / "ADAUSDT"
        klines_root = scratch / "raw" / "klines" / "ADAUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_ADAUSDT_ob200.data")
        _write_trade_fixture(trades_root / "ADAUSDT_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        _write_kline_fixture(klines_root / "ADAUSDT_1_2025-04-29.csv", timestamp_ms=1_745_884_800_000)
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text("symbol\nADAUSDT\n", encoding="utf-8")
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            raw_roots="L:\\ordre book part 1\\BNBUSDT,L:\\klines\\BTCUSDT\\1,L:\\trades\\BTCUSDT",
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        raw_roots = tuple(str(path) for path in captured["raw_roots"])
        assert all("ADAUSDT" in path for path in raw_roots)
        assert not any("BNBUSDT" in path or "BTCUSDT" in path for path in raw_roots)
        assert str(captured["historical_metadata_root"]).endswith("spot")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_metadata_root_is_not_blocked_by_date_range_in_preview() -> None:
    scratch = _scratch_dir("patch6_metadata_not_date_pruned")
    try:
        client = _build_client(scratch)
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "venue,exchange,market_type,symbol,base_coin,quote_coin,status,tick_size,qty_step,min_order_qty,min_notional,maker_fee_rate,taker_fee_rate,fee_source,metadata_purpose,proof_level,source,fetched_at_utc,raw_payload_hash\n"
            "bybit,bybit,spot,ADAUSDT,ADA,USDT,Trading,0.0001,0.1,0.1,5,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-06T00:00:00+00:00,abc\n",
            encoding="utf-8",
        )
        write_backtest_form_state(
            client.app.state.paths.backtest_jobs_root,
            BacktestFormState(
                action_name="DATA_FACTORY_DRY_RUN",
                export_dir=str(scratch / "export"),
                metadata_path=str(metadata_root),
                start="2025-04-29",
                end="2025-04-29",
            ),
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "PREVIEW_NOT_GENERATED" in page.text
        assert "Use Generate Preview to scan selected source folders." in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase2_preview_and_launch_enable_engine_native_mode(monkeypatch) -> None:
    scratch = _scratch_dir("patch6_phase2_engine_native")
    try:
        client = _build_client(scratch)
        captured: dict[str, object] = {}

        def _fake_launch_backtest_job(**kwargs):
            captured.update(kwargs)
            return CockpitBacktestJobRecord(
                job_id="strategy_ladder_first_controlled_run-test",
                correlation_id="corr-test",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
                status=CockpitBacktestJobStatus.JOB_CREATED,
                requested_at_iso="2026-05-06T00:00:00+00:00",
                output_root=str(scratch / "out"),
                record_path=str(scratch / "job.json"),
                stdout_log_path=str(scratch / "stdout.log"),
                command=("python", "scripts/run_strategy_ladder_first_controlled_run.py"),
                action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
                phase_id="PHASE_2B",
                preview_id="preview-test",
                request_hash="hash-test",
            )

        monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        preview_response = _post_patch6(
            client,
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert preview_response.status_code == 303
        previews_root = client.app.state.paths.backtest_jobs_root / "previews"
        manifest_path = next(previews_root.glob("*/source_date_preview_manifest.json"))
        preview_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "--engine-native-mode" in preview_payload["command_preview"]
        assert "--engine-native-sample-size 10" in preview_payload["command_preview"]

        launch_response = _post_patch6(
            client,
            action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
            intent="launch",
            preview_id=preview_payload["preview_id"],
            request_hash=preview_payload["request_hash"],
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert launch_response.status_code == 303
        assert captured["engine_native_mode"] is True
        assert captured["engine_native_sample_size"] == 10
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_reuses_persisted_preview_without_rescanning_sources() -> None:
    scratch = _scratch_dir("patch6_lazy_preview_read")
    try:
        client = _build_client(scratch)
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "venue,exchange,market_type,symbol,base_coin,quote_coin,status,tick_size,qty_step,min_order_qty,min_notional,maker_fee_rate,taker_fee_rate,fee_source,metadata_purpose,proof_level,source,fetched_at_utc,raw_payload_hash\n"
            "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.1,0.001,0.001,5,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-06T00:00:00+00:00,abc\n",
            encoding="utf-8",
        )
        response = _post_patch6(
            client,
            action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        shutil.rmtree(scratch / "raw", ignore_errors=True)
        shutil.rmtree(scratch / "metadata", ignore_errors=True)
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "PREVIEW_LAUNCHABLE" in page.text
        assert "Matched files total" in page.text
        assert "FOLDER_NOT_FOUND" not in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_uses_manual_refresh_mode() -> None:
    scratch = _scratch_dir("patch6_manual_refresh_mode")
    try:
        client = _build_client(scratch)
        page = client.get("/backtest")
        assert page.status_code == 200
        assert 'http-equiv="refresh"' not in page.text
        assert "Lightweight status polling is enabled on the backtest page." in page.text
        assert "Refresh Status" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_latest_summary_state_is_marked_not_current_request() -> None:
    scratch = _scratch_dir("patch6_latest_summary_mismatch")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        from cockpit.action_support import launch_backtest_job

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=scratch / "export",
            action_name="DATA_FACTORY_DRY_RUN",
            phase_id="PHASE_1A",
            preview_id="preview-old",
            request_hash="oldhash",
            operator_output_root=str(scratch / "summary_base"),
            blocked_reason="MANUAL_SUMMARY_TEST",
        )
        output_root = Path(record.output_root)
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(
            output_root / "pair_universe_report.json",
            {
                "requested_pairs": ["BTCUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": [],
            },
        )
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="DATA_FACTORY_SMALL_SCOPE_RUN",
                export_dir=str(scratch / "export"),
                orderbook_path="L:\\ordre book part 1\\ADAUSDT",
                trades_path="L:\\trades\\ADAUSDT",
                klines_path="L:\\klines\\ADAUSDT\\1",
                pairs=("ADAUSDT",),
                start="2025-07-22",
                end="2025-07-23",
            ),
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "LATEST_SUMMARY_NOT_CURRENT_REQUEST" in page.text
        assert "Showing latest completed run, not current preview." in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_a1_preview_writes_workflow_phase_without_a2_dependencies() -> None:
    scratch = _scratch_dir("patch6_phase_a1_workflow_preview")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )
        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        preview_payload = _latest_preview_payload(jobs_root)
        workflow_root = jobs_root / "workflows" / str(preview_payload["workflow_run_id"])
        workflow_manifest = read_workflow_manifest(workflow_root)
        assert workflow_manifest is not None
        assert workflow_manifest.current_phase_id == PHASE_A1
        phase_record = workflow_manifest.phases[PHASE_A1]
        assert not any(
            key.startswith("phase_a2_")
            for key in phase_record.consumed_artifact_refs
        )
        assert "phase_a1_preview_manifest" in phase_record.produced_artifact_refs
        assert "phase_a1_source_scope_report" in phase_record.produced_artifact_refs
        assert Path(
            phase_record.produced_artifact_refs["phase_a1_preview_manifest"]
        ).is_file()
        assert Path(
            phase_record.produced_artifact_refs["phase_a1_source_scope_report"]
        ).is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_a1_preview_refresh_clears_stale_workflow_flags_and_blockers() -> None:
    scratch = _scratch_dir("patch6_phase_a1_refresh_truth")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "venue,exchange,market_type,symbol,base_coin,quote_coin,status,tick_size,qty_step,min_order_qty,min_notional,maker_fee_rate,taker_fee_rate,fee_source,metadata_purpose,proof_level,source,fetched_at_utc,raw_payload_hash\n"
            "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.1,0.001,0.001,5,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-06T00:00:00+00:00,abc\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        preview_payload = _latest_preview_payload(jobs_root)
        workflow_root = jobs_root / "workflows" / str(preview_payload["workflow_run_id"])

        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id=str(preview_payload["workflow_run_id"]),
            request_hash="stale-request-hash",
            phase_id=PHASE_A1,
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="BROAD_DIAGNOSTIC",
            engine_native_sample_size=250,
            engine_count=4,
            allow_broad_run=True,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="parquet",
            silver_storage_mode_effective="parquet",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id=str(preview_payload["workflow_run_id"]),
            phase_id=PHASE_A1,
            phase_run_id="stale-phase-a1",
            phase_output_root=workflow_root / "phase_a1_preview",
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_A1_PREVIEW_BLOCKED",
            blocker_codes=("SILVER_STORAGE_READER_NOT_PROVEN",),
            error_code="SILVER_STORAGE_READER_NOT_PROVEN",
            stderr_ref="stale.log",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            workflow_run_id=str(preview_payload["workflow_run_id"]),
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303

        workflow_manifest = read_workflow_manifest(workflow_root)
        assert workflow_manifest is not None
        assert workflow_manifest.allow_broad_run is False
        assert workflow_manifest.small_scope_enabled is True
        assert workflow_manifest.full_scan_enabled is False
        assert workflow_manifest.silver_storage_mode_requested == "jsonl_gz"
        assert workflow_manifest.silver_storage_mode_effective == "jsonl_gz"
        phase_record = workflow_manifest.phases[PHASE_A1]
        assert phase_record.blocker_codes == ()
        assert phase_record.error_code == ""
        assert phase_record.stderr_ref == ""
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_launches_use_phase_specific_consumed_artifact_refs(monkeypatch) -> None:
    scratch = _scratch_dir("patch6_phase_dependency_refs")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text(
            "symbol\nBTCUSDT\n",
            encoding="utf-8",
        )
        response = _post_patch6(
            client,
            action_name="PHASE_A1_PREVIEW",
            intent="preview",
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        a1_preview = _latest_preview_payload(jobs_root)
        workflow_run_id = str(a1_preview["workflow_run_id"])
        workflow_root = jobs_root / "workflows" / workflow_run_id
        captured_calls: list[dict[str, object]] = []

        def _fake_launch_backtest_job(**kwargs):
            captured_calls.append(kwargs)
            job_kind = kwargs["job_kind"]
            phase_id = kwargs["phase_id"]
            job_id = f"{job_kind.value}-test-{len(captured_calls)}"
            return CockpitBacktestJobRecord(
                job_id=job_id,
                correlation_id=f"corr-{len(captured_calls)}",
                job_kind=job_kind,
                status=CockpitBacktestJobStatus.JOB_CREATED,
                requested_at_iso="2026-05-10T00:00:00+00:00",
                output_root=str(scratch / "out" / job_id),
                record_path=str(scratch / "jobs" / job_id / "job.json"),
                stdout_log_path=str(scratch / "jobs" / job_id / "stdout.log"),
                command=("python", "stub.py"),
                action_name=str(kwargs["action_name"]),
                phase_id=str(phase_id),
                workflow_run_id=str(kwargs["workflow_run_id"]),
                phase_run_id=f"{phase_id.lower()}-test",
                parent_workflow_ref=str(
                    workflow_manifest_path(workflow_root).resolve()
                ),
                preview_id=str(kwargs["preview_id"]),
                request_hash=str(kwargs["request_hash"]),
            )

        monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)

        response = _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        a2_preview = _latest_preview_payload(jobs_root)
        response = _post_patch6(
            client,
            action_name="PHASE_A2_DATA_FACTORY",
            intent="launch",
            preview_id=str(a2_preview["preview_id"]),
            request_hash=str(a2_preview["request_hash"]),
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        assert set(captured_calls[-1]["consumed_artifact_refs"]) == {
            "phase_a1_preview_manifest",
            "phase_a1_source_scope_report",
        }

        phase_a2_root = workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        b1_preview = _latest_preview_payload(jobs_root)
        response = _post_patch6(
            client,
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            intent="launch",
            preview_id=str(b1_preview["preview_id"]),
            request_hash=str(b1_preview["request_hash"]),
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        assert set(captured_calls[-1]["consumed_artifact_refs"]) == {
            "phase_a2_data_factory_manifest",
            "phase_a2_silver_index",
            "phase_a2_gold_root",
        }

        phase_b1_candidate_events = (
            workflow_root
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / workflow_run_id
            / "fast_candidates"
            / "candidate_events.jsonl"
        )
        phase_b1_candidate_events.parent.mkdir(parents=True, exist_ok=True)
        phase_b1_candidate_events.write_text(
            json.dumps({"candidate_id": "cand-1"}) + "\n",
            encoding="utf-8",
        )

        response = _post_patch6(
            client,
            action_name="PHASE_B2_DETAILED_REPLAY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        b2_preview = _latest_preview_payload(jobs_root)
        assert "PHASE_B2_REQUIRES_B1_NATIVE_PRESELECTION" in b2_preview["blockers"]

        phase_b1_run_root = phase_b1_candidate_events.parent.parent
        (phase_b1_run_root / "reports").mkdir(parents=True, exist_ok=True)
        (phase_b1_run_root / "preselection_candidates.jsonl").write_text(
            json.dumps({"candidate_id": "cand-1"}) + "\n",
            encoding="utf-8",
        )
        _write_json(
            phase_b1_run_root / "reports" / "preselection_summary.json",
            {
                "status": "ENGINE_NATIVE_PRESELECTION_READY",
                "replay_input_mode_status": "PRESELECTED_ONLY",
                "engine_native_preselected_count": 1,
            },
        )

        response = _post_patch6(
            client,
            action_name="PHASE_B2_DETAILED_REPLAY",
            intent="preview",
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        b2_preview = _latest_preview_payload(jobs_root)
        assert b2_preview["blockers"] == []
        response = _post_patch6(
            client,
            action_name="PHASE_B2_DETAILED_REPLAY",
            intent="launch",
            preview_id=str(b2_preview["preview_id"]),
            request_hash=str(b2_preview["request_hash"]),
            workflow_run_id=workflow_run_id,
            export_dir=str(scratch / "export"),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            metadata_path=str(metadata_root),
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        assert set(captured_calls[-1]["consumed_artifact_refs"]) == {
            "phase_a2_data_factory_manifest",
            "phase_a2_silver_index",
            "phase_a2_gold_root",
            "phase_b1_candidate_events",
        }
        assert str(captured_calls[-1]["candidate_events_path"]).endswith(
            "preselection_candidates.jsonl"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_b2_preview_blocks_when_a2_manifest_is_critically_blocked() -> None:
    scratch = _scratch_dir("patch6_b2_blocks_on_a2_critical")
    try:
        jobs_root = scratch / "jobs"
        orderbook_root = scratch / "raw" / "orderbook" / "BTCUSDT"
        trades_root = scratch / "raw" / "trades" / "BTCUSDT"
        klines_root = scratch / "raw" / "klines" / "BTCUSDT" / "1"
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
        _write_trade_fixture(
            trades_root / "BTCUSDT_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        _write_kline_fixture(
            klines_root / "BTCUSDT_1_2025-04-29.csv",
            timestamp_ms=1_745_884_800_000,
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "symbol_metadata.csv").write_text("symbol\nBTCUSDT\n", encoding="utf-8")
        initial_preview = build_patch6_preflight_preview(
            selected_form=BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                workflow_phase=PHASE_B2,
                workflow_run_id="strategy_ladder_workflow-b2-critical",
                export_dir=str(scratch / "export"),
                output_root=str(scratch / "export"),
                orderbook_path=str(orderbook_root),
                trades_path=str(trades_root),
                klines_path=str(klines_root),
                metadata_path=str(metadata_root),
                start="2025-04-29",
                end="2025-04-29",
                ml_mode="ML_MODE_OFF",
            ),
            jobs_root=jobs_root,
        )
        workflow_run_id = initial_preview.workflow_run_id
        workflow_root = scratch / "export" / "runs" / workflow_run_id
        phase_a2_root = workflow_root / "phase_a2_data_factory"
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS",
                "blocker_codes": ["OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED"],
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})
        (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)

        phase_b1_candidate_events = (
            workflow_root
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / workflow_run_id
            / "fast_candidates"
            / "candidate_events.jsonl"
        )
        phase_b1_candidate_events.parent.mkdir(parents=True, exist_ok=True)
        phase_b1_candidate_events.write_text(
            json.dumps({"candidate_id": "cand-1"}) + "\n",
            encoding="utf-8",
        )
        phase_b1_run_root = phase_b1_candidate_events.parent.parent
        (phase_b1_run_root / "reports").mkdir(parents=True, exist_ok=True)
        (phase_b1_run_root / "preselection_candidates.jsonl").write_text(
            json.dumps({"candidate_id": "cand-1"}) + "\n",
            encoding="utf-8",
        )
        _write_json(
            phase_b1_run_root / "reports" / "preselection_summary.json",
            {
                "status": "ENGINE_NATIVE_PRESELECTION_READY",
                "replay_input_mode_status": "PRESELECTED_ONLY",
                "engine_native_preselected_count": 1,
            },
        )

        preview = build_patch6_preflight_preview(
            selected_form=BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                workflow_phase=PHASE_B2,
                workflow_run_id=workflow_run_id,
                export_dir=str(scratch / "export"),
                output_root=str(scratch / "export"),
                orderbook_path=str(orderbook_root),
                trades_path=str(trades_root),
                klines_path=str(klines_root),
                metadata_path=str(metadata_root),
                start="2025-04-29",
                end="2025-04-29",
                ml_mode="ML_MODE_OFF",
            ),
            jobs_root=jobs_root,
        )
        assert (
            "A2_BLOCKED_UPSTREAM:DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS"
            in preview.blockers
        )
        assert preview.inspection_status == "PHASE_B2_BACKTEST_PROOF_BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_failed_phase_records_error_code_and_log_refs(monkeypatch) -> None:
    scratch = _scratch_dir("patch6_failed_phase_error_surface")
    try:
        jobs_root = scratch / "jobs"

        def _failing_command(**kwargs):
            return (
                kwargs["python_executable"],
                "-c",
                "import sys; sys.exit(3)",
            )

        monkeypatch.setattr(
            action_support_module,
            "_build_backtest_command",
            _failing_command,
        )
        record = action_support_module.launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=scratch / "export",
            action_name="PHASE_A2_DATA_FACTORY",
            phase_id=PHASE_A2,
            request_hash="workflow-failed",
            operator_output_root=str(scratch / "outputs"),
            workflow_run_id="strategy_ladder_workflow-failed",
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            small_scope_enabled=True,
        )
        assert record.workflow_run_id == "strategy_ladder_workflow-failed"
        terminal = _wait_for_terminal_job(jobs_root)
        assert terminal.status == CockpitBacktestJobStatus.JOB_FAILED
        workflow_root = scratch / "outputs" / "runs" / "strategy_ladder_workflow-failed"
        deadline = time.time() + 5.0
        phase_record = None
        while time.time() < deadline:
            workflow_manifest = read_workflow_manifest(workflow_root)
            if workflow_manifest is not None:
                phase_record = workflow_manifest.phases.get(PHASE_A2)
                if phase_record is not None and phase_record.error_code:
                    break
            time.sleep(0.05)
        assert phase_record is not None
        assert phase_record.error_code == "EXIT_CODE_3"
        assert phase_record.stderr_ref.endswith("stdout.log")
        assert phase_record.phase_status == "PHASE_A2_DATA_FACTORY_BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_status_from_finished_record_blocks_a2_when_manifest_is_critical() -> None:
    scratch = _scratch_dir("patch6_a2_phase_status_critical_manifest")
    try:
        phase_a2_root = scratch / "phase_a2_data_factory"
        phase_a2_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS",
                "blocker_codes": (
                    "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED",
                    "CURRENT_METADATA_PROXY",
                ),
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="a2-critical",
            correlation_id="corr-a2-critical",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-21T10:00:00+00:00",
            started_at_iso="2026-05-21T10:00:01+00:00",
            finished_at_iso="2026-05-21T10:00:02+00:00",
            output_root=str(phase_a2_root),
            record_path=str(scratch / "job.json"),
            stdout_log_path=str(scratch / "stdout.log"),
            command=("python", "stub.py"),
            phase_id=PHASE_A2,
            blockers=("OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED",),
        )
        assert (
            action_support_module._phase_status_from_finished_record(record)
            == "PHASE_A2_DATA_FACTORY_BLOCKED"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_phase_status_from_finished_record_keeps_a2_ready_for_research_only_blockers() -> None:
    scratch = _scratch_dir("patch6_a2_phase_status_research_only_manifest")
    try:
        phase_a2_root = scratch / "phase_a2_data_factory"
        phase_a2_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "blocker_codes": (
                    "RAW_SOURCE_TYPE_INFERRED",
                    "CURRENT_METADATA_PROXY",
                    "SINGLE_PAIR_RESEARCH_ONLY",
                    "OHLCV_1M_PARTIAL_DAY_ACCEPTED",
                ),
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="a2-research-only",
            correlation_id="corr-a2-research-only",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-21T10:00:00+00:00",
            started_at_iso="2026-05-21T10:00:01+00:00",
            finished_at_iso="2026-05-21T10:00:02+00:00",
            output_root=str(phase_a2_root),
            record_path=str(scratch / "job.json"),
            stdout_log_path=str(scratch / "stdout.log"),
            command=("python", "stub.py"),
            phase_id=PHASE_A2,
            blockers=("RAW_SOURCE_TYPE_INFERRED", "CURRENT_METADATA_PROXY"),
        )
        assert (
            action_support_module._phase_status_from_finished_record(record)
            == "PHASE_A2_DATA_FACTORY_READY"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_latest_summary_resolves_by_workflow_run_id_and_current_phase() -> None:
    scratch = _scratch_dir("patch6_summary_resolver_current_phase")
    try:
        workflow_root = scratch / "workflows" / "strategy_ladder_workflow-current"
        phase_a2_root = workflow_root / "phase_a2_data_factory"
        phase_b1_root = workflow_root / "phase_b1_candidate_discovery"
        phase_a2_root.mkdir(parents=True, exist_ok=True)
        phase_b1_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-current",
            request_hash="workflow-hash",
            phase_id=PHASE_A2,
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="BROAD_DIAGNOSTIC",
            engine_native_sample_size=100,
            engine_count=4,
            allow_broad_run=True,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-current",
            phase_id=PHASE_A2,
            phase_run_id="phase-a2",
            phase_output_root=phase_a2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_A2_DATA_FACTORY_READY",
            produced_artifact_refs={
                "phase_a2_data_factory_manifest": str(
                    (phase_a2_root / "data_factory_manifest.json").resolve()
                )
            },
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-current",
            phase_id=PHASE_B1,
            phase_run_id="phase-b1",
            phase_output_root=phase_b1_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED",
            error_code="PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS",
            blocker_codes=("PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS",),
        )
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            },
        )
        jobs = (
            CockpitBacktestJobRecord(
                job_id="runner-current",
                correlation_id="corr-current",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_FAILED,
                requested_at_iso="2026-05-10T10:00:00+00:00",
                started_at_iso="2026-05-10T10:00:01+00:00",
                finished_at_iso="2026-05-10T10:00:02+00:00",
                output_root=str(phase_a2_root),
                record_path=str(scratch / "job_current.json"),
                stdout_log_path=str(scratch / "runner_current.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B1,
                workflow_run_id="strategy_ladder_workflow-current",
                phase_run_id="phase-b1",
                parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
                request_hash="workflow-hash",
            ),
            CockpitBacktestJobRecord(
                job_id="runner-older",
                correlation_id="corr-older",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
                status=CockpitBacktestJobStatus.JOB_COMPLETED,
                requested_at_iso="2026-05-10T09:00:00+00:00",
                started_at_iso="2026-05-10T09:00:01+00:00",
                finished_at_iso="2026-05-10T09:00:02+00:00",
                output_root=str(phase_a2_root),
                record_path=str(scratch / "job_older.json"),
                stdout_log_path=str(scratch / "runner_older.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_A2,
                workflow_run_id="strategy_ladder_workflow-current",
                phase_run_id="phase-a2",
                parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
                request_hash="workflow-hash",
            ),
        )
        summary = _read_strategy_ladder_summary(jobs)
        assert summary.workflow_run_id == "strategy_ladder_workflow-current"
        assert summary.phase_id == PHASE_B1
        assert summary.output_root == str(phase_b1_root.resolve())
        assert summary.current_phase_status == "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
        assert summary.current_phase_error_code == "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS"
        assert summary.source_status == "workflow_phase_only"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_summary_separates_current_job_from_last_successful_b2() -> None:
    scratch = _scratch_dir("patch6_strategy_ladder_stale_summary_split")
    try:
        workflow_root = scratch / "workflows" / "strategy_ladder_workflow-stale"
        phase_b2_root = workflow_root / "phase_b2_detailed_replay"
        phase_b2_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-stale",
            request_hash="workflow-hash",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="BROAD_DIAGNOSTIC",
            engine_native_sample_size=100,
            engine_count=4,
            allow_broad_run=True,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-stale",
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-current",
            phase_output_root=phase_b2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B2_BACKTEST_PROOF_BLOCKED",
            error_code="RAW_WINDOW_EXTRACTION_FAILED",
            blocker_codes=("RAW_WINDOW_EXTRACTION_FAILED",),
        )
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-stale"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-stale",
                "workflow_run_id": "strategy_ladder_workflow-stale",
                "phase_run_id": "phase-b2-older",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
                "data_factory_status": "DATA_FACTORY_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        jobs = (
            CockpitBacktestJobRecord(
                job_id="runner-current-blocked",
                correlation_id="corr-current-blocked",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_BLOCKED,
                requested_at_iso="2026-05-10T10:00:00+00:00",
                started_at_iso="2026-05-10T10:00:01+00:00",
                finished_at_iso="2026-05-10T10:00:02+00:00",
                output_root=str(phase_b2_root),
                record_path=str(scratch / "job_current_blocked.json"),
                stdout_log_path=str(scratch / "runner_current_blocked.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B2,
                phase_run_id="phase-b2-current",
                workflow_run_id="strategy_ladder_workflow-stale",
                parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
                request_hash="workflow-hash",
                error_summary="RAW_WINDOW_EXTRACTION_FAILED",
                blockers=("RAW_WINDOW_EXTRACTION_FAILED",),
            ),
            CockpitBacktestJobRecord(
                job_id="runner-older-success",
                correlation_id="corr-older-success",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
                requested_at_iso="2026-05-10T09:00:00+00:00",
                started_at_iso="2026-05-10T09:00:01+00:00",
                finished_at_iso="2026-05-10T09:00:02+00:00",
                output_root=str(phase_b2_root),
                record_path=str(scratch / "job_older_success.json"),
                stdout_log_path=str(scratch / "runner_older_success.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B2,
                phase_run_id="phase-b2-older",
                workflow_run_id="strategy_ladder_workflow-stale",
                parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
                request_hash="workflow-hash",
                stage_summary_path=str(summary_path.resolve()),
            ),
        )
        summary = _read_strategy_ladder_summary(jobs)
        assert summary.current_job_id == "runner-current-blocked"
        assert summary.current_job_status == "JOB_BLOCKED"
        assert summary.current_job_blocker_codes == ("RAW_WINDOW_EXTRACTION_FAILED",)
        assert summary.last_successful_b2_job_id == "runner-older-success"
        assert summary.last_successful_b2_status == "JOB_COMPLETED_WITH_BLOCKERS"
        assert (
            summary.last_successful_b2_final_status
            == "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES"
        )
        assert summary.displayed_summary_source == "LAST_SUCCESSFUL_B2_SUMMARY"
        assert summary.displayed_summary_job_id == "runner-older-success"
        assert summary.summary_matches_current_job is False
        assert summary.stale_summary_warning is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_summary_marks_current_job_when_b2_summary_matches() -> None:
    scratch = _scratch_dir("patch6_strategy_ladder_current_summary_split")
    try:
        run_root = scratch / "phase_b2_detailed_replay"
        run_dir = run_root / "backtest_strategy_ladder" / "strategy_ladder_workflow-current"
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-current",
                "workflow_run_id": "strategy_ladder_workflow-current",
                "phase_run_id": "phase-b2-current",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        jobs = (
            CockpitBacktestJobRecord(
                job_id="runner-current-success",
                correlation_id="corr-current-success",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
                requested_at_iso="2026-05-10T10:00:00+00:00",
                started_at_iso="2026-05-10T10:00:01+00:00",
                finished_at_iso="2026-05-10T10:00:02+00:00",
                output_root=str(run_root),
                record_path=str(scratch / "job_current_success.json"),
                stdout_log_path=str(scratch / "runner_current_success.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B2,
                phase_run_id="phase-b2-current",
                workflow_run_id="strategy_ladder_workflow-current",
                request_hash="workflow-hash",
                stage_summary_path=str(summary_path.resolve()),
            ),
        )
        summary = _read_strategy_ladder_summary(jobs)
        assert summary.current_job_id == "runner-current-success"
        assert summary.last_successful_b2_job_id == "runner-current-success"
        assert summary.displayed_summary_source == "CURRENT_B2_SUMMARY"
        assert summary.displayed_summary_job_id == "runner-current-success"
        assert summary.displayed_summary_path == str(summary_path.resolve())
        assert summary.summary_matches_current_job is True
        assert summary.stale_summary_warning is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_summary_prefers_current_completed_b2_over_stale_workflow_summary() -> None:
    scratch = _scratch_dir("patch6_strategy_ladder_current_b2_wins")
    try:
        run_root = scratch / "phase_b2_detailed_replay"
        stale_run_dir = (
            run_root / "backtest_strategy_ladder" / "strategy_ladder_workflow-current"
        )
        current_run_dir = (
            run_root / "backtest_strategy_ladder" / "strategy_ladder_runner-1778683039500"
        )
        stale_summary_path = stale_run_dir / "reports" / "strategy_ladder_summary.json"
        current_summary_path = current_run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            stale_summary_path,
            {
                "run_id": "strategy_ladder_workflow-current",
                "workflow_run_id": "strategy_ladder_workflow-current",
                "phase_run_id": "phase-b2-stale",
                "candidate_count": 40,
                "replay_record_count": 160,
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS",
            },
        )
        _write_json(
            current_summary_path,
            {
                "run_id": "strategy_ladder_workflow-current",
                "workflow_run_id": "strategy_ladder_workflow-current",
                "phase_run_id": "phase-b2-current",
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "candidate_count": 1000,
                "engine_native_candidate_count": 1000,
                "replay_record_count": 4000,
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        jobs = (
            CockpitBacktestJobRecord(
                job_id="strategy_ladder_runner-1778683039500",
                correlation_id="corr-current-success",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_COMPLETED,
                requested_at_iso="2026-05-13T10:00:00+00:00",
                started_at_iso="2026-05-13T10:00:01+00:00",
                finished_at_iso="2026-05-13T10:00:02+00:00",
                output_root=str(run_root),
                record_path=str(scratch / "job_current_success.json"),
                stdout_log_path=str(scratch / "runner_current_success.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B2,
                phase_run_id="phase-b2-current",
                workflow_run_id="strategy_ladder_workflow-current",
                request_hash="workflow-hash",
                stage_summary_path=str(current_summary_path.resolve()),
            ),
        )
        summary = _read_strategy_ladder_summary(jobs)
        assert summary.displayed_summary_source == "CURRENT_B2_SUMMARY"
        assert summary.displayed_summary_job_id == "strategy_ladder_runner-1778683039500"
        assert summary.displayed_summary_path == str(current_summary_path.resolve())
        assert summary.summary_matches_current_job is True
        assert summary.stale_summary_warning is False
        assert summary.raw_window_extraction_status == "RAW_WINDOW_READY"
        assert summary.detailed_replay_status == "DETAILED_REPLAY_READY"
        assert summary.candidate_count == 1000
        assert summary.engine_native_candidate_count == 1000
        assert summary.replay_record_count == 4000
        assert summary.final_status == "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_summary_builds_no_trade_refusal_audit_surface() -> None:
    scratch = _scratch_dir("patch6_strategy_ladder_no_trade_audit")
    try:
        run_root = scratch / "phase_b2_detailed_replay"
        run_dir = (
            run_root / "backtest_strategy_ladder" / "strategy_ladder_workflow-no-trade"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-no-trade",
                "workflow_run_id": "strategy_ladder_workflow-no-trade",
                "phase_run_id": "phase-b2-no-trade",
                "sample_size_survival_status": "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS",
                "refusal_ledger_evidence_class": "SCRATCH_ONLY",
                "sample_size_survival_evidence_class": "SCRATCH_ONLY",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        _write_json(
            run_dir / "reports" / "engine_matrix.json",
            [
                {
                    "engine_id": "engine_a",
                    "record_count": 2,
                    "selected_count": 0,
                    "hard_blocked_count": 2,
                },
                {
                    "engine_id": "engine_b",
                    "record_count": 1,
                    "selected_count": 0,
                    "hard_blocked_count": 1,
                },
            ],
        )
        _write_json(
            run_dir / "reports" / "pair_matrix.json",
            [
                {
                    "pair": "BTCUSDT",
                    "record_count": 3,
                    "selected_count": 0,
                    "hard_blocked_count": 3,
                }
            ],
        )
        _write_jsonl(
            run_dir / "refusal_ledger.jsonl",
            [
                {
                    "candidate_id": "cand-a-400",
                    "engine_id": "engine_a",
                    "pair": "BTCUSDT",
                    "capital_bucket": 400,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "engine_a.structure.unfavorable",
                    ],
                },
                {
                    "candidate_id": "cand-a-500",
                    "engine_id": "engine_a",
                    "pair": "BTCUSDT",
                    "capital_bucket": 500,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "engine_a.structure.unfavorable",
                    ],
                },
                {
                    "candidate_id": "cand-b-400",
                    "engine_id": "engine_b",
                    "pair": "BTCUSDT",
                    "capital_bucket": 400,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "engine_b.excess.no_excess",
                    ],
                },
            ],
        )
        jobs = (
            CockpitBacktestJobRecord(
                job_id="runner-no-trade",
                correlation_id="corr-no-trade",
                job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                status=CockpitBacktestJobStatus.JOB_COMPLETED,
                requested_at_iso="2026-05-13T10:00:00+00:00",
                started_at_iso="2026-05-13T10:00:01+00:00",
                finished_at_iso="2026-05-13T10:00:02+00:00",
                output_root=str(run_root),
                record_path=str(scratch / "job_no_trade.json"),
                stdout_log_path=str(scratch / "runner_no_trade.log"),
                command=("python", "stub.py"),
                phase_id=PHASE_B2,
                phase_run_id="phase-b2-no-trade",
                workflow_run_id="strategy_ladder_workflow-no-trade",
                request_hash="workflow-hash",
                stage_summary_path=str(summary_path.resolve()),
            ),
        )
        summary = _read_strategy_ladder_summary(jobs)
        assert summary.no_trade_audit_status == "NO_TRADE_COLLAPSED_AFTER_HARD_FILTERS"
        assert summary.no_trade_refusal_rows_total == 3
        assert summary.no_trade_selected_count_total == 0
        assert summary.no_trade_hard_blocked_count_total == 3
        assert summary.no_trade_sample_size_status == "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS"
        assert summary.no_trade_common_reason_codes == (
            "ENGINE_NATIVE_NO_TRADE",
            "EXPECTED_EDGE_PROXY_BLOCKED",
        )
        assert summary.no_trade_engine_rows[0]["engine_id"] == "engine_a"
        assert summary.no_trade_engine_rows[0]["refusal_count"] == 2
        assert summary.no_trade_capital_bucket_rows[0]["capital_bucket"] == 400
        assert summary.no_trade_capital_bucket_rows[0]["refusal_count"] == 2
        assert summary.no_trade_reason_rows[0]["reason_code"] == "ENGINE_NATIVE_NO_TRADE"
        assert summary.no_trade_reason_rows[0]["count"] == 3
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_shows_current_job_and_last_successful_b2_separately() -> None:
    scratch = _scratch_dir("patch6_backtest_page_current_vs_successful")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        workflow_root = jobs_root / "workflows" / "strategy_ladder_workflow-page"
        phase_b2_root = workflow_root / "phase_b2_detailed_replay"
        phase_b2_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-page",
            request_hash="workflow-hash-page",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="BROAD_DIAGNOSTIC",
            engine_native_sample_size=100,
            engine_count=4,
            allow_broad_run=True,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-page",
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-current",
            phase_output_root=phase_b2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B2_BACKTEST_PROOF_BLOCKED",
            error_code="RAW_WINDOW_EXTRACTION_FAILED",
            blocker_codes=("RAW_WINDOW_EXTRACTION_FAILED",),
        )
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-page"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-page",
                "workflow_run_id": "strategy_ladder_workflow-page",
                "phase_run_id": "phase-b2-page-older",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        current_record = CockpitBacktestJobRecord(
            job_id="runner-page-current-blocked",
            correlation_id="corr-page-current-blocked",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_BLOCKED,
            requested_at_iso="2026-05-10T10:00:00+00:00",
            started_at_iso="2026-05-10T10:00:01+00:00",
            finished_at_iso="2026-05-10T10:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-page-current-blocked" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-page-current-blocked" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-current",
            workflow_run_id="strategy_ladder_workflow-page",
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            request_hash="workflow-hash-page",
            error_summary="RAW_WINDOW_EXTRACTION_FAILED",
            blockers=("RAW_WINDOW_EXTRACTION_FAILED",),
        )
        older_record = CockpitBacktestJobRecord(
            job_id="runner-page-older-success",
            correlation_id="corr-page-older-success",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
            requested_at_iso="2026-05-10T09:00:00+00:00",
            started_at_iso="2026-05-10T09:00:01+00:00",
            finished_at_iso="2026-05-10T09:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-page-older-success" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-page-older-success" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-older",
            workflow_run_id="strategy_ladder_workflow-page",
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            request_hash="workflow-hash-page",
            stage_summary_path=str(summary_path.resolve()),
        )
        _write_json(Path(current_record.record_path), current_record.model_dump(mode="json"))
        _write_json(Path(older_record.record_path), older_record.model_dump(mode="json"))

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Current job" in page.text
        assert "Last successful B2 summary" in page.text
        assert "Workflow canonical summary" in page.text
        assert "runner-page-current-blocked" in page.text
        assert "JOB_BLOCKED" in page.text
        assert "runner-page-older-success" in page.text
        assert "LAST_SUCCESSFUL_B2_SUMMARY" in page.text
        assert "Summary matches current job" in page.text
        assert "Stale summary warning" in page.text
        assert "Current job and displayed canonical summary do not refer to the same job." in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_shows_no_trade_refusal_audit_panel() -> None:
    scratch = _scratch_dir("patch6_backtest_page_no_trade_refusal_audit")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        phase_b2_root = jobs_root / "workflows" / "strategy_ladder_workflow-no-trade-page" / "phase_b2_detailed_replay"
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-no-trade-page"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-no-trade-page",
                "workflow_run_id": "strategy_ladder_workflow-no-trade-page",
                "phase_run_id": "phase-b2-no-trade-page",
                "sample_size_survival_status": "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS",
                "refusal_ledger_evidence_class": "SCRATCH_ONLY",
                "sample_size_survival_evidence_class": "SCRATCH_ONLY",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        _write_json(
            run_dir / "reports" / "engine_matrix.json",
            [
                {
                    "engine_id": "engine_a",
                    "record_count": 2,
                    "selected_count": 0,
                    "hard_blocked_count": 2,
                }
            ],
        )
        _write_json(
            run_dir / "reports" / "pair_matrix.json",
            [
                {
                    "pair": "BTCUSDT",
                    "record_count": 2,
                    "selected_count": 0,
                    "hard_blocked_count": 2,
                }
            ],
        )
        _write_jsonl(
            run_dir / "refusal_ledger.jsonl",
            [
                {
                    "candidate_id": "cand-a-400",
                    "engine_id": "engine_a",
                    "pair": "BTCUSDT",
                    "capital_bucket": 400,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                    ],
                },
                {
                    "candidate_id": "cand-a-500",
                    "engine_id": "engine_a",
                    "pair": "BTCUSDT",
                    "capital_bucket": 500,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                    ],
                },
            ],
        )
        record = CockpitBacktestJobRecord(
            job_id="runner-no-trade-page",
            correlation_id="corr-no-trade-page",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-13T10:00:00+00:00",
            started_at_iso="2026-05-13T10:00:01+00:00",
            finished_at_iso="2026-05-13T10:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-no-trade-page" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-no-trade-page" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-no-trade-page",
            workflow_run_id="strategy_ladder_workflow-no-trade-page",
            request_hash="workflow-hash-page",
            stage_summary_path=str(summary_path.resolve()),
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Post-B2 No-Trade Audit" in page.text
        assert "ENGINE_NATIVE_NO_TRADE" in page.text
        assert "EXPECTED_EDGE_PROXY_BLOCKED" in page.text
        assert "EVIDENCE_AUDIT_NOT_CONFIRMED" in page.text
        assert "By Capital Bucket" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_renders_engine_no_trade_diagnosis_panel() -> None:
    scratch = _scratch_dir("patch6_backtest_page_engine_no_trade_diagnosis")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        workflow_root = jobs_root / "workflows" / "strategy_ladder_workflow-engine-diagnosis-page"
        phase_b2_root = workflow_root / "phase_b2_detailed_replay"
        phase_b2_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-engine-diagnosis-page",
            request_hash="hash-engine-diagnosis-page",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-05-03",
            end="2025-05-04",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=250,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-engine-diagnosis-page",
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-engine-diagnosis-page",
            phase_output_root=phase_b2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B2_DETAILED_REPLAY_READY",
        )
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-engine-diagnosis-page"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-engine-diagnosis-page",
                "workflow_run_id": "strategy_ladder_workflow-engine-diagnosis-page",
                "phase_run_id": "phase-b2-engine-diagnosis-page",
                "candidate_count": 1000,
                "engine_native_candidate_count": 1000,
                "replay_record_count": 4000,
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        _write_json(
            run_dir / "reports" / "engine_no_trade_diagnosis.json",
            {
                "source_status": "ok",
                "first_gate_analysis": {"gate_status": "FIRST_GATE_BLOCKS_BEFORE_SELECTION"},
                "common_blockers": [
                    {"reason_code": "EXPECTED_EDGE_PROXY_BLOCKED", "count": 4000}
                ],
                "engines": [
                    {
                        "engine_id": "engine_d",
                        "candidate_count": 250,
                        "replay_record_count": 1000,
                        "selected_count": 0,
                        "hard_blocked_count": 1000,
                        "first_blocking_layer": "history_gate",
                        "suspected_wiring_gaps": [
                            "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL"
                        ],
                        "recommended_next_action": "BUILD_CLOSED_EPISODE_JOURNAL_FOR_ENGINE_D",
                    }
                ],
                "next_action_ranking": [
                    {
                        "rank": "B",
                        "action": "BUILD_CLOSED_EPISODE_JOURNAL_FOR_ENGINE_D",
                        "rationale": "Engine D requires historical linkage.",
                    }
                ],
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="runner-engine-diagnosis-page",
            correlation_id="corr-engine-diagnosis-page",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-13T10:00:00+00:00",
            started_at_iso="2026-05-13T10:00:01+00:00",
            finished_at_iso="2026-05-13T10:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-engine-diagnosis-page" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-engine-diagnosis-page" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-engine-diagnosis-page",
            workflow_run_id="strategy_ladder_workflow-engine-diagnosis-page",
            request_hash="workflow-hash-engine-diagnosis-page",
            stage_summary_path=str(summary_path.resolve()),
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Engine No-Trade Diagnosis" in page.text
        assert "BUILD_CLOSED_EPISODE_JOURNAL_FOR_ENGINE_D" in page.text
        assert "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_renders_gate_waterfall_and_readiness_panels() -> None:
    scratch = _scratch_dir("patch6_backtest_page_gate_waterfall")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        workflow_root = jobs_root / "workflows" / "strategy_ladder_workflow-gate-waterfall-page"
        phase_b2_root = workflow_root / "phase_b2_detailed_replay"
        phase_b2_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-gate-waterfall-page",
            request_hash="hash-gate-waterfall-page",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-05-03",
            end="2025-05-04",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=250,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-gate-waterfall-page",
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-gate-waterfall-page",
            phase_output_root=phase_b2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B2_DETAILED_REPLAY_READY",
        )
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-gate-waterfall-page"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-gate-waterfall-page",
                "workflow_run_id": "strategy_ladder_workflow-gate-waterfall-page",
                "phase_run_id": "phase-b2-gate-waterfall-page",
                "candidate_count": 1000,
                "engine_native_candidate_count": 1000,
                "replay_record_count": 4000,
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        _write_json(
            run_dir / "reports" / "gate_waterfall_analysis.json",
            {
                "status": "GATE_WATERFALL_ANALYSIS_READY",
                "canonical_selected_count": 0,
                "canonical_executed_count": 0,
                "best_counterfactual_scenario": {
                    "scenario_id": "expected_edge_governed",
                    "counterfactual_survival_count": 120,
                    "delta_vs_canonical_selected": 120,
                },
                "dominant_blocking_gates": [
                    {
                        "gate_id": "expected_edge_layer",
                        "gate_label": "Expected edge",
                        "first_blocking_count": 2400,
                        "first_blocking_pct": 0.6,
                        "dominant_reason_codes": [
                            {"reason_code": "EXPECTED_EDGE_PROXY_BLOCKED", "count": 2400}
                        ],
                    }
                ],
                "funnel_metrics": [
                    {
                        "gate_id": "expected_edge_layer",
                        "gate_label": "Expected edge",
                        "remaining_after_gate_count": 120,
                        "marginal_drop_by_gate": 3880,
                        "cumulative_drop_by_gate": 3880,
                    }
                ],
                "scenario_summaries": [
                    {
                        "scenario_id": "expected_edge_governed",
                        "counterfactual_survival_count": 120,
                        "counterfactual_survival_pct": 0.03,
                        "delta_vs_canonical_selected": 120,
                    }
                ],
            },
        )
        _write_json(
            run_dir / "reports" / "gate_counterfactual_by_engine.json",
            {
                "rows": [
                    {
                        "engine_id": "engine_c",
                        "replay_record_count": 1000,
                        "dominant_blocking_gate": "fragility_layer",
                        "dominant_gate_label": "Fragility",
                        "best_counterfactual_scenario": "engine_c_fragility_relaxed",
                        "counterfactual_survival_count": 40,
                    }
                ]
            },
        )
        _write_json(
            run_dir / "reports" / "gate_counterfactual_by_timeframe.json",
            {
                "rows": [
                    {
                        "timeframe": "10m",
                        "replay_record_count": 160,
                        "dominant_blocking_gate": "expected_edge_layer",
                        "dominant_gate_label": "Expected edge",
                        "best_counterfactual_scenario": "expected_edge_governed",
                        "counterfactual_survival_count": 24,
                    }
                ]
            },
        )
        _write_json(
            run_dir / "reports" / "expected_edge_readiness_audit.json",
            {
                "status": "EXPECTED_EDGE_READINESS_AUDIT_READY",
                "verdict": "EXPECTED_EDGE_TRAINING_RESEARCH_ONLY_ALLOWED",
                "key_findings": [
                    "replay_grounded_label_count=0",
                    "expected_edge_counterfactual_delta=120",
                ],
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="runner-gate-waterfall-page",
            correlation_id="corr-gate-waterfall-page",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-15T10:00:00+00:00",
            started_at_iso="2026-05-15T10:00:01+00:00",
            finished_at_iso="2026-05-15T10:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-gate-waterfall-page" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-gate-waterfall-page" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-gate-waterfall-page",
            workflow_run_id="strategy_ladder_workflow-gate-waterfall-page",
            request_hash="workflow-hash-gate-waterfall-page",
            stage_summary_path=str(summary_path.resolve()),
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Gate Waterfall" in page.text
        assert "RESEARCH_ONLY_COUNTERFACTUAL" in page.text
        assert "Best counterfactual survival" in page.text
        assert "expected_edge_governed" in page.text
        assert "Expected-Edge Readiness Audit" in page.text
        assert "EXPECTED_EDGE_TRAINING_RESEARCH_ONLY_ALLOWED" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_build_state_consistency_flags_current_form_moved_after_launch() -> None:
    current_form_state = CockpitPatch6State(
        state_name="current_form_state",
        request_hash="hash-current",
        workflow_run_id="strategy_ladder_workflow-current",
        phase_id=PHASE_B2,
        phase_label="Phase B2 Detailed Replay",
        action_name="PHASE_B2_DETAILED_REPLAY",
    )
    source_preview_state = CockpitPatch6State(
        state_name="source_preview_state",
        request_hash="hash-old",
        preview_id="preview-old",
        workflow_run_id="strategy_ladder_workflow-old",
        phase_id=PHASE_B2,
        phase_label="Phase B2 Detailed Replay",
        action_name="PHASE_B2_DETAILED_REPLAY",
    )
    launch_request_state = CockpitPatch6State(
        state_name="launch_request_state",
        request_hash="hash-old",
        preview_id="preview-old",
        job_id="runner-old",
        workflow_run_id="strategy_ladder_workflow-old",
        phase_id=PHASE_B2,
        phase_label="Phase B2 Detailed Replay",
        action_name="PHASE_B2_DETAILED_REPLAY",
        status="JOB_BLOCKED",
    )
    latest_canonical_summary_state = CockpitPatch6State(
        state_name="latest_canonical_summary_state",
        request_hash="hash-old",
        job_id="runner-old-success",
        run_id="strategy_ladder_workflow-old",
        workflow_run_id="strategy_ladder_workflow-old",
        phase_id=PHASE_B2,
        phase_label="Phase B2 Detailed Replay",
        action_name="PHASE_B2_DETAILED_REPLAY",
        status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
    )

    consistency = build_state_consistency(
        current_form_state=current_form_state,
        source_preview_state=source_preview_state,
        launch_request_state=launch_request_state,
        latest_canonical_summary_state=latest_canonical_summary_state,
    )

    assert consistency.consistency_status == "DASHBOARD_STATE_MISMATCH"
    assert consistency.current_form_changed_since_launch is True
    assert consistency.current_form_changed_since_summary is True
    assert consistency.launch_matches_displayed_summary_workflow is True
    assert consistency.operator_context_status == "CURRENT_FORM_MOVED_AFTER_LAUNCH"
    assert (
        consistency.operator_context_message
        == "Current form now targets a different workflow than the latest launch job. The displayed summary still belongs to the latest launch workflow."
    )
    assert "current_form_workflow_vs_launch" in consistency.mismatch_fields
    assert "current_form_workflow_vs_summary" in consistency.mismatch_fields


def test_backtest_page_explains_current_form_moved_after_launch() -> None:
    scratch = _scratch_dir("patch6_backtest_page_form_moved_after_launch")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        workflow_root = jobs_root / "workflows" / "strategy_ladder_workflow-page-context"
        phase_b2_root = workflow_root / "phase_b2_detailed_replay"
        phase_b2_root.mkdir(parents=True, exist_ok=True)
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-page-context",
            request_hash="hash-old",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=100,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="strategy_ladder_workflow-page-context",
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-context-current",
            phase_output_root=phase_b2_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            phase_status="PHASE_B2_BACKTEST_PROOF_BLOCKED",
            error_code="OUTPUT_ROOT_EXISTS_NON_EMPTY",
            blocker_codes=("OUTPUT_ROOT_EXISTS_NON_EMPTY",),
        )
        run_dir = (
            phase_b2_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_workflow-page-context"
        )
        summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
        _write_json(
            summary_path,
            {
                "run_id": "strategy_ladder_workflow-page-context",
                "workflow_run_id": "strategy_ladder_workflow-page-context",
                "phase_run_id": "phase-b2-page-context-older",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            },
        )
        current_record = CockpitBacktestJobRecord(
            job_id="runner-page-context-current",
            correlation_id="corr-page-context-current",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_BLOCKED,
            requested_at_iso="2026-05-10T10:00:00+00:00",
            started_at_iso="2026-05-10T10:00:01+00:00",
            finished_at_iso="2026-05-10T10:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-page-context-current" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-page-context-current" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-context-current",
            workflow_run_id="strategy_ladder_workflow-page-context",
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            request_hash="hash-old",
            error_summary="OUTPUT_ROOT_EXISTS_NON_EMPTY",
            blockers=("OUTPUT_ROOT_EXISTS_NON_EMPTY",),
        )
        older_record = CockpitBacktestJobRecord(
            job_id="runner-page-context-older",
            correlation_id="corr-page-context-older",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-05-10T09:00:00+00:00",
            started_at_iso="2026-05-10T09:00:01+00:00",
            finished_at_iso="2026-05-10T09:00:02+00:00",
            output_root=str(phase_b2_root),
            record_path=str((jobs_root / "runner-page-context-older" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "runner-page-context-older" / "stdout.log").resolve()),
            command=("python", "stub.py"),
            phase_id=PHASE_B2,
            phase_run_id="phase-b2-page-context-older",
            workflow_run_id="strategy_ladder_workflow-page-context",
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            request_hash="hash-old",
            stage_summary_path=str(summary_path.resolve()),
        )
        _write_json(Path(current_record.record_path), current_record.model_dump(mode="json"))
        _write_json(Path(older_record.record_path), older_record.model_dump(mode="json"))

        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                phase_id=PHASE_B2,
                workflow_phase=PHASE_B2,
                orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
                trades_path="L:\\trades\\BTCUSDT",
                klines_path="L:\\klines\\BTCUSDT",
                metadata_path="K:\\v5.3 backtest\\metadata\\bybit\\spot",
                pairs=("BTCUSDT",),
                start="2025-05-26",
                end="2025-05-26",
                candidate_discovery_mode="FULL_DISCOVERY",
                engine_native_sample_size=100,
                full_scan_enabled="true",
                silver_storage_mode="jsonl_gz",
                output_root="K:\\v5.3 backtest\\output2",
            ),
        )
        write_source_preview_state(
            jobs_root,
            CockpitPatch6State(
                state_name="source_preview_state",
                request_hash="hash-old",
                preview_id="preview-old",
                workflow_run_id="strategy_ladder_workflow-page-context",
                phase_id=PHASE_B2,
                phase_label="Phase B2 Detailed Replay",
                action_name="PHASE_B2_DETAILED_REPLAY",
                status="PHASE_B2_DETAILED_REPLAY_READY",
            ),
        )
        write_launch_request_state(
            jobs_root,
            CockpitPatch6State(
                state_name="launch_request_state",
                request_hash="hash-old",
                preview_id="preview-old",
                job_id="runner-page-context-current",
                workflow_run_id="strategy_ladder_workflow-page-context",
                phase_id=PHASE_B2,
                phase_label="Phase B2 Detailed Replay",
                action_name="PHASE_B2_DETAILED_REPLAY",
                status="JOB_BLOCKED",
            ),
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "CURRENT_FORM_MOVED_AFTER_LAUNCH" in page.text
        assert "Current form now targets a different workflow than the latest launch job. The displayed summary still belongs to the latest launch workflow." in page.text
        assert "Current form changed since launch" in page.text
        assert "Launch matches displayed summary workflow" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_ignores_stale_preview_state_from_other_workflow() -> None:
    scratch = _scratch_dir("patch6_dashboard_stale_preview_workflow")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                phase_id=PHASE_B2,
                workflow_phase=PHASE_B2,
                orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
                trades_path="L:\\trades\\BTCUSDT",
                klines_path="L:\\klines\\BTCUSDT",
                metadata_path="K:\\v5.3 backtest\\metadata\\bybit\\spot",
                pairs=("BTCUSDT",),
                start="2025-05-26",
                end="2025-05-26",
                candidate_discovery_mode="FULL_DISCOVERY",
                engine_native_sample_size=100,
                full_scan_enabled="true",
                silver_storage_mode="jsonl_gz",
                output_root="K:\\v5.3 backtest\\output2",
            ),
        )
        write_source_preview_state(
            jobs_root,
            CockpitPatch6State(
                state_name="source_preview_state",
                request_hash="hash-stale-preview",
                preview_id="preview-stale",
                workflow_run_id="strategy_ladder_workflow-stalepreview",
                phase_id=PHASE_A1,
                phase_label="Phase A1 Preview",
                action_name="PHASE_A1_PREVIEW",
                status="PHASE_A1_PREVIEW_READY",
            ),
        )
        vm = build_dashboard_view_model(
            paths=client.app.state.paths,
            welcome_message="Welcome",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            current_page="backtest",
        )
        assert vm.current_form_state is not None
        assert vm.current_form_state.workflow_run_id
        assert (
            vm.current_form_state.workflow_run_id
            != "strategy_ladder_workflow-stalepreview"
        )
        assert vm.source_preview_state is None
        assert vm.backtest_preflight.preview_id == ""
        assert "current_form_vs_preview" not in vm.cockpit_state_consistency.mismatch_fields
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_explains_default_output_root_and_b1_a2_dependency() -> None:
    scratch = _scratch_dir("patch6_output_root_b1_dependency")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B1_CANDIDATE_DISCOVERY",
                phase_id=PHASE_B1,
                workflow_phase=PHASE_B1,
                workflow_run_id="strategy_ladder_workflow-de11c968e60f2856",
                export_dir="K:\\v5.3 backtest\\output2",
                baseline_export_dir="K:\\v5.3 backtest\\output2",
                orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
                trades_path="L:\\trades\\BTCUSDT",
                klines_path="L:\\klines\\BTCUSDT",
                metadata_path="K:\\v5.3 backtest\\metadata\\bybit\\spot",
                pairs=("BTCUSDT",),
                start="2025-07-19",
                end="2025-07-30",
                ml_mode="ML_MODE_OVERLAY_FROZEN",
                silver_storage_mode="jsonl_gz",
                full_scan_enabled="true",
                candidate_discovery_mode="FULL_DISCOVERY",
                output_root="",
            ),
        )
        write_source_preview_state(
            jobs_root,
            CockpitPatch6State(
                state_name="source_preview_state",
                request_hash="hash-b1-a2",
                preview_id="preview-b1-a2",
                workflow_run_id="strategy_ladder_workflow-de11c968e60f2856",
                phase_id=PHASE_B1,
                phase_label="Phase B1 Candidate Discovery",
                action_name="PHASE_B1_CANDIDATE_DISCOVERY",
                status="PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED",
                output_root_effective=str(
                    jobs_root
                    / "workflows"
                    / "strategy_ladder_workflow-de11c968e60f2856"
                    / "phase_b1_candidate_discovery"
                ),
                blockers=(
                    "PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS",
                    "FEATURE_STORE_NOT_MATERIALIZED_FOR_B1",
                    "SILVER_INDEX_NOT_MATERIALIZED_FOR_B1",
                ),
            ),
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Workflow artifact root defaulted" in page.text
        assert "A2 silver/gold and B1/B2 workflow artifacts will be written under" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_adopt_launch_workflow_updates_form_state() -> None:
    scratch = _scratch_dir("patch6_adopt_launch_workflow")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                phase_id=PHASE_B2,
                workflow_phase=PHASE_B2,
                orderbook_path="L:\\ordrebookpart1\\OLD",
                trades_path="L:\\trades\\OLD",
                klines_path="L:\\klines\\OLD",
                metadata_path="K:\\metadata\\old",
                pairs=("OLDUSDT",),
                start="2025-05-27",
                end="2025-05-27",
                candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
                engine_native_sample_size=10,
                output_root="K:\\v5.3 backtest\\output_old",
                signed_by="tester",
            ),
        )
        write_launch_request_state(
            jobs_root,
            CockpitPatch6State(
                state_name="launch_request_state",
                request_hash="hash-launch",
                preview_id="preview-launch",
                job_id="runner-launch",
                workflow_run_id="strategy_ladder_workflow-launch",
                pair_subset=("BTCUSDT",),
                start="2025-05-25",
                end="2025-05-26",
                orderbook_root="L:\\ordrebookpart1\\BTCUSDT",
                trades_root="L:\\trades\\BTCUSDT",
                klines_root="L:\\klines\\BTCUSDT",
                historical_metadata_root="K:\\v5.3 backtest\\metadata\\bybit\\spot",
                output_root_selected="K:\\v5.3 backtest\\output2",
                ml_mode="ML_MODE_OFF",
                candidate_discovery_mode="FULL_DISCOVERY",
                engine_native_sample_size=100,
                allow_broad_run=False,
                small_scope_enabled=False,
                full_scan_enabled=True,
                no_full_scan_enabled=False,
                silver_storage_mode="jsonl_gz",
                status="JOB_BLOCKED",
                phase_id=PHASE_B2,
                phase_label="Phase B2 Detailed Replay",
                action_name="PHASE_B2_DETAILED_REPLAY",
            ),
        )

        response = client.post(
            "/backtest/adopt-launch-workflow",
            follow_redirects=False,
        )
        assert response.status_code == 303

        updated_form = read_backtest_form_state(jobs_root)
        assert updated_form.workflow_run_id == "strategy_ladder_workflow-launch"
        assert updated_form.pairs == ("BTCUSDT",)
        assert updated_form.start == "2025-05-25"
        assert updated_form.end == "2025-05-26"
        assert updated_form.orderbook_path == "L:\\ordrebookpart1\\BTCUSDT"
        assert updated_form.trades_path == "L:\\trades\\BTCUSDT"
        assert updated_form.klines_path == "L:\\klines\\BTCUSDT"
        assert updated_form.metadata_path == "K:\\v5.3 backtest\\metadata\\bybit\\spot"
        assert updated_form.candidate_discovery_mode == "FULL_DISCOVERY"
        assert updated_form.engine_native_sample_size == 100
        assert updated_form.full_scan_enabled == "true"
        assert updated_form.output_root == "K:\\v5.3 backtest\\output2"
        assert updated_form.signed_by == "tester"

        updated_current_state = read_current_form_state(jobs_root)
        assert updated_current_state is not None
        assert updated_current_state.workflow_run_id == "strategy_ladder_workflow-launch"
        assert updated_current_state.phase_id == PHASE_B2
        assert updated_current_state.request_hash == "hash-launch"
        assert updated_current_state.status == "JOB_BLOCKED"

        vm = build_dashboard_view_model(
            paths=client.app.state.paths,
            welcome_message="Welcome",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            current_page="backtest",
        )
        assert vm.current_form_state is not None
        assert vm.current_form_state.workflow_run_id == "strategy_ladder_workflow-launch"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dashboard_recovers_preview_from_current_form_when_source_preview_state_missing() -> None:
    scratch = _scratch_dir("patch6_preview_recovery_from_current_form")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        response = client.post(
            "/backtest/run",
            data={
                "intent": "preview",
                "action_name": "PHASE_A2_DATA_FACTORY",
                "export_dir": "K:\\v5.3 backtest\\output2",
                "baseline_export_dir": "K:\\v5.3 backtest\\output2",
                "orderbook_path": "L:\\ordrebookpart1\\BTCUSDT",
                "trades_path": "L:\\trades\\BTCUSDT",
                "klines_path": "L:\\klines\\BTCUSDT",
                "metadata_path": "K:\\v5.3 backtest\\metadata\\bybit\\spot",
                "pairs": "BTCUSDT",
                "start": "2025-07-19",
                "end": "2025-07-20",
                "ml_mode": "ML_MODE_OFF",
                "candidate_discovery_mode": "TEMPORAL_STRATIFIED",
                "engine_native_sample_size": "10",
                "b1_5_policy_mode": "conservative_hard_only",
                "full_scan_enabled": "true",
                "silver_storage_mode": "jsonl_gz",
                "output_root": "K:\\v5.3 backtest\\output2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        source_preview_state_path = jobs_root / "_source_preview_state.json"
        assert source_preview_state_path.is_file()
        source_preview_state_path.unlink()

        vm = build_dashboard_view_model(
            paths=client.app.state.paths,
            welcome_message="Welcome",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            current_page="backtest",
        )
        assert vm.current_form_state is not None
        assert vm.current_form_state.preview_id
        assert vm.source_preview_state is not None
        assert vm.source_preview_state.preview_id == vm.current_form_state.preview_id
        assert vm.backtest_preflight.inspection_status == "PHASE_A2_DATA_FACTORY_READY"
        assert vm.backtest_preflight.preview_id == vm.current_form_state.preview_id
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_shows_adopt_launch_workflow_control() -> None:
    scratch = _scratch_dir("patch6_adopt_launch_workflow_button")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        write_backtest_form_state(
            jobs_root,
            BacktestFormState(
                action_name="PHASE_B2_DETAILED_REPLAY",
                phase_id=PHASE_B2,
                workflow_phase=PHASE_B2,
                orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
                trades_path="L:\\trades\\BTCUSDT",
                klines_path="L:\\klines\\BTCUSDT",
                metadata_path="K:\\v5.3 backtest\\metadata\\bybit\\spot",
                pairs=("BTCUSDT",),
                start="2025-05-26",
                end="2025-05-26",
                candidate_discovery_mode="FULL_DISCOVERY",
                engine_native_sample_size=100,
                full_scan_enabled="true",
                silver_storage_mode="jsonl_gz",
                output_root="K:\\v5.3 backtest\\output2",
            ),
        )
        write_launch_request_state(
            jobs_root,
            CockpitPatch6State(
                state_name="launch_request_state",
                request_hash="hash-launch",
                preview_id="preview-launch",
                job_id="runner-launch",
                workflow_run_id="strategy_ladder_workflow-launch",
                phase_id=PHASE_B2,
                phase_label="Phase B2 Detailed Replay",
                action_name="PHASE_B2_DETAILED_REPLAY",
                status="JOB_BLOCKED",
            ),
        )
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Adopt Current Launch Workflow" in page.text
        assert "/backtest/adopt-launch-workflow" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_folder_picker_browse_endpoint_lists_directories() -> None:
    scratch = _scratch_dir("patch6_folder_picker")
    try:
        client = _build_client(scratch)
        (scratch / "a_dir").mkdir(parents=True, exist_ok=True)
        (scratch / "b_dir").mkdir(parents=True, exist_ok=True)
        response = client.get("/backtest/picker/browse", params={"path": str(scratch)})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "FOLDER_LIST_READY"
        names = {item["name"] for item in payload["directories"]}
        assert {"a_dir", "b_dir"}.issubset(names)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_folder_picker_native_endpoint_returns_selected_directory(monkeypatch) -> None:
    scratch = _scratch_dir("patch6_folder_picker_native")
    try:
        client = _build_client(scratch)
        selected = scratch / "chosen_dir"
        selected.mkdir(parents=True, exist_ok=True)

        def _fake_pick(initial_path_text: str) -> dict[str, str]:
            assert str(scratch) in initial_path_text
            return {
                "status": "FOLDER_PICKER_SELECTED",
                "reason": "",
                "selected_path": str(selected),
            }

        monkeypatch.setattr(server_module, "_pick_native_directory", _fake_pick)
        response = client.get("/backtest/picker/native", params={"path": str(scratch)})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "FOLDER_PICKER_SELECTED"
        assert payload["selected_path"] == str(selected)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_status_json_returns_lightweight_snapshot() -> None:
    scratch = _scratch_dir("backtest_status_snapshot")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        output_root = scratch / "run_output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "blocker_codes": [],
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_data_factory-1",
            correlation_id="corr-1",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            requested_at_iso="2026-01-01T00:00:00+00:00",
            started_at_iso="2026-01-01T00:00:01+00:00",
            finished_at_iso="2026-01-01T00:00:03+00:00",
            output_root=str(output_root),
            record_path=str((jobs_root / "strategy_ladder_data_factory-1" / "job.json").resolve()),
            stdout_log_path=str((jobs_root / "strategy_ladder_data_factory-1" / "stdout.log").resolve()),
            output_refs=(str((output_root / "data_factory_manifest.json").resolve()),),
            pid=0,
        )
        _write_json(jobs_root / "strategy_ladder_data_factory-1" / "job.json", record.model_dump(mode="json"))

        response = client.get("/backtest/status.json")
        assert response.status_code == 200
        payload = response.json()
        assert payload["service"]["label"] == "Shadow Service"
        assert payload["summary"]["requested_count"] == 1
        assert payload["summary"]["latest_status"] == "JOB_COMPLETED"
        assert payload["latest_job"]["job_id"] == "strategy_ladder_data_factory-1"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_status_json_reconciles_dead_running_job_from_manifests() -> None:
    scratch = _scratch_dir("backtest_status_stale_running")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_root = jobs_root / "strategy_ladder_first_controlled_run-stale"
        output_root = scratch / "stale_output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "first_run_manifest.json",
            {
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_status": "RAW_WINDOW_PARTIAL",
                "blocker_codes": ["RAW_WINDOW_NOT_PROVEN"],
                "stage_statuses": {
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "raw_window_status": "RAW_WINDOW_PARTIAL",
                },
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_first_controlled_run-stale",
            correlation_id="corr-stale",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            requested_at_iso="2026-01-01T00:00:00+00:00",
            started_at_iso="2026-01-01T00:00:01+00:00",
            output_root=str(output_root),
            record_path=str((job_root / "job.json").resolve()),
            stdout_log_path=str((job_root / "stdout.log").resolve()),
            pid=999999,
        )
        _write_json(job_root / "job.json", record.model_dump(mode="json"))

        response = client.get("/backtest/status.json")
        assert response.status_code == 200
        payload = response.json()
        latest_job = payload["latest_job"]
        assert latest_job["job_id"] == "strategy_ladder_first_controlled_run-stale"
        assert latest_job["status"] == "JOB_COMPLETED_WITH_BLOCKERS"
        assert latest_job["pid_alive"] is False
        assert "JOB_RECORD_STALE_PID_DEAD" in latest_job["error_summary"]
        updated = json.loads((job_root / "job.json").read_text(encoding="utf-8"))
        assert updated["status"] == "JOB_COMPLETED_WITH_BLOCKERS"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_tolerates_stale_job_reconcile_write_failure(monkeypatch) -> None:
    scratch = _scratch_dir("lab_stale_job_write_failure")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None
        job_root = jobs_root / "strategy_ladder_first_controlled_run-stale"
        output_root = scratch / "stale_output"
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_root / "first_run_manifest.json",
            {
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_status": "RAW_WINDOW_PARTIAL",
                "blocker_codes": ["RAW_WINDOW_NOT_PROVEN"],
                "stage_statuses": {
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "raw_window_status": "RAW_WINDOW_PARTIAL",
                },
            },
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_first_controlled_run-stale",
            correlation_id="corr-stale",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            requested_at_iso="2026-01-01T00:00:00+00:00",
            started_at_iso="2026-01-01T00:00:01+00:00",
            output_root=str(output_root),
            record_path=str((job_root / "job.json").resolve()),
            stdout_log_path=str((job_root / "stdout.log").resolve()),
            pid=999999,
        )
        _write_json(job_root / "job.json", record.model_dump(mode="json"))

        def _fail_write(*args, **kwargs) -> None:
            raise PermissionError("simulated job record lock")

        monkeypatch.setattr(action_support_module, "_write_backtest_job_record", _fail_write)

        response = client.get("/lab")
        assert response.status_code == 200
        assert "Strategy Ladder ML Handoff" in response.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_lab_page_tolerates_null_service_state_heartbeat() -> None:
    scratch = _scratch_dir("lab_null_service_state_heartbeat")
    try:
        client = _build_client(scratch)
        service_dir = client.app.state.paths.service_dir
        assert service_dir is not None
        state_path = service_dir / "shadow_vps_service.state.json"
        payload_path = service_dir / "shadow_vps_service_monitoring_backend_payload.json"
        state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        state_payload["last_heartbeat_at"] = None
        state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        payload_path.unlink(missing_ok=True)

        response = client.get("/lab")
        assert response.status_code == 200
        assert "Strategy Ladder ML Handoff" in response.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_labels_shadow_service_and_light_polling_notice() -> None:
    scratch = _scratch_dir("backtest_shadow_service_label")
    try:
        client = _build_client(scratch)
        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Shadow Service offline" in page.text
        assert "Lightweight status polling is enabled on the backtest page." in page.text
        assert "/backtest/status.json" in page.text
        assert 'id="backtest-jobs-table-host"' in page.text
        assert "Observe the active run here first" in page.text
        assert "B1.5 policy mode" in page.text
        assert "conservative_hard_only" in page.text
        assert page.text.index("Recent Backtest Jobs") < page.text.index("Cockpit State Consistency")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_b15_preselection_panel() -> None:
    scratch = _scratch_dir("backtest_b15_preselection_panel")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        job_dir = jobs_root / "strategy_ladder_runner-preselection"
        output_root = job_dir / "output"
        run_dir = (
            output_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_runner-preselection"
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_runner-preselection",
            correlation_id="cockpit-preselection",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.COMPLETED,
            requested_at_iso="2026-05-16T08:00:00+00:00",
            finished_at_iso="2026-05-16T08:03:00+00:00",
            export_dir=str((scratch / "export").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_backtest_strategy_ladder.py"),
            command_preview="python run_backtest_strategy_ladder.py --preselected-only",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            run_dir / "reports" / "strategy_ladder_summary.json",
            {
                "run_id": "strategy_ladder_runner-preselection",
                "final_status": "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
                "feature_store_status": "FEATURE_STORE_READY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "capital_profile_generation_status": "CAPITAL_PROFILE_GENERATION_READY",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
                "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
            },
        )
        _write_json(
            run_dir / "run_manifest.json",
            {
                "run_id": "strategy_ladder_runner-preselection",
                "preselection_status": "ENGINE_NATIVE_PRESELECTION_READY",
                "replay_input_mode_status": "PRESELECTED_ONLY",
                "preselected_only": True,
                "diagnostic_full_replay": False,
                "b1_5_policy_mode": "conservative_hard_only",
                "candidate_count": 12,
                "unique_candidate_count": 12,
                "discovery_pre_candidate_count": 12,
                "engine_native_preselected_count": 3,
                "preselection_hard_rejected_count": 5,
                "preselection_soft_flagged_count": 4,
                "preselection_passed_count": 3,
                "b2_replay_candidate_count": 3,
                "trade_eligible_candidate_count": 0,
                "preselection_rejection_count": 9,
                "replay_savings_estimate_count": 9,
                "replay_record_count": 12,
                "evaluation_record_count": 12,
                "promotion_record_count": 12,
                "capital_bucket_record_count": 12,
                "candidate_source_status": "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
            },
        )
        _write_json(
            run_dir / "reports" / "preselection_summary.json",
            {
                "status": "ENGINE_NATIVE_PRESELECTION_READY",
                "replay_input_mode_status": "PRESELECTED_ONLY",
                "preselected_only": True,
                "diagnostic_full_replay": False,
                "b1_5_policy_mode": "conservative_hard_only",
                "discovery_pre_candidate_count": 12,
                "engine_native_preselected_count": 3,
                "preselection_hard_rejected_count": 5,
                "preselection_soft_flagged_count": 4,
                "preselection_passed_count": 3,
                "b2_replay_candidate_count": 3,
                "preselection_rejection_count": 9,
                "replay_savings_estimate_count": 9,
                "top_hard_rejection_reasons": [
                    {
                        "reason_code": "engine_internal.engine_a.direction.non_long",
                        "count": 5,
                    }
                ],
                "top_soft_advisory_reasons": [
                    {
                        "reason_code": "BUILD14_READER:execution_fragility_score:ELEVATED",
                        "count": 4,
                    }
                ],
                "top_rejection_reasons": [
                    {
                        "reason_code": "engine_internal.engine_a.direction.non_long",
                        "count": 5,
                    }
                ],
            },
        )
        _write_jsonl(
            run_dir / "preselection_rejection_ledger.jsonl",
            [
                {
                    "candidate_id": "cand-1",
                    "engine_id": "engine_a",
                    "candidate_intent": "DISCOVERY_PRE_CANDIDATE",
                    "preselection_reason_primary": (
                        "engine_internal.engine_a.direction.non_long"
                    ),
                }
            ],
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "B1.5 Native Preselection" in page.text
        assert "Engine-native preselected" in page.text
        assert "Hard rejected" in page.text
        assert "Soft flagged" in page.text
        assert "Replay savings estimate" in page.text
        assert "engine_internal.engine_a.direction.non_long" in page.text
        assert "BUILD14_READER:execution_fragility_score:ELEVATED" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_launch_defaults_to_preselected_only_replay() -> None:
    scratch = _scratch_dir("patch6_preselected_only_default")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            action_name="PHASE_B2_DETAILED_REPLAY",
            export_dir=str(scratch / "export"),
            orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
            trades_path="L:\\trades\\BTCUSDT",
            klines_path="L:\\klines\\BTCUSDT\\1",
            start="2025-04-29",
            end="2025-04-29",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request["b1_5_policy_mode"] == "conservative_hard_only"
        assert request["preselected_only"] is True
        assert request["diagnostic_full_replay"] is False
        assert "--b1-5-policy-mode conservative_hard_only" in request["command_preview"]
        assert "--preselected-only" in request["command_preview"]
        assert "--diagnostic-full-replay" not in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_launch_supports_diagnostic_full_replay_override() -> None:
    scratch = _scratch_dir("patch6_diagnostic_full_replay")
    try:
        client = _build_client(scratch)
        response = _post_patch6(
            client,
            action_name="PHASE_B2_DETAILED_REPLAY",
            export_dir=str(scratch / "export"),
            orderbook_path="L:\\ordrebookpart1\\BTCUSDT",
            trades_path="L:\\trades\\BTCUSDT",
            klines_path="L:\\klines\\BTCUSDT\\1",
            start="2025-04-29",
            end="2025-04-29",
            b1_5_policy_mode="diagnostic_full_replay",
        )
        assert response.status_code == 303
        request = _read_latest_job_request(client.app.state.paths.backtest_jobs_root)
        assert request["b1_5_policy_mode"] == "diagnostic_full_replay"
        assert request["preselected_only"] is False
        assert request["diagnostic_full_replay"] is True
        assert "--b1-5-policy-mode diagnostic_full_replay" in request["command_preview"]
        assert "--diagnostic-full-replay" in request["command_preview"]
        assert "--no-preselected-only" in request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_page_surfaces_replay_performance_panel() -> None:
    scratch = _scratch_dir("backtest_replay_performance_panel")
    try:
        client = _build_client(scratch)
        jobs_root = client.app.state.paths.backtest_jobs_root
        assert jobs_root is not None

        job_dir = jobs_root / "strategy_ladder_runner-replay-performance"
        output_root = job_dir / "output"
        run_dir = (
            output_root
            / "backtest_strategy_ladder"
            / "strategy_ladder_runner-replay-performance"
        )
        record = CockpitBacktestJobRecord(
            job_id="strategy_ladder_runner-replay-performance",
            correlation_id="cockpit-replay-performance",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            status=CockpitBacktestJobStatus.COMPLETED,
            requested_at_iso="2026-05-15T08:00:00+00:00",
            finished_at_iso="2026-05-15T08:05:00+00:00",
            export_dir=str((scratch / "export").resolve()),
            output_root=str(output_root.resolve()),
            record_path=str((job_dir / "job.json").resolve()),
            stdout_log_path=str((job_dir / "stdout.log").resolve()),
            command=("python", "run_backtest_strategy_ladder.py"),
            command_preview="python run_backtest_strategy_ladder.py",
        )
        _write_json(Path(record.record_path), record.model_dump(mode="json"))
        _write_json(
            run_dir / "reports" / "strategy_ladder_summary.json",
            {
                "run_id": "strategy_ladder_runner-replay-performance",
                "final_status": "STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED",
                "feature_store_status": "FEATURE_STORE_READY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "raw_window_extraction_status": "RAW_WINDOW_READY",
                "detailed_replay_status": "DETAILED_REPLAY_READY",
                "capital_profile_generation_status": "CAPITAL_PROFILE_GENERATION_READY",
                "promotion_artifact_status": "PROMOTION_ARTIFACTS_READY",
                "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
            },
        )
        _write_json(
            run_dir / "replay_performance_profile.json",
            {
                "run_id": "strategy_ladder_runner-replay-performance",
                "status": "REPLAY_PERFORMANCE_PROFILE_READY",
                "total_wall_time_s": 180.0,
                "total_cpu_time_s": 75.0,
                "total_io_wait_estimate_s": 105.0,
                "rows_processed": 36000,
                "files_scanned": 128,
                "candidate_count": 1000,
                "replay_record_count": 4000,
                "bottleneck_summary": [
                    "replay_orchestration:92.0s",
                    "raw_window_extraction:41.0s",
                ],
                "indexed_lookup_metrics": {
                    "status": "INDEXED_WINDOW_LOOKUP_READY",
                    "indexed_lookup_hit_rate": 0.97,
                    "index_lookup_miss_count": 2,
                    "fallback_scan_count": 0,
                },
                "window_cache_metrics": {
                    "status": "WINDOW_CACHE_READY",
                    "cache_hit_count": 480,
                    "cache_miss_count": 40,
                    "cache_reuse_ratio": 0.923077,
                },
                "phases": [
                    {
                        "phase_name": "raw_window_extraction",
                        "wall_time_s": 41.0,
                    },
                    {
                        "phase_name": "replay_orchestration",
                        "wall_time_s": 92.0,
                    },
                    {
                        "phase_name": "dashboard_report_generation",
                        "wall_time_s": 7.0,
                    },
                ],
                "parquet_fast_path_status": "PARQUET_REPLAY_NOT_PROVEN",
                "research_fast_debug_mode_status": (
                    "RESEARCH_FAST_DEBUG_MODE_NOT_REQUESTED"
                ),
                "replay_workers_used": 0,
                "replay_queue_wait_time_s": 0.0,
            },
        )

        page = client.get("/backtest")
        assert page.status_code == 200
        assert "Replay Performance" in page.text
        assert "REPLAY_PERFORMANCE_PROFILE_READY" in page.text
        assert "INDEXED_WINDOW_LOOKUP_READY" in page.text
        assert "WINDOW_CACHE_READY" in page.text
        assert "replay_orchestration:92.0s" in page.text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patch6_preflight_dedupes_archive_and_extracted_orderbook_variants() -> None:
    scratch = _scratch_dir("patch6_preflight_dedupes_orderbook")
    try:
        orderbook_root = scratch / "ordre book part 1" / "ADAUSDT"
        orderbook_root.mkdir(parents=True, exist_ok=True)
        raw_text = (
            '{"topic":"orderbook.200.ADAUSDT","type":"snapshot","ts":1714410000000,'
            '"data":{"s":"ADAUSDT","b":[["1.0","2.0"]],"a":[["1.1","3.0"]],"u":100,"seq":100},'
            '"cts":1714410000000}\n'
        )
        zip_path = orderbook_root / "2025-07-22_ADAUSDT_ob200.data.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("2025-07-22_ADAUSDT_ob200.data", raw_text)
        extracted_dir = orderbook_root / "2025-07-22_ADAUSDT_ob200.data"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        (extracted_dir / "2025-07-22_ADAUSDT_ob200.data").write_text(raw_text, encoding="utf-8")

        preview = build_patch6_preflight_preview(
            selected_form=BacktestFormState(
                action_name="DATA_FACTORY_DRY_RUN",
                export_dir=str(scratch / "export"),
                orderbook_path=str(orderbook_root),
                pairs=("ADAUSDT",),
                start="2025-07-22",
                end="2025-07-22",
            ),
            jobs_root=scratch / "jobs",
        )

        assert preview.orderbook.files_matched == 1
        assert preview.files_matched_total == 1
        assert preview.orderbook.preview_status == "SOURCE_PREVIEW_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_running_job_progress_is_clamped_below_100() -> None:
    pct, eta = estimate_job_progress(
        job_kind="strategy_ladder_data_factory",
        status="JOB_RUNNING",
        started_at_iso="2026-01-01T00:00:00+00:00",
        finished_at_iso="",
    )
    assert 0 <= pct <= 95
    assert eta >= 0.0


def test_completed_job_shows_full_progress_and_zero_eta() -> None:
    pct, eta = estimate_job_progress(
        job_kind="strategy_ladder_data_factory",
        status="JOB_COMPLETED",
        started_at_iso="2026-01-01T00:00:00+00:00",
        finished_at_iso="2026-01-01T00:05:00+00:00",
    )
    assert pct == 100
    assert eta == 0.0


def test_is_valid_raw_source_manifest_path_unit() -> None:
    assert is_valid_raw_source_manifest_path("L:\\raw_sources.json")
    assert is_valid_raw_source_manifest_path("/tmp/sources.json")
    assert not is_valid_raw_source_manifest_path("L:\\raw_sources\\")
    assert not is_valid_raw_source_manifest_path("L:\\dump.data")
    assert not is_valid_raw_source_manifest_path("L:\\dump.csv")
    assert not is_valid_raw_source_manifest_path("L:\\dump.jsonl")
    assert not is_valid_raw_source_manifest_path("")


def test_infer_pair_universe_from_paths_unit() -> None:
    syms, ambiguous = infer_pair_universe_from_paths((
        "L:\\klines\\BTCUSDT\\1",
        "L:\\trades\\BTCUSDT\\",
    ))
    assert syms == ("BTCUSDT",)
    assert not ambiguous

    syms, ambiguous = infer_pair_universe_from_paths((
        "L:\\klines\\BTCUSDT\\1",
        "L:\\klines\\ETHUSDT\\1",
    ))
    assert ambiguous
    assert "BTCUSDT" in syms and "ETHUSDT" in syms
