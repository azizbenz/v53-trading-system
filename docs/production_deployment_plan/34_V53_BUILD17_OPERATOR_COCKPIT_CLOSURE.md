# Build-17 Operator Cockpit Closure

## Status

- Build: `Build 17 = typed LiveComplete control surface + governed operator cockpit`.
- Closure status: `STABLE_BUT_NOT_FINAL`.
- Reason: typed contracts, command queue, monitoring projections, Grafana panels, credential metadata, and recovery/warm-up checks are tested locally; multi-day Testnet soak is still missing.

## Repo Truth

- Build 17 is not a new autonomous trading runtime.
- Dashboard actions mutate VPS state only through the typed governed file queue.
- Grafana can request upload, activation, export inventory, and deactivation of Binance credential profiles by sealed reference only.
- Grafana never receives or displays raw Binance API key material.
- Warm-up/recovery blocks trading when credential profile, auth, user-data, or time-sync requirements are not validated.

## Implemented Operator Surface

- Active ML artifact status.
- Active RegimeDetector artifact status.
- Active Binance profile id, environment, validation status, inventory count, and failure reason count.
- Queue request/ack/result status.
- Recovery and warm-up status.
- Recent VPS event/log projection.
- IA Lab navigation and artifact comparison context.

## Proof Executed

- `python -m pytest -q tests\test_protocols\test_live_complete_runtime.py tests\test_protocols\test_live_complete_dashboard.py tests\test_monitoring\test_local_grafana_dashboard.py tests\test_monitoring\test_shadow_vps_service_monitoring.py tests\test_ui\test_complete_dashboard_view.py --tb=short --basetemp=tmp_pytest_security_wave_ui`: `13 passed`.
- `python -m pytest -q tests\test_secrets_manager tests\test_venue_adapters\test_binance_spot tests\test_protocols\test_dashboard_command_queue.py tests\test_protocols\test_live_complete_runtime.py tests\test_monitoring tests\test_ui\test_complete_dashboard_view.py tests\test_security\test_binance_credentials_redaction.py tests\test_protocols\test_vps_recovery_warmup_credentials.py --tb=short --basetemp=tmp_pytest_security_wave_bundles_final2`: `274 passed`.
- DAG proof: `python scripts\run_dag_check.py` PASS with 0 violations.
- Guardrail proof: `python scripts\run_engineering_guardrails.py` PASS with `new_violations=0`.

## Blockers Before COMPLETE

- Run sealed Binance Testnet profile upload, activation, restart, recovery, inventory export, and redaction checks over multiple days.
- Attach live operator report artifacts from the Testnet soak.
- Validate that no dashboard/queue/log/report output contains secret material during the soak.
