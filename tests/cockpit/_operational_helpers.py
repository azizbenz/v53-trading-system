from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from cockpit.queue_support import (
    initialize_dashboard_command_queue,
    resolve_dashboard_command_queue_paths,
)
from cockpit.state import CockpitPaths
from interface_contracts import (
    DashboardGovernedCommandAck,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    ProfileId,
    RuntimeMode,
)
from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceState
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    candidates = (
        repo_root / ".test_tmp" / "pytest_phase25",
        repo_root / ".test_tmp" / "pytest_phase25_alt",
    )
    for base in candidates:
        try:
            base.mkdir(parents=True, exist_ok=True)
            target = base / f"{label}_{uuid4().hex}"
            target.mkdir(parents=True, exist_ok=False)
            return target
        except PermissionError:
            continue
    base = repo_root / ".test_tmp" / f"pytest_phase25_fallback_{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{label}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def cleanup_scratch(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def build_paths(tmp_path: Path) -> CockpitPaths:
    service_dir = tmp_path / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    auto_exports_root = tmp_path / "auto_exports"
    auto_exports_root.mkdir(parents=True, exist_ok=True)
    live_config = tmp_path / "live_websocket_config.json"
    write_json(live_config, {"pairs": ["BTCUSDT", "ETHUSDT"]})
    calibration = tmp_path / "thresholds.yml"
    calibration.write_text(
        'schema_version: calibration.v1\nthresholds:\n  - threshold_id: THR-X02\n    value: 30.0\n',
        encoding="utf-8",
    )
    queue_root = tmp_path / "dashboard_command_queue"
    initialize_dashboard_command_queue(queue_root)
    build_root = tmp_path / "build_root"
    build_root.mkdir(parents=True, exist_ok=True)
    return CockpitPaths(
        service_dir=service_dir,
        pid_file=tmp_path / "shadow_vps_service.pid",
        log_file=service_dir / "shadow_vps_service.log",
        auto_exports_root=auto_exports_root,
        live_websocket_config=live_config,
        calibration_thresholds=calibration,
        build_root=build_root,
        dashboard_command_queue_root=queue_root,
        observability_output_dir=tmp_path / "observability",
        backtest_jobs_root=tmp_path / "backtest_jobs",
        artifact_ingress_root=tmp_path / "artifact_ingress",
    )


def seed_phase25_files(paths: CockpitPaths) -> None:
    current_dir = paths.auto_exports_root / "2026-04-27"
    previous_dir = paths.auto_exports_root / "2026-04-26"
    current_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        current_dir / "replay_metrics.json",
        {
            "total_records": 2,
            "total_opportunities": 2,
            "selected_count": 1,
            "executed_count": 1,
            "hard_blocked_count": 0,
            "rejected_ranking_count": 1,
            "ce_net": 0.002193,
            "engine_aggregates": [
                {
                    "engine_id": "engine_a",
                    "record_count": 1,
                    "selected_count": 1,
                    "hard_blocked_count": 0,
                    "ce_net": 0.0016,
                    "expected_cost_mean": 0.0001,
                    "realized_cost_mean": 0.0001,
                },
                {
                    "engine_id": "engine_b",
                    "record_count": 1,
                    "selected_count": 0,
                    "hard_blocked_count": 0,
                    "ce_net": 0.000593,
                    "expected_cost_mean": 0.000107,
                    "realized_cost_mean": 0.0,
                },
            ],
        },
    )
    write_json(
        previous_dir / "replay_metrics.json",
        {
            "total_records": 1,
            "total_opportunities": 1,
            "selected_count": 1,
            "executed_count": 1,
            "hard_blocked_count": 0,
            "rejected_ranking_count": 0,
            "ce_net": 0.0016,
            "engine_aggregates": [
                {
                    "engine_id": "engine_a",
                    "record_count": 1,
                    "selected_count": 1,
                    "hard_blocked_count": 0,
                    "ce_net": 0.0016,
                    "expected_cost_mean": 0.0001,
                    "realized_cost_mean": 0.0001,
                }
            ],
        },
    )
    write_json(
        current_dir / "feature_bridge.json",
        {
            "bridge_status": "ok",
            "record_count": 2,
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "engines": ["engine_a", "engine_b"],
            "feature_keys": ["spread_bps"],
            "recognized_feature_keys": [],
            "unrecognized_feature_keys": ["spread_bps"],
            "lineage_lock_status": "missing",
            "lineage_lock_reasons": ["feature lineage lock is required"],
            "feature_to_engine_path": "historical_prices -> computed_features -> engines -> scoring",
        },
    )
    write_json(
        previous_dir / "feature_bridge.json",
        {
            "bridge_status": "ok",
            "record_count": 1,
            "pairs": ["BTCUSDT"],
            "engines": ["engine_a"],
            "feature_keys": ["spread_bps"],
            "recognized_feature_keys": [],
            "unrecognized_feature_keys": ["spread_bps"],
            "lineage_lock_status": "missing",
            "lineage_lock_reasons": ["feature lineage lock is required"],
            "feature_to_engine_path": "historical_prices -> computed_features -> engines -> scoring",
        },
    )
    write_json(
        current_dir / "replay_run_manifest.json",
        {
            "run_id": "run-shadow-vps-live-2026-04-27",
            "artifact_hash": "artifact-run-shadow-vps-live-2026-04-26",
            "lineage_version": "a.v4.2.r1",
        },
    )
    write_json(
        previous_dir / "replay_run_manifest.json",
        {
            "run_id": "run-shadow-vps-live-2026-04-26",
            "artifact_hash": "artifact-run-shadow-vps-live-2026-04-26",
            "lineage_version": "a.v4.2.r1",
        },
    )
    (current_dir / "replay_dtr.jsonl").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "timestamp": 1777244426.652,
                        "pair": "ETHUSDT",
                        "engine_id": "engine_b",
                        "raw_score": 0.81,
                        "penalized_score": 0.79,
                        "final_score": 0.76,
                        "hard_blocked": False,
                        "final_size": 0.0,
                        "expected_cost": 0.000107,
                        "ce_expected": 0.000593,
                        "decision_state": "rejected_ranking",
                        "primary_reason": "rank_cutoff",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": 1777244426.695,
                        "pair": "BTCUSDT",
                        "engine_id": "engine_a",
                        "raw_score": 0.91,
                        "penalized_score": 0.88,
                        "final_score": 0.86,
                        "hard_blocked": False,
                        "final_size": 1.0,
                        "expected_cost": 0.0001,
                        "ce_expected": 0.0016,
                        "decision_state": "executed",
                        "primary_reason": "",
                    }
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    capture_dir = paths.service_dir.parent / "live_captures" / "2026-04-27"
    capture_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        capture_dir / "live_websocket_snapshot_batch.json",
        [
            {
                "event_type": "snapshot",
                "event": {
                    "timestamp_ms": 1777244426577,
                    "pair": "BTCUSDT",
                    "last_price": 78282.26,
                    "bid": 78282.35,
                    "ask": 78282.36,
                },
                "route_hint": {"feature_values": {"spread_bps": 3.0}},
            },
            {
                "event_type": "trade",
                "event": {
                    "timestamp_ms": 1777244426652,
                    "pair": "ETHUSDT",
                    "price": 2360.37,
                },
                "route_hint": {"feature_values": {"spread_bps": 5.0}},
            },
        ],
    )
    write_json(
        capture_dir / "live_time_sync_offsets.json",
        {"time_sync_offsets_ms": [-433.0, -433.0, -422.0], "sample_count": 3},
    )
    write_json(
        paths.warmup_summary,
        {
            "runtime_mode": "shadow",
            "final_state": "blocked",
            "eligible_to_trade": False,
            "blocking_reasons": [
                "shadow.bootstrap.not_ready",
                "shadow.remote_account.bootstrap_unavailable",
            ],
            "report": {
                "checks": [
                    {
                        "check_id": "bootstrap_reconciliation",
                        "status": "blocked",
                        "reasons": ["shadow.bootstrap.not_ready"],
                    },
                    {
                        "check_id": "remote_account_state",
                        "status": "blocked",
                        "reasons": ["shadow.remote_account.bootstrap_unavailable"],
                    },
                    {"check_id": "time_sync", "status": "passed", "reasons": []},
                    {"check_id": "market_data_capture", "status": "passed", "reasons": []},
                    {
                        "check_id": "account_user_data",
                        "status": "review_only",
                        "reasons": ["shadow.user_data.not_authenticated"],
                    },
                    {"check_id": "binance_credentials", "status": "passed", "reasons": []},
                ]
            },
        },
    )
    state = ShadowVpsServiceState(
        service_status="degraded",
        last_heartbeat_at=1777304627.046874,
        loop_count=215,
        last_completed_session_date="2026-04-27",
        last_live_capture_snapshot_batch_ref=str(
            (capture_dir / "live_websocket_snapshot_batch.json").resolve()
        ),
        last_export_dir_ref=str(current_dir.resolve()),
        last_vps_warmup_summary_ref=str(paths.warmup_summary.resolve()),
        last_vps_warmup_final_state="blocked",
        last_vps_warmup_eligible_to_trade=False,
        dashboard_control_suspended_pairs=(),
        dashboard_control_suspended_engines=(),
    )
    (paths.service_dir / "shadow_vps_service.state.json").write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    payload = ShadowVpsServiceMonitoringPayload(
        timestamp_ms=1777304627371,
        correlation_id="shadow-vps-service",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status="critical",
        detail="phase25",
        service_status="degraded",
        heartbeat_age_ms=325,
        loop_count=215,
        success_count=4,
        idle_count=206,
        failure_count=4,
        resumed=True,
        last_completed_session_date="2026-04-27",
        last_live_complete_status="blocked",
        last_live_complete_verdict="blocked",
        last_live_complete_run_state="blocked",
        last_live_complete_operator_report_recommendation="investigate_live_complete_blockers",
        dashboard_control_halted=False,
        dashboard_control_last_request_id="",
        dashboard_control_last_command_kind="",
        dashboard_control_last_result_status="",
        process=ProcessMetricsSample(
            pid=6576,
            cpu_pct=3.0,
            ram_pct=0.0,
            rss_mb=0.0,
            thread_count=1,
            sampling_mode="fallback",
        ),
        disk=DiskUsageSample(
            path=str(paths.service_dir.resolve()),
            total_gb=931.0,
            free_gb=260.0,
            used_pct=72.0,
            sampling_mode="shutil_disk_usage",
        ),
    )
    (paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (paths.service_dir / "shadow_vps_service.events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "service_stop_requested",
                "timestamp": 1777299660.2610781,
                "message": "Shadow VPS service stop requested: signal HALT_FLAG_OBSERVED.",
                "session_date": "2026-04-27",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    lab_dir = paths.build_root / "local_lab_analysis_real" / "post_trade_review"
    lab_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        lab_dir / "meta_learning_review.bundle.json",
        {
            "correlation_id": "real-binance-2026-04-26",
            "mistake_classes": ["economic_sterilization"],
            "breakdown_report": {"summary": "CRA sterilization elevated at 100.00%"},
            "merge_gate_report": {"all_passed": True, "gates": []},
            "review_decisions": [{}],
        },
    )
    write_json(
        lab_dir / "governed_input_summary.json",
        {
            "artifact_hash": "artifact-run-shadow-vps-live-2026-04-26",
            "lineage_version": "a.v4.2.r1",
            "feature_bridge_ref": str((previous_dir / "feature_bridge.json").resolve()),
        },
    )


def write_queue_request(
    paths: CockpitPaths,
    *,
    request_id: str = "req-1",
    timestamp_ms: int = 1_777_304_627_000,
) -> None:
    request = DashboardGovernedCommandRequest(
        timestamp_ms=timestamp_ms,
        correlation_id="corr-1",
        request_id=request_id,
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE,
        source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
        target_runtime_mode=RuntimeMode.LIVE,
        requested_by="tester",
    )
    paths_queue = resolve_dashboard_command_queue_paths(paths.dashboard_command_queue_root)
    write_json(paths_queue.requests_dir / f"{timestamp_ms}_{request_id}.request.json", request.model_dump(mode="json"))


def write_queue_ack(
    paths: CockpitPaths,
    *,
    request_id: str = "req-1",
    timestamp_ms: int = 1_777_304_627_100,
) -> None:
    ack = DashboardGovernedCommandAck(
        timestamp_ms=timestamp_ms,
        correlation_id="corr-1",
        ack_id="ack-1",
        request_id=request_id,
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE,
        status=DashboardGovernedCommandStatus.ACCEPTED,
        idempotency_key="idempo",
    )
    paths_queue = resolve_dashboard_command_queue_paths(paths.dashboard_command_queue_root)
    write_json(paths_queue.acks_dir / f"{timestamp_ms}_{request_id}.ack.json", ack.model_dump(mode="json"))


def write_queue_result(
    paths: CockpitPaths,
    *,
    request_id: str = "req-1",
    timestamp_ms: int = 1_777_304_627_200,
    status: DashboardGovernedCommandStatus = DashboardGovernedCommandStatus.COMPLETED,
) -> None:
    result = DashboardGovernedCommandResult(
        timestamp_ms=timestamp_ms,
        correlation_id="corr-1",
        result_id="res-1",
        request_id=request_id,
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE,
        status=status,
        idempotency_key="idempo",
        reason_codes=() if status == DashboardGovernedCommandStatus.COMPLETED else ("failed",),
    )
    paths_queue = resolve_dashboard_command_queue_paths(paths.dashboard_command_queue_root)
    write_json(paths_queue.results_dir / f"{timestamp_ms}_{request_id}.result.json", result.model_dump(mode="json"))
