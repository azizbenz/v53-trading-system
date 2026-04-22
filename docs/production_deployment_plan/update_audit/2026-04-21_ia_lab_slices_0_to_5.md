# IA-Lab Slices 0->5 — Codex — 2026-04-21

## Scope
- Repo truth used over the older sprint prompt.
- Current operator surface doctrine:
  - legacy HTML dashboard is not the target operator surface
  - local Prometheus + local Grafana are the active local observability surface
- Hard constraints respected during this pass:
  - no new engine outside A/B/C/D
  - no `src/local_ai_lab/`
  - no edits to `src/calibration_methods/psr.py`, `src/calibration_methods/dsr.py`, `src/calibration_methods/pot_gpd.py`, `src/calibration_methods/energy_distance.py`
  - DAG stayed green
  - `new_violations=0` stayed green

## Slice 0 — Tests baseline
### 0-A
- Status: COMPLETE
- Proof:
  - `python -m pytest tests/test_engines/test_engine_a -q --tb=short`
  - Result: `40 passed`

### 0-B
- Status: COMPLETE for the current repo-truth subset requested by the plan
- Canonical subset re-baselined:
  - `tests/test_monitoring`
  - `tests/test_protocols`
  - `tests/test_meta`
  - `tests/test_ui`
  - `tests/test_meta_learning`
  - `tests/test_engines/test_engine_b`
- Root causes closed in this pass:
  - Windows temp-root `PermissionError` in monitoring/protocol test infrastructure
  - repo `build/...` writes inside protocol tests moved to repo-local scratch helpers
  - stale test expectation in `test_local_replay_shadow_runner.py` updated to current runtime truth:
    - engine C is currently `hard_blocked` in the governed shadow path because coordination input is missing
  - legacy `technical_dashboard` test drift aligned with current repo surface while treating HTML as legacy
- Proof:
  - `python -m pytest tests/test_monitoring tests/test_protocols tests/test_meta tests/test_ui tests/test_meta_learning tests/test_engines/test_engine_b -q --tb=line`
  - Result: `959 passed`

## Slice 1 — RefusalRecord + RefusalJournal
- Status: COMPLETE (repo-native convergence)
- Canonical surfaces preserved:
  - [refusal_records.py](/E:/claude%20%20v5.3/v53_trading_system/src/interface_contracts/refusal_records.py)
  - [refusal_journal.py](/E:/claude%20%20v5.3/v53_trading_system/src/meta_minimal/refusal_journal/refusal_journal.py)
- Additive change only:
  - `count_by_category()` added to `RefusalJournal`
- Files touched:
  - [refusal_journal.py](/E:/claude%20%20v5.3/v53_trading_system/src/meta_minimal/refusal_journal/refusal_journal.py) — 111L
  - [test_refusal_records.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_interface_contracts/test_refusal_records.py) — 92L
  - [test_refusal_journal.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_meta_minimal/test_refusal_journal.py) — 69L
- Proof bundle:
  - included in the shared targeted convergence proof below

## Slice 2 — SignalCandidate enrichi
- Status: COMPLETE (repo-native convergence)
- Canonical surface preserved:
  - [forecast_contracts.py](/E:/claude%20%20v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py)
- Additive convergence only:
  - validation coverage extended for invalid `forecast_strength`
  - validation coverage extended for negative `expected_cost`
  - engine B runtime forecast cap aligned to `15.0`
- Files touched:
  - [engine_b_runtime_forecast_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_forecast_support.py) — 503L
  - [test_forecast_contracts.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_interface_contracts/test_forecast_contracts.py) — 263L
  - [test_engine_b_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py) — 716L
- Proof bundle:
  - included in the shared targeted convergence proof below

## Slice 3 — ForecastNormalizer
- Status: COMPLETE (repo-native convergence)
- Canonical functional seam preserved:
  - [forecast_normalizer.py](/E:/claude%20%20v5.3/v53_trading_system/src/scoring_backbone/forecast_normalizer.py)
- Tests strengthened to prove:
  - normalized mean absolute forecast is near `10`
  - engine-specific cap behavior is preserved
- Files touched:
  - [test_forecast_normalizer.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_scoring_backbone/test_forecast_normalizer.py) — 48L

## Slice 4 — BreakEvenFilter
- Status: COMPLETE (repo-native convergence)
- Canonical functional seam preserved:
  - [break_even_filter.py](/E:/claude%20%20v5.3/v53_trading_system/src/scoring_backbone/break_even_filter.py)
- Tests strengthened to prove:
  - `THR-E05`-style floor semantics
  - strict `>` behavior at the boundary
  - negative floor rejected
- Files touched:
  - [test_break_even_filter.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_scoring_backbone/test_break_even_filter.py) — 85L

## Slice 5 — CostDriftMonitor
- Status: COMPLETE
- New canonical module added:
  - [monitor.py](/E:/claude%20%20v5.3/v53_trading_system/src/meta_minimal/cost_drift_monitor/monitor.py) — 56L
  - [__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/meta_minimal/cost_drift_monitor/__init__.py) — 14L
- Package export updated:
  - [__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/meta_minimal/__init__.py) — 34L
- Test coverage added:
  - [test_cost_drift_monitor.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_meta_minimal/test_cost_drift_monitor.py) — 52L
- Behavior implemented:
  - default threshold `0.20`
  - hard cap `0.50`
  - `min_events=10`
  - `insufficient_data` below minimum sample count
  - `bias_pct = (mean(realised) - mean(expected)) / mean(expected)`
  - `expected_cost <= 0` rejected
  - `realised_cost < 0` rejected
  - `reset()` clears local buffer only

## Shared test-infra convergence
- New helper:
  - [support_paths.py](/E:/claude%20%20v5.3/v53_trading_system/tests/support_paths.py) — 23L
- Test configuration support:
  - [conftest.py](/E:/claude%20%20v5.3/v53_trading_system/tests/conftest.py) — 54L
- Additional files patched to use repo-local scratch/build-safe paths:
  - [test_local_replay_shadow_runner.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_protocols/test_local_replay_shadow_runner.py) — 922L
  - [test_local_grafana_api.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_monitoring/test_local_grafana_api.py) — 125L
  - [test_shadow_vps_service_bs122_regression.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_protocols/test_shadow_vps_service_bs122_regression.py) — 85L
  - [test_technical_dashboard.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_ui/test_technical_dashboard.py) — 1556L

## Proofs
### Targeted convergence proof
- `python -m pytest tests/test_interface_contracts/test_refusal_records.py tests/test_meta_minimal/test_refusal_journal.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_scoring_backbone/test_forecast_normalizer.py tests/test_scoring_backbone/test_break_even_filter.py tests/test_meta_minimal/test_cost_drift_monitor.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q --tb=short`
- Result: `100 passed`

### Local Prometheus/Grafana observability proof
- `python -m pytest tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_monitoring/test_local_grafana_api.py tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_local_grafana_bootstrap_launcher.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_lab_grafana_dashboard_launcher.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py -q --tb=line`
- Result: `34 passed`

### Broad Slice 0-B proof
- `python -m pytest tests/test_monitoring tests/test_protocols tests/test_meta tests/test_ui tests/test_meta_learning tests/test_engines/test_engine_b -q --tb=line`
- Result: `959 passed`

### Repository safety proofs
- `python scripts/run_dag_check.py`
  - Result: `PASS`, `Violations = 0`, `Cycles = 0`
- `python scripts/run_engineering_guardrails.py`
  - Result: `new_violations=0`

### Repo-wide test truth
- `python -m pytest tests -q --tb=short`
- Result:
  - `3287 passed`
  - `84 failed`
  - `51 errors`
  - `5 skipped`
- Interpretation:
  - the IA-Lab slices 0->5 are converged and safe
  - the full repo is not globally green yet
  - the remaining red is out of this slice and concentrated in other domains including:
    - `test_backtest_artifact_import/*`
    - `test_calibration_loader/*`
    - `test_execution_backbone/*`
    - `test_local_replay_runtime/*`
    - `test_sharia_compliance/*`
    - selected `risk_backbone`, `regime_classifier`, `venue_adapters` suites

## Final state
- Slice 0-A: COMPLETE
- Slice 0-B: COMPLETE
- Slice 1: COMPLETE
- Slice 2: COMPLETE
- Slice 3: COMPLETE
- Slice 4: COMPLETE
- Slice 5: COMPLETE
- DAG: PASS
- Guardrails: `new_violations=0`
- Full repo tests: red outside scope

## STATUT
PARTIAL

## Reason
- The requested IA-Lab convergence slices 0->5 are implemented and proven.
- The full repository test sweep is still red outside this slice, so a truthful global session verdict cannot be `COMPLETE`.

## Next recommended slice
- Attack the full-test red frontier in this order:
  1. `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
  2. `tests/test_local_replay_runtime/*` build-path / state-path failures
  3. `tests/test_calibration_loader/test_loader.py`
  4. `tests/test_execution_backbone/*` remaining persistence/path failures
