# Wave 2 Reconciliation Test Plan

## Existing evidence
- Producer metrics are recomputed from DTRs in:
  - `src/backtest_artifact_import/export_dir_bridge_support.py::_validate_metrics_consistency`
- Existing tests already cover:
  - replay export generation
  - replay metrics schema and DTR consistency
  - cockpit economic sterilization
  - run comparison loading
  - decision trace loading

## Exact validation commands

### Syntax
```powershell
python -m py_compile src/local_replay_runtime/replay_metrics_collector.py src/local_replay_runtime/replay_executor.py src/local_replay_runtime/artifact_exporter.py src/meta_minimal/dtr_core/dtr_record_builder.py src/cockpit/state_replay_metrics.py src/cockpit/state_economic_sterilization.py
```

### Replay and bridge
```powershell
python -m pytest -q tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_artifact_exporter.py tests/test_backtest_artifact_import/test_export_dir_bridge.py --tb=short --disable-warnings
```

### Cockpit replay consumers
```powershell
python -m pytest -q tests/cockpit/test_state_economic_sterilization.py tests/cockpit/test_state_engine_why.py tests/cockpit/test_state_decision_trace.py tests/cockpit/test_state_run_comparison.py --tb=short --disable-warnings
```

### Cost drift comparator
```powershell
python -m pytest -q tests/test_meta_minimal/test_cost_drift_monitor.py --tb=short --disable-warnings
```

## Missing but recommended tests

### Producer reconciliation
1. `global_ce_net ~= sum(pair.ce_net)`
2. `global_ce_net ~= sum(engine.ce_net)`
3. `global_selected_count == sum(selected_count by state partition logic)` from the same DTR set
4. `global_executed_count == sum(executed state count from DTRs)`
5. `global_hard_blocked_count`, `rejected_ranking_count`, `phantom_count` remain exclusive and bounded by `total_records`

Note:
- use tolerance-aware assertions for `ce_net` if per-group rounding at 6 decimals can accumulate

### CE with blocked records
6. replay metrics with one executed and one hard-blocked record prove:
   - blocked record may still contribute `ce_expected`
   - `ce_net` is expected CE, not realized CE

### Cost separation
7. replay metrics prove:
   - `expected_cost_mean` is all-record ex-ante mean
   - `realized_cost_mean` is all-record realized replay-fill mean
   - non-executed records can have `realized_cost == 0.0`

### Exec-rate denominator
8. direct unit test on `ReplayMetricsSnapshot.exec_rate` proving:
   - denominator is `total_records`
   - `0.0` is returned when `total_records == 0`
9. direct unit test on `state_run_comparison._exec_rate` with same semantics

### Cockpit false-green
10. state-level test proving zero-record replay snapshots are classified as non-measured in future cockpit/state patch
11. denominator-label test for any future replay metric view-model

## Wave 2 test verdict
- Reconciliation and replay-source integrity are already strongly validated by the bridge.
- Exact pair/engine/global economics reconciliation still deserves explicit tests.
- The highest-value missing tests are:
  - `exec_rate` denominator
  - CE semantics with blocked records
  - tolerance-based aggregate reconciliation
