# Wave 2 Test Coverage Evidence

## Coverage summary
- `EVIDENCE_EXTRACTED`
- Tests prove:
  - replay summary generation
  - replay export serialization
  - bridge consistency and fail-closed checks
  - parity diagnostic basics
  - cockpit replay consumer loading
  - cost drift monitor behavior
- Tests do not fully prove:
  - explicit CE reconciliation equality across pair/engine/global
  - explicit `exec_rate` denominator naming doctrine
  - explicit count ordering invariants

## Metric-to-test map
| Metric | Test files | Evidence status | Notes |
|---|---|---|---|
| `ce_expected` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`, `tests/cockpit/test_state_decision_trace.py` | `TEST_COVERED` | simulator populates record fields; decision trace loads `ce_expected` into cockpit row |
| `ce_net` | `tests/test_local_replay_runtime/test_replay_executor.py`, `tests/test_backtest_artifact_import/test_export_dir_bridge.py` | `TEST_COVERED` | summary CE value pinned on small fixture and bridge consistency enforced |
| `gross_return` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | execution states imply zero/non-zero gross paths |
| `expected_cost` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | parity/cost alignment and DTR production |
| `realized_cost` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | reduced > 0, hard-blocked == 0 |
| `cost_drift` | `tests/test_meta_minimal/test_cost_drift_monitor.py`, `tests/test_meta_minimal/test_break_even_dashboard_minimal.py` | `TEST_COVERED` | point drift and normalized drift monitor |
| `exec_rate` | `tests/cockpit/test_state_run_comparison.py`, `tests/cockpit/test_state_economic_sterilization.py` | `TEST_COVERED` but indirect | no direct dedicated unit test on `ReplayMetricsSnapshot.exec_rate` |
| `selected_count` | `tests/test_local_replay_runtime/test_replay_executor.py` | `TEST_COVERED` | small fixture pinned |
| `executed_count` | bridge and cockpit fixture tests | `TEST_COVERED` but indirect | no dedicated standalone replay metrics unit assertion |
| `hard_blocked_count` | `tests/test_local_replay_runtime/test_replay_executor.py` | `TEST_COVERED` | small fixture pinned |
| `rejected_ranking_count` | `tests/test_backtest_artifact_import/test_export_dir_bridge.py` | `TEST_COVERED` at payload consistency level | no dedicated standalone assertion |
| `phantom_count` | bridge payload consistency tests | `TEST_COVERED` at payload consistency level | no dedicated standalone assertion |
| `block_rate / non_execution_rate` | `tests/test_local_replay_runtime/test_artifact_ablation_study.py` | `TEST_COVERED` | ablation study logic |
| `drawdown_proxy` | `tests/test_local_replay_runtime/test_replay_executor.py` | `TEST_COVERED` | only non-negative property, not path-identity precision |
| `pair_aggregates` | `tests/test_local_replay_runtime/test_replay_executor.py`, `tests/test_backtest_artifact_import/test_export_dir_bridge.py` | `TEST_COVERED` | structure and bridge consistency |
| `engine_aggregates` | `tests/test_local_replay_runtime/test_replay_executor.py`, `tests/test_backtest_artifact_import/test_export_dir_bridge.py` | `TEST_COVERED` | structure and bridge consistency |
| `decision_match_rate` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | exact 1.0 anchor and warning path |
| `score_match_rate` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | baseline/tolerance behavior |
| `mean_cost_gap` | `tests/test_local_replay_runtime/test_shadow_execution_simulator.py` | `TEST_COVERED` | parity cost alignment behavior |

## Exact evidence snippets

### Replay summary
```python
assert summary.total_records == 2
assert summary.selected_count == 1
assert summary.hard_blocked_count == 1
assert summary.ce_net == 0.0005
assert summary.drawdown_proxy >= 0.0
```

### Simulator realized-cost behavior
```python
assert records[1].realized_cost > 0.0
assert records[2].realized_cost == 0.0
```

### Bridge fail-closed behavior
```python
with pytest.raises(
    ValueError,
    match="governed export replay_metrics must stay consistent with replay_dtr records",
):
    discover_local_replay_export(export_dir)
```

### Cockpit thin sample
```python
assert snapshot.economic_sterilization_ratio == 0.8
assert snapshot.status == "insufficient_sample"
```

### Cost drift monitor
```python
assert result.bias_pct == pytest.approx(0.30)
assert result.reason == "alert_bias_exceeded"
```

## Test gaps relevant to external audit
- `AMBIGUITY_FOUND`
- No direct unit test proving:
  - `ReplayMetricsSnapshot.exec_rate` denominator semantics in isolation
  - `sum(pair.ce_net)` equals global CE within tolerance
  - `sum(engine.ce_net)` equals global CE within tolerance
  - `executed_count <= selected_count <= total_records`
  - exclusivity of hard-blocked / rejected-ranking / phantom on a dedicated mixed-state fixture

## External audit questions
1. Which missing tests are mandatory before any scientific sign-off on replay economics?
2. Should aggregate-reconciliation tests use exact equality or tolerance because of per-group rounding?
