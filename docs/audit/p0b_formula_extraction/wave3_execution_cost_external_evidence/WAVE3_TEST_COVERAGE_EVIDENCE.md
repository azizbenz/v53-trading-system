# Wave 3 Test Coverage Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Test files found

- `tests/test_execution_backbone/test_execution_cost_meter.py`
- `tests/test_execution_backbone/test_fill_tracker.py`
- `tests/test_execution_backbone/test_venue_constraints_provider.py`
- `tests/test_execution_backbone/test_execution_runtime.py`
- `tests/test_execution_backbone/test_slippage_model.py`
- `tests/test_execution_backbone/test_rate_limiter.py`
- `tests/test_execution_backbone/test_spread_guard.py`
- `tests/unit/protocols/test_execution_routing_bridge.py`
- `tests/integration/execution/test_execution_runtime_hybrid_router.py`
- `tests/integration/execution/test_execution_runtime_fallback_path.py`
- `tests/test_venue_adapters/test_binance_spot/test_rest_client.py`
- `tests/test_venue_adapters/test_binance_spot/test_rate_limiter.py`
- `tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py`
- `tests/test_venue_adapters/test_binance_spot/test_execution_adapter.py`
- `tests/test_venue_adapters/test_binance_spot/test_order_translator.py`
- `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`
- `tests/test_local_replay_runtime/test_replay_executor.py`
- `tests/test_local_replay_runtime/test_artifact_exporter.py`
- `tests/test_local_replay_runtime/test_artifact_ablation_study.py`
- `tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py`
- `tests/test_meta_minimal/test_cost_drift_monitor.py`
- `tests/test_meta_minimal/test_break_even_dashboard_minimal.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_economic_sterilization.py`
- `tests/cockpit/test_state_run_comparison.py`
- `tests/cockpit/test_state_engine_why.py`
- `tests/cockpit/test_state_data_quality.py`
- `tests/cockpit/test_cockpit_server_routes.py`

## Exact assertions already proven by source inspection

Fee:
- `compute_fee` returns `fee_rate == 0.001` when `fee_amount = 50` on `gross_value = 50000`
- `estimate_fee(50000, 1, 0.001) == 50`

Cost aggregation:
- `total_cost = explicit_fee + implicit_cost + adverse_selection + partial_fill_cost + market_impact`
- `cost_surprise = total_cost - expected_cost`

Fill tracking:
- weighted average fill price is preserved across partial fills
- duplicate fill ids are idempotent
- zero-quantity fill aggregation is rejected

Replay fill realism:
- reduced decision state produces positive `realized_cost`
- hard-blocked decision state produces zero `realized_cost`

Runtime cost gating:
- insufficient edge vs fees returns `EDGE_INSUFFICIENT_VS_FEES`
- rate-limit excess returns `RATE_LIMIT_QUOTA_RATIO_EXCEEDED`
- spread guard blocks on excessive spread
- missing rate-limit telemetry can fail open
- invalid spread can fail open

Venue constraints:
- cache-only critical path is enforced
- `NOTIONAL` filter accepted as min-notional source

Routing bridge:
- side passthrough buy -> `BUY`
- side passthrough sell -> `SELL`
- stale snapshot rejected
- low coverage rejected

Cockpit replay semantics:
- replay economics placeholders and sample warnings are covered
- execution semantics labels are surfaced through state/template tests from Wave 2

## Missing or incomplete test proof for external audit

- Separate realized slippage metric was not proven as a surfaced tested metric.
- Replay expected-cost explicit fee inclusion was not proven.
- Replay expected-cost explicit impact inclusion was not proven.
- Empirical calibration realism of `p_fill_proxy` was not proven by the inspected tests.
- Engine-why and sterilization zero-default execution fields remain more weakly proven than replay-metrics main card semantics.

## Environment failures

Validation commands run:
- `python -m pytest -q tests/test_execution_backbone --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_execution_backbone`
- `python -m pytest -q tests/integration/execution --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_integration_execution`
- `python -m pytest -q tests/test_venue_adapters --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_venue_adapters`
- `python -m pytest -q tests/test_local_replay_runtime --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_local_replay`
- `python -m pytest -q tests/test_meta_minimal/test_cost_drift_monitor.py tests/test_meta_minimal/test_break_even_dashboard_minimal.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_meta_cost`
- `python -m pytest -q tests/cockpit --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_cockpit`
- targeted replay slice:
  `python -m pytest -q tests/test_local_replay_runtime/test_shadow_execution_simulator.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_artifact_exporter.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_local_replay_targeted`
- targeted backtest bridge slice:
  `python -m pytest -q tests/test_backtest_artifact_import/test_export_dir_bridge.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_backtest_bridge`
- targeted cockpit slice:
  `python -m pytest -q tests/cockpit/test_state_replay_metrics.py tests/cockpit/test_state_economic_sterilization.py tests/cockpit/test_state_run_comparison.py tests/cockpit/test_state_engine_why.py tests/cockpit/test_state_data_quality.py tests/cockpit/test_cockpit_server_routes.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave3_cockpit_targeted`

Results:
- execution backbone broad slice: `178 passed`, `6 failed`, `4 errors`; all observed failures were `PermissionError [WinError 5]` writes under `build/` rather than formula/assertion mismatches in the seams used by this pack
- integration execution slice: `11 passed`
- venue adapters broad slice: `80 passed`, `5 skipped`, `1 failed`, `1 error`; both observed failures were `PermissionError [WinError 5]` writes under `build/`
- local replay broad slice: test bodies ran through `181` collected items, then pytest session-finish cleanup failed on `tmp_pytest_wave3_local_replay`; one unrelated test in `test_regime_detector_shadow_audit_diagnosis.py` also surfaced before cleanup
- meta cost slice: `17 passed`
- cockpit broad slice: `60 passed`, `1 failed`; failure was `tests/cockpit/test_service_pid_smoke.py::test_service_pid_lifecycle_e2e`, unrelated to execution-cost formulas in this pack
- targeted replay slice: `14 passed`
- targeted backtest bridge slice: `26 passed`
- targeted cockpit slice: `21 passed`

Environment failures observed:
- repeated `PermissionError [WinError 5]` under repo `build/` paths for some broad execution/venue test fixtures
- pytest session-finish cleanup `PermissionError [WinError 5]` on the broad local replay `--basetemp` directory

Interpretation for external audit:
- targeted Wave 3 evidence seams are test-covered and passed on the narrow slices above
- broad-suite failures in this run are dominated by local filesystem permission/setup issues and one unrelated cockpit service PID smoke test
