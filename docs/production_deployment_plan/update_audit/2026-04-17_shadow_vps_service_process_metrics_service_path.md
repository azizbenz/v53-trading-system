# SHADOW VPS SERVICE PROCESS METRICS SERVICE PATH

## Objective

Prove whether the real Shadow VPS service path already wires bounded process metrics sampling and Prometheus-style export, or whether doc 16 still points to a real missing gap. This slice is proof-oriented: add end-to-end behavioral coverage on the existing service support path instead of inventing new monitoring architecture.

## Docs Governants

- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` `§3-§7`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` `Phase G posture: current code wins`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` `§1-§8`
- `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Current Code Seam

- Canonical file today: `scripts/shadow_vps_service_monitoring_support.py`
- Why this seam is the right place: it is the real service-path helper that samples process metrics, builds the monitoring payload, writes the bounded `.prom` export, writes the node_exporter textfile payload, and emits the scrape manifest/file_sd artifacts.
- Forbidden shortcut for this slice: do not create a second monitoring writer or a parallel VPS exporter stack under `src/`.

## Placement

- Target file: `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- Doc target path: docs 16 only names likely code targets, not a mandatory test path
- Actual landing decision: add a behavioral test at the monitoring test seam while keeping the runtime code unchanged because the service path already exists

## Files Changed

- `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- `docs/production_deployment_plan/update_audit/2026-04-17_shadow_vps_service_process_metrics_service_path.md`

## Claims Implemented

- The real Shadow VPS service support path already samples process metrics and writes bounded monitoring artifacts -> `scripts/shadow_vps_service_monitoring_support.py`
- End-to-end proof now exists that one service-path call writes:
  - backend payload JSON
  - observability export JSON
  - `.prom` text payload
  - optional node_exporter textfile payload
  - optional scrape manifest
  - optional Prometheus file_sd JSON
  -> `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- The optional outputs are now explicitly guarded by test coverage when node_exporter/scrape inputs are absent -> `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile tests/test_monitoring/test_shadow_vps_service_monitoring_support.py` -> pass
- `$env:TEMP='.test_tmp'; $env:TMP='.test_tmp'; $env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring_support.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_process_metrics.py -q` -> `5 passed, 1 warning`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No runtime code change was needed in this slice.
- This slice does not prove production deployment of node_exporter itself; it proves the service writes the bounded artifacts for that rail.
- This slice does not audit Grafana or local Prometheus ingestion end-to-end.

## Risks / Open Questions

- Doc 16 is partially stale on code existence, but that does not automatically prove all production deployment wiring is exercised outside tests.
- If a future gap appears here, it should be a service-path wiring gap, not an excuse to add a second exporter architecture.

## Completion Status

`COMPLETE`

Reason:

The real service-path proof is now executed and clean. The sampler, bounded `.prom` export, node_exporter textfile write, and scrape manifest/file_sd write are all covered without adding a second monitoring architecture.

## Next Safe Step

`Move to the next bounded observability gap only if it is a real deployment/integration gap, not a stale-doc code-existence claim.`
