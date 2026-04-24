from __future__ import annotations

from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
    RuntimeMode,
    ShadowVpsServiceState,
    binance_credential_entry_from_manifest,
)
from monitoring.local_grafana_dashboard import build_local_shadow_vps_grafana_dashboard


SECRET_SENTINELS = (
    "LIVE_API_KEY_SHOULD_NOT_LEAK",
    "LIVE_SECRET_KEY_SHOULD_NOT_LEAK",
    "BINANCE_SECRET",
    "api_key",
    "secret_key",
)


def _manifest() -> DashboardSecretTransferManifest:
    return DashboardSecretTransferManifest(
        secret_hash="d" * 64,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        profile_id="binance-live-001",
        environment=DashboardSecretEnvironment.LIVE,
        sealed_ref="secrets/binance-live-001.sealed.json",
        review_state="approved",
        validation_status="accepted",
    )


def _assert_no_secret_material(payload: str) -> None:
    for sentinel in SECRET_SENTINELS:
        assert sentinel not in payload


def test_dashboard_queue_models_do_not_carry_plaintext_binance_secret_material() -> None:
    request = DashboardGovernedCommandRequest(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-redaction",
        request_id="req-redaction",
        command_kind=DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
        source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
        target_runtime_mode=RuntimeMode.LIVE,
        operator_reason="upload sealed profile",
        secret_manifest=_manifest(),
    )
    result = DashboardGovernedCommandResult(
        timestamp_ms=1_700_000_000_000,
        correlation_id=request.correlation_id,
        result_id="result-redaction",
        request_id=request.request_id,
        command_kind=request.command_kind,
        status=DashboardGovernedCommandStatus.COMPLETED,
        idempotency_key=request.idempotency_key,
        secret_manifest=_manifest(),
    )
    state = ShadowVpsServiceState(
        binance_credential_inventory=(
            binance_credential_entry_from_manifest(_manifest()),
        ),
    )

    _assert_no_secret_material(request.model_dump_json())
    _assert_no_secret_material(result.model_dump_json())
    _assert_no_secret_material(state.model_dump_json())


def test_grafana_dashboard_contains_no_binance_plaintext_secret_fields() -> None:
    dashboard_json = str(build_local_shadow_vps_grafana_dashboard())

    _assert_no_secret_material(dashboard_json)
    assert "request_upload_binance_credentials_bundle" in dashboard_json
    assert "secret-hash" in dashboard_json
    assert "secret-sealed-ref" in dashboard_json
