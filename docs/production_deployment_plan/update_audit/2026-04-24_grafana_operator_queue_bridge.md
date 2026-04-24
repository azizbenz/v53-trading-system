# 2026-04-24 - Grafana operator queue bridge

## Status

`COMPLETE` for the bounded bridge slice.

Grafana remains an observation/operator surface. It does not mutate VPS state directly. Operator actions are submitted as typed `DashboardGovernedCommandRequest` files into the governed dashboard command queue, then the VPS launcher consumes that queue at the start of each service cycle when `--dashboard-command-queue-root` is configured. The VPS queue processor validates and applies or rejects requests behind the existing state machine.

## Files

- `scripts/run_dashboard_governed_command.py`
- `src/monitoring/grafana_operator_bridge_markdown.py`
- `src/monitoring/local_grafana_dashboard_build17.py`
- `src/monitoring/local_grafana_dashboard.py`
- `scripts/run_shadow_vps_service.py`
- `scripts/shadow_vps_service_cli_support.py`
- `scripts/shadow_vps_service_context_support.py`
- `scripts/shadow_vps_service_models.py`
- `scripts/shadow_vps_service_startup_support.py`
- `tests/test_protocols/test_dashboard_governed_command_launcher.py`
- `tests/test_protocols/test_shadow_vps_service_launcher.py`
- `tests/test_monitoring/test_local_grafana_dashboard.py`
- `tests/test_monitoring/test_local_grafana_dashboard_launcher.py`

## Operator command

```powershell
python .\scripts\run_dashboard_governed_command.py --queue-root .\build\dashboard_command_queue --command-kind set_halted --operator-reason "manual halt from grafana"
```

This command writes a request file only. It does not halt trading by itself. The VPS command processor remains responsible for validation, acknowledgement, result emission, and state mutation.

The matching VPS service command must use the same queue root:

```powershell
python .\scripts\run_shadow_vps_service.py --dashboard-command-queue-root .\build\dashboard_command_queue
```

## Doctrine checks

- No direct Grafana-to-VPS mutation.
- No new API control plane.
- No bypass of Shadow, Micro-live, Live-Light, recovery, or warm-up checks.
- No A/B/C/D engine changes.
- No quant-anchor changes.
- No directional ML semantics.

## Proof

- `python -X pycache_prefix=.test_tmp\pycache -m py_compile scripts/run_dashboard_governed_command.py scripts/run_shadow_vps_service.py scripts/shadow_vps_service_cli_support.py scripts/shadow_vps_service_context_support.py scripts/shadow_vps_service_models.py scripts/shadow_vps_service_startup_support.py src/monitoring/grafana_operator_bridge_markdown.py src/monitoring/local_grafana_dashboard_build17.py src/monitoring/local_grafana_dashboard.py tests/test_protocols/test_dashboard_governed_command_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py` - PASS
- `rtk pytest tests/test_protocols/test_dashboard_governed_command_launcher.py tests/test_protocols/test_dashboard_command_queue.py tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_consumes_dashboard_command_queue_before_cycle tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_skips_cycle_when_dashboard_control_halt_is_active tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_dashboard_metric_guides.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q --tb=short --basetemp=.test_tmp/pytest_grafana_queue_launcher_final` - `20 passed`
- `python scripts/run_dag_check.py` - `VERDICT: PASS`
- `python scripts/run_engineering_guardrails.py` - `new_violations=0`

## Remaining boundary

This slice adds operator request submission, Grafana instructions, and launcher-side queue consumption behind `run_shadow_vps_service.py`. It does not add a Grafana write API.
