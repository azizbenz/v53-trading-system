"""Build-17 VPS recovery and warm-up proof helpers."""

from __future__ import annotations

from interface_contracts import (
    BinanceCredentialInventorySnapshot,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DeploymentState,
    RuntimeMode,
    ShadowVpsExecutionRuntimeBootstrapSummary,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)


def _build_check(
    *,
    check_id: str,
    passed: bool,
    blocked_reason: str,
) -> VpsRecoveryCheck:
    if passed:
        return VpsRecoveryCheck(check_id=check_id, status=VpsRecoveryCheckStatus.PASSED)
    return VpsRecoveryCheck(
        check_id=check_id,
        status=VpsRecoveryCheckStatus.BLOCKED,
        reasons=(blocked_reason,),
    )


def build_vps_recovery_readiness_report(
    *,
    report_id: str,
    runtime_mode: RuntimeMode = RuntimeMode.LIVE,
    deployment_state: DeploymentState = DeploymentState.LIVE_COMPLETE,
    circuit_breaker_active: bool,
    artifact_registry_readable: bool,
    active_artifact_manifest: DashboardArtifactTransferManifest | None,
    active_artifact_hash_matches: bool,
    bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary | None,
    command_queue_snapshot: DashboardCommandQueueSnapshot | None,
    websocket_ready: bool,
    regime_lite_ready: bool,
    info_stress_ready: bool,
    pending_ambiguous_command_count: int = 0,
    binance_credential_inventory: BinanceCredentialInventorySnapshot | None = None,
    active_binance_profile_id: str = "",
    binance_credentials_decryptable: bool = False,
    binance_credentials_authenticated: bool = False,
    binance_time_sync_ok: bool = False,
) -> VpsRecoveryReadinessReport:
    """Build the bounded pre-trading go/no-go report after crash or restart."""

    bootstrap_ready = (
        bootstrap_summary is not None
        and bootstrap_summary.reconciliation_boot_executed
        and not bootstrap_summary.reconciliation_boot_trading_blocked
        and not bootstrap_summary.reconciliation_boot_circuit_breaker_tripped
    )
    queue_ready = (
        command_queue_snapshot is not None
        and command_queue_snapshot.writable
        and command_queue_snapshot.drainable
        and pending_ambiguous_command_count == 0
        and command_queue_snapshot.ambiguous_pending_count == 0
    )
    credential_ready = (
        binance_credential_inventory is not None
        and bool(active_binance_profile_id)
        and binance_credential_inventory.active_profile_id == active_binance_profile_id
        and binance_credentials_decryptable
        and binance_credentials_authenticated
        and binance_time_sync_ok
    )
    checks = (
        _build_check(
            check_id="persisted_halt_restore",
            passed=not circuit_breaker_active,
            blocked_reason="persisted halt or circuit breaker state remains active",
        ),
        _build_check(
            check_id="artifact_registry",
            passed=artifact_registry_readable
            and active_artifact_manifest is not None
            and active_artifact_hash_matches,
            blocked_reason="active artifact registry or manifest state is unreadable or mismatched",
        ),
        _build_check(
            check_id="bootstrap_reconciliation",
            passed=bootstrap_ready,
            blocked_reason="execution bootstrap reconciliation is incomplete or trading_blocked",
        ),
        _build_check(
            check_id="websocket_capture",
            passed=websocket_ready,
            blocked_reason="websocket or user-data capture is not ready",
        ),
        _build_check(
            check_id="command_queue",
            passed=queue_ready,
            blocked_reason="dashboard command queue is not writable/drainable or has ambiguous pending requests",
        ),
        _build_check(
            check_id="binance_credentials",
            passed=credential_ready,
            blocked_reason="active Binance credential profile is missing, invalid, unauthenticated, or time-sync unsafe",
        ),
        _build_check(
            check_id="regime_dependencies",
            passed=regime_lite_ready and info_stress_ready,
            blocked_reason="regime-lite or info-stress dependencies are not ready",
        ),
    )
    blocking_reasons = tuple(
        reason
        for check in checks
        for reason in check.reasons
        if check.status == VpsRecoveryCheckStatus.BLOCKED
    )
    caution_flags: list[str] = []
    if command_queue_snapshot is not None and command_queue_snapshot.failed_result_count:
        caution_flags.append("dashboard.command.queue.failed_results_present")
    if bootstrap_summary is not None and bootstrap_summary.error:
        caution_flags.append("execution.bootstrap.error_present")
    return VpsRecoveryReadinessReport(
        report_id=report_id,
        runtime_mode=runtime_mode,
        deployment_state=deployment_state,
        active_artifact=active_artifact_manifest,
        binance_credential_inventory=binance_credential_inventory,
        active_binance_profile_id=active_binance_profile_id,
        binance_credential_validation_status=(
            "validated" if credential_ready else "blocked"
        ),
        command_queue_snapshot=command_queue_snapshot,
        bootstrap_summary=bootstrap_summary,
        websocket_ready=websocket_ready,
        regime_lite_ready=regime_lite_ready,
        info_stress_ready=info_stress_ready,
        pending_ambiguous_command_count=pending_ambiguous_command_count,
        checks=checks,
        eligible_to_trade=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        caution_flags=tuple(dict.fromkeys(caution_flags)),
    )


def run_vps_warmup(
    *,
    run_id: str,
    report: VpsRecoveryReadinessReport,
) -> VpsWarmupRunSummary:
    """Resolve the deterministic warm-up state machine from one readiness report."""

    phase_sequence = (
        VpsWarmupState.COLD_START,
        VpsWarmupState.RECOVERY_RESTORE,
        VpsWarmupState.BOOTSTRAP_RECONCILIATION,
        VpsWarmupState.PREFLIGHT_VALIDATION,
    )
    if report.eligible_to_trade:
        final_state = VpsWarmupState.ELIGIBLE_TO_TRADE
    else:
        core_recovery_ready = all(
            check.status == VpsRecoveryCheckStatus.PASSED
            for check in report.checks
            if check.check_id
            in {"persisted_halt_restore", "artifact_registry", "bootstrap_reconciliation"}
        )
        final_state = (
            VpsWarmupState.WARMUP_SHADOW_ONLY
            if core_recovery_ready
            else VpsWarmupState.BLOCKED
        )
    return VpsWarmupRunSummary(
        run_id=run_id,
        runtime_mode=report.runtime_mode,
        final_state=final_state,
        phase_sequence=phase_sequence + (final_state,),
        report=report,
        eligible_to_trade=final_state == VpsWarmupState.ELIGIBLE_TO_TRADE,
        blocking_reasons=report.blocking_reasons,
        caution_flags=report.caution_flags,
    )


__all__ = [
    "build_vps_recovery_readiness_report",
    "run_vps_warmup",
]
