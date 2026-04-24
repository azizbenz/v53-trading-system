# V5.3 Security Credentials + Build-17 Operator Closure

## Status

- Security credential wave: `STABLE_BUT_NOT_FINAL`.
- Build-17 operator cockpit: `STABLE_BUT_NOT_FINAL`.
- Build-15 Engine C repo-truth closure: `STABLE_BUT_NOT_FINAL`, supported by targeted Engine C tests.
- Build-16 Engine D repo-truth closure: `STABLE_BUT_NOT_FINAL`, supported by targeted Engine D tests.
- Production verdict: not hedge-fund ready until sealed Testnet soak is green over multiple days.

## Decisions Locked

- Binance credentials are governed secrets, not ML artifacts.
- Grafana never carries `api_key`, `secret_key`, or plaintext payloads.
- Dashboard operations mutate VPS state only through the typed file queue.
- `LIVE`, `MICRO_LIVE`, and VPS runtime paths require sealed credential bundles.
- `LOCAL_REPLAY` may use env/plaintext credentials only through explicit dev/test flags.
- Credential profile activation/deactivation requires halted or blocked VPS state.
- Warm-up/recovery blocks trading unless an active Binance profile is present and validated.

## Implemented Surfaces

- `DashboardSecretKind`, `DashboardSecretEnvironment`, `DashboardSecretTransferManifest`.
- `BinanceCredentialProfileRef`, `BinanceCredentialInventoryEntry`, `BinanceCredentialInventorySnapshot`.
- Governed command kinds:
  - `request_upload_binance_credentials_bundle`
  - `request_activate_binance_credentials_profile`
  - `request_export_binance_credential_inventory`
  - `request_deactivate_binance_credentials_profile`
- Shadow VPS state stores only credential metadata:
  - active profile id
  - environment
  - validation status
  - last auth check timestamp
  - failure reason codes
  - inventory entries with sealed refs and hashes
- Build-17 monitoring/Grafana exposes:
  - active Binance profile
  - credential environment
  - validation status
  - inventory count
  - failure reason count
- Recovery/warm-up exposes credential blockers without secret material.

## Operator Runbook

1. Seal the Binance credential payload locally with the canonical `secrets_manager`.
2. Place only the sealed bundle reference in the dashboard command request.
3. Upload the sealed bundle metadata:

```powershell
python .\scripts\run_dashboard_governed_command.py --queue-root .\build\dashboard_command_queue --command-kind request_upload_binance_credentials_bundle --secret-hash "<sealed-bundle-sha256>" --secret-profile-id "binance-live-001" --secret-environment live --secret-sealed-ref "secrets/binance-live-001.sealed.json" --operator-reason "sealed Binance profile upload"
```

4. Halt or block the VPS before profile activation.
5. Activate the profile:

```powershell
python .\scripts\run_dashboard_governed_command.py --queue-root .\build\dashboard_command_queue --command-kind request_activate_binance_credentials_profile --target-secret-profile "binance-live-001" --operator-reason "activate reviewed sealed Binance profile"
```

6. Export safe inventory metadata:

```powershell
python .\scripts\run_dashboard_governed_command.py --queue-root .\build\dashboard_command_queue --command-kind request_export_binance_credential_inventory
```

7. Deactivate during rotation or incident response:

```powershell
python .\scripts\run_dashboard_governed_command.py --queue-root .\build\dashboard_command_queue --command-kind request_deactivate_binance_credentials_profile --target-secret-profile "binance-live-001" --operator-reason "credential rotation or incident response"
```

## Proof Executed

- `python -m py_compile ...` on modified security/dashboard/recovery seams with isolated `PYTHONPYCACHEPREFIX`: PASS.
- `python -m pytest -q tests\test_interface_contracts\test_dashboard_command_contracts.py tests\test_protocols\test_dashboard_command_queue.py tests\test_venue_adapters\test_binance_spot\test_credential_loader.py tests\test_protocols\test_vps_recovery_warmup_credentials.py tests\test_security\test_binance_credentials_redaction.py tests\test_protocols\test_shadow_vps_service_launcher.py::test_shadow_vps_service_startup_writes_eligible_recovery_report_from_persisted_live_capture --tb=short --basetemp=tmp_pytest_security_wave_refactor`: `33 passed`.
- `python -m pytest -q tests\test_protocols\test_live_complete_runtime.py tests\test_protocols\test_live_complete_dashboard.py tests\test_monitoring\test_local_grafana_dashboard.py tests\test_monitoring\test_shadow_vps_service_monitoring.py tests\test_ui\test_complete_dashboard_view.py --tb=short --basetemp=tmp_pytest_security_wave_ui`: `13 passed`.
- `python -m pytest -q tests\test_secrets_manager tests\test_protocols\test_shadow_vps_service_launcher.py::test_shadow_vps_service_startup_writes_blocked_recovery_report_when_market_capture_missing tests\test_protocols\test_shadow_vps_service_launcher.py::test_shadow_vps_service_startup_writes_eligible_recovery_report_from_persisted_live_capture --tb=short --basetemp=tmp_pytest_security_wave_recovery2`: `7 passed`.
- `python -m pytest -q tests\test_secrets_manager tests\test_venue_adapters\test_binance_spot tests\test_protocols\test_dashboard_command_queue.py tests\test_protocols\test_live_complete_runtime.py tests\test_monitoring tests\test_ui\test_complete_dashboard_view.py tests\test_security\test_binance_credentials_redaction.py tests\test_protocols\test_vps_recovery_warmup_credentials.py --tb=short --basetemp=tmp_pytest_security_wave_bundles_final2`: `274 passed`.
- `python -m pytest -q tests\test_engines\test_engine_c tests\test_engines\test_engine_d --tb=short --basetemp=tmp_pytest_security_wave_engine_cd_final`: `226 passed`.
- `python scripts\run_dag_check.py`: PASS, 673 files scanned, 1401 imports authorized, 0 cycles, 0 violations.
- `python scripts\run_engineering_guardrails.py`: PASS, `new_violations=0`.

## Deferred Proof

- Multi-day Binance Testnet soak with sealed profile upload, activation, restart, recovery, inventory export, and log/dashboard redaction checks.
- Full production auth validation against real Binance account permissions before any live trading.
- Final `COMPLETE` status for Build 15/16/17 after soak evidence is attached.

## Non-Negotiable Failure Modes

- Missing active profile blocks warm-up.
- Unknown profile activation fails.
- Activation/deactivation outside halted/blocked state is rejected.
- Plain JSON/YAML/env credentials are rejected by runtime loaders outside explicit local replay dev seams.
- Any credential leak in queue, state, monitoring, dashboard, recovery report, warm-up summary, or logs is a release blocker.
