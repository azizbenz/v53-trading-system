from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cockpit.form_state_support import (
    LabMlHandoffFormState,
    read_lab_ml_handoff_form_state,
    write_lab_ml_handoff_form_state,
)
from cockpit.action_support import (
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
)
from cockpit.queue_support import initialize_dashboard_command_queue
from cockpit.server import _build_lab_ml_handoff_form_state, create_app
from cockpit.state import CockpitPaths
from cockpit.strategy_ladder_ml_handoff_support import (
    discover_lab_feature_governance,
    resolve_lab_feature_picker_defaults,
    resolve_lab_selected_feature_names,
)
from local_replay_runtime.expected_edge_feature_promotion_registry import (
    ExpectedEdgeFeatureVerdict,
    FeaturePromotionEntry,
    FeaturePromotionRegistry,
    save_feature_promotion_registry,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
)


def _build_client(tmp_path: Path) -> TestClient:
    service_dir = tmp_path / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    auto_exports_root = tmp_path / "auto_exports"
    auto_exports_root.mkdir(parents=True, exist_ok=True)
    queue_root = tmp_path / "dashboard_command_queue"
    initialize_dashboard_command_queue(queue_root)
    backtest_jobs_root = tmp_path / "backtest_jobs"
    backtest_jobs_root.mkdir(parents=True, exist_ok=True)
    artifact_ingress_root = tmp_path / "artifact_ingress"
    artifact_ingress_root.mkdir(parents=True, exist_ok=True)
    observability_output_dir = tmp_path / "observability"
    observability_output_dir.mkdir(parents=True, exist_ok=True)
    live_websocket_config = tmp_path / "live_websocket.json"
    live_websocket_config.write_text("{}", encoding="utf-8")
    paths = CockpitPaths(
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
    app = create_app(
        paths=paths,
        grafana_url="http://127.0.0.1:3000",
        prometheus_url="http://127.0.0.1:9090",
    )
    return TestClient(app)


def _entry(
    *,
    pair: str = "BTCUSDT",
    timeframe: str = "1m",
    feature_name: str = "vpin",
    verdict: ExpectedEdgeFeatureVerdict = ExpectedEdgeFeatureVerdict.PROMOTED,
) -> FeaturePromotionEntry:
    return FeaturePromotionEntry(
        pair=pair,
        timeframe=timeframe,
        feature_name=feature_name,
        verdict=verdict,
        shap_rank=1,
        ablation_delta_psr=0.07,
        ablation_delta_sharpe=0.03,
        ablation_delta_break_even_bps=1.2,
        talab_quadruple_pass=True,
        min_btl_required=252,
        min_btl_satisfied=True,
        evidence_artifact_ref="E:/artifact.json",
    )


def test_lab_form_state_selected_features_backward_compat() -> None:
    state = LabMlHandoffFormState(feature_names="close_return,high_low_range,volume")
    assert state.selected_features == ()


def test_lab_form_state_selected_features_priority() -> None:
    state = LabMlHandoffFormState(
        feature_names="close_return",
        selected_features=("vpin", "kyle_lambda"),
    )
    assert resolve_lab_selected_feature_names(state) == ("vpin", "kyle_lambda")


def test_lab_feature_picker_defaults_drop_demoted_registry_entries() -> None:
    state = LabMlHandoffFormState(feature_names="close_return,vpin,high_low_range")
    defaults = resolve_lab_feature_picker_defaults(
        form_state=state,
        governance_entries=(
            _entry(
                feature_name="vpin",
                verdict=ExpectedEdgeFeatureVerdict.DEMOTED,
            ),
        ),
        supported_feature_names=("close_return", "vpin", "high_low_range"),
    )
    assert defaults == ("close_return", "high_low_range")


def test_discover_lab_feature_governance_missing_registry_returns_empty(tmp_path: Path) -> None:
    state = LabMlHandoffFormState(pair="BTCUSDT", timeframe="1m")
    assert discover_lab_feature_governance(
        state,
        registry_path=tmp_path / "missing.json",
    ) == ()


def test_discover_lab_feature_governance_filters_by_pair_tf(tmp_path: Path) -> None:
    registry_path = tmp_path / "feature_promotion_registry.json"
    registry = FeaturePromotionRegistry(
        entries=(
            _entry(pair="BTCUSDT", timeframe="1m", feature_name="vpin"),
            _entry(pair="BTCUSDT", timeframe="5m", feature_name="queue_pressure"),
            _entry(pair="ETHUSDT", timeframe="1m", feature_name="kyle_lambda"),
        )
    )
    save_feature_promotion_registry(registry_path, registry)
    state = LabMlHandoffFormState(pair="BTCUSDT", timeframe="1m")
    entries = discover_lab_feature_governance(state, registry_path=registry_path)
    assert len(entries) == 1
    assert entries[0].feature_name == "vpin"


def test_sync_handoff_uses_selected_features_when_present(tmp_path: Path) -> None:
    built = _build_lab_ml_handoff_form_state(
        kline_root=str(tmp_path / "klines"),
        b2_run_root="",
        orderbook_root="",
        trades_root="",
        metadata_root="",
        handoff_export_dir="",
        pair="BTCUSDT",
        selected_pairs=None,
        timeframe="1m",
        train_start="2025-01-01",
        train_end="2025-06-30",
        requested_backtest_start="",
        requested_backtest_days=130,
        train_days=180,
        validation_days=30,
        freshness_days=30,
        chunk_days=30,
        calibration_version="strategy_ladder_expected_edge.v1",
        feature_names="close_return,high_low_range,volume",
        selected_features=["vpin", "kyle_lambda"],
        feature_picker_enabled=True,
        sample_stride_minutes=60,
        target_horizon_minutes=1,
        training_seed=5307,
        max_optuna_trials=0,
        min_training_rows=210,
        shap_summary_ref="",
        signed_by="cockpit_operator",
        intent="launch",
    )
    assert built.selected_features == ("vpin", "kyle_lambda")
    assert built.feature_names == "vpin,kyle_lambda"


def test_template_renders_supported_feature_count_25(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    response = client.get("/lab")
    assert response.status_code == 200
    assert response.text.count('name="selected_features" value="') == 25
    assert 'name="selected_features_csv"' in response.text


def test_template_feature_badge_class_matches_verdict(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    write_lab_ml_handoff_form_state(
        jobs_root,
        LabMlHandoffFormState(pair="BTCUSDT", timeframe="1m"),
    )
    save_feature_promotion_registry(
        jobs_root / "feature_promotion_registry.json",
        FeaturePromotionRegistry(entries=(_entry(verdict=ExpectedEdgeFeatureVerdict.PROMOTED),)),
    )
    response = client.get("/lab")
    assert response.status_code == 200
    assert "feat-badge--promoted" in response.text
    assert "REPLAY_MICROSTRUCTURE" in response.text


def test_template_warns_when_demoted_feature_is_selected(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    write_lab_ml_handoff_form_state(
        jobs_root,
        LabMlHandoffFormState(
            pair="BTCUSDT",
            timeframe="1m",
            selected_features=("vpin",),
            feature_names="vpin",
        ),
    )
    save_feature_promotion_registry(
        jobs_root / "feature_promotion_registry.json",
        FeaturePromotionRegistry(
            entries=(
                _entry(
                    feature_name="vpin",
                    verdict=ExpectedEdgeFeatureVerdict.DEMOTED,
                ),
            )
        ),
    )
    response = client.get("/lab")
    assert response.status_code == 200
    assert "Inline warning:" in response.text
    assert "vpin" in response.text


def test_endpoint_rejects_empty_selected_features(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    response = client.post(
        "/lab/strategy-ladder-ml-handoff",
        data={
            "intent": "launch",
            "kline_root": str(tmp_path / "klines"),
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "train_start": "2025-01-01",
            "train_end": "2025-06-30",
            "requested_backtest_days": "130",
            "train_days": "180",
            "validation_days": "30",
            "freshness_days": "30",
            "chunk_days": "30",
            "feature_names": "",
            "feature_picker_enabled": "1",
            "sample_stride_minutes": "60",
            "target_horizon_minutes": "1",
            "training_seed": "5307",
            "max_optuna_trials": "0",
            "min_training_rows": "210",
            "signed_by": "cockpit_operator",
        },
    )
    assert response.status_code == 400


def test_lab_launch_uses_csv_mirror_when_checkbox_payload_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    captured: dict[str, object] = {}

    def _fake_launch_backtest_job(**kwargs):
        captured.update(kwargs)
        return CockpitBacktestJobRecord(
            job_id="strategy_ladder_ml_lab_handoff-001",
            correlation_id="corr-001",
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            status=CockpitBacktestJobStatus.JOB_CREATED,
            requested_at_iso="2026-05-24T08:00:00+00:00",
            output_root=str(tmp_path / "ml_handoff_output"),
            record_path=str(tmp_path / "job.json"),
            stdout_log_path=str(tmp_path / "stdout.log"),
            command=("python", "stub.py"),
        )

    monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)
    jobs_root = tmp_path / "backtest_jobs"
    response = client.post(
        "/lab/strategy-ladder-ml-handoff",
        data={
            "intent": "launch",
            "kline_root": str(tmp_path / "klines"),
            "b2_run_root": str(tmp_path / "phase_b2" / "backtest_strategy_ladder" / "wf"),
            "pair": "BTCUSDT",
            "timeframe": "1m,5m,10m,15m",
            "train_start": "2025-05-02",
            "train_end": "2025-07-17",
            "requested_backtest_start": "2025-07-18",
            "requested_backtest_days": "15",
            "train_days": "180",
            "validation_days": "30",
            "freshness_days": "30",
            "chunk_days": "15",
            "feature_names": "close_return,high_low_range,volume",
            "selected_features_csv": "vpin,kyle_lambda",
            "feature_picker_enabled": "1",
            "sample_stride_minutes": "60",
            "target_horizon_minutes": "1",
            "training_seed": "5307",
            "max_optuna_trials": "9",
            "min_training_rows": "210",
            "signed_by": "cockpit_operator",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    state = read_lab_ml_handoff_form_state(jobs_root)
    assert state.selected_features == ("vpin", "kyle_lambda")
    assert state.feature_names == "vpin,kyle_lambda"
    assert captured["feature_names_csv"] == "vpin,kyle_lambda"


def test_lab_launch_blocks_non_legacy_features_without_b2_run_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)

    def _unexpected_launch_backtest_job(**kwargs):
        raise AssertionError("launch_backtest_job must not be called")

    monkeypatch.setattr(
        "cockpit.server.launch_backtest_job",
        _unexpected_launch_backtest_job,
    )
    jobs_root = tmp_path / "backtest_jobs"
    response = client.post(
        "/lab/strategy-ladder-ml-handoff",
        data={
            "intent": "launch",
            "kline_root": str(tmp_path / "klines"),
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "train_start": "2025-05-02",
            "train_end": "2025-07-17",
            "requested_backtest_start": "2025-07-18",
            "requested_backtest_days": "15",
            "train_days": "180",
            "validation_days": "30",
            "freshness_days": "30",
            "chunk_days": "15",
            "feature_names": "close_return,high_low_range,volume",
            "selected_features_csv": ",".join(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES),
            "feature_picker_enabled": "1",
            "sample_stride_minutes": "60",
            "target_horizon_minutes": "1",
            "training_seed": "5307",
            "max_optuna_trials": "9",
            "min_training_rows": "210",
            "signed_by": "cockpit_operator",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Non-legacy+ML+features+require+B2+run+root+before+launch" in response.headers["location"]
    state = read_lab_ml_handoff_form_state(jobs_root)
    assert state.selected_features == SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES
