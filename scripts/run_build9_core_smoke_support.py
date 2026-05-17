from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time

import httpx


class _FakeSocket:
    def __init__(self, messages: list[str]) -> None:
        self._messages = list(messages)

    def settimeout(self, timeout: float) -> None:
        return None

    def send(self, payload: str) -> None:
        return None

    def recv(self) -> str:
        if not self._messages:
            raise TimeoutError("no more messages")
        return self._messages.pop(0)

    def close(self) -> None:
        return None


def _mock_binance_request(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/v3/order" and request.method.upper() == "POST":
        params = request.url.params
        return httpx.Response(
            200,
            json={
                "symbol": params.get("symbol", "BTCUSDT"),
                "orderId": 123462,
                "clientOrderId": params.get("newClientOrderId", "smoke-order"),
                "transactTime": 1_710_000_001_000,
                "status": "NEW",
                "side": params.get("side", "BUY"),
                "type": params.get("type", "MARKET"),
                "price": params.get("price", "0"),
                "origQty": params.get("quantity", "0.25"),
            },
        )
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


def _validate_execution_bootstrap_submission(
    runtime: object,
    gatekeeper_audit_path: Path | None,
) -> tuple[bool, str] | None:
    if gatekeeper_audit_path is None:
        return None
    from execution_backbone import ExecutionOpportunity, ExecutionSubmissionStatus

    submission = runtime.submit_opportunity(
        ExecutionOpportunity(
            intent_id="smoke-intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            quantity=0.25,
            expected_gain=0.01,
            expected_cost=0.0015,
            score=0.82,
            justification="build9 gatekeeper audit smoke",
            spread_bps=2.0,
        ),
        now=1_710_000_001.0,
    )
    if submission.status != ExecutionSubmissionStatus.SUBMITTED:
        return (
            False,
            "bounded Binance execution bootstrap did not submit through the canonical gatekeeper path",
        )
    if not gatekeeper_audit_path.exists():
        return (
            False,
            "bounded Binance execution bootstrap did not materialize the gatekeeper audit store",
        )
    return None


def _validate_execution_bootstrap_bundle(
    bundle: object,
    runtime: object,
    *,
    execution_runtime_projection_path: Path | None,
    reconciliation_calibration_root: Path | None,
    gatekeeper_audit_path: Path | None,
) -> tuple[bool, str]:
    submission_check = _validate_execution_bootstrap_submission(
        runtime,
        gatekeeper_audit_path,
    )
    if submission_check is not None:
        return submission_check
    events = runtime._adapter.poll_order_events()
    if len(events) != 1 or events[0].event_type.value != "ack":
        return (
            False,
            "bounded Binance execution bootstrap did not emit the expected ACK event",
        )
    if bundle.reconciliation_scheduler is None or bundle.reconciliation_boot_result is None:
        return (
            False,
            "bounded Binance execution bootstrap did not expose boot reconciliation state",
        )
    if (
        not bundle.reconciliation_boot_result.executed
        or bundle.reconciliation_boot_result.trading_blocked
    ):
        return (
            False,
            "bounded Binance execution bootstrap did not complete aligned boot reconciliation",
        )

    detail_parts = [
        "bounded Binance execution bootstrap wires authenticated user-data polling",
        "boot reconciliation",
    ]
    if reconciliation_calibration_root is not None:
        if bundle.reconciliation_boot_result.interval_s != 1800.0:
            return (
                False,
                "bounded Binance execution bootstrap did not load governed THR-I04 for reconciliation boot",
            )
        detail_parts.append("governed THR-I04 scheduler")
    if execution_runtime_projection_path is not None and (
        runtime._rate_limit_model is None
        or runtime._spread_guard_model is None
        or runtime._slippage_model is None
    ):
        return (
            False,
            "bounded Binance execution bootstrap did not load all governed execution consumers",
        )
    if execution_runtime_projection_path is not None:
        detail_parts.append("governed THR-X03/X04/X05 consumers")
    if gatekeeper_audit_path is not None:
        detail_parts.append("gatekeeper audit store")
    return True, " + ".join(detail_parts)


def _build_mock_execution_bootstrap_bundle(
    *,
    execution_runtime_projection_path: Path | None = None,
    reconciliation_calibration_root: Path | None = None,
    gatekeeper_audit_path: Path | None = None,
) -> tuple[httpx.AsyncClient, object]:
    from execution_backbone.reconciliation_layer.scheduler import (
        ReconciliationSchedulerCalibrationConfig,
    )
    from interface_contracts.binance_contracts import BinanceCredentials
    from protocols import build_binance_execution_runtime_bootstrap_bundle
    from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig

    reconciliation_calibration_config = None
    if reconciliation_calibration_root is not None:
        reconciliation_calibration_config = ReconciliationSchedulerCalibrationConfig(
            calibration_root=str(reconciliation_calibration_root),
            calibration_version="v1",
        )
    http_client = httpx.AsyncClient(
        base_url="https://testnet.binance.vision",
        transport=httpx.MockTransport(_mock_binance_request),
    )
    bundle = build_binance_execution_runtime_bootstrap_bundle(
        credentials=BinanceCredentials(
            api_key="smoke-api-key",
            secret_key="smoke-secret-key",
            label="smoke",
        ),
        config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
        http_client=http_client,
        user_data_stream_enabled=True,
        user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeSocket(
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
                            "E": 1_710_000_007_000,
                            "s": "BTCUSDT",
                            "c": "v53_engine_a_intent-1",
                            "S": "BUY",
                            "o": "LIMIT",
                            "f": "GTC",
                            "q": "0.25000000",
                            "p": "50000.10000000",
                            "x": "NEW",
                            "X": "NEW",
                            "i": 123462,
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
        ),
        clock_ms=lambda: 1_710_000_000_000,
        execution_runtime_projection_path=execution_runtime_projection_path,
        gatekeeper_audit_path=gatekeeper_audit_path,
        reconciliation_scheduler_calibration_config=reconciliation_calibration_config,
        reconciliation_boot_now=1_710_000_000.5,
    )
    return http_client, bundle


def measure_smoke_submission_latency(
    opportunity: object,
) -> str:
    from execution_backbone import ExecutionSubmissionStatus

    bootstrap_started = time.perf_counter()
    http_client, bundle = _build_mock_execution_bootstrap_bundle()
    try:
        bootstrap_overhead = time.perf_counter() - bootstrap_started
        adjusted_timestamps: dict[str, float] = {}
        for field_name in (
            "signal_arrival_monotonic_s",
            "scoring_completed_monotonic_s",
            "risk_completed_monotonic_s",
            "portfolio_completed_monotonic_s",
        ):
            field_value = getattr(opportunity, field_name, None)
            if field_value is not None:
                adjusted_timestamps[field_name] = field_value + bootstrap_overhead
        adjusted_opportunity = (
            opportunity.model_copy(update=adjusted_timestamps)
            if adjusted_timestamps
            else opportunity
        )
        submit_now = time.perf_counter()
        submission = bundle.runtime.submit_opportunity(adjusted_opportunity, now=submit_now)
        if submission.status != ExecutionSubmissionStatus.SUBMITTED:
            return "indicative pre-submit latency unavailable (submission not accepted)"
        parts: list[str] = []
        if submission.signal_to_submit_s is not None:
            parts.append(
                f"indicative signal_to_submit={submission.signal_to_submit_s * 1000.0:.2f}ms"
            )
        if submission.portfolio_to_submit_s is not None:
            parts.append(
                f"portfolio_to_submit={submission.portfolio_to_submit_s * 1000.0:.2f}ms"
            )
        if not parts:
            return "indicative pre-submit latency unavailable (timestamps not populated)"
        return ", ".join(parts)
    finally:
        bundle.close()
        asyncio.run(http_client.aclose())


def run_execution_bootstrap_smoke_with_projection(
    execution_runtime_projection_path: Path | None = None,
    reconciliation_calibration_root: Path | None = None,
    gatekeeper_audit_path: Path | None = None,
) -> tuple[bool, str]:
    http_client, bundle = _build_mock_execution_bootstrap_bundle(
        execution_runtime_projection_path=execution_runtime_projection_path,
        reconciliation_calibration_root=reconciliation_calibration_root,
        gatekeeper_audit_path=gatekeeper_audit_path,
    )
    try:
        return _validate_execution_bootstrap_bundle(
            bundle,
            bundle.runtime,
            execution_runtime_projection_path=execution_runtime_projection_path,
            reconciliation_calibration_root=reconciliation_calibration_root,
            gatekeeper_audit_path=gatekeeper_audit_path,
        )
    finally:
        bundle.close()
        asyncio.run(http_client.aclose())
