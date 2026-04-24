#!/usr/bin/env python3
"""Shadow VPS recovery and warm-up evidence helpers."""

from __future__ import annotations

import json
from pathlib import Path

from interface_contracts import (
    DeploymentState,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from interface_contracts.atomic_io import atomic_write_json
from protocols import ShadowLiveWebSocketCaptureResult, ShadowLiveWebSocketConfig
from shadow_vps_service_io_support import (
    _build_bootstrap_adapter_config,
    _read_live_websocket_config,
)
from shadow_vps_service_loader_support import _read_live_capture_result
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext
from venue_adapters.binance_spot.time_sync import (
    BinanceAdapterConfig,
    resolve_time_sync_threshold_ms,
)


_EPS = 1e-12


def _passed(check_id: str) -> VpsRecoveryCheck:
    return VpsRecoveryCheck(
        check_id=check_id,
        status=VpsRecoveryCheckStatus.PASSED,
    )


def _review_only(check_id: str, *reasons: str) -> VpsRecoveryCheck:
    return VpsRecoveryCheck(
        check_id=check_id,
        status=VpsRecoveryCheckStatus.REVIEW_ONLY,
        reasons=tuple(reasons),
    )


def _blocked(check_id: str, *reasons: str) -> VpsRecoveryCheck:
    return VpsRecoveryCheck(
        check_id=check_id,
        status=VpsRecoveryCheckStatus.BLOCKED,
        reasons=tuple(reasons),
    )


def _load_capture_result(
    context: ShadowVpsServiceRuntimeContext,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> ShadowLiveWebSocketCaptureResult | None:
    if live_capture_result is not None:
        return live_capture_result
    capture_dir_ref = context.store.state.last_live_capture_dir_ref.strip()
    if not capture_dir_ref:
        return None
    return _read_live_capture_result(Path(capture_dir_ref))


def _load_time_sync_payload(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_time_sync_offsets_path(
    context: ShadowVpsServiceRuntimeContext,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> Path | None:
    candidates = (
        context.execution_time_sync_offsets_path,
        Path(capture_result.time_sync_offsets_path_ref)
        if capture_result is not None and capture_result.time_sync_offsets_path_ref
        else None,
        Path(context.store.state.last_live_capture_time_sync_offsets_ref)
        if context.store.state.last_live_capture_time_sync_offsets_ref
        else None,
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def _resolve_live_config(
    context: ShadowVpsServiceRuntimeContext,
) -> ShadowLiveWebSocketConfig | None:
    if context.live_websocket_config_path is None:
        return None
    if not context.live_websocket_config_path.is_file():
        return None
    return _read_live_websocket_config(context.live_websocket_config_path)


def _resolve_recovery_status(report: VpsRecoveryReadinessReport) -> str:
    if report.eligible_to_trade:
        return "eligible_to_trade"
    if any(check.status == VpsRecoveryCheckStatus.BLOCKED for check in report.checks):
        return "blocked"
    return "review_only"


def _clear_recovery_state(context: ShadowVpsServiceRuntimeContext) -> None:
    state = context.store.state
    state.last_vps_recovery_readiness_report_ref = ""
    state.last_vps_recovery_status = "not_configured"
    state.last_vps_recovery_eligible_to_trade = False
    state.last_vps_warmup_summary_ref = ""
    state.last_vps_warmup_final_state = "not_configured"
    state.last_vps_warmup_eligible_to_trade = False
    context.store.persist()


def _count_review_only_checks(checks: tuple[VpsRecoveryCheck, ...]) -> int:
    return sum(1 for check in checks if check.status == VpsRecoveryCheckStatus.REVIEW_ONLY)


def _build_bootstrap_check(context: ShadowVpsServiceRuntimeContext) -> VpsRecoveryCheck:
    summary = context.bootstrap_summary
    if summary.status != "ready":
        return _blocked("bootstrap_reconciliation", "shadow.bootstrap.not_ready")
    if summary.reconciliation_boot_trading_blocked:
        return _blocked("bootstrap_reconciliation", "shadow.bootstrap.trading_blocked")
    if summary.reconciliation_boot_circuit_breaker_tripped:
        return _blocked("bootstrap_reconciliation", "shadow.bootstrap.circuit_breaker")
    if not summary.reconciliation_boot_executed:
        return _blocked("bootstrap_reconciliation", "shadow.bootstrap.not_executed")
    return _passed("bootstrap_reconciliation")


def _build_remote_account_check(
    context: ShadowVpsServiceRuntimeContext,
) -> VpsRecoveryCheck:
    summary = context.bootstrap_summary
    if summary.status != "ready":
        return _blocked("remote_account_state", "shadow.remote_account.bootstrap_unavailable")
    if not summary.remote_state_snapshot_captured:
        return _blocked("remote_account_state", "shadow.remote_account.snapshot_missing")
    reasons: list[str] = []
    if summary.remote_open_orders_present:
        reasons.append("shadow.remote_account.open_orders_present")
    if summary.remote_positions_present:
        reasons.append("shadow.remote_account.positions_present")
    if reasons:
        return _review_only("remote_account_state", *reasons)
    return _passed("remote_account_state")


def _build_time_sync_check(
    context: ShadowVpsServiceRuntimeContext,
    *,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> VpsRecoveryCheck:
    required = bool(
        context.execution_time_sync_offsets_path is not None
        or (capture_result is not None and capture_result.time_sync_offsets_path_ref)
        or (live_config is not None and live_config.time_sync_probe_enabled)
    )
    if not required:
        return _passed("time_sync")
    if capture_result is not None and capture_result.time_sync_probe_error:
        return _blocked("time_sync", "shadow.time_sync.probe_error")
    offsets_path = _resolve_time_sync_offsets_path(context, capture_result)
    payload = _load_time_sync_payload(offsets_path)
    if payload is None:
        return _blocked("time_sync", "shadow.time_sync.offsets_missing")
    offsets = payload.get("time_sync_offsets_ms", ())
    if not isinstance(offsets, list) or not offsets:
        return _blocked("time_sync", "shadow.time_sync.offsets_invalid")
    try:
        max_abs_offset_ms = max(abs(float(value)) for value in offsets)
        threshold_ms = resolve_time_sync_threshold_ms(
            (
                _build_bootstrap_adapter_config(live_config)
                if live_config is not None
                else BinanceAdapterConfig()
            )
        )
    except Exception as exc:
        _ = exc
        return _blocked("time_sync", "shadow.time_sync.threshold_unavailable")
    if max_abs_offset_ms > float(threshold_ms) + _EPS:
        return _blocked("time_sync", "shadow.time_sync.drift_exceeded")
    return _passed("time_sync")


def _build_market_data_check(
    context: ShadowVpsServiceRuntimeContext,
    *,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> VpsRecoveryCheck:
    required = bool(
        live_config is not None
        or capture_result is not None
        or context.store.state.last_live_capture_dir_ref
    )
    if not required:
        return _passed("market_data_capture")
    if capture_result is None:
        return _blocked("market_data_capture", "shadow.market_data.capture_missing")
    if not capture_result.snapshot_batch_path_ref:
        return _blocked("market_data_capture", "shadow.market_data.snapshot_ref_missing")
    if not Path(capture_result.snapshot_batch_path_ref).is_file():
        return _blocked("market_data_capture", "shadow.market_data.snapshot_missing")
    if capture_result.accepted_message_count <= 0:
        return _blocked("market_data_capture", "shadow.market_data.no_accepted_messages")
    return _passed("market_data_capture")


def _build_user_data_check(
    *,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> VpsRecoveryCheck:
    if live_config is None or not live_config.user_data_stream_enabled:
        return _passed("account_user_data")
    if capture_result is not None and capture_result.user_data_authenticated:
        return _passed("account_user_data")
    return _review_only("account_user_data", "shadow.user_data.not_authenticated")


def _build_projection_check(context: ShadowVpsServiceRuntimeContext) -> VpsRecoveryCheck:
    projection_path = context.execution_runtime_projection_path
    if projection_path is None:
        return _passed("metrics_refresh")
    if projection_path.is_file():
        return _passed("metrics_refresh")
    return _review_only("metrics_refresh", "shadow.metrics.projection_missing")


def _build_dependency_check(
    *,
    check_id: str,
    path: Path | None,
    missing_reason: str,
) -> VpsRecoveryCheck:
    if path is None:
        return _passed(check_id)
    if path.is_file():
        return _passed(check_id)
    return _blocked(check_id, missing_reason)


def _build_readiness_report(
    context: ShadowVpsServiceRuntimeContext,
    *,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> VpsRecoveryReadinessReport:
    checks = (
        _build_bootstrap_check(context),
        _build_remote_account_check(context),
        _build_time_sync_check(
            context,
            capture_result=capture_result,
            live_config=live_config,
        ),
        _build_market_data_check(
            context,
            capture_result=capture_result,
            live_config=live_config,
        ),
        _build_user_data_check(capture_result=capture_result, live_config=live_config),
        _build_projection_check(context),
        _build_dependency_check(
            check_id="regime_lite_dependency",
            path=context.regime_lite_assessment_path,
            missing_reason="shadow.regime_lite.assessment_missing",
        ),
        _build_dependency_check(
            check_id="info_stress_dependency",
            path=context.info_stress_assessment_path,
            missing_reason="shadow.info_stress.assessment_missing",
        ),
    )
    blocking_reasons = tuple(
        reason
        for check in checks
        for reason in check.reasons
        if check.status == VpsRecoveryCheckStatus.BLOCKED
    )
    caution_flags = tuple(
        reason
        for check in checks
        for reason in check.reasons
        if check.status == VpsRecoveryCheckStatus.REVIEW_ONLY
    )
    eligible_to_trade = not blocking_reasons and not caution_flags
    return VpsRecoveryReadinessReport(
        report_id=f"shadow-vps-recovery:{context.store.state.loop_count}",
        runtime_mode=RuntimeMode.SHADOW,
        deployment_state=DeploymentState.SHADOW,
        bootstrap_summary=context.bootstrap_summary,
        websocket_ready=(
            capture_result is not None and capture_result.accepted_message_count > 0
        ),
        regime_lite_ready=(
            context.regime_lite_assessment_path is None
            or context.regime_lite_assessment_path.is_file()
        ),
        info_stress_ready=(
            context.info_stress_assessment_path is None
            or context.info_stress_assessment_path.is_file()
        ),
        checks=checks,
        eligible_to_trade=eligible_to_trade,
        blocking_reasons=blocking_reasons,
        caution_flags=caution_flags,
    )


def _build_warmup_summary(report: VpsRecoveryReadinessReport) -> VpsWarmupRunSummary:
    has_blockers = any(
        check.status == VpsRecoveryCheckStatus.BLOCKED for check in report.checks
    )
    final_state = (
        VpsWarmupState.BLOCKED
        if has_blockers
        else VpsWarmupState.ELIGIBLE_TO_TRADE
        if report.eligible_to_trade
        else VpsWarmupState.WARMUP_SHADOW_ONLY
    )
    return VpsWarmupRunSummary(
        run_id=f"shadow-vps-warmup:{report.report_id}",
        runtime_mode=RuntimeMode.SHADOW,
        final_state=final_state,
        phase_sequence=(
            VpsWarmupState.COLD_START,
            VpsWarmupState.RECOVERY_RESTORE,
            VpsWarmupState.BOOTSTRAP_RECONCILIATION,
            VpsWarmupState.PREFLIGHT_VALIDATION,
            final_state,
        ),
        report=report,
        eligible_to_trade=final_state == VpsWarmupState.ELIGIBLE_TO_TRADE,
        blocking_reasons=report.blocking_reasons,
        caution_flags=report.caution_flags,
    )


def _persist_recovery_artifacts(
    context: ShadowVpsServiceRuntimeContext,
    report: VpsRecoveryReadinessReport,
    warmup: VpsWarmupRunSummary,
) -> None:
    report_path = context.service_dir / "vps_recovery_readiness.report.json"
    warmup_path = context.service_dir / "vps_warmup_run.summary.json"
    atomic_write_json(report_path, report.model_dump(mode="json"), indent=2)
    atomic_write_json(warmup_path, warmup.model_dump(mode="json"), indent=2)
    state = context.store.state
    state.last_vps_recovery_readiness_report_ref = str(report_path.resolve())
    state.last_vps_recovery_status = _resolve_recovery_status(report)
    state.last_vps_recovery_eligible_to_trade = report.eligible_to_trade
    state.last_vps_warmup_summary_ref = str(warmup_path.resolve())
    state.last_vps_warmup_final_state = warmup.final_state.value
    state.last_vps_warmup_eligible_to_trade = warmup.eligible_to_trade
    context.store.persist()


def _has_recovery_scope(
    context: ShadowVpsServiceRuntimeContext,
    *,
    capture_result: ShadowLiveWebSocketCaptureResult | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> bool:
    return bool(
        live_config is not None
        or context.bootstrap_summary.status != "not_configured"
        or capture_result is not None
        or context.execution_time_sync_offsets_path is not None
    )


def _refresh_shadow_vps_recovery_artifacts(
    context: ShadowVpsServiceRuntimeContext,
    *,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None = None,
) -> tuple[VpsRecoveryReadinessReport | None, VpsWarmupRunSummary | None]:
    capture_result = _load_capture_result(context, live_capture_result)
    live_config = _resolve_live_config(context)
    if not _has_recovery_scope(
        context,
        capture_result=capture_result,
        live_config=live_config,
    ):
        _clear_recovery_state(context)
        return None, None
    report = _build_readiness_report(
        context,
        capture_result=capture_result,
        live_config=live_config,
    )
    warmup = _build_warmup_summary(report)
    _persist_recovery_artifacts(context, report, warmup)
    return report, warmup


__all__ = ["_refresh_shadow_vps_recovery_artifacts"]
