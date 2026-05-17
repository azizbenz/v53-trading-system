# Wave 2 Cost Formula Audit

## Ex-ante cost

### Source
- `src/local_replay_runtime/shadow_execution_simulator.py::_expected_cost`

### Implemented formula
- `expected_cost = (spread_bps + slippage_bps * slippage_multiplier + latency_penalty_bps * latency_penalty_multiplier) / 10_000.0`

### Verdict
- `MATCH_INTERNAL_CONVENTION`
- Clear ex-ante cost seam

### Notes
- Ex-ante expected cost includes:
  - spread
  - slippage assumption
  - latency penalty
- No explicit fee term is visible in this replay simulator seam.
- No explicit market-impact or partial-fill penalty term is separated here.

## Realized cost

### Source
- `src/local_replay_runtime/shadow_execution_simulator.py::simulate_shadow_compatible_dtrs`

### Implemented formula
- `realized_cost = expected_cost * execution_factor`

### Verdict
- `MATCH_INTERNAL_CONVENTION`
- Realized replay cost is a replay-fill realization of the ex-ante cost model, not a venue-native fill ledger

### Notes
- `execution_factor` is:
  - `0.0` for blocked / rejected / evaluated / phantom
  - `fill_ratio` for reduced
  - `1.0` for executed
- This means non-executed records often contribute `0.0` realized cost.
- That is valid under the current replay convention, but it means `realized_cost_mean` is an all-record replay artifact, not an executed-only cost statistic.

## Replay summary means

### Source
- `src/local_replay_runtime/replay_metrics_collector.py`

### Implemented formulas
- `expected_cost_mean = mean(record.expected_cost for record in records)`
- `realized_cost_mean = mean(record.realized_cost for record in records)`

### Verdict
- `MATCH_INTERNAL_CONVENTION`

### Risk
- Comparing `realized_cost_mean` to `expected_cost_mean` at replay-summary level is mathematically valid, but economically coarse because:
  - non-executed records keep expected cost
  - non-executed records often get zero realized cost
- This can understate executed-only realized-vs-expected drift when sample mix shifts.

## Cost drift

### Realized point drift
- Source:
  - `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
- Formula:
  - `cost_drift = realized_cost - expected_cost`
- Verdict:
  - `MATCH_STANDARD_FORMULA`

### Mean drift monitor
- Source:
  - `src/meta_minimal/cost_drift_monitor/monitor.py`
- Formula:
  - `bias_pct = (mean_realised - mean_expected) / mean_expected`
- Preconditions:
  - `expected_cost > 0`
  - minimum sample count
- Verdict:
  - `MATCH_STANDARD_FORMULA`

## Presence of fee / slippage / impact / partial-fill penalty
| Component | Producer evidence | Status |
|---|---|---|
| Spread | `_expected_cost` uses `row.spread_bps` | `IMPLEMENTED_AND_WIRED` |
| Slippage | `_expected_cost` uses `row.slippage_bps * slippage_multiplier` | `IMPLEMENTED_AND_WIRED` |
| Latency penalty | `_expected_cost` uses `row.latency_penalty_bps * latency_penalty_multiplier` | `IMPLEMENTED_AND_WIRED` |
| Fees | no explicit fee term in replay simulator seam | `HUMAN_DECISION_REQUIRED` |
| Impact | no explicit separate impact term in replay simulator seam | `HUMAN_DECISION_REQUIRED` |
| Partial-fill penalty | partial fills reduce `realized_cost` through `execution_factor`; no separate penalty field | `CONSERVATIVE_VARIANT_UNDOCUMENTED` |

## Ex-ante vs realized separation
- The repo does separate:
  - ex-ante expected cost
  - realized cost
  - realized break-even drift
- The ambiguity is not formula collision.
- The ambiguity is that replay summary means are not executed-only economics views.

## Wave 2 verdict
- No confirmed mismatch in producer formulas.
- No Wave 2 producer patch recommended.
- Future policy/display work should separate:
  - all-record replay means
  - executed-only realized economics
  - drift-monitor results
