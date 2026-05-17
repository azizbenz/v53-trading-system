"""Shadow VPS service configuration + bootstrap helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from interface_contracts.binance_contracts import BinanceCredentials
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsExecutionRuntimeBootstrapSummary,
)
from protocols import (
    ExecutionRuntimeBootstrapBundle,
    ShadowLiveWebSocketConfig,
    ShadowVpsRawInputConfig,
    ShadowVpsServiceStore,
    build_binance_execution_runtime_bootstrap_bundle,
)
from venue_adapters.binance_spot.credential_loader import (
    BinanceCredentialLoadError,
    load_binance_credentials_from_file,
)
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig


def _read_raw_input_config(config_path: Path | None) -> ShadowVpsRawInputConfig:
    if config_path is None or not config_path.is_file():
        return ShadowVpsRawInputConfig()
    return ShadowVpsRawInputConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _read_live_websocket_config(config_path: Path) -> ShadowLiveWebSocketConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing live websocket config: {config_path}")
    return ShadowLiveWebSocketConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _resolve_live_websocket_artifact_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    ref: str,
) -> tuple[Path | None, str]:
    if explicit_path is not None:
        return explicit_path, "cli"
    resolved_ref = ref.strip()
    if not resolved_ref:
        return None, "not_configured"
    candidate = Path(resolved_ref)
    if candidate.is_absolute() or live_websocket_config_path is None:
        return candidate, "live_websocket_config"
    return (
        (live_websocket_config_path.parent / candidate).resolve(),
        "live_websocket_config",
    )


def _resolve_execution_runtime_projection_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.execution_runtime_projection_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_execution_runtime_bootstrap_enabled(
    *,
    explicit_enabled: bool,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[bool, str]:
    if explicit_enabled:
        return True, "cli"
    if live_config is not None and live_config.execution_runtime_bootstrap_enabled:
        return True, "live_websocket_config"
    return False, "not_configured"


def _resolve_execution_runtime_gatekeeper_audit_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.execution_runtime_gatekeeper_audit_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_regime_lite_assessment_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.regime_lite_assessment_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_regime_lite_safing_recommendation_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.regime_lite_safing_recommendation_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_info_stress_assessment_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.info_stress_assessment_path_ref if live_config is not None else ""
        ),
    )


def _resolve_telegram_alert_config_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.telegram_alert_config_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_telegram_alert_key_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(live_config.telegram_alert_key_path_ref if live_config is not None else ""),
    )


def _pin_auto_export_session_date(auto_export_dir: Path, session_date: str) -> None:
    manifest_path = auto_export_dir / "replay_run_manifest.json"
    if not manifest_path.is_file():
        return
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return
    governed_timeframe_scope = f"{session_date}/{session_date}"
    if payload.get("timeframe_scope") == governed_timeframe_scope:
        return
    payload["timeframe_scope"] = governed_timeframe_scope
    manifest_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _resolve_bootstrap_credentials(
    bootstrap_config: ShadowLiveWebSocketConfig,
    *,
    service_dir: Path,
) -> BinanceCredentials:
    store = ShadowVpsServiceStore(service_dir)
    state = store.state
    active_profile_id = state.active_binance_credential_profile_id
    if not active_profile_id:
        raise BinanceCredentialLoadError(
            "No active Binance credential profile in state store — run run_shadow_credential_seed.py"
        )
    entry = next(
        (item for item in state.binance_credential_inventory
         if item.profile.profile_id == active_profile_id),
        None,
    )
    if entry is None:
        raise BinanceCredentialLoadError(
            f"Active credential profile {active_profile_id!r} not found in inventory"
        )
    repo_root = Path(__file__).resolve().parent.parent
    sealed_path = repo_root / entry.profile.sealed_ref
    key_path = sealed_path.with_name(sealed_path.name.replace(".sealed.json", ".key"))
    return load_binance_credentials_from_file(sealed_path, key_path=key_path)


def _build_bootstrap_adapter_config(
    bootstrap_config: ShadowLiveWebSocketConfig,
) -> BinanceAdapterConfig:
    return BinanceAdapterConfig(
        rest_base_url=bootstrap_config.time_sync_rest_base_url,
        timeout_s=bootstrap_config.time_sync_rest_timeout_s,
        recv_window_ms=bootstrap_config.user_data_recv_window_ms,
        websocket_endpoint=bootstrap_config.endpoint,
        user_data_websocket_endpoint=bootstrap_config.user_data_endpoint,
        user_data_connect_timeout_s=bootstrap_config.connect_timeout_s,
        user_data_recv_timeout_s=bootstrap_config.recv_timeout_s,
        user_data_max_messages_per_poll=bootstrap_config.user_data_event_limit,
    )


def _count_remote_open_orders(bundle: ExecutionRuntimeBootstrapBundle) -> int:
    remote_state = getattr(bundle, "remote_state_snapshot", None)
    if remote_state is None:
        return 0
    return len(getattr(remote_state, "orders", {}) or {})


def _count_remote_position_assets(bundle: ExecutionRuntimeBootstrapBundle) -> int:
    remote_state = getattr(bundle, "remote_state_snapshot", None)
    if remote_state is None:
        return 0
    positions = getattr(remote_state, "positions", {}) or {}
    return sum(1 for quantity in positions.values() if abs(float(quantity)) > 1e-12)


def _build_bootstrap_success_summary(
    *,
    bundle: ExecutionRuntimeBootstrapBundle,
    bootstrap_source: str,
    execution_runtime_projection_path: Path | None,
    execution_runtime_projection_source: str,
    gatekeeper_audit_ref: str,
    gatekeeper_audit_source: str,
    user_data_stream_enabled: bool,
) -> ShadowVpsExecutionRuntimeBootstrapSummary:
    reconciliation_boot_result = bundle.reconciliation_boot_result
    remote_state_snapshot = getattr(bundle, "remote_state_snapshot", None)
    remote_open_order_count = _count_remote_open_orders(bundle)
    remote_position_asset_count = _count_remote_position_assets(bundle)
    return ShadowVpsExecutionRuntimeBootstrapSummary(
        status="ready",
        source=bootstrap_source,
        execution_runtime_projection_ref=(
            str(execution_runtime_projection_path.resolve())
            if execution_runtime_projection_path is not None
            else ""
        ),
        execution_runtime_projection_source=(
            execution_runtime_projection_source
            if execution_runtime_projection_path is not None
            else "not_configured"
        ),
        gatekeeper_audit_ref=gatekeeper_audit_ref,
        gatekeeper_audit_source=(
            gatekeeper_audit_source if gatekeeper_audit_ref else "not_configured"
        ),
        user_data_stream_enabled=user_data_stream_enabled,
        reconciliation_boot_executed=(
            reconciliation_boot_result.executed
            if reconciliation_boot_result is not None
            else False
        ),
        reconciliation_boot_trading_blocked=(
            reconciliation_boot_result.trading_blocked
            if reconciliation_boot_result is not None
            else False
        ),
        reconciliation_boot_circuit_breaker_tripped=(
            reconciliation_boot_result.circuit_breaker_tripped
            if reconciliation_boot_result is not None
            else False
        ),
        reconciliation_boot_detail=(
            reconciliation_boot_result.detail
            if reconciliation_boot_result is not None
            else ""
        ),
        reconciliation_boot_recovery_action=(
            reconciliation_boot_result.recovery_action
            if reconciliation_boot_result is not None
            else ""
        ),
        reconciliation_boot_divergence_count=(
            reconciliation_boot_result.divergence_count
            if reconciliation_boot_result is not None
            else 0
        ),
        remote_state_snapshot_captured=remote_state_snapshot is not None,
        remote_open_order_count=remote_open_order_count,
        remote_position_asset_count=remote_position_asset_count,
        remote_open_orders_present=remote_open_order_count > 0,
        remote_positions_present=remote_position_asset_count > 0,
        error="",
    )


def _build_bootstrap_failure_summary(
    *,
    bootstrap_source: str,
    execution_runtime_projection_path: Path | None,
    execution_runtime_projection_source: str,
    gatekeeper_audit_ref: str,
    gatekeeper_audit_source: str,
    live_config: ShadowLiveWebSocketConfig,
    error: Exception,
) -> ShadowVpsExecutionRuntimeBootstrapSummary:
    return ShadowVpsExecutionRuntimeBootstrapSummary(
        status="failed",
        source=bootstrap_source,
        execution_runtime_projection_ref=(
            str(execution_runtime_projection_path.resolve())
            if execution_runtime_projection_path is not None
            else ""
        ),
        execution_runtime_projection_source=(
            execution_runtime_projection_source
            if execution_runtime_projection_path is not None
            else "not_configured"
        ),
        gatekeeper_audit_ref=gatekeeper_audit_ref,
        gatekeeper_audit_source=(
            gatekeeper_audit_source if gatekeeper_audit_ref else "not_configured"
        ),
        user_data_stream_enabled=live_config.user_data_stream_enabled,
        error=str(error),
    )


def _write_execution_runtime_bootstrap_summary(
    *,
    service_dir: Path,
    bootstrap_enabled: bool,
    bootstrap_source: str,
    live_config: ShadowLiveWebSocketConfig | None,
    execution_runtime_projection_path: Path | None,
    execution_runtime_projection_source: str,
    gatekeeper_audit_path: Path | None,
    gatekeeper_audit_source: str,
) -> tuple[ShadowVpsExecutionRuntimeBootstrapSummary, Path | None]:
    if not bootstrap_enabled:
        return ShadowVpsExecutionRuntimeBootstrapSummary(), None

    summary_path = service_dir / "execution_runtime_bootstrap.summary.json"
    bootstrap_config = live_config or ShadowLiveWebSocketConfig()
    gatekeeper_audit_ref = (
        str(gatekeeper_audit_path.resolve()) if gatekeeper_audit_path is not None else ""
    )
    bundle = None
    try:
        credentials = _resolve_bootstrap_credentials(bootstrap_config, service_dir=service_dir)
        bundle = build_binance_execution_runtime_bootstrap_bundle(
            credentials=credentials,
            config=_build_bootstrap_adapter_config(bootstrap_config),
            gatekeeper_audit_path=gatekeeper_audit_path,
            execution_runtime_projection_path=execution_runtime_projection_path,
            user_data_stream_enabled=bootstrap_config.user_data_stream_enabled,
            reconciliation_boot_now=time.time(),
            capture_remote_state_snapshot=True,
        )
        summary = _build_bootstrap_success_summary(
            bundle=bundle,
            bootstrap_source=bootstrap_source,
            execution_runtime_projection_path=execution_runtime_projection_path,
            execution_runtime_projection_source=execution_runtime_projection_source,
            gatekeeper_audit_ref=gatekeeper_audit_ref,
            gatekeeper_audit_source=gatekeeper_audit_source,
            user_data_stream_enabled=bootstrap_config.user_data_stream_enabled,
        )
    except Exception as exc:
        summary = _build_bootstrap_failure_summary(
            bootstrap_source=bootstrap_source,
            execution_runtime_projection_path=execution_runtime_projection_path,
            execution_runtime_projection_source=execution_runtime_projection_source,
            gatekeeper_audit_ref=gatekeeper_audit_ref,
            gatekeeper_audit_source=gatekeeper_audit_source,
            live_config=bootstrap_config,
            error=exc,
        )
    finally:
        if bundle is not None:
            bundle.close()

    atomic_write_json(summary_path, summary.model_dump(mode="json"))
    return summary, summary_path
