from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import httpx
import yaml

from calibration_loader import CalibrationArtifact
from execution_backbone import (
    ExecutionOpportunity,
    ExecutionSubmissionStatus,
    RemoteExecutionState,
    SubmitReceipt,
    VenueOrderEvent,
    VenueOrderEventType,
)
from execution_backbone.reconciliation_layer.scheduler import (
    ReconciliationSchedulerCalibrationConfig,
)
from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from interface_contracts.binance_contracts import BinanceCredentials
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    LocalLabExecutionTelemetry,
    build_edge_gate_calibration_artifact,
    build_local_lab_execution_review,
    build_local_lab_execution_runtime_projection,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import repo_build_path
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    build_binance_execution_runtime_bootstrap_bundle,
    build_binance_execution_runtime,
    build_execution_runtime_bootstrap_bundle,
    build_execution_runtime,
    inspect_execution_runtime_bootstrap,
)
from scoring_backbone import FeeAwareEdgeGateConfig
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig


class FakeExecutionVenue:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, object, float]] = []
        self._counter = 0
        self.constraints_by_pair: dict[str, VenueConstraintSnapshot] = {}

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        return self.constraints_by_pair.get(pair)

    def submit_order(self, intent, now: float) -> SubmitReceipt:
        self._counter += 1
        order_id = f"ord-{self._counter}"
        self.submissions.append((order_id, intent, now))
        return SubmitReceipt(order_id=order_id, submitted_at=now)

    def replace_order(self, original_order_id: str, intent, now: float):
        raise NotImplementedError

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        return None

    def poll_order_events(self) -> tuple:
        return ()

    def fetch_remote_state(self) -> RemoteExecutionState:
        return RemoteExecutionState()


def _opportunity() -> ExecutionOpportunity:
    return ExecutionOpportunity(
        intent_id="intent-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        side="buy",
        quantity=0.25,
        expected_gain=0.01,
        expected_cost=0.0015,
        score=0.82,
        justification="validated execution path",
        spread_bps=2.0,
    )


def _edge_dtr(
    *,
    dtr_id: str,
    expected_cost: float,
    realized_cost: float,
    gross_return: float,
):
    return build_dtr(
        dtr_id=dtr_id,
        pair="BTCUSDT",
        engine_id="engine_a",
        decision_state=DecisionState.EXECUTED,
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        gross_return=gross_return,
        ce_expected=gross_return - expected_cost,
        runtime_mode="local_replay",
        input_source="local_replay",
        timestamp=1_700_000_000.0,
    )


def _write_fee_aware_edge_artifact(root: Path) -> None:
    records = (
        _edge_dtr(dtr_id="dtr-1", expected_cost=0.0010, realized_cost=0.0008, gross_return=0.0038),
        _edge_dtr(dtr_id="dtr-2", expected_cost=0.0011, realized_cost=0.0009, gross_return=0.0041),
        _edge_dtr(dtr_id="dtr-3", expected_cost=0.0012, realized_cost=0.0010, gross_return=0.0040),
        _edge_dtr(dtr_id="dtr-4", expected_cost=0.0013, realized_cost=0.0011, gross_return=0.0047),
        _edge_dtr(dtr_id="dtr-5", expected_cost=0.0014, realized_cost=0.0012, gross_return=0.0048),
        _edge_dtr(dtr_id="dtr-6", expected_cost=0.0015, realized_cost=0.0013, gross_return=0.0050),
    )
    config = EdgeGateCalibrationConfig(
        min_positive_trades=5,
        min_cost_observations=6,
        bootstrap_samples=250,
        rng_seed=7,
    )
    report = calibrate_edge_gate_thresholds(
        records,
        config=config,
        generated_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
    )
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by="operator.aziz",
        config=config,
        signed_at=datetime(2026, 4, 10, 13, 5, tzinfo=timezone.utc),
    )
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "edge_gate.yml").write_text(
        yaml.safe_dump(artifact.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def _publish_execution_no_trade_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/execution_no_trade.json",
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                    artifact_ids=("artifact-1",),
                    action_kinds=(ArtifactActionKind.NO_TRADE,),
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _write_ready_execution_runtime_projection(path: Path) -> None:
    projection = build_local_lab_execution_runtime_projection(
        build_local_lab_execution_review(
            correlation_id="corr-1",
            export_dir="E:/lab/export",
            run_id="run-1",
            telemetry=LocalLabExecutionTelemetry(
                correlation_id="corr-1",
                export_dir="E:/lab/export",
                run_id="run-1",
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
    atomic_write_json(path, projection.model_dump(mode="json"), indent=2)


def _write_reconciliation_scheduler_artifact(root: Path, *, interval_s: int | float = 1800) -> None:
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_id": "thr-i04-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-12T12:00:00Z",
        "thresholds": (
            {
                "threshold_id": "THR-I04",
                "value": interval_s,
                "source_module": "src/execution_backbone/reconciliation_layer/scheduler.py",
                "calibration_artifact": "config/calibration/v1/infra.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-12T12:05:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    (version_dir / "infra.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


class _FakeSocket:
    def __init__(self, messages) -> None:
        self._messages = list(messages)
        self.sent: list[str] = []
        self.closed = False

    def settimeout(self, timeout: float) -> None:
        return None

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self):
        if not self._messages:
            raise TimeoutError("no more messages")
        next_message = self._messages.pop(0)
        if isinstance(next_message, Exception):
            raise next_message
        return next_message

    def close(self) -> None:
        self.closed = True
        return None


def _mock_binance_remote_state_request(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/v3/openOrders":
        return httpx.Response(200, json=[])
    if request.url.path == "/api/v3/account":
        return httpx.Response(
            200,
            json={
                "makerCommission": 10,
                "takerCommission": 10,
                "buyerCommission": 0,
                "sellerCommission": 0,
                "canTrade": True,
                "canWithdraw": True,
                "canDeposit": True,
                "accountType": "SPOT",
                "updateTime": 1_710_000_000_000,
                "balances": [],
            },
        )
    return httpx.Response(404, json={"code": -1, "msg": "unexpected path"})


def test_build_execution_runtime_without_registry_state_dir_keeps_baseline_submission():
    adapter = FakeExecutionVenue()
    runtime = build_execution_runtime(adapter)

    submission = runtime.submit_opportunity(_opportunity(), now=10.0)

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert len(adapter.submissions) == 1


def test_build_execution_runtime_can_wire_fee_aware_edge_gate():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_fee_aware_edge")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _write_fee_aware_edge_artifact(state_dir)
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            fee_aware_edge_gate_config=FeeAwareEdgeGateConfig(calibration_root=state_dir),
        )

        submission = runtime.submit_opportunity(
            _opportunity().model_copy(update={"expected_gain": 0.0013, "expected_cost": 0.0007}),
            now=10.25,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.detail.startswith("edge=")
        assert len(adapter.submissions) == 0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_execution_runtime_bootstrap_reports_unconfigured_when_state_dir_missing():
    status = inspect_execution_runtime_bootstrap()

    assert status.configured is False
    assert status.selection_status.value == "no_snapshot"


def test_build_execution_runtime_with_compiled_registry_blocks_when_plan_blocks():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_bootstrap_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_EXECUTION_BLOCK"],
                    "detail": "artifact veto at execution boundary",
                },
            },
        )
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            compiled_registry_state_dir=state_dir,
        )

        submission = runtime.submit_opportunity(_opportunity(), now=11.0)

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.detail == "artifact veto at execution boundary"
        assert len(adapter.submissions) == 0

        status = inspect_execution_runtime_bootstrap(compiled_registry_state_dir=state_dir)
        assert status.configured is True
        assert status.selection_status.value == "loaded"
        assert status.loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_with_empty_registry_state_dir_fails_open():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_bootstrap_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            compiled_registry_state_dir=state_dir,
        )

        submission = runtime.submit_opportunity(_opportunity(), now=12.0)

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert len(adapter.submissions) == 1
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_can_load_lab_execution_runtime_projection():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_projection_bootstrap")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        projection_path = state_dir / "local_lab_execution_runtime_projection.json"
        _write_ready_execution_runtime_projection(projection_path)
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            execution_runtime_projection_path=projection_path,
        )

        submission = runtime.submit_opportunity(
            _opportunity().model_copy(
                update={
                    "quantity": 9.0,
                    "metadata": {"rest_quota_ratio_current": 0.85},
                }
            ),
            now=12.1,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.context["gate"] == "rate_limiter"
        assert len(adapter.submissions) == 0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_bootstrap_bundle_can_run_boot_reconciliation():
    adapter = FakeExecutionVenue()

    bundle = build_execution_runtime_bootstrap_bundle(
        adapter,
        reconciliation_boot_now=1_700_000_000.5,
    )

    assert bundle.reconciliation_scheduler is not None
    assert bundle.reconciliation_boot_result is not None
    assert bundle.reconciliation_boot_result.executed is True
    assert bundle.reconciliation_boot_result.trading_blocked is False
    assert bundle.reconciliation_boot_result.interval_s == 3600.0
    assert bundle.reconciliation_scheduler.state.next_due_ts == 1_700_003_600.5


def test_build_execution_runtime_bootstrap_bundle_can_load_governed_thr_i04():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_reconciliation_bootstrap")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _write_reconciliation_scheduler_artifact(state_dir, interval_s=1800)
        adapter = FakeExecutionVenue()
        bundle = build_execution_runtime_bootstrap_bundle(
            adapter,
            reconciliation_scheduler_calibration_config=(
                ReconciliationSchedulerCalibrationConfig(
                    calibration_root=str(state_dir),
                    calibration_version="v1",
                )
            ),
            reconciliation_boot_now=1_700_000_001.0,
        )

        assert bundle.reconciliation_scheduler is not None
        assert bundle.reconciliation_boot_result is not None
        assert bundle.reconciliation_boot_result.executed is True
        assert bundle.reconciliation_boot_result.interval_s == 1800.0
        assert bundle.reconciliation_scheduler.state.next_due_ts == 1_700_001_801.0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_bootstrap_bundle_accepts_gatekeeper_audit_path():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_gatekeeper_audit")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        adapter = FakeExecutionVenue()
        audit_path = state_dir / "artifacts" / "gatekeeper" / "audit.jsonl"

        bundle = build_execution_runtime_bootstrap_bundle(
            adapter,
            gatekeeper_audit_path=audit_path,
        )

        submission = bundle.runtime.submit_opportunity(_opportunity(), now=100.0)

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["decision"] == "submitted"
        assert payload["pair"] == "BTCUSDT"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_binance_execution_runtime_wires_bounded_user_data_source():
    fake_socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "v53-user-data-subscribe",
                    "status": 200,
                    "result": {"subscriptionId": 7},
                }
            ),
            json.dumps(
                {
                    "subscriptionId": 7,
                    "event": {
                        "e": "executionReport",
                        "E": 1_710_000_006_000,
                        "s": "BTCUSDT",
                        "c": "v53_engine_a_intent-1",
                        "S": "BUY",
                        "o": "LIMIT",
                        "f": "GTC",
                        "q": "0.25000000",
                        "p": "50000.10000000",
                        "x": "NEW",
                        "X": "NEW",
                        "i": 123461,
                        "l": "0.00000000",
                        "z": "0.00000000",
                        "L": "0.00000000",
                        "n": "0",
                        "N": None,
                        "t": -1,
                        "r": "NONE",
                    },
                }
            ),
        ]
    )
    http_client = httpx.AsyncClient(base_url="https://testnet.binance.vision", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    try:
        runtime = build_binance_execution_runtime(
            credentials=BinanceCredentials(
                api_key="test-api-key",
                secret_key="test-api-secret",
                label="testnet",
            ),
            config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
            http_client=http_client,
            user_data_stream_enabled=True,
            user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: fake_socket,
            clock_ms=lambda: 1_710_000_000_000,
        )

        assert runtime._adapter.poll_order_events() == (
            VenueOrderEvent(
                order_id="123461",
                event_type=VenueOrderEventType.ACK,
                timestamp=1_710_000_006.0,
            ),
        )
        assert len(fake_socket.sent) == 1
    finally:
        asyncio.run(http_client.aclose())


def test_build_binance_execution_runtime_can_enable_fee_aware_edge_gate_from_adapter_config():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_binance_fee_aware_edge")
    shutil.rmtree(state_dir, ignore_errors=True)
    http_client = httpx.AsyncClient(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
    )
    try:
        _write_fee_aware_edge_artifact(state_dir)
        runtime = build_binance_execution_runtime(
            credentials=BinanceCredentials(
                api_key="test-api-key",
                secret_key="test-api-secret",
                label="testnet",
            ),
            config=BinanceAdapterConfig(
                rest_base_url="https://testnet.binance.vision",
                calibration_root=state_dir.as_posix(),
                fee_aware_edge_gate_enabled=True,
            ),
            http_client=http_client,
        )

        submission = runtime.submit_opportunity(
            _opportunity().model_copy(update={"expected_gain": 0.0013, "expected_cost": 0.0007}),
            now=10.5,
        )

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.context["gate"] == "fee_aware_edge"
        assert submission.no_trade.context["reason_code"] == "EDGE_INSUFFICIENT_VS_FEES"
    finally:
        asyncio.run(http_client.aclose())
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_binance_execution_runtime_bootstrap_bundle_exposes_boot_reconciliation():
    fake_socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "v53-user-data-subscribe",
                    "status": 200,
                    "result": {"subscriptionId": 7},
                }
            ),
            json.dumps(
                {
                    "subscriptionId": 7,
                    "event": {
                        "e": "executionReport",
                        "E": 1_710_000_008_000,
                        "s": "BTCUSDT",
                        "c": "v53_engine_a_intent-1",
                        "S": "BUY",
                        "o": "LIMIT",
                        "f": "GTC",
                        "q": "0.25000000",
                        "p": "50000.10000000",
                        "x": "NEW",
                        "X": "NEW",
                        "i": 123463,
                        "l": "0.00000000",
                        "z": "0.00000000",
                        "L": "0.00000000",
                        "n": "0",
                        "N": None,
                        "t": -1,
                        "r": "NONE",
                    },
                }
            ),
        ]
    )
    http_client = httpx.AsyncClient(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(_mock_binance_remote_state_request),
    )
    try:
        bundle = build_binance_execution_runtime_bootstrap_bundle(
            credentials=BinanceCredentials(
                api_key="test-api-key",
                secret_key="test-api-secret",
                label="testnet",
            ),
            config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
            http_client=http_client,
            user_data_stream_enabled=True,
            user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: fake_socket,
            clock_ms=lambda: 1_710_000_000_000,
            reconciliation_boot_now=1_710_000_000.5,
        )

        assert bundle.reconciliation_scheduler is not None
        assert bundle.reconciliation_boot_result is not None
        assert bundle.reconciliation_boot_result.executed is True
        assert bundle.reconciliation_boot_result.trading_blocked is False
        assert bundle.runtime._adapter.poll_order_events()[0].event_type == VenueOrderEventType.ACK
    finally:
        asyncio.run(http_client.aclose())


def test_build_binance_execution_runtime_bootstrap_bundle_can_capture_remote_state_snapshot() -> None:
    http_client = httpx.AsyncClient(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(_mock_binance_remote_state_request),
    )
    try:
        bundle = build_binance_execution_runtime_bootstrap_bundle(
            credentials=BinanceCredentials(
                api_key="test-api-key",
                secret_key="test-api-secret",
                label="testnet",
            ),
            config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
            http_client=http_client,
            capture_remote_state_snapshot=True,
        )

        assert bundle.remote_state_snapshot is not None
        assert bundle.remote_state_snapshot.orders == {}
        assert bundle.remote_state_snapshot.positions == {}
    finally:
        asyncio.run(http_client.aclose())


def test_build_binance_execution_runtime_bootstrap_bundle_close_releases_owned_clients() -> None:
    fake_socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "v53-user-data-subscribe",
                    "status": 200,
                    "result": {"subscriptionId": 7},
                }
            ),
            json.dumps(
                {
                    "subscriptionId": 7,
                    "event": {
                        "e": "executionReport",
                        "E": 1_710_000_006_000,
                        "s": "BTCUSDT",
                        "c": "v53_engine_a_intent-1",
                        "S": "BUY",
                        "o": "LIMIT",
                        "f": "GTC",
                        "q": "0.25000000",
                        "p": "50000.10000000",
                        "x": "NEW",
                        "X": "NEW",
                        "i": 123464,
                        "l": "0.00000000",
                        "z": "0.00000000",
                        "L": "0.00000000",
                        "n": "0",
                        "N": None,
                        "t": -1,
                        "r": "NONE",
                    },
                }
            ),
        ]
    )
    bundle = build_binance_execution_runtime_bootstrap_bundle(
        credentials=BinanceCredentials(
            api_key="test-api-key",
            secret_key="test-api-secret",
            label="testnet",
        ),
        config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
        user_data_stream_enabled=True,
        user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: fake_socket,
        clock_ms=lambda: 1_710_000_000_000,
    )
    adapter = bundle.runtime._adapter

    assert adapter.poll_order_events()[0].event_type == VenueOrderEventType.ACK
    assert adapter._rest_client._client.is_closed is False

    bundle.close()

    assert adapter._rest_client._client.is_closed is True
    assert fake_socket.closed is True
