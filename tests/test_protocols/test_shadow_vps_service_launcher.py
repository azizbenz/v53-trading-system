"""Tests for the autonomous VPS Shadow service launcher."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

from interface_contracts.binance_contracts import BinanceServerTime
from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    ProfileId,
    RuntimeMode,
    StrategyClassification,
)
from local_replay_runtime import (
    LocalLabExecutionTelemetry,
    build_local_lab_execution_review,
    build_local_lab_execution_runtime_projection,
    ReplayExecutionInput,
    ReplayRunManifest,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from protocols import (
    BinanceSpotLiveWebSocketAdapter,
    ShadowLiveWebSocketCaptureResult,
    ShadowLiveWebSocketConfig,
    capture_live_websocket_snapshot_batch,
    initialize_dashboard_command_queue,
    load_dashboard_command_acks,
    load_dashboard_command_results,
    write_dashboard_command_request,
)
from regime_classifier import RegimeLiteAssessment, RegimeLiteState
from risk_backbone import (
    InfoStressAssessment,
    InfoStressLevel,
    build_regime_lite_safing_recommendation,
)


def _load_service_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_shadow_vps_service.py"
    module_name = "test_run_shadow_vps_service"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_vps_service_tests", label)


def _read_runtime_evidence_bundle(service_dir: Path, session_date: str) -> dict:
    return json.loads(
        (
            service_dir
            / "runtime_evidence"
            / f"{session_date}.shadow_vps_runtime_evidence.json"
        ).read_text(encoding="utf-8")
    )


def _read_campaign_summary(service_dir: Path) -> dict:
    return json.loads(
        (service_dir / "shadow_vps_service.campaign_summary.json").read_text(
            encoding="utf-8"
        )
    )


def _read_execution_telemetry(service_dir: Path) -> dict:
    return json.loads(
        (
            service_dir / "shadow_vps_service_execution_telemetry.json"
        ).read_text(encoding="utf-8")
    )


def _write_daily_export(export_dir: Path, session_date: str, run_suffix: str) -> None:
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id=f"run-shadow-vps-{run_suffix}",
                strategy_id=f"strategy-shadow-vps-{run_suffix}",
                strategy_version="a.v3.1",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version=f"a.v3.1.r{run_suffix}",
                profile_scope=ProfileId.COMPLETE,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id=f"dataset-shadow-vps-{session_date}",
                timeframe_scope=f"{session_date}/{session_date}",
                feature_set_version="3.0.0",
                transform_set_version="3.0.0",
                formula_set_version="formula.v3",
                scoring_version="score.v3",
                regime_version="regime.v3",
                risk_policy_version="risk.v3",
                cost_model_version="cost.v3",
                performance_mode="research_fast_mode",
                artifact_schema_version="3.0.0",
                artifact_hash=f"artifact-shadow-vps-{run_suffix}",
                clock_id=f"clock-shadow-vps-{run_suffix}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=1024,
            ),
            total_opportunities=2,
            dtr_records=(
                build_dtr(
                    dtr_id=f"run-shadow-vps-{run_suffix}:dtr:1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.SELECTED,
                    expected_cost=0.0010,
                    realized_cost=0.0011,
                    gross_return=0.0020,
                    ce_expected=0.0006,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_000.0,
                ),
            ),
            feature_bridge_payload={
                "bridge": "ok",
                "dataset_id": f"dataset-shadow-vps-{session_date}",
                "feature_set_version": "3.0.0",
                "transform_set_version": "3.0.0",
                "pairs": ["BTCUSDT", "ETHUSDT"],
                "engines": ["engine_a", "engine_b"],
            },
            parity_diagnostics_payload={
                "parity_status": "ok",
                "dataset_id": f"dataset-shadow-vps-{session_date}",
                "decision_match_rate": 1.0,
            },
            review_notes=(f"vps service export {session_date}",),
        ),
    )


def _write_telegram_alert_config(path: Path, *, min_severity: str = "warning") -> None:
    path.write_text(
        json.dumps(
            {
                "bot_token": "bot-token",
                "chat_id": "123456",
                "message_prefix": "[V5.3]",
                "min_severity": min_severity,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_raw_dataset_input(raw_input_dir: Path, session_date: str) -> None:
    payload = [
        {
            "opportunity_id": f"raw-{session_date}-1",
            "timestamp_ms": 1_700_000_000_000,
            "pair": "BTCUSDT",
            "engine_id": "engine_a",
            "close_price": 43250.0,
            "raw_score": 0.91,
            "penalized_score": 0.88,
            "final_score": 0.86,
            "expected_edge_bps": 17.0,
            "spread_bps": 3.0,
            "slippage_bps": 4.0,
            "latency_penalty_bps": 1.0,
            "fill_ratio": 1.0,
            "target_decision_state": "executed",
            "production_decision_state": "executed",
            "production_final_score": 0.86,
            "production_expected_cost": 0.00086,
            "candidate_size": 1.0,
            "final_size": 1.0,
            "gross_return_bps": 21.0,
            "feature_values": {"spread_bps": 3.0},
        },
        {
            "opportunity_id": f"raw-{session_date}-2",
            "timestamp_ms": 1_700_000_060_000,
            "pair": "ETHUSDT",
            "engine_id": "engine_b",
            "close_price": 2280.0,
            "raw_score": 0.81,
            "penalized_score": 0.79,
            "final_score": 0.76,
            "expected_edge_bps": 7.0,
            "spread_bps": 5.0,
            "slippage_bps": 3.0,
            "latency_penalty_bps": 1.0,
            "fill_ratio": 0.0,
            "target_decision_state": "rejected_ranking",
            "production_decision_state": "rejected_ranking",
            "production_final_score": 0.76,
            "production_expected_cost": 0.00094,
            "ranking_position": 3,
            "gross_return_bps": -4.0,
            "primary_reason": "rank_cutoff",
            "feature_values": {"spread_bps": 5.0},
        },
    ]
    (raw_input_dir / "replay_dataset.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    (raw_input_dir / "shadow_input_config.json").write_text(
        json.dumps(
            {
                "strategy_id": "strategy-shadow-vps-native",
                "strategy_version": "a.v4.0",
                "lineage_version": "a.v4.0.r1",
                "strategy_classification": "a_variant",
                "performance_mode": "research_fast_mode",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_websocket_stream_input(websocket_input_dir: Path, session_date: str) -> None:
    websocket_input_dir.joinpath("websocket_stream.jsonl").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "BTCUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 43250.0,
                            "bid": 43249.5,
                            "ask": 43250.5,
                            "volume_24h": 125000.0,
                        },
                        "recv_time": 1700000000.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": f"btc-ws-{session_date}",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "penalized_score": 0.88,
                            "final_score": 0.86,
                            "expected_edge_bps": 17.0,
                            "target_decision_state": "executed",
                            "production_decision_state": "executed",
                            "production_final_score": 0.86,
                            "production_expected_cost": 0.00086,
                            "candidate_size": 1.0,
                            "final_size": 1.0,
                            "gross_return_bps": 21.0,
                            "feature_values": {"spread_bps": 3.0},
                        },
                    }
                ),
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "ETHUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 2280.0,
                            "bid": 2279.8,
                            "ask": 2280.2,
                            "volume_24h": 98000.0,
                        },
                        "recv_time": 1700000060.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": f"eth-ws-{session_date}",
                            "engine_id": "engine_b",
                            "raw_score": 0.81,
                            "penalized_score": 0.79,
                            "final_score": 0.76,
                            "expected_edge_bps": 7.0,
                            "ranking_position": 3,
                            "target_decision_state": "rejected_ranking",
                            "production_decision_state": "rejected_ranking",
                            "production_final_score": 0.76,
                            "production_expected_cost": 0.00094,
                            "primary_reason": "rank_cutoff",
                            "gross_return_bps": -4.0,
                            "feature_values": {"spread_bps": 5.0},
                        },
                    }
                ),
            )
        ),
        encoding="utf-8",
    )
    websocket_input_dir.joinpath("shadow_input_config.json").write_text(
        json.dumps(
            {
                "strategy_id": "strategy-shadow-vps-websocket",
                "strategy_version": "a.v4.1",
                "lineage_version": "a.v4.1.r1",
                "strategy_classification": "a_variant",
                "performance_mode": "research_fast_mode",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_live_websocket_config(
    config_path: Path,
    session_date: str,
    *,
    pairs: tuple[str, ...] = ("BTCUSDT",),
    user_data_stream_enabled: bool = False,
    time_sync_probe_enabled: bool = False,
    execution_runtime_bootstrap_enabled: bool = False,
    execution_runtime_gatekeeper_audit_path_ref: str = "",
    execution_runtime_projection_path_ref: str = "",
    regime_lite_assessment_path_ref: str = "",
    regime_lite_safing_recommendation_path_ref: str = "",
    info_stress_assessment_path_ref: str = "",
    telegram_alert_config_path_ref: str = "",
    telegram_alert_key_path_ref: str = "",
) -> None:
    config_path.write_text(
        json.dumps(
            {
                "endpoint": "wss://stream.binance.com:9443/ws",
                "pairs": list(pairs),
                "stream_types": ["trade", "ticker"],
                "capture_frame_limit": 2,
                "idle_poll_limit": 3,
                "capture_timeout_s": 5.0,
                "time_sync_probe_enabled": time_sync_probe_enabled,
                "time_sync_sample_count": 3,
                "execution_runtime_bootstrap_enabled": (
                    execution_runtime_bootstrap_enabled
                ),
                "execution_runtime_gatekeeper_audit_path_ref": (
                    execution_runtime_gatekeeper_audit_path_ref
                ),
                "execution_runtime_projection_path_ref": (
                    execution_runtime_projection_path_ref
                ),
                "regime_lite_assessment_path_ref": regime_lite_assessment_path_ref,
                "regime_lite_safing_recommendation_path_ref": (
                    regime_lite_safing_recommendation_path_ref
                ),
                "info_stress_assessment_path_ref": info_stress_assessment_path_ref,
                "telegram_alert_config_path_ref": telegram_alert_config_path_ref,
                "telegram_alert_key_path_ref": telegram_alert_key_path_ref,
                "user_data_stream_enabled": user_data_stream_enabled,
                "user_data_api_key_env_var": "BINANCE_API_KEY",
                "user_data_api_secret_env_var": "BINANCE_API_SECRET",
                "session_date_override": session_date,
                "route_hints_by_pair": {
                    "BTCUSDT": {
                        "route_id": f"btc-live-{session_date}",
                        "engine_id": "engine_a",
                        "raw_score": 0.91,
                        "penalized_score": 0.88,
                        "final_score": 0.86,
                        "expected_edge_bps": 17.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.86,
                        "production_expected_cost": 0.00086,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 21.0,
                        "feature_values": {"spread_bps": 3.0},
                    },
                    "ETHUSDT": {
                        "route_id": f"eth-live-{session_date}",
                        "engine_id": "engine_b",
                        "raw_score": 0.81,
                        "penalized_score": 0.79,
                        "final_score": 0.76,
                        "expected_edge_bps": 7.0,
                        "target_decision_state": "rejected_ranking",
                        "production_decision_state": "rejected_ranking",
                        "production_final_score": 0.76,
                        "production_expected_cost": 0.00094,
                        "ranking_position": 3,
                        "gross_return_bps": -4.0,
                        "primary_reason": "rank_cutoff",
                        "feature_values": {"spread_bps": 5.0},
                    }
                },
                "config": {
                    "strategy_id": "strategy-shadow-vps-live",
                    "strategy_version": "a.v4.2",
                    "lineage_version": "a.v4.2.r1",
                    "strategy_classification": "a_variant",
                    "performance_mode": "research_fast_mode",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_time_sync_offsets(path: Path, offsets_ms: list[float]) -> None:
    path.write_text(
        json.dumps({"time_sync_offsets_ms": offsets_ms}, indent=2),
        encoding="utf-8",
    )


def _write_live_capture_result(
    live_capture_dir: Path,
    *,
    session_date: str,
    accepted_message_count: int,
    time_sync_offsets_path: Path | None = None,
    user_data_authenticated: bool = False,
) -> None:
    live_capture_dir.mkdir(parents=True, exist_ok=True)
    snapshot_batch_path = live_capture_dir / "live_websocket_snapshot_batch.json"
    snapshot_batch_path.write_text(
        json.dumps({"events": []}, indent=2),
        encoding="utf-8",
    )
    summary = ShadowLiveWebSocketCaptureResult(
        session_date=session_date,
        live_capture_dir_ref=str(live_capture_dir.resolve()),
        snapshot_batch_path_ref=str(snapshot_batch_path.resolve()),
        summary_path_ref=str(
            (live_capture_dir / "live_websocket_capture_summary.json").resolve()
        ),
        emitted_message_count=accepted_message_count,
        accepted_message_count=accepted_message_count,
        ignored_message_count=0,
        rejected_message_count=0,
        pair_scope=("BTCUSDT",),
        event_types=("trade", "ticker"),
        time_sync_offsets_path_ref=(
            str(time_sync_offsets_path.resolve())
            if time_sync_offsets_path is not None
            else ""
        ),
        time_sync_sample_count=3 if time_sync_offsets_path is not None else 0,
        time_sync_probe_error="",
        user_data_summary_path_ref="",
        user_data_events_path_ref="",
        user_data_authenticated=user_data_authenticated,
        user_data_subscription_id=None,
        user_data_event_count=0,
        user_data_event_types=(),
    )
    (live_capture_dir / "live_websocket_capture_summary.json").write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _write_validated_binance_credential_state(service_dir: Path) -> None:
    service_dir.mkdir(parents=True, exist_ok=False)
    (service_dir / "shadow_vps_service.state.json").write_text(
        json.dumps(
            {
                "loop_count": 1,
                "binance_credential_inventory": [
                    {
                        "profile": {
                            "profile_id": "binance-testnet-001",
                            "venue": "binance_spot",
                            "environment": "testnet",
                            "secret_kind": "binance_spot_credentials",
                            "secret_hash": "b" * 64,
                            "sealed_ref": "secrets/binance-testnet-001.sealed.json",
                            "backend": "dpapi",
                        },
                        "active": True,
                        "review_state": "approved",
                        "validation_status": "validated",
                        "last_auth_check_ms": 1_700_000_000_000,
                        "last_failure_reason_codes": [],
                        "source_ref": "secrets/binance-testnet-001.sealed.json",
                        "lineage_version": "credentials.v1",
                        "created_at_ms": 1_700_000_000_000,
                    }
                ],
                "active_binance_credential_profile_id": "binance-testnet-001",
                "active_binance_credential_environment": "testnet",
                "binance_credential_validation_status": "validated",
                "binance_credential_last_auth_check_ms": 1_700_000_000_000,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_execution_runtime_projection(path: Path) -> None:
    projection = build_local_lab_execution_runtime_projection(
        build_local_lab_execution_review(
            correlation_id="corr-shadow-vps",
            export_dir="E:/lab/export",
            run_id="run-shadow-vps",
            telemetry=LocalLabExecutionTelemetry(
                correlation_id="corr-shadow-vps",
                export_dir="E:/lab/export",
                run_id="run-shadow-vps",
                quota_call_counts=(45, 48, 42, 46),
                quota_probe_durations_s=(60.0, 60.0, 60.0, 60.0),
                quota_limit_calls_per_minute_values=(100, 120),
                quota_calls_per_minute_observed=(45.0, 48.0, 42.0, 46.0),
                quota_observation_days=31.0,
                spread_bps=(6.0, 8.0, 9.0, 12.0),
                spread_observation_days=31.0,
                slippage_bps=(2.0, 2.8, 3.4, 4.0),
                slippage_observation_days=31.0,
                final_sizes=(1.0, 4.0, 9.0, 16.0),
            ),
        )
    )
    path.write_text(
        projection.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _write_regime_lite_assessment(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(RegimeLiteState.STRESSED, RegimeLiteState.EXTREME),
        reason_codes=("RG_EXTREME_BTC_DROP_1H",),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def _write_regime_lite_safing_recommendation(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(RegimeLiteState.STRESSED, RegimeLiteState.EXTREME),
        reason_codes=("RG_EXTREME_BTC_DROP_1H",),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    recommendation = build_regime_lite_safing_recommendation(
        assessment,
        source_runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
    )
    path.write_text(recommendation.model_dump_json(indent=2), encoding="utf-8")


def _write_info_stress_assessment(path: Path) -> None:
    assessment = InfoStressAssessment(
        pair="BTCUSDT",
        level=InfoStressLevel.EXTREME,
        alert_count=3,
        reason_codes=(
            "INFO_STRESS_SPREAD_EXPLOSION",
            "INFO_STRESS_DEPTH_RATIO_COLLAPSE",
            "INFO_STRESS_CANCELLATION_SPIKE",
        ),
        entries_blocked=True,
        entries_blocked_until_ts=1_700_086_400,
        detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def test_shadow_vps_service_advances_to_next_dated_export_when_shadow_day_is_recorded():
    service = _load_service_module()
    output_dir = _scratch_dir("multi_day")

    try:
        service_dir = output_dir / "service"
        node_textfile_dir = output_dir / "node_textfile"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        execution_runtime_projection_path = (
            output_dir / "local_lab_execution_runtime_projection.json"
        )
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        (exports_root / "2026-04-02").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_daily_export(exports_root / "2026-04-02", "2026-04-02", "2")
        _write_execution_runtime_projection(execution_runtime_projection_path)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--node-exporter-textfile-dir",
                str(node_textfile_dir),
                "--scrape-host",
                "10.0.0.5",
                "--vps-id",
                "vps-paris-01",
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--execution-runtime-projection-path",
                str(execution_runtime_projection_path),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        shadow_session_summary = json.loads(
            (shadow_output_dir / "local_replay_shadow.shadow_session_summary.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        observability_export = json.loads(
            (
                service_dir / "shadow_vps_service_observability_export.json"
            ).read_text(encoding="utf-8")
        )
        recent_events_summary = json.loads(
            (
                service_dir / "shadow_vps_service_recent_events.json"
            ).read_text(encoding="utf-8")
        )
        scrape_manifest = json.loads(
            (
                service_dir / "shadow_vps_service_scrape_manifest.json"
            ).read_text(encoding="utf-8")
        )
        prometheus_file_sd = json.loads(
            (
                service_dir / "shadow_vps_service_prometheus_file_sd.json"
            ).read_text(encoding="utf-8")
        )
        observability_text = (
            service_dir / "shadow_vps_service_observability.prom"
        ).read_text(encoding="utf-8")
        node_exporter_text = (
            node_textfile_dir / "v53_shadow_vps_service.prom"
        ).read_text(encoding="utf-8")

        assert state["service_status"] == "stopped"
        assert state["loop_count"] == 2
        assert state["success_count"] == 2
        assert state["failure_count"] == 0
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_campaign_summary_ref"].endswith(
            "shadow_vps_service.campaign_summary.json"
        )
        assert state["last_local_replay_evidence_ref"].endswith(
            "local_replay_shadow.local_replay_evidence.json"
        )
        assert state["last_shadow_runtime_evidence_ref"].endswith(
            "local_replay_shadow.shadow_runtime_evidence.json"
        )
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert state["last_execution_runtime_projection_ref"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert state["last_execution_runtime_projection_source"] == "cli"
        assert shadow_session_summary["consecutive_days"] == 2
        assert runtime_bundle["acquisition_mode"] == "dated_export"
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert runtime_bundle["accepted"] is False
        assert runtime_bundle["consecutive_days"] == 2
        assert runtime_bundle["execution_runtime_projection_ref"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert runtime_bundle["execution_runtime_projection_source"] == "cli"
        assert runtime_bundle["execution_runtime_projection_status"] == "ready"
        assert runtime_bundle["execution_runtime_projection_ready"] is True
        assert runtime_bundle["execution_runtime_projection_ready_consumer_count"] == 3
        assert runtime_bundle["execution_runtime_projection_bridge_status"] == "healthy"
        assert runtime_bundle["execution_runtime_projection_bridge_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_rate_limit_model_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_spread_guard_model_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_slippage_model_loaded"] is True
        assert runtime_bundle["regime_lite_governance_status"] == "not_configured"
        assert runtime_bundle["regime_lite_safing_severity"] == "not_configured"
        assert campaign_summary["service_status"] == "stopped"
        assert campaign_summary["success_count"] == 2
        assert campaign_summary["acquisition_mode"] == "dated_export"
        assert campaign_summary["consecutive_days"] == 2
        assert campaign_summary["remaining_days"] == 28
        assert campaign_summary["promotion_gate_passed"] is False
        assert campaign_summary["execution_runtime_projection_ref"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert campaign_summary["execution_runtime_projection_source"] == "cli"
        assert campaign_summary["execution_runtime_projection_status"] == "ready"
        assert campaign_summary["execution_runtime_projection_ready"] is True
        assert campaign_summary["execution_runtime_projection_bridge_status"] == "healthy"
        assert campaign_summary["execution_runtime_projection_bridge_loaded"] is True
        assert campaign_summary["regime_lite_governance_status"] == "not_configured"
        assert campaign_summary["regime_lite_safing_severity"] == "not_configured"
        assert monitoring_payload["service_status"] == "stopped"
        assert monitoring_payload["state_path"].endswith(
            "shadow_vps_service.state.json"
        )
        assert monitoring_payload["events_path"].endswith(
            "shadow_vps_service.events.jsonl"
        )
        assert monitoring_payload["recent_events_summary_ref"].endswith(
            "shadow_vps_service_recent_events.json"
        )
        assert monitoring_payload["execution_runtime_projection_ref"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert monitoring_payload["execution_runtime_projection_source"] == "cli"
        assert monitoring_payload["execution_runtime_projection_status"] == "ready"
        assert monitoring_payload["execution_runtime_projection_ready"] is True
        assert monitoring_payload["execution_runtime_projection_bridge_status"] == "healthy"
        assert monitoring_payload["execution_runtime_projection_bridge_loaded"] is True
        assert monitoring_payload["execution_runtime_projection_rate_limit_model_loaded"] is True
        assert monitoring_payload["execution_runtime_projection_spread_guard_model_loaded"] is True
        assert monitoring_payload["execution_runtime_projection_slippage_model_loaded"] is True
        assert monitoring_payload["regime_lite_governance_status"] == "not_configured"
        assert monitoring_payload["regime_lite_safing_severity"] == "not_configured"
        assert monitoring_payload["node_exporter_textfile_ref"].endswith(
            "v53_shadow_vps_service.prom"
        )
        assert monitoring_payload["scrape_manifest_ref"].endswith(
            "shadow_vps_service_scrape_manifest.json"
        )
        assert monitoring_payload["prometheus_file_sd_ref"].endswith(
            "shadow_vps_service_prometheus_file_sd.json"
        )
        assert monitoring_payload["disk"]["sampling_mode"] == "shutil_disk_usage"
        assert observability_export["correlation_id"] == "shadow-vps-service"
        assert recent_events_summary["scan_mode"] == "tail_recent"
        assert recent_events_summary["returned_event_count"] >= 1
        assert scrape_manifest["node_exporter_target"] == "10.0.0.5:9100"
        assert scrape_manifest["vps_id"] == "vps-paris-01"
        assert prometheus_file_sd[0]["targets"] == ["10.0.0.5:9100"]
        assert prometheus_file_sd[0]["labels"]["vps_id"] == "vps-paris-01"
        assert observability_text.startswith(
            "# V5.3 Shadow VPS service observability export"
        )
        assert node_exporter_text.startswith(
            "# V5.3 Shadow VPS service observability export"
        )
        assert any(
            sample["name"] == "v53_shadow_vps_process_cpu_pct"
            for sample in observability_export["samples"]
        )
        assert any(
            sample["name"] == "v53_shadow_vps_disk_used_pct"
            for sample in observability_export["samples"]
        )
        assert any(
            sample["name"] == "v53_shadow_vps_execution_runtime_projection_ready"
            for sample in observability_export["samples"]
        )
        assert any(
            sample["name"]
            == "v53_shadow_vps_execution_runtime_projection_bridge_loaded"
            for sample in observability_export["samples"]
        )
        assert any(
            sample["name"] == "v53_shadow_vps_regime_lite_safing_status"
            for sample in observability_export["samples"]
        )

        event_types = [event["event_type"] for event in events]
        assert event_types[0] == "service_started"
        assert event_types.count("runtime_evidence_bundle_written") == 2
        assert event_types.count("shadow_day_completed") == 2
        assert event_types[-1] == "service_stopped"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_resumes_and_advances_after_recorded_day():
    service = _load_service_module()
    output_dir = _scratch_dir("resume")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")

        first_exit = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )
        (exports_root / "2026-04-02").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-02", "2026-04-02", "2")
        second_exit = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert first_exit == 0
        assert second_exit == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert state["resumed"] is True
        assert state["loop_count"] == 2
        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert any(
            event["event_type"] == "service_started"
            and event["message"] == "Shadow VPS service resumed"
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_accepts_regime_lite_inputs():
    service = _load_service_module()
    output_dir = _scratch_dir("regime_lite_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        assessment_path = output_dir / "regime_lite_assessment.json"
        recommendation_path = output_dir / "regime_lite_safing_recommendation.json"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_regime_lite_assessment(assessment_path)
        _write_regime_lite_safing_recommendation(recommendation_path)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--regime-lite-assessment-path",
                str(assessment_path),
                "--regime-lite-safing-recommendation-path",
                str(recommendation_path),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-01")
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert state["last_regime_lite_assessment_ref"] == str(assessment_path.resolve())
        assert state["last_regime_lite_assessment_source"] == "cli"
        assert state["last_regime_lite_safing_recommendation_ref"] == str(
            recommendation_path.resolve()
        )
        assert state["last_regime_lite_safing_recommendation_source"] == "cli"
        assert runtime_bundle["regime_lite_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert runtime_bundle["regime_lite_assessment_source"] == "cli"
        assert runtime_bundle["regime_lite_safing_recommendation_ref"] == str(
            recommendation_path.resolve()
        )
        assert runtime_bundle["regime_lite_safing_recommendation_source"] == "cli"
        assert runtime_bundle["regime_lite_governance_status"] == "ready"
        assert runtime_bundle["regime_lite_state"] == "extreme"
        assert runtime_bundle["regime_lite_safing_severity"] == "halt_recommended"
        assert runtime_bundle["regime_lite_safing_should_exit_all"] is True
        assert campaign_summary["regime_lite_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert campaign_summary["regime_lite_assessment_source"] == "cli"
        assert campaign_summary["regime_lite_safing_recommendation_ref"] == str(
            recommendation_path.resolve()
        )
        assert campaign_summary["regime_lite_safing_recommendation_source"] == "cli"
        assert campaign_summary["regime_lite_governance_status"] == "ready"
        assert campaign_summary["regime_lite_state"] == "extreme"
        assert campaign_summary["regime_lite_safing_severity"] == "halt_recommended"
        assert campaign_summary["regime_lite_safing_should_exit_all"] is True
        assert monitoring_payload["regime_lite_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert monitoring_payload["regime_lite_assessment_source"] == "cli"
        assert monitoring_payload["regime_lite_safing_recommendation_ref"] == str(
            recommendation_path.resolve()
        )
        assert monitoring_payload["regime_lite_safing_recommendation_source"] == "cli"
        assert monitoring_payload["regime_lite_governance_status"] == "ready"
        assert monitoring_payload["regime_lite_state"] == "extreme"
        assert monitoring_payload["regime_lite_safing_severity"] == "halt_recommended"
        assert monitoring_payload["regime_lite_safing_should_exit_all"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_accepts_info_stress_input():
    service = _load_service_module()
    output_dir = _scratch_dir("info_stress_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        assessment_path = output_dir / "info_stress_assessment.json"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_info_stress_assessment(assessment_path)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--info-stress-assessment-path",
                str(assessment_path),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-01")
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert state["last_info_stress_assessment_ref"] == str(assessment_path.resolve())
        assert state["last_info_stress_assessment_source"] == "cli"
        assert runtime_bundle["info_stress_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert runtime_bundle["info_stress_assessment_source"] == "cli"
        assert runtime_bundle["info_stress_governance_status"] == "assessment_only"
        assert runtime_bundle["info_stress_level"] == "extreme"
        assert runtime_bundle["info_stress_alert_count"] == 3
        assert runtime_bundle["info_stress_entries_blocked"] is True
        assert campaign_summary["info_stress_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert campaign_summary["info_stress_assessment_source"] == "cli"
        assert campaign_summary["info_stress_governance_status"] == "assessment_only"
        assert campaign_summary["info_stress_level"] == "extreme"
        assert campaign_summary["info_stress_entries_blocked"] is True
        assert monitoring_payload["info_stress_assessment_ref"] == str(
            assessment_path.resolve()
        )
        assert monitoring_payload["info_stress_assessment_source"] == "cli"
        assert monitoring_payload["info_stress_governance_status"] == "assessment_only"
        assert monitoring_payload["info_stress_level"] == "extreme"
        assert monitoring_payload["info_stress_entries_blocked"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_sends_telegram_alerts_when_configured():
    service = _load_service_module()
    output_dir = _scratch_dir("telegram_alerting_success")

    captured_payloads: list[dict[str, object]] = []

    def _fake_post(url: str, payload: dict[str, object], timeout_s: float) -> tuple[int, str]:
        captured_payloads.append(
            {
                "url": url,
                "payload": dict(payload),
                "timeout_s": timeout_s,
            }
        )
        return 200, '{"ok": true}'

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        telegram_config_path = output_dir / "telegram_alert_config.json"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_telegram_alert_config(telegram_config_path, min_severity="info")

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            exports_root=exports_root,
            telegram_alert_config_path=telegram_config_path,
            telegram_post_func=_fake_post,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        telegram_events = [
            event for event in events if event["event_type"] == "telegram_alert_sent"
        ]

        assert len(captured_payloads) == 3
        assert len(telegram_events) == 3
        assert state["last_telegram_alert_delivery_status"] == "sent"
        assert state["last_telegram_alert_delivery_event_type"] == "service_stopped"
        assert state["last_telegram_alert_delivery_error"] == ""
        assert campaign_summary["telegram_alert_delivery_status"] == "sent"
        assert campaign_summary["telegram_alert_delivery_event_type"] == "service_stopped"
        assert monitoring_payload["telegram_alert_delivery_status"] == "sent"
        assert (
            monitoring_payload["telegram_alert_delivery_event_type"] == "service_stopped"
        )
        assert captured_payloads[0]["url"] == "https://api.telegram.org/botbot-token/sendMessage"
        assert captured_payloads[0]["payload"]["chat_id"] == "123456"
        assert "[INFO][INFRA]" in str(captured_payloads[0]["payload"]["text"])
        assert any("service_started" in event["message"] for event in telegram_events)
        assert any("shadow_day_completed" in event["message"] for event in telegram_events)
        assert any("service_stopped" in event["message"] for event in telegram_events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_telegram_failures_do_not_crash_service():
    service = _load_service_module()
    output_dir = _scratch_dir("telegram_alerting_failure")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        telegram_config_path = output_dir / "telegram_alert_config.json"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_telegram_alert_config(telegram_config_path, min_severity="info")

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            exports_root=exports_root,
            telegram_alert_config_path=telegram_config_path,
            telegram_post_func=lambda *_args: (500, '{"ok": false}'),
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        assert any(event["event_type"] == "telegram_alert_failed" for event in events)
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        assert state["last_error"] == ""
        assert state["last_telegram_alert_delivery_status"] == "failed"
        assert state["last_telegram_alert_delivery_event_type"] == "service_stopped"
        assert state["last_telegram_alert_delivery_error"] == "http_500"
        assert campaign_summary["telegram_alert_delivery_status"] == "failed"
        assert monitoring_payload["telegram_alert_delivery_status"] == "failed"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_loads_telegram_alert_config_from_live_websocket_config(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("telegram_alerting_live_websocket_config")

    captured_payloads: list[dict[str, object]] = []

    def _fake_post(
        url: str,
        payload: dict[str, object],
        timeout_s: float,
    ) -> tuple[int, str]:
        captured_payloads.append(
            {
                "url": url,
                "payload": dict(payload),
                "timeout_s": timeout_s,
            }
        )
        return 200, '{"ok": true}'

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        config_telegram_path = output_dir / "config_telegram_alert_config.json"
        _write_telegram_alert_config(config_telegram_path, min_severity="info")
        _write_live_websocket_config(
            live_config_path,
            "2026-04-01",
            telegram_alert_config_path_ref=config_telegram_path.name,
        )

        def _fake_auto_export_from_live_websocket(
            config: ShadowLiveWebSocketConfig,
            *,
            live_captures_root: Path,
            auto_exports_root: Path,
        ) -> tuple[Path, Path]:
            live_capture_dir = live_captures_root / "2026-04-01"
            live_capture_dir.mkdir(parents=True, exist_ok=False)
            auto_export_dir = auto_exports_root / "2026-04-01"
            auto_export_dir.mkdir(parents=True, exist_ok=False)
            _write_daily_export(auto_export_dir, "2026-04-01", "1")
            return live_capture_dir, auto_export_dir

        monkeypatch.setattr(
            service,
            "_ensure_auto_export_from_live_websocket",
            _fake_auto_export_from_live_websocket,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            telegram_post_func=_fake_post,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert len(captured_payloads) == 3
        assert state["last_telegram_alert_config_ref"] == str(
            config_telegram_path.resolve()
        )
        assert state["last_telegram_alert_config_source"] == "live_websocket_config"
        assert state["last_telegram_alert_key_ref"] == ""
        assert state["last_telegram_alert_key_source"] == "not_configured"
        assert campaign_summary["telegram_alert_config_ref"] == str(
            config_telegram_path.resolve()
        )
        assert (
            campaign_summary["telegram_alert_config_source"]
            == "live_websocket_config"
        )
        assert monitoring_payload["telegram_alert_config_ref"] == str(
            config_telegram_path.resolve()
        )
        assert (
            monitoring_payload["telegram_alert_config_source"]
            == "live_websocket_config"
        )
        assert monitoring_payload["telegram_alert_key_ref"] == ""
        assert monitoring_payload["telegram_alert_key_source"] == "not_configured"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_cli_telegram_alert_config_overrides_live_websocket_config(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("telegram_alerting_cli_override")

    captured_payloads: list[dict[str, object]] = []

    def _fake_post(
        url: str,
        payload: dict[str, object],
        timeout_s: float,
    ) -> tuple[int, str]:
        captured_payloads.append(
            {
                "url": url,
                "payload": dict(payload),
                "timeout_s": timeout_s,
            }
        )
        return 200, '{"ok": true}'

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        config_telegram_path = output_dir / "config_telegram_alert_config.json"
        cli_telegram_path = output_dir / "cli_telegram_alert_config.json"
        _write_telegram_alert_config(config_telegram_path, min_severity="info")
        _write_telegram_alert_config(cli_telegram_path, min_severity="info")
        _write_live_websocket_config(
            live_config_path,
            "2026-04-01",
            telegram_alert_config_path_ref=config_telegram_path.name,
        )

        def _fake_auto_export_from_live_websocket(
            config: ShadowLiveWebSocketConfig,
            *,
            live_captures_root: Path,
            auto_exports_root: Path,
        ) -> tuple[Path, Path]:
            live_capture_dir = live_captures_root / "2026-04-01"
            live_capture_dir.mkdir(parents=True, exist_ok=False)
            auto_export_dir = auto_exports_root / "2026-04-01"
            auto_export_dir.mkdir(parents=True, exist_ok=False)
            _write_daily_export(auto_export_dir, "2026-04-01", "1")
            return live_capture_dir, auto_export_dir

        monkeypatch.setattr(
            service,
            "_ensure_auto_export_from_live_websocket",
            _fake_auto_export_from_live_websocket,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            telegram_alert_config_path=cli_telegram_path,
            telegram_post_func=_fake_post,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert len(captured_payloads) == 3
        assert state["last_telegram_alert_config_ref"] == str(cli_telegram_path.resolve())
        assert state["last_telegram_alert_config_source"] == "cli"
        assert campaign_summary["telegram_alert_config_ref"] == str(
            cli_telegram_path.resolve()
        )
        assert campaign_summary["telegram_alert_config_source"] == "cli"
        assert monitoring_payload["telegram_alert_config_ref"] == str(
            cli_telegram_path.resolve()
        )
        assert monitoring_payload["telegram_alert_config_source"] == "cli"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_writes_execution_runtime_bootstrap_summary_from_live_config(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("execution_runtime_bootstrap_live_config")

    captured_kwargs: dict[str, object] = {}

    def _fake_bootstrap_bundle(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            reconciliation_boot_result=SimpleNamespace(
                executed=True,
                trading_blocked=False,
                circuit_breaker_tripped=False,
                detail="boot reconciliation aligned local and remote state",
                recovery_action="none",
                divergence_count=0,
            ),
            remote_state_snapshot=SimpleNamespace(
                orders={"ord-1": "NEW"},
                positions={"BTC": 0.25},
            ),
        )

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        gatekeeper_dir = output_dir / "config_gatekeeper"
        gatekeeper_dir.mkdir(parents=True, exist_ok=False)
        gatekeeper_audit_path = gatekeeper_dir / "audit.jsonl"
        _write_live_websocket_config(
            live_config_path,
            "2026-04-01",
            execution_runtime_bootstrap_enabled=True,
            execution_runtime_gatekeeper_audit_path_ref=str(
                gatekeeper_audit_path.relative_to(output_dir)
            ),
        )

        def _fake_auto_export_from_live_websocket(
            config: ShadowLiveWebSocketConfig,
            *,
            live_captures_root: Path,
            auto_exports_root: Path,
        ) -> tuple[Path, Path]:
            live_capture_dir = live_captures_root / "2026-04-01"
            live_capture_dir.mkdir(parents=True, exist_ok=False)
            auto_export_dir = auto_exports_root / "2026-04-01"
            auto_export_dir.mkdir(parents=True, exist_ok=False)
            _write_daily_export(auto_export_dir, "2026-04-01", "1")
            return live_capture_dir, auto_export_dir

        monkeypatch.setattr(
            service,
            "_ensure_auto_export_from_live_websocket",
            _fake_auto_export_from_live_websocket,
        )
        monkeypatch.setattr(
            service,
            "build_binance_execution_runtime_bootstrap_bundle",
            _fake_bootstrap_bundle,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-01")
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        bootstrap_summary = json.loads(
            (service_dir / "execution_runtime_bootstrap.summary.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert captured_kwargs == {}
        assert bootstrap_summary["status"] == "failed"
        assert bootstrap_summary["source"] == "live_websocket_config"
        assert bootstrap_summary["gatekeeper_audit_ref"] == str(
            gatekeeper_audit_path.resolve()
        )
        assert (
            bootstrap_summary["gatekeeper_audit_source"] == "live_websocket_config"
        )
        assert "sealed Binance credential profile" in bootstrap_summary["error"]
        assert bootstrap_summary["reconciliation_boot_executed"] is False
        assert state["last_execution_runtime_bootstrap_ref"].endswith(
            "execution_runtime_bootstrap.summary.json"
        )
        assert state["last_execution_runtime_bootstrap_status"] == "failed"
        assert (
            state["last_execution_runtime_bootstrap_source"]
            == "live_websocket_config"
        )
        assert state["last_execution_runtime_gatekeeper_audit_ref"] == str(
            gatekeeper_audit_path.resolve()
        )
        assert (
            state["last_execution_runtime_gatekeeper_audit_source"]
            == "live_websocket_config"
        )
        assert campaign_summary["execution_runtime_bootstrap_status"] == "failed"
        assert (
            campaign_summary["execution_runtime_bootstrap_source"]
            == "live_websocket_config"
        )
        assert campaign_summary["execution_runtime_gatekeeper_audit_ref"] == str(
            gatekeeper_audit_path.resolve()
        )
        assert runtime_bundle["execution_runtime_bootstrap_status"] == "failed"
        assert (
            runtime_bundle["execution_runtime_bootstrap_source"]
            == "live_websocket_config"
        )
        assert runtime_bundle["execution_runtime_gatekeeper_audit_ref"] == str(
            gatekeeper_audit_path.resolve()
        )
        assert monitoring_payload["execution_runtime_bootstrap_status"] == "failed"
        assert (
            monitoring_payload["execution_runtime_bootstrap_source"]
            == "live_websocket_config"
        )
        assert monitoring_payload["execution_runtime_gatekeeper_audit_ref"] == str(
            gatekeeper_audit_path.resolve()
        )
        assert any(
            event["event_type"] == "execution_runtime_bootstrap_failed"
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_cli_execution_runtime_gatekeeper_audit_path_overrides_live_config(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("execution_runtime_bootstrap_cli_audit_override")

    captured_kwargs: dict[str, object] = {}

    def _fake_bootstrap_bundle(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            reconciliation_boot_result=SimpleNamespace(
                executed=True,
                trading_blocked=False,
                circuit_breaker_tripped=False,
                detail="boot reconciliation aligned local and remote state",
                recovery_action="none",
                divergence_count=0,
            )
        )

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        config_gatekeeper_dir = output_dir / "config_gatekeeper"
        config_gatekeeper_dir.mkdir(parents=True, exist_ok=False)
        config_gatekeeper_audit_path = config_gatekeeper_dir / "audit.jsonl"
        cli_gatekeeper_dir = output_dir / "cli_gatekeeper"
        cli_gatekeeper_dir.mkdir(parents=True, exist_ok=False)
        cli_gatekeeper_audit_path = cli_gatekeeper_dir / "audit.jsonl"
        _write_live_websocket_config(
            live_config_path,
            "2026-04-01",
            execution_runtime_bootstrap_enabled=True,
            execution_runtime_gatekeeper_audit_path_ref=str(
                config_gatekeeper_audit_path.relative_to(output_dir)
            ),
        )

        def _fake_auto_export_from_live_websocket(
            config: ShadowLiveWebSocketConfig,
            *,
            live_captures_root: Path,
            auto_exports_root: Path,
        ) -> tuple[Path, Path]:
            live_capture_dir = live_captures_root / "2026-04-01"
            live_capture_dir.mkdir(parents=True, exist_ok=False)
            auto_export_dir = auto_exports_root / "2026-04-01"
            auto_export_dir.mkdir(parents=True, exist_ok=False)
            _write_daily_export(auto_export_dir, "2026-04-01", "1")
            return live_capture_dir, auto_export_dir

        monkeypatch.setattr(
            service,
            "_ensure_auto_export_from_live_websocket",
            _fake_auto_export_from_live_websocket,
        )
        monkeypatch.setattr(
            service,
            "build_binance_execution_runtime_bootstrap_bundle",
            _fake_bootstrap_bundle,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            execution_runtime_gatekeeper_audit_path=cli_gatekeeper_audit_path,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        campaign_summary = _read_campaign_summary(service_dir)
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-01")
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert captured_kwargs == {}
        assert state["last_execution_runtime_bootstrap_status"] == "failed"
        assert (
            state["last_execution_runtime_gatekeeper_audit_ref"]
            == str(cli_gatekeeper_audit_path.resolve())
        )
        assert state["last_execution_runtime_gatekeeper_audit_source"] == "cli"
        assert (
            campaign_summary["execution_runtime_gatekeeper_audit_ref"]
            == str(cli_gatekeeper_audit_path.resolve())
        )
        assert campaign_summary["execution_runtime_gatekeeper_audit_source"] == "cli"
        assert (
            runtime_bundle["execution_runtime_gatekeeper_audit_ref"]
            == str(cli_gatekeeper_audit_path.resolve())
        )
        assert runtime_bundle["execution_runtime_gatekeeper_audit_source"] == "cli"
        assert monitoring_payload["execution_runtime_gatekeeper_audit_ref"] == str(
            cli_gatekeeper_audit_path.resolve()
        )
        assert monitoring_payload["execution_runtime_gatekeeper_audit_source"] == "cli"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_startup_writes_blocked_recovery_report_when_market_capture_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    import shadow_vps_service_recovery_support as recovery_support

    output_dir = _scratch_dir("startup_recovery_blocked")

    def _fake_bootstrap_bundle(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            reconciliation_boot_result=SimpleNamespace(
                executed=True,
                trading_blocked=False,
                circuit_breaker_tripped=False,
                detail="boot reconciliation aligned local and remote state",
                recovery_action="none",
                divergence_count=0,
            ),
            remote_state_snapshot=SimpleNamespace(
                orders={"ord-1": "NEW"},
                positions={"BTC": 0.25},
            ),
        )

    try:
        service_dir = output_dir / "service"
        live_config_path = output_dir / "live_websocket_config.json"
        time_sync_offsets_path = output_dir / "time_sync_offsets.json"
        _write_time_sync_offsets(time_sync_offsets_path, [4.0, -3.0, 2.0])
        _write_live_websocket_config(
            live_config_path,
            "2026-04-01",
            execution_runtime_bootstrap_enabled=True,
            time_sync_probe_enabled=True,
        )
        monkeypatch.setattr(
            service,
            "build_binance_execution_runtime_bootstrap_bundle",
            _fake_bootstrap_bundle,
        )
        monkeypatch.setattr(
            recovery_support,
            "resolve_time_sync_threshold_ms",
            lambda config: 500,
        )
        exit_code = service.run_shadow_vps_service(
            service_dir,
            live_websocket_config_path=live_config_path,
            execution_time_sync_offsets_path=time_sync_offsets_path,
            max_cycles=0,
            poll_interval_s=0.0,
        )

        assert exit_code == 0
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        recovery_report = json.loads(
            (service_dir / "vps_recovery_readiness.report.json").read_text(
                encoding="utf-8"
            )
        )
        warmup_summary = json.loads(
            (service_dir / "vps_warmup_run.summary.json").read_text(
                encoding="utf-8"
            )
        )
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        assert recovery_report["runtime_mode"] == "shadow"
        assert recovery_report["deployment_state"] == "shadow"
        assert recovery_report["eligible_to_trade"] is False
        assert any(
            check["check_id"] == "bootstrap_reconciliation"
            and check["status"] == "blocked"
            for check in recovery_report["checks"]
        )
        assert any(
            check["check_id"] == "remote_account_state"
            and check["status"] == "blocked"
            for check in recovery_report["checks"]
        )
        assert warmup_summary["final_state"] == "blocked"
        assert state["last_vps_recovery_status"] == "blocked"
        assert state["last_vps_warmup_final_state"] == "blocked"
        assert (
            monitoring_payload["vps_recovery_readiness_report_ref"].endswith(
                "vps_recovery_readiness.report.json"
            )
        )
        assert monitoring_payload["vps_recovery_status"] == "blocked"
        assert monitoring_payload["vps_warmup_final_state"] == "blocked"
        assert monitoring_payload["execution_runtime_bootstrap_status"] == "failed"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_startup_writes_eligible_recovery_report_from_persisted_live_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    import shadow_vps_service_recovery_support as recovery_support

    output_dir = _scratch_dir("startup_recovery_eligible")

    def _fake_bootstrap_bundle(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            reconciliation_boot_result=SimpleNamespace(
                executed=True,
                trading_blocked=False,
                circuit_breaker_tripped=False,
                detail="boot reconciliation aligned local and remote state",
                recovery_action="none",
                divergence_count=0,
            ),
            remote_state_snapshot=SimpleNamespace(
                orders={},
                positions={},
            ),
        )

    try:
        service_dir = output_dir / "service"
        live_capture_dir = output_dir / "live_captures" / "2026-04-02"
        live_config_path = output_dir / "live_websocket_config.json"
        time_sync_offsets_path = live_capture_dir / "live_time_sync_offsets.json"
        live_capture_dir.mkdir(parents=True, exist_ok=False)
        _write_time_sync_offsets(time_sync_offsets_path, [1.0, -1.0, 0.5])
        _write_live_capture_result(
            live_capture_dir,
            session_date="2026-04-02",
            accepted_message_count=2,
            time_sync_offsets_path=time_sync_offsets_path,
        )
        _write_validated_binance_credential_state(service_dir)
        state_path = service_dir / "shadow_vps_service.state.json"
        state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        state_payload.update(
            {
                "last_live_capture_dir_ref": str(live_capture_dir.resolve()),
                "last_live_capture_time_sync_offsets_ref": str(
                    time_sync_offsets_path.resolve()
                ),
            }
        )
        state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        _write_live_websocket_config(
            live_config_path,
            "2026-04-02",
            execution_runtime_bootstrap_enabled=True,
            time_sync_probe_enabled=True,
        )
        monkeypatch.setattr(
            service,
            "build_binance_execution_runtime_bootstrap_bundle",
            _fake_bootstrap_bundle,
        )
        monkeypatch.setattr(
            recovery_support,
            "resolve_time_sync_threshold_ms",
            lambda config: 500,
        )
        exit_code = service.run_shadow_vps_service(
            service_dir,
            live_websocket_config_path=live_config_path,
            max_cycles=0,
            poll_interval_s=0.0,
        )

        assert exit_code == 0
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        recovery_report = json.loads(
            (service_dir / "vps_recovery_readiness.report.json").read_text(
                encoding="utf-8"
            )
        )
        warmup_summary = json.loads(
            (service_dir / "vps_warmup_run.summary.json").read_text(
                encoding="utf-8"
            )
        )
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        assert recovery_report["eligible_to_trade"] is False
        assert any(
            check["check_id"] == "bootstrap_reconciliation"
            and check["status"] == "blocked"
            for check in recovery_report["checks"]
        )
        assert warmup_summary["final_state"] == "blocked"
        assert state["last_vps_recovery_status"] == "blocked"
        assert state["last_vps_warmup_final_state"] == "blocked"
        assert monitoring_payload["vps_recovery_status"] == "blocked"
        assert monitoring_payload["vps_warmup_final_state"] == "blocked"
        assert monitoring_payload["vps_recovery_eligible_to_trade"] is False
        assert monitoring_payload["vps_warmup_eligible_to_trade"] is False
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_demo_run_skips_execution_telemetry_without_degrading():
    service = _load_service_module()
    output_dir = _scratch_dir("demo_skip_execution_telemetry")

    try:
        session_date = datetime.now(tz=timezone.utc).date().isoformat()
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, session_date)
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert state["service_status"] == "stopped"
        assert state["success_count"] == 1
        assert state["failure_count"] == 0
        assert state["last_completed_session_date"] == session_date
        assert state["last_export_dir_ref"] == ""
        assert state["last_execution_telemetry_ref"] == ""
        assert state["last_execution_telemetry_status"] == "skipped"
        assert state["last_error"] == ""
        assert runtime_bundle["acquisition_mode"] == "demo"
        assert runtime_bundle["export_dir_ref"] == ""
        assert campaign_summary["service_status"] == "stopped"
        assert campaign_summary["acquisition_mode"] == "demo"
        assert monitoring_payload["execution_telemetry_ref"] == ""
        assert monitoring_payload["execution_telemetry_status"] == "skipped"
        assert any(
            event["event_type"] == "execution_telemetry_skipped"
            and event["session_date"] == session_date
            for event in events
        )
        assert not any(
            event["event_type"] == "execution_telemetry_written" for event in events
        )
        assert any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_advances_raw_input_days_when_shadow_day_is_recorded():
    service = _load_service_module()
    output_dir = _scratch_dir("raw_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        auto_exports_root = output_dir / "auto_exports"
        raw_inputs_root = output_dir / "raw_inputs_root"
        day_one_dir = raw_inputs_root / "2026-04-01"
        day_two_dir = raw_inputs_root / "2026-04-02"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        day_two_dir.mkdir(parents=True, exist_ok=False)
        _write_raw_dataset_input(day_one_dir, "2026-04-01")
        _write_raw_dataset_input(day_two_dir, "2026-04-02")

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--raw-inputs-root",
                str(raw_inputs_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")

        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_raw_input_dir_ref"].endswith("raw_inputs_root\\2026-04-02")
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-native"
        assert runtime_bundle["acquisition_mode"] == "raw_input_auto_export"
        assert runtime_bundle["raw_input_dir_ref"].endswith("raw_inputs_root\\2026-04-02")
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert any(
            event["event_type"] == "auto_export_completed"
            and event["session_date"] == "2026-04-01"
            for event in events
        )
        assert (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_advances_websocket_days_when_shadow_day_is_recorded():
    service = _load_service_module()
    output_dir = _scratch_dir("websocket_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        auto_snapshots_root = output_dir / "auto_snapshots"
        auto_exports_root = output_dir / "auto_exports"
        websocket_streams_root = output_dir / "websocket_streams_root"
        time_sync_offsets_path = output_dir / "time_sync_offsets.json"
        day_one_dir = websocket_streams_root / "2026-04-01"
        day_two_dir = websocket_streams_root / "2026-04-02"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        day_two_dir.mkdir(parents=True, exist_ok=False)
        _write_websocket_stream_input(day_one_dir, "2026-04-01")
        _write_websocket_stream_input(day_two_dir, "2026-04-02")
        _write_time_sync_offsets(time_sync_offsets_path, [20.0, 25.0, 30.0])

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--websocket-streams-root",
                str(websocket_streams_root),
                "--auto-snapshots-root",
                str(auto_snapshots_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--execution-time-sync-offsets-path",
                str(time_sync_offsets_path),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        snapshot_summary = json.loads(
            (auto_snapshots_root / "2026-04-02" / "websocket_snapshot_ingest.json").read_text(
                encoding="utf-8"
            )
        )
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        execution_telemetry = _read_execution_telemetry(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_websocket_input_dir_ref"].endswith(
            "websocket_streams_root\\2026-04-02"
        )
        assert state["last_auto_snapshot_dir_ref"].endswith("auto_snapshots\\2026-04-02")
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert state["last_execution_telemetry_ref"].endswith(
            "shadow_vps_service_execution_telemetry.json"
        )
        assert state["last_execution_telemetry_status"] == "written"
        assert snapshot_summary["accepted_message_count"] == 2
        assert snapshot_summary["event_types"] == ["snapshot"]
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-websocket"
        assert runtime_bundle["acquisition_mode"] == "websocket_stream_auto_export"
        assert runtime_bundle["websocket_input_dir_ref"].endswith(
            "websocket_streams_root\\2026-04-02"
        )
        assert runtime_bundle["auto_snapshot_dir_ref"].endswith("auto_snapshots\\2026-04-02")
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert execution_telemetry["export_dir"].endswith("auto_exports\\2026-04-02")
        assert execution_telemetry["time_sync_observation_days"] == 2.0
        assert execution_telemetry["websocket_observation_days"] == 2.0
        assert execution_telemetry["time_sync_offsets_ms"] == [
            20.0,
            25.0,
            30.0,
            20.0,
            25.0,
            30.0,
        ]
        assert execution_telemetry["websocket_interarrival_s"] == [60.0, 60.0]
        assert monitoring_payload["execution_telemetry_ref"].endswith(
            "shadow_vps_service_execution_telemetry.json"
        )
        assert monitoring_payload["execution_telemetry_status"] == "written"
        assert any(
            event["event_type"] == "auto_snapshot_completed"
            and event["session_date"] == "2026-04-01"
            for event in events
        )
        assert any(
            event["event_type"] == "auto_export_completed"
            and event["session_date"] == "2026-04-01"
            for event in events
        )
        assert any(
            event["event_type"] == "execution_telemetry_written"
            and event["session_date"] == "2026-04-02"
            for event in events
        )
        assert (auto_snapshots_root / "2026-04-02" / "websocket_snapshot_ingest.json").exists()
        assert (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_captures_native_live_websocket_then_runs_shadow(monkeypatch):
    service = _load_service_module()
    output_dir = _scratch_dir("live_websocket")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_captures_root = output_dir / "live_captures"
        auto_exports_root = output_dir / "auto_exports"
        live_config_path = output_dir / "live_websocket_config.json"
        execution_runtime_projection_path = (
            output_dir / "local_lab_execution_runtime_projection.json"
        )
        regime_lite_assessment_path = output_dir / "regime_lite_assessment.json"
        regime_lite_safing_recommendation_path = (
            output_dir / "regime_lite_safing_recommendation.json"
        )
        _write_execution_runtime_projection(execution_runtime_projection_path)
        _write_regime_lite_assessment(regime_lite_assessment_path)
        _write_regime_lite_safing_recommendation(
            regime_lite_safing_recommendation_path
        )
        _write_live_websocket_config(
            live_config_path,
            "2026-04-02",
            time_sync_probe_enabled=True,
            execution_runtime_projection_path_ref=(
                execution_runtime_projection_path.name
            ),
            regime_lite_assessment_path_ref=regime_lite_assessment_path.name,
            regime_lite_safing_recommendation_path_ref=(
                regime_lite_safing_recommendation_path.name
            ),
        )

        class _FakeSocket:
            def __init__(self) -> None:
                self.payloads = [
                    json.dumps({"result": None, "id": 1}),
                    json.dumps(
                        {
                            "stream": "btcusdt@trade",
                            "data": {
                                "e": "trade",
                                "s": "BTCUSDT",
                                "t": 101,
                                "p": "43250.1",
                                "q": "0.250",
                                "m": False,
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "stream": "btcusdt@ticker",
                            "data": {
                                "e": "24hrTicker",
                                "s": "BTCUSDT",
                                "c": "43255.0",
                                "b": "43254.5",
                                "a": "43255.5",
                                "v": "125000.0",
                                "h": "44000.0",
                                "l": "42000.0",
                            },
                        }
                    ),
                ]

            def settimeout(self, timeout: float) -> None:
                return None

            def send(self, payload: str) -> None:
                return None

            def recv(self) -> str | bytes | None:
                if not self.payloads:
                    raise TimeoutError("done")
                return self.payloads.pop(0)

            def close(self) -> None:
                return None

        server_times = iter(
            (
                BinanceServerTime(server_time_ms=1_699_999_999_980),
                BinanceServerTime(server_time_ms=1_699_999_999_975),
                BinanceServerTime(server_time_ms=1_699_999_999_970),
            )
        )

        async def _fake_server_time_reader() -> BinanceServerTime:
            return next(server_times)

        def _fake_live_capture(config: ShadowLiveWebSocketConfig, *, output_dir: Path):
            return capture_live_websocket_snapshot_batch(
                config,
                output_dir=output_dir,
                adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                    cfg,
                    socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeSocket(),
                    clock=lambda: 1_700_000_000.0,
                ),
                time_sync_server_time_reader=_fake_server_time_reader,
                clock=lambda: 1_700_000_000.0,
            )

        monkeypatch.setattr(service, "capture_live_websocket_snapshot_batch", _fake_live_capture)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--live-websocket-config",
                str(live_config_path),
                "--live-captures-root",
                str(live_captures_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        campaign_summary = _read_campaign_summary(service_dir)
        execution_telemetry = _read_execution_telemetry(service_dir)

        assert state["success_count"] == 1
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_live_capture_dir_ref"].endswith("live_captures\\2026-04-02")
        assert state["last_live_capture_snapshot_batch_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_snapshot_batch.json"
        )
        assert state["last_live_capture_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_capture_summary.json"
        )
        assert state["last_live_capture_time_sync_offsets_ref"].endswith(
            "live_captures\\2026-04-02\\live_time_sync_offsets.json"
        )
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_shadow_runtime_evidence_ref"].endswith(
            "local_replay_shadow.shadow_runtime_evidence.json"
        )
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert state["last_execution_telemetry_ref"].endswith(
            "shadow_vps_service_execution_telemetry.json"
        )
        assert state["last_execution_telemetry_status"] == "written"
        assert state["last_execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert state["last_execution_runtime_projection_source"] == "live_websocket_config"
        assert state["last_regime_lite_assessment_ref"] == str(
            regime_lite_assessment_path.resolve()
        )
        assert state["last_regime_lite_assessment_source"] == "live_websocket_config"
        assert state["last_regime_lite_safing_recommendation_ref"] == str(
            regime_lite_safing_recommendation_path.resolve()
        )
        assert (
            state["last_regime_lite_safing_recommendation_source"]
            == "live_websocket_config"
        )
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-live"
        assert runtime_bundle["acquisition_mode"] == "native_live_websocket_auto_export"
        assert runtime_bundle["live_capture_dir_ref"].endswith("live_captures\\2026-04-02")
        assert runtime_bundle["live_capture_snapshot_batch_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_snapshot_batch.json"
        )
        assert runtime_bundle["live_capture_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_capture_summary.json"
        )
        assert runtime_bundle["live_capture_time_sync_offsets_ref"].endswith(
            "live_captures\\2026-04-02\\live_time_sync_offsets.json"
        )
        assert runtime_bundle["live_capture_time_sync_sample_count"] == 3
        assert runtime_bundle["live_capture_time_sync_probe_error"] == ""
        assert runtime_bundle["live_capture_emitted_message_count"] == 2
        assert runtime_bundle["live_capture_accepted_message_count"] == 2
        assert runtime_bundle["live_capture_ignored_message_count"] == 0
        assert runtime_bundle["live_capture_rejected_message_count"] == 0
        assert runtime_bundle["live_capture_pair_scope"] == ["BTCUSDT"]
        assert runtime_bundle["live_capture_event_types"] == ["snapshot", "trade"]
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert runtime_bundle["accepted"] is False
        assert runtime_bundle["consecutive_days"] == 1
        assert runtime_bundle["execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert runtime_bundle["execution_runtime_projection_source"] == "live_websocket_config"
        assert runtime_bundle["regime_lite_assessment_ref"] == str(
            regime_lite_assessment_path.resolve()
        )
        assert (
            runtime_bundle["regime_lite_assessment_source"]
            == "live_websocket_config"
        )
        assert runtime_bundle["regime_lite_safing_recommendation_ref"] == str(
            regime_lite_safing_recommendation_path.resolve()
        )
        assert (
            runtime_bundle["regime_lite_safing_recommendation_source"]
            == "live_websocket_config"
        )
        assert runtime_bundle["execution_runtime_projection_status"] == "ready"
        assert runtime_bundle["execution_runtime_projection_ready"] is True
        assert runtime_bundle["execution_runtime_projection_ready_consumer_count"] == 3
        assert runtime_bundle["execution_runtime_projection_bridge_status"] == "healthy"
        assert runtime_bundle["execution_runtime_projection_bridge_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_rate_limit_model_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_spread_guard_model_loaded"] is True
        assert runtime_bundle["execution_runtime_projection_slippage_model_loaded"] is True
        assert runtime_bundle["regime_lite_governance_status"] == "ready"
        assert runtime_bundle["regime_lite_safing_severity"] == "halt_recommended"
        assert runtime_bundle["regime_lite_safing_should_exit_all"] is True
        assert execution_telemetry["time_sync_observation_days"] == 1.0
        assert execution_telemetry["time_sync_offsets_ms"] == [20.0, 25.0, 30.0]
        assert execution_telemetry["time_sync_source_refs"][0].endswith(
            "live_captures\\2026-04-02\\live_time_sync_offsets.json"
        )
        assert execution_telemetry["quota_observation_days"] == 1.0
        assert execution_telemetry["quota_call_counts"] == [3]
        assert len(execution_telemetry["quota_probe_durations_s"]) == 1
        assert execution_telemetry["quota_probe_durations_s"][0] >= 0.0
        assert execution_telemetry["quota_limit_calls_per_minute_values"] == []
        assert len(execution_telemetry["quota_calls_per_minute_observed"]) == 1
        assert execution_telemetry["quota_calls_per_minute_observed"][0] > 0.0
        assert execution_telemetry["quota_source_refs"][0].endswith(
            "live_captures\\2026-04-02\\live_time_sync_offsets.json"
        )
        assert execution_telemetry["websocket_observation_days"] == 1.0
        assert execution_telemetry["coverage_caution_flags"] == [
            "THR-X02_ACCEPTED_EVENTS_ONLY"
        ]
        assert execution_telemetry["websocket_source_refs"][0].endswith(
            "live_captures\\2026-04-02\\live_websocket_snapshot_batch.json"
        )
        assert campaign_summary["service_status"] == "stopped"
        assert campaign_summary["acquisition_mode"] == "native_live_websocket_auto_export"
        assert campaign_summary["live_capture_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_capture_summary.json"
        )
        assert campaign_summary["live_capture_time_sync_offsets_ref"].endswith(
            "live_captures\\2026-04-02\\live_time_sync_offsets.json"
        )
        assert campaign_summary["live_capture_time_sync_sample_count"] == 3
        assert campaign_summary["live_capture_accepted_message_count"] == 2
        assert campaign_summary["live_capture_event_types"] == ["snapshot", "trade"]
        assert campaign_summary["consecutive_days"] == 1
        assert campaign_summary["remaining_days"] == 29
        assert campaign_summary["execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert campaign_summary["execution_runtime_projection_source"] == "live_websocket_config"
        assert campaign_summary["regime_lite_assessment_ref"] == str(
            regime_lite_assessment_path.resolve()
        )
        assert (
            campaign_summary["regime_lite_assessment_source"]
            == "live_websocket_config"
        )
        assert campaign_summary["regime_lite_safing_recommendation_ref"] == str(
            regime_lite_safing_recommendation_path.resolve()
        )
        assert (
            campaign_summary["regime_lite_safing_recommendation_source"]
            == "live_websocket_config"
        )
        assert campaign_summary["execution_runtime_projection_status"] == "ready"
        assert campaign_summary["execution_runtime_projection_ready"] is True
        assert campaign_summary["execution_runtime_projection_bridge_status"] == "healthy"
        assert campaign_summary["execution_runtime_projection_bridge_loaded"] is True
        assert campaign_summary["regime_lite_governance_status"] == "ready"
        assert campaign_summary["regime_lite_safing_severity"] == "halt_recommended"
        live_capture_event = next(
            event for event in events if event["event_type"] == "live_capture_completed"
        )
        assert live_capture_event["live_capture_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_websocket_capture_summary.json"
        )
        assert live_capture_event["emitted_message_count"] == 2
        assert live_capture_event["accepted_message_count"] == 2
        assert live_capture_event["pair_scope"] == ["BTCUSDT"]
        assert live_capture_event["event_types"] == ["snapshot", "trade"]
        assert any(
            event["event_type"] == "runtime_evidence_bundle_written" for event in events
        )
        assert any(
            event["event_type"] == "execution_telemetry_written" for event in events
        )
        assert any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_cli_regime_lite_paths_override_live_websocket_config(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("live_websocket_regime_cli_override")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_captures_root = output_dir / "live_captures"
        auto_exports_root = output_dir / "auto_exports"
        live_config_path = output_dir / "live_websocket_config.json"
        config_regime_assessment_path = output_dir / "config_regime_lite_assessment.json"
        config_regime_safing_path = (
            output_dir / "config_regime_lite_safing_recommendation.json"
        )
        cli_regime_assessment_path = output_dir / "cli_regime_lite_assessment.json"
        cli_regime_safing_path = output_dir / "cli_regime_lite_safing_recommendation.json"
        _write_regime_lite_assessment(config_regime_assessment_path)
        _write_regime_lite_safing_recommendation(config_regime_safing_path)
        _write_regime_lite_assessment(cli_regime_assessment_path)
        _write_regime_lite_safing_recommendation(cli_regime_safing_path)
        _write_live_websocket_config(
            live_config_path,
            "2026-04-02",
            regime_lite_assessment_path_ref=config_regime_assessment_path.name,
            regime_lite_safing_recommendation_path_ref=config_regime_safing_path.name,
        )

        class _FakeSocket:
            def __init__(self) -> None:
                self.payloads = [
                    json.dumps({"result": None, "id": 1}),
                    json.dumps(
                        {
                            "stream": "btcusdt@trade",
                            "data": {
                                "e": "trade",
                                "s": "BTCUSDT",
                                "t": 101,
                                "p": "43250.1",
                                "q": "0.250",
                                "m": False,
                            },
                        }
                    ),
                ]

            def settimeout(self, timeout: float) -> None:
                return None

            def send(self, payload: str) -> None:
                return None

            def recv(self) -> str | bytes | None:
                if not self.payloads:
                    raise TimeoutError("done")
                return self.payloads.pop(0)

            def close(self) -> None:
                return None

        def _fake_live_capture(config: ShadowLiveWebSocketConfig, *, output_dir: Path):
            return capture_live_websocket_snapshot_batch(
                config,
                output_dir=output_dir,
                adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                    cfg,
                    socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeSocket(),
                    clock=lambda: 1_700_000_000.0,
                ),
                clock=lambda: 1_700_000_000.0,
            )

        monkeypatch.setattr(service, "capture_live_websocket_snapshot_batch", _fake_live_capture)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--live-websocket-config",
                str(live_config_path),
                "--live-captures-root",
                str(live_captures_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--regime-lite-assessment-path",
                str(cli_regime_assessment_path),
                "--regime-lite-safing-recommendation-path",
                str(cli_regime_safing_path),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        campaign_summary = _read_campaign_summary(service_dir)
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )

        assert state["last_regime_lite_assessment_ref"] == str(
            cli_regime_assessment_path.resolve()
        )
        assert state["last_regime_lite_assessment_source"] == "cli"
        assert state["last_regime_lite_safing_recommendation_ref"] == str(
            cli_regime_safing_path.resolve()
        )
        assert state["last_regime_lite_safing_recommendation_source"] == "cli"
        assert runtime_bundle["regime_lite_assessment_ref"] == str(
            cli_regime_assessment_path.resolve()
        )
        assert runtime_bundle["regime_lite_assessment_source"] == "cli"
        assert runtime_bundle["regime_lite_safing_recommendation_ref"] == str(
            cli_regime_safing_path.resolve()
        )
        assert runtime_bundle["regime_lite_safing_recommendation_source"] == "cli"
        assert campaign_summary["regime_lite_assessment_ref"] == str(
            cli_regime_assessment_path.resolve()
        )
        assert campaign_summary["regime_lite_assessment_source"] == "cli"
        assert campaign_summary["regime_lite_safing_recommendation_ref"] == str(
            cli_regime_safing_path.resolve()
        )
        assert campaign_summary["regime_lite_safing_recommendation_source"] == "cli"
        assert monitoring_payload["regime_lite_assessment_source"] == "cli"
        assert monitoring_payload["regime_lite_safing_recommendation_source"] == "cli"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_preserves_execution_runtime_projection_when_telemetry_write_fails(
    monkeypatch,
):
    service = _load_service_module()
    output_dir = _scratch_dir("projection_persist_on_telemetry_failure")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        execution_runtime_projection_path = (
            output_dir / "local_lab_execution_runtime_projection.json"
        )
        export_day = exports_root / "2026-04-02"
        export_day.mkdir(parents=True, exist_ok=False)
        _write_daily_export(export_day, "2026-04-02", "projection-persist")
        _write_execution_runtime_projection(execution_runtime_projection_path)

        def _raise_execution_telemetry(*args, **kwargs):
            raise RuntimeError("forced execution telemetry write failure")

        monkeypatch.setattr(
            service,
            "_write_execution_telemetry_artifacts",
            _raise_execution_telemetry,
        )

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--execution-runtime-projection-path",
                str(execution_runtime_projection_path),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert state["service_status"] == "degraded"
        assert state["failure_count"] == 1
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert state["last_execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert state["last_execution_runtime_projection_source"] == "cli"
        assert runtime_bundle["execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert runtime_bundle["execution_runtime_projection_status"] == "ready"
        assert runtime_bundle["execution_runtime_projection_ready"] is True
        assert runtime_bundle["execution_runtime_projection_bridge_status"] == "healthy"
        assert runtime_bundle["execution_runtime_projection_bridge_loaded"] is True
        assert monitoring_payload["execution_runtime_projection_ref"] == str(
            execution_runtime_projection_path.resolve()
        )
        assert monitoring_payload["execution_runtime_projection_source"] == "cli"
        assert monitoring_payload["execution_runtime_projection_status"] == "ready"
        assert monitoring_payload["execution_runtime_projection_ready"] is True
        assert monitoring_payload["execution_runtime_projection_ready_consumer_count"] == 3
        assert monitoring_payload["execution_runtime_projection_bridge_status"] == "healthy"
        assert monitoring_payload["execution_runtime_projection_bridge_loaded"] is True
        assert any(event["event_type"] == "shadow_day_failed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_skips_cycle_when_dashboard_control_halt_is_active() -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("dashboard_control_halt_active")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        export_day = exports_root / "2026-04-02"
        export_day.mkdir(parents=True, exist_ok=False)
        _write_daily_export(export_day, "2026-04-02", "halted")
        service_dir.mkdir(parents=True, exist_ok=False)
        (service_dir / "shadow_vps_service.state.json").write_text(
            json.dumps(
                {
                    "dashboard_control_halted": True,
                    "dashboard_control_target_profile": "light",
                    "dashboard_control_target_deployment_state": "rollback",
                    "dashboard_control_last_request_id": "req-halt-1",
                    "dashboard_control_last_command_kind": "set_halted",
                    "dashboard_control_last_result_status": "completed",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert state["dashboard_control_halted"] is True
        assert state["service_status"] == "degraded"
        assert state["loop_count"] == 1
        assert state["idle_count"] == 1
        assert state["success_count"] == 0
        assert state["last_selected_session_date"] == ""
        assert monitoring_payload["status"] == "critical"
        assert monitoring_payload["dashboard_control_halted"] is True
        assert monitoring_payload["dashboard_control_target_profile"] == "light"
        assert monitoring_payload["dashboard_control_target_deployment_state"] == "rollback"
        assert any(
            event["event_type"] == "dashboard_control_halted_active" for event in events
        )
        assert not any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_consumes_dashboard_command_queue_before_cycle() -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("dashboard_command_queue_halt")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        command_queue_root = output_dir / "dashboard_command_queue"
        export_day = exports_root / "2026-04-02"
        export_day.mkdir(parents=True, exist_ok=False)
        _write_daily_export(export_day, "2026-04-02", "queue-halted")
        initialize_dashboard_command_queue(command_queue_root)
        request = DashboardGovernedCommandRequest(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-dashboard-queue-halt",
            request_id="req-dashboard-queue-halt",
            command_kind=DashboardGovernedCommandKind.SET_HALTED,
            source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
            target_runtime_mode=RuntimeMode.LIVE,
            operator_reason="manual halt from grafana",
        )
        write_dashboard_command_request(command_queue_root, request)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--dashboard-command-queue-root",
                str(command_queue_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        acks = load_dashboard_command_acks(command_queue_root)
        results = load_dashboard_command_results(command_queue_root)
        assert len(acks) == 1
        assert len(results) == 1
        assert results[0].status.value == "completed"
        assert state["dashboard_control_halted"] is True
        assert state["dashboard_control_last_request_id"] == request.request_id
        assert state["dashboard_control_last_command_kind"] == "set_halted"
        assert state["idle_count"] == 1
        assert state["success_count"] == 0
        assert state["last_selected_session_date"] == ""
        assert any(
            event["event_type"] == "dashboard_control_halted_active"
            and event["reason_codes"] == ["shadow.dashboard_control.halted_active"]
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_persists_user_data_stream_metadata(monkeypatch):
    service = _load_service_module()
    output_dir = _scratch_dir("live_websocket_user_data")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_captures_root = output_dir / "live_captures"
        auto_exports_root = output_dir / "auto_exports"
        live_config_path = output_dir / "live_websocket_config.json"
        _write_live_websocket_config(
            live_config_path,
            "2026-04-02",
            pairs=("BTCUSDT", "ETHUSDT"),
            user_data_stream_enabled=True,
        )
        monkeypatch.setenv("BINANCE_API_KEY", "test-api-key")
        monkeypatch.setenv("BINANCE_API_SECRET", "test-api-secret")

        class _FakeMarketSocket:
            def __init__(self) -> None:
                self.payloads = [
                    json.dumps({"result": None, "id": 1}),
                    json.dumps(
                        {
                            "stream": "btcusdt@trade",
                            "data": {
                                "e": "trade",
                                "s": "BTCUSDT",
                                "t": 101,
                                "p": "43250.1",
                                "q": "0.250",
                                "m": False,
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "stream": "ethusdt@ticker",
                            "data": {
                                "e": "24hrTicker",
                                "s": "ETHUSDT",
                                "c": "2280.0",
                                "b": "2279.8",
                                "a": "2280.2",
                                "v": "98000.0",
                                "h": "2350.0",
                                "l": "2200.0",
                            },
                        }
                    ),
                ]

            def settimeout(self, timeout: float) -> None:
                return None

            def send(self, payload: str) -> None:
                return None

            def recv(self) -> str | bytes | None:
                if not self.payloads:
                    raise TimeoutError("done")
                return self.payloads.pop(0)

            def close(self) -> None:
                return None

        class _FakeUserSocket:
            def __init__(self) -> None:
                self.payloads = [
                    json.dumps(
                        {
                            "id": "shadow-user-data-subscribe",
                            "status": 200,
                            "result": {"subscriptionId": 11},
                        }
                    ),
                    json.dumps(
                        {
                            "subscriptionId": 11,
                            "event": {
                                "e": "executionReport",
                                "s": "BTCUSDT",
                            },
                        }
                    ),
                ]

            def settimeout(self, timeout: float) -> None:
                return None

            def send(self, payload: str) -> None:
                return None

            def recv(self) -> str | bytes | None:
                if not self.payloads:
                    raise TimeoutError("done")
                return self.payloads.pop(0)

            def close(self) -> None:
                return None

        def _fake_live_capture(config: ShadowLiveWebSocketConfig, *, output_dir: Path):
            return capture_live_websocket_snapshot_batch(
                config,
                output_dir=output_dir,
                adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                    cfg,
                    socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeMarketSocket(),
                    clock=lambda: 1_700_000_000.0,
                ),
                user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeUserSocket(),
                clock=lambda: 1_700_000_000.0,
            )

        monkeypatch.setattr(service, "capture_live_websocket_snapshot_batch", _fake_live_capture)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--live-websocket-config",
                str(live_config_path),
                "--live-captures-root",
                str(live_captures_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")
        campaign_summary = _read_campaign_summary(service_dir)

        assert state["last_live_user_data_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_user_data_capture_summary.json"
        )
        assert runtime_bundle["live_capture_pair_scope"] == ["BTCUSDT", "ETHUSDT"]
        assert runtime_bundle["live_user_data_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_user_data_capture_summary.json"
        )
        assert runtime_bundle["live_user_data_authenticated"] is True
        assert runtime_bundle["live_user_data_subscription_id"] == 11
        assert runtime_bundle["live_user_data_event_count"] == 1
        assert runtime_bundle["live_user_data_event_types"] == ["executionReport"]
        assert campaign_summary["live_user_data_summary_ref"].endswith(
            "live_captures\\2026-04-02\\live_user_data_capture_summary.json"
        )
        assert campaign_summary["live_user_data_authenticated"] is True
        assert campaign_summary["live_user_data_subscription_id"] == 11
        assert campaign_summary["live_user_data_event_count"] == 1
        assert campaign_summary["live_user_data_event_types"] == ["executionReport"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
