# Wave 2 Exec Rate and Block Rate Audit

## `exec_rate`

### Implemented cockpit formula
- `src/cockpit/state_replay_metrics.py::ReplayMetricsSnapshot.exec_rate`
- `src/cockpit/state_run_comparison.py::_exec_rate`

```text
exec_rate = executed_count / total_records
```

### Current denominator
- `total_records`

### Current meaning
- Opportunity-level or replay-record-level execution rate.
- Under current code, this is not selected-only execution success.

### Evidence for internal convention
- `state_replay_metrics.py` uses `total_records`
- `state_run_comparison.py` uses `total_records`
- `artifact_ablation_study.py::_block_rate` uses `1 - executed_count / len(records)`
- no producer-side `exec_rate` field contradicts this

### Conflict
- `docs/backtest/V5_3_CODEX_BACKTEST_DASHBOARD_MATH_VERIFIED_SPEC.md` documents:

```text
exec_rate = executed_count / max(selected_count, 1)
```

### Wave 2 classification
- Code truth: `MATCH_INTERNAL_CONVENTION`
- Cross-doc doctrine: `HUMAN_DECISION_REQUIRED`
- Confirmed producer mismatch: `NO`

### Safe naming recommendation
- Current implemented metric should be named or labeled as:
  - `exec_rate_total`
  - or `opportunity_execution_rate`
- If selected-only semantics are desired later, add a separate metric:
  - `selected_execution_rate = executed_count / max(selected_count, 1)`

## `block_rate`

### Replay summary
- There is no top-level `block_rate` field in `ReplayMetricsSummary`.
- The replay summary exposes counts:
  - `hard_blocked_count`
  - `rejected_ranking_count`
  - `phantom_count`
  - `selected_count`
  - `executed_count`

### Ablation block-rate seam
- `src/local_replay_runtime/artifact_ablation_study.py::_block_rate`

```text
block_rate = 1 - executed_count / len(records)
```

### Current meaning
- This is a non-executed-rate proxy over aligned ablation records.
- It is not a pure hard-block rate.
- It can include:
  - hard blocks
  - ranking rejects
  - phantoms
  - evaluated/no-trade states

### Wave 2 classification
- `CONSERVATIVE_VARIANT_DOCUMENTED`
- No confirmed mismatch

## State exclusivity / double-count risk
- DTR records have one `decision_state`.
- Therefore:
  - `hard_blocked_count`
  - `rejected_ranking_count`
  - `phantom_count`
  are mutually exclusive at record level.
- `selected_count` is not exclusive with `phantom` by semantic history:
  - selected states are defined as `{SELECTED, REDUCED, PHANTOM, EXECUTED}`
- `block_rate` as currently derived in ablation is not built from the explicit block-class counts, so it is not a pure “hard block” fraction.

## Denominator recommendations
| Metric | Recommended explicit name | Formula |
|---|---|---|
| Current replay cockpit exec rate | `exec_rate_total` | `executed_count / total_records` |
| Possible future selected-only execution rate | `selected_execution_rate` | `executed_count / max(selected_count, 1)` |
| Current ablation block proxy | `non_execution_rate` or `block_rate_proxy` | `1 - executed_count / aligned_record_count` |
| Possible future hard block rate | `hard_block_rate` | `hard_blocked_count / total_records` |

## Wave 2 verdict
- No code patch recommended.
- Current formulas are internally coherent.
- The unresolved issue is naming and display labeling, not a confirmed replay-math bug.
