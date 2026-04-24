from __future__ import annotations

from interface_contracts import (
    BinanceCredentialInventorySnapshot,
    BinanceCredentialValidationStatus,
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
    DeploymentState,
    RuntimeMode,
    ShadowVpsExecutionRuntimeBootstrapSummary,
    VpsWarmupState,
    binance_credential_entry_from_manifest,
)
from protocols import build_vps_recovery_readiness_report, run_vps_warmup


def _artifact() -> DashboardArtifactTransferManifest:
    return DashboardArtifactTransferManifest(
        artifact_hash="a" * 64,
        artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
        artifact_id="ml-active",
        source_ref="exports/ml-active.json",
    )


def _queue() -> DashboardCommandQueueSnapshot:
    return DashboardCommandQueueSnapshot(
        queue_dir_ref="build/queue",
        request_dir_ref="build/queue/requests",
        ack_dir_ref="build/queue/acks",
        result_dir_ref="build/queue/results",
        queue_status=DashboardCommandQueueStatus.HEALTHY,
        writable=True,
        drainable=True,
        healthy=True,
    )


def _bootstrap() -> ShadowVpsExecutionRuntimeBootstrapSummary:
    return ShadowVpsExecutionRuntimeBootstrapSummary(
        status="ready",
        reconciliation_boot_executed=True,
        reconciliation_boot_trading_blocked=False,
        reconciliation_boot_circuit_breaker_tripped=False,
    )


def _inventory() -> BinanceCredentialInventorySnapshot:
    manifest = DashboardSecretTransferManifest(
        secret_hash="b" * 64,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        profile_id="binance-live-001",
        environment=DashboardSecretEnvironment.LIVE,
        sealed_ref="secrets/binance-live-001.sealed.json",
        review_state="approved",
        validation_status="validated",
    )
    return BinanceCredentialInventorySnapshot(
        active_profile_id="binance-live-001",
        entries=(
            binance_credential_entry_from_manifest(
                manifest,
                active=True,
                validation_status=BinanceCredentialValidationStatus.VALIDATED,
            ),
        ),
        exported_at_ms=1_700_000_000_000,
    )


def _base_report_kwargs() -> dict[str, object]:
    return {
        "report_id": "recovery-credentials",
        "runtime_mode": RuntimeMode.LIVE,
        "deployment_state": DeploymentState.LIVE_COMPLETE,
        "circuit_breaker_active": False,
        "artifact_registry_readable": True,
        "active_artifact_manifest": _artifact(),
        "active_artifact_hash_matches": True,
        "bootstrap_summary": _bootstrap(),
        "command_queue_snapshot": _queue(),
        "websocket_ready": True,
        "regime_lite_ready": True,
        "info_stress_ready": True,
    }


def test_vps_recovery_blocks_when_binance_credentials_missing() -> None:
    report = build_vps_recovery_readiness_report(**_base_report_kwargs())
    warmup = run_vps_warmup(run_id="warmup-credentials", report=report)

    assert report.eligible_to_trade is False
    assert "active Binance credential profile is missing" in " / ".join(
        report.blocking_reasons
    )
    assert any(check.check_id == "binance_credentials" for check in report.checks)
    assert warmup.final_state == VpsWarmupState.WARMUP_SHADOW_ONLY


def test_vps_recovery_allows_trade_only_after_validated_binance_credentials() -> None:
    report = build_vps_recovery_readiness_report(
        **_base_report_kwargs(),
        binance_credential_inventory=_inventory(),
        active_binance_profile_id="binance-live-001",
        binance_credentials_decryptable=True,
        binance_credentials_authenticated=True,
        binance_time_sync_ok=True,
    )
    warmup = run_vps_warmup(run_id="warmup-credentials", report=report)

    assert report.eligible_to_trade is True
    assert report.active_binance_profile_id == "binance-live-001"
    assert report.binance_credential_validation_status == "validated"
    assert warmup.final_state == VpsWarmupState.ELIGIBLE_TO_TRADE
    dumped = warmup.model_dump_json()
    assert "api_key" not in dumped
    assert "secret_key" not in dumped
    assert "api-key-value" not in dumped
    assert "secret-key-value" not in dumped
