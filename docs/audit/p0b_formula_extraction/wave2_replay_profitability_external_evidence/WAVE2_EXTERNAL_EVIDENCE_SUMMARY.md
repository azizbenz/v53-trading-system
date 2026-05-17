# Wave 2 External Evidence Summary

## Role boundary
- `EVIDENCE_EXTRACTED`
- This pack does not mark any replay/profitability metric as finally scientifically approved.
- This pack does not mark any replay/profitability metric as finally mismatched.
- This pack is for external quant audit review.

## Files inspected
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/artifact_exporter.py`
- `src/local_replay_runtime/artifact_ablation_study.py`
- `src/backtest_artifact_import/export_dir_bridge_support.py`
- `src/meta_minimal/dtr_core/dtr_record_builder.py`
- `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
- `src/meta_minimal/cost_drift_monitor/monitor.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_run_comparison.py`
- `src/cockpit/state_decision_trace.py`
- `src/cockpit/state_freshness.py`
- `src/cockpit/templates/partials/_replay_metrics.html`
- relevant tests under `tests/test_local_replay_runtime`, `tests/test_backtest_artifact_import`, `tests/cockpit`, `tests/test_meta_minimal`

## Metric evidence ledger

### `ce_expected`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `EXPECTED_REALIZED_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `simulate_shadow_compatible_dtrs`
- Exact code excerpt:
```python
ce_expected=round((row.expected_edge_bps / 10_000.0) - expected_cost, 6),
```
- Plain-text formula:
  - expected edge in return fraction minus expected cost
- Inputs:
  - `row.expected_edge_bps`
  - `expected_cost`
- Output field:
  - `DTRRecord.ce_expected`
- Units:
  - `fraction`
- Denominator:
  - none
- Scope:
  - `per-record`
- Gross/net semantics:
  - net of expected cost
- Expected/realized/simulated/report semantics:
  - expected
  - simulated replay record field
- Blocked/rejected/phantom included:
  - yes, because the field is populated regardless of final execution factor
- Non-executed records contribute non-zero expected values:
  - yes
- Non-executed records contribute zero realized values:
  - not directly applicable to `ce_expected`; see `realized_cost`
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states`
- Consumers:
  - replay report: `CONSUMER_FOUND` via `ce_net` aggregation
  - cockpit: `CONSUMER_FOUND` via `state_decision_trace.py`
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_FOUND` via `_ce_mean` in `artifact_ablation_study.py`
  - shadow comparison: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
- False-green risk:
  - row-level cockpit adapter renames `ce_expected` to `ce_net`
- Ambiguities found:
  - row label says `ce_net`, source field is `ce_expected`
- External-audit questions:
  - should row-level cockpit naming expose `ce_expected` explicitly instead of `ce_net`

### `ce_net`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
ce_net=round(sum(record.ce_expected for record in records), 6),
```
- Plain-text formula:
  - sum of per-record expected CE values
- Inputs:
  - `record.ce_expected`
- Output field:
  - `ReplayMetricsSummary.ce_net`
- Units:
  - `fraction`
- Denominator:
  - none
- Scope:
  - `global`
  - pair and engine variants are computed analogously
- Gross/net semantics:
  - net of expected cost, not net of realized cost
- Expected/realized/simulated/report semantics:
  - expected
  - replay-derived report value
- Blocked/rejected/phantom included:
  - yes, all DTR records are included
- Non-executed records contribute non-zero expected values:
  - yes, if `ce_expected` is non-zero
- Non-executed records contribute zero realized values:
  - yes for realized cost, not for `ce_net`
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py::test_build_replay_metrics_summary_aggregates_pairs_engines_and_drawdown`
  - `tests/test_backtest_artifact_import/test_export_dir_bridge.py::test_discover_local_replay_export_rejects_metrics_summary_drift_from_dtr`
- Consumers:
  - replay report: `CONSUMER_FOUND` via `replay_executor._review_markdown`
  - cockpit: `CONSUMER_FOUND` via `state_replay_metrics.py`, `state_economic_sterilization.py`, template
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_NOT_FOUND` directly; local lab uses `ce_expected` means
  - shadow comparison: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
- False-green risk:
  - numeric default `0.0`
  - positive color if `>= 0`
- Ambiguities found:
  - expected CE can be mistaken for realized profitability
- External-audit questions:
  - should replay cockpit rename this to `expected_ce_net`

### `gross_return`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `simulate_shadow_compatible_dtrs`
- Exact code excerpt:
```python
gross_return = round((row.gross_return_bps / 10_000.0) * execution_factor, 6)
```
- Plain-text formula:
  - gross return in bps converted to fraction and scaled by execution factor
- Inputs:
  - `row.gross_return_bps`
  - `execution_factor`
- Output field:
  - `DTRRecord.gross_return`
- Units:
  - `fraction`
- Denominator:
  - none
- Scope:
  - `per-record`
- Gross/net semantics:
  - gross, before realized cost
- Expected/realized/simulated/report semantics:
  - simulated realized replay output
- Blocked/rejected/phantom included:
  - yes as records, but with `execution_factor = 0.0` they contribute zero
- Non-executed records contribute non-zero expected values:
  - not applicable
- Non-executed records contribute zero realized values:
  - yes
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states`
- Consumers:
  - replay report: `CONSUMER_FOUND` via `gross_return_total`
  - cockpit: `CONSUMER_FOUND` via `gross_return_mean` display
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_FOUND` via `_net_pnl`
  - shadow comparison: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
- False-green risk:
  - gross can be mistaken for net profitability
- Ambiguities found:
  - none in formula, only display interpretation
- External-audit questions:
  - should gross replay returns always be paired with realized-cost context on display

### `expected_cost`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `EXPECTED_REALIZED_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `_expected_cost`
- Exact code excerpt:
```python
return (
    row.spread_bps
    + row.slippage_bps * config.slippage_multiplier
    + row.latency_penalty_bps * config.latency_penalty_multiplier
) / 10_000.0
```
- Plain-text formula:
  - spread plus slippage plus latency penalty, converted from bps to fraction
- Inputs:
  - `row.spread_bps`
  - `row.slippage_bps`
  - `config.slippage_multiplier`
  - `row.latency_penalty_bps`
  - `config.latency_penalty_multiplier`
- Output field:
  - `expected_cost`
  - then `DTRRecord.expected_cost`
- Units:
  - `fraction`
- Denominator:
  - `10_000`
- Scope:
  - `per-record`
- Gross/net semantics:
  - cost term
- Expected/realized/simulated/report semantics:
  - expected
  - simulated replay cost model
- Blocked/rejected/phantom included:
  - yes, per-record expected cost exists even for non-executed outcomes
- Non-executed records contribute non-zero expected values:
  - yes
- Non-executed records contribute zero realized values:
  - not for expected cost
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND` via expected cost means
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_FOUND` in cost drift / loss surrogate / edge calibration pathways
  - shadow comparison: `CONSUMER_FOUND` via parity `mean_cost_gap`
- False-green risk:
  - all-record means can be mistaken for executed-only economics
- Ambiguities found:
  - no explicit fee term
  - no explicit separate impact term
- External-audit questions:
  - are fees and impact intentionally absent from this replay seam

### `realized_cost`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `EXPECTED_REALIZED_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `simulate_shadow_compatible_dtrs`
- Exact code excerpt:
```python
realized_cost=round(expected_cost * execution_factor, 6),
```
- Plain-text formula:
  - expected cost scaled by execution factor
- Inputs:
  - `expected_cost`
  - `execution_factor`
- Output field:
  - `DTRRecord.realized_cost`
- Units:
  - `fraction`
- Denominator:
  - none
- Scope:
  - `per-record`
- Gross/net semantics:
  - cost term
- Expected/realized/simulated/report semantics:
  - simulated realized replay cost
- Blocked/rejected/phantom included:
  - yes as records
- Non-executed records contribute non-zero expected values:
  - yes, on `expected_cost`
- Non-executed records contribute zero realized values:
  - yes
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states`
- Consumers:
  - replay report: `CONSUMER_FOUND` via realized-cost mean
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_FOUND` via `_net_pnl`
  - shadow comparison: `CONSUMER_NOT_FOUND` directly
- False-green risk:
  - zero realized cost on non-executed records can look like “cheap trading” in mean form
- Ambiguities found:
  - realized replay cost is model-based, not venue-native fill ledger evidence
- External-audit questions:
  - should replay display differentiate executed-only realized costs from all-record realized-cost means

### `cost_drift`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
  - `src/meta_minimal/cost_drift_monitor/monitor.py`
- Function/class:
  - `compute_realized_break_even`
  - `CostDriftMonitor.evaluate`
- Exact code excerpt:
```python
cost_drift=realized_cost - expected_cost,
```
```python
bias_pct = (mean_realised - mean_expected) / mean_expected
```
- Plain-text formula:
  - point drift = realized minus expected
  - monitor drift = normalized mean realized minus mean expected
- Inputs:
  - `realized_cost`
  - `expected_cost`
  - monitor sample list
- Output field:
  - `RealizedBreakEven.cost_drift`
  - `CostDriftResult.bias_pct`
- Units:
  - point drift: `fraction`
  - monitor drift: `ratio`
- Denominator:
  - monitor uses `mean_expected`
- Scope:
  - `per-record`
  - per-monitor evaluation scope
- Gross/net semantics:
  - cost delta
- Expected/realized/simulated/report semantics:
  - realized-vs-expected
- Blocked/rejected/phantom included:
  - point calculator can accept any inputs; monitor requires positive expected cost samples
- Non-executed records contribute non-zero expected values:
  - possible if passed in
- Non-executed records contribute zero realized values:
  - possible if passed in
- Tests covering behavior:
  - `tests/test_meta_minimal/test_cost_drift_monitor.py`
  - `tests/test_meta_minimal/test_break_even_dashboard_minimal.py`
- Consumers:
  - replay report: `CONSUMER_NOT_FOUND`
  - cockpit: `CONSUMER_NOT_FOUND` directly on replay page
  - promotion: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
  - local lab: `CONSUMER_FOUND` via proof summary / meta runtime family
  - shadow comparison: `CONSUMER_NOT_FOUND` in inspected Wave 2 scope
- False-green risk:
  - not a replay-page metric currently
- Ambiguities found:
  - replay summary does not surface true cost drift directly
- External-audit questions:
  - should replay economics eventually expose executed-only cost drift explicitly

### `exec_rate`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `DENOMINATOR_AMBIGUITY`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/cockpit/state_replay_metrics.py`
  - `src/cockpit/state_run_comparison.py`
- Function/class:
  - `ReplayMetricsSnapshot.exec_rate`
  - `_exec_rate`
- Exact code excerpt:
```python
if self.total_records == 0:
    return 0.0
return self.executed_count / self.total_records
```
```python
if total_records <= 0:
    return 0.0
return float(payload.get("executed_count", 0) or 0) / float(total_records)
```
- Plain-text formula:
  - executed records divided by total records
- Inputs:
  - `executed_count`
  - `total_records`
- Output field:
  - `ReplayMetricsSnapshot.exec_rate`
  - run comparison transition input
- Units:
  - `ratio`
- Denominator:
  - `total_records`
- Scope:
  - `cockpit-derived`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay report-derived view metric
- Blocked/rejected/phantom included:
  - in denominator through `total_records`
- Non-executed records contribute non-zero expected values:
  - not applicable
- Non-executed records contribute zero realized values:
  - not applicable
- Tests covering behavior:
  - `tests/cockpit/test_state_run_comparison.py`
  - indirect through `tests/cockpit/test_state_economic_sterilization.py`
- Consumers:
  - replay report: `CONSUMER_NOT_FOUND`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - denominator not labeled in template
  - zero-record case returns `0.0`
- Ambiguities found:
  - conflicting dashboard spec uses `selected_count` denominator
- External-audit questions:
  - should this be renamed `exec_rate_total`

### `selected_count`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
selected_states = {
    DecisionState.SELECTED,
    DecisionState.REDUCED,
    DecisionState.PHANTOM,
    DecisionState.EXECUTED,
}
selected_count=sum(
    1 for record in records if record.decision_state in selected_states
),
```
- Plain-text formula:
  - count records in selected, reduced, phantom, or executed states
- Inputs:
  - `record.decision_state`
- Output field:
  - `ReplayMetricsSummary.selected_count`
- Units:
  - `raw count`
- Denominator:
  - none
- Scope:
  - `global`
  - pair / engine variants use same logic
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay-derived report count
- Blocked/rejected/phantom included:
  - phantom yes
  - hard blocked and ranking rejected no
- Non-executed records contribute non-zero expected values:
  - possible elsewhere, but count logic is separate
- Non-executed records contribute zero realized values:
  - possible elsewhere
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py`
  - bridge mismatch tests
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - selected can include phantom
- Ambiguities found:
  - “selected” is broader than “executed”
- External-audit questions:
  - should phantom remain inside selected_count for operator-facing economics

### `executed_count`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
executed_count=sum(
    1 for record in records if record.decision_state == DecisionState.EXECUTED
),
```
- Plain-text formula:
  - count executed records
- Inputs:
  - `record.decision_state`
- Output field:
  - `ReplayMetricsSummary.executed_count`
- Units:
  - `raw count`
- Denominator:
  - none
- Scope:
  - `global`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay-derived report count
- Blocked/rejected/phantom included:
  - no
- Non-executed records contribute non-zero expected values:
  - not applicable
- Non-executed records contribute zero realized values:
  - not applicable
- Tests covering behavior:
  - bridge validation family
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_FOUND` in ablation
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - indirectly affects unlabeled `exec_rate`
- Ambiguities found:
  - none in count definition
- External-audit questions:
  - none beyond exec-rate denominator naming

### `hard_blocked_count`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
hard_blocked_count=sum(
    1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED
),
```
- Plain-text formula:
  - count hard-blocked records
- Inputs:
  - `record.decision_state`
- Output field:
  - `ReplayMetricsSummary.hard_blocked_count`
- Units:
  - `raw count`
- Denominator:
  - none
- Scope:
  - `global`
  - engine aggregate variant exists
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay-derived report count
- Blocked/rejected/phantom included:
  - only hard blocked
- Non-executed records contribute non-zero expected values:
  - yes elsewhere
- Non-executed records contribute zero realized values:
  - yes elsewhere
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py`
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - none direct
- Ambiguities found:
  - none
- External-audit questions:
  - none

### `rejected_ranking_count`
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
rejected_ranking_count=sum(
    1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING
),
```
- Plain-text formula:
  - count ranking-rejected records
- Inputs:
  - `record.decision_state`
- Output field:
  - `ReplayMetricsSummary.rejected_ranking_count`
- Units:
  - `raw count`
- Denominator:
  - none
- Scope:
  - `global`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay-derived report count
- Blocked/rejected/phantom included:
  - only ranking-rejected
- Non-executed records contribute non-zero expected values:
  - yes elsewhere
- Non-executed records contribute zero realized values:
  - yes elsewhere
- Tests covering behavior:
  - bridge consistency tests cover serialized field integrity
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND` through snapshot
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - none direct
- Ambiguities found:
  - low direct test coverage
- External-audit questions:
  - should a direct replay metrics unit test pin this count explicitly

### `phantom_count`
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
phantom_count=sum(
    1 for record in records if record.decision_state == DecisionState.PHANTOM
),
```
- Plain-text formula:
  - count phantom records
- Inputs:
  - `record.decision_state`
- Output field:
  - `ReplayMetricsSummary.phantom_count`
- Units:
  - `raw count`
- Denominator:
  - none
- Scope:
  - `global`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - replay-derived report count
- Blocked/rejected/phantom included:
  - only phantom
- Non-executed records contribute non-zero expected values:
  - yes elsewhere
- Non-executed records contribute zero realized values:
  - yes elsewhere
- Tests covering behavior:
  - bridge validation family covers schema/consistency
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND` through snapshot
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - phantom still contributes to selected_count
- Ambiguities found:
  - phantom semantics affect selected-count interpretation
- External-audit questions:
  - should operator views separate selected-from-executed more explicitly

### `block_rate / non_execution_rate`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `DENOMINATOR_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/artifact_ablation_study.py`
- Function/class:
  - `_block_rate`
- Exact code excerpt:
```python
if not records:
    return 1.0
executed_count = sum(1 for record in records if record.decision_state == "executed")
return max(0.0, min(1.0, 1.0 - (executed_count / len(records))))
```
- Plain-text formula:
  - one minus executed fraction over aligned records
- Inputs:
  - `record.decision_state`
  - `len(records)`
- Output field:
  - `_block_rate`
  - then `candidate_block_rate`, `baseline_block_rate`, `block_rate_delta`
- Units:
  - `ratio`
- Denominator:
  - `len(records)` on aligned ablation records
- Scope:
  - candidate / baseline / delta
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - local-lab ablation metric
- Blocked/rejected/phantom included:
  - yes, all non-executed records affect the metric
- Non-executed records contribute non-zero expected values:
  - possible elsewhere, not part of formula
- Non-executed records contribute zero realized values:
  - possible elsewhere, not part of formula
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_artifact_ablation_study.py`
- Consumers:
  - replay report: `CONSUMER_NOT_FOUND`
  - cockpit: `CONSUMER_NOT_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - name `block_rate` can be read as pure hard-block rate, but denominator is all aligned records
- Ambiguities found:
  - it is closer to non-execution rate than hard-block rate
- External-audit questions:
  - should future naming use `non_execution_rate` or `block_rate_proxy`

### `drawdown_proxy`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `GROSS_NET_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `_drawdown_proxy`
- Exact code excerpt:
```python
running += record.gross_return
peak = max(peak, running)
worst = min(worst, running - peak)
return abs(worst)
```
- Plain-text formula:
  - cumulative gross-return path, then worst peak-to-trough loss magnitude
- Inputs:
  - `record.gross_return`
- Output field:
  - `drawdown_proxy`
- Units:
  - `fraction`
- Denominator:
  - none
- Scope:
  - `global`
- Gross/net semantics:
  - gross-return path, not net equity
- Expected/realized/simulated/report semantics:
  - replay-derived report value
- Blocked/rejected/phantom included:
  - yes, through their gross-return contribution, often zero
- Non-executed records contribute non-zero expected values:
  - not relevant
- Non-executed records contribute zero realized values:
  - often yes through zero gross return
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py`
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND` in inspected scope
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - numeric display without extra proxy caveat
- Ambiguities found:
  - not a true max drawdown on net equity curve
- External-audit questions:
  - should any promotion logic ever consume this proxy

### `pair_aggregates`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
pair_aggregates = tuple(
    ReplayPairAggregate(
        pair=pair,
        record_count=len(group),
        selected_count=sum(1 for record in group if record.decision_state in selected_states),
        ce_net=round(sum(record.ce_expected for record in group), 6),
        expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
        realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
        gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
    )
    for pair, group in sorted(pair_groups.items())
)
```
- Plain-text formula:
  - partition records by pair and compute scoped counts and means
- Inputs:
  - grouped DTR records by pair
- Output field:
  - `ReplayMetricsSummary.pair_aggregates`
- Units:
  - mixed composite values
- Denominator:
  - counts: none
  - means: all records in pair group
- Scope:
  - `pair`
- Gross/net semantics:
  - same semantics as component metrics
- Expected/realized/simulated/report semantics:
  - replay-derived report aggregates
- Blocked/rejected/phantom included:
  - yes, according to each component metric
- Non-executed records contribute non-zero expected values:
  - yes to `ce_net` and expected-cost mean
- Non-executed records contribute zero realized values:
  - yes to realized-cost mean
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py`
  - `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
- Consumers:
  - replay report: `CONSUMER_FOUND` through `replay_metrics.json`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - pair rows with `record_count == 0` can still exist in some seeded fixtures elsewhere
- Ambiguities found:
  - rounded pair sums may not equal global sums exactly at floating precision
- External-audit questions:
  - should reconciliation be tolerance-based at the CE field level

### `engine_aggregates`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function/class:
  - `build_replay_metrics_summary`
- Exact code excerpt:
```python
engine_aggregates = tuple(
    ReplayEngineAggregate(
        engine_id=engine_id,
        record_count=len(group),
        selected_count=sum(1 for record in group if record.decision_state in selected_states),
        hard_blocked_count=sum(
            1 for record in group if record.decision_state == DecisionState.HARD_BLOCKED
        ),
        ce_net=round(sum(record.ce_expected for record in group), 6),
        expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
        realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
        gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
    )
    for engine_id, group in sorted(engine_groups.items())
)
```
- Plain-text formula:
  - partition records by engine and compute scoped counts and means
- Inputs:
  - grouped DTR records by engine
- Output field:
  - `ReplayMetricsSummary.engine_aggregates`
- Units:
  - mixed composite values
- Denominator:
  - counts: none
  - means: all records in engine group
- Scope:
  - `engine`
- Gross/net semantics:
  - same semantics as component metrics
- Expected/realized/simulated/report semantics:
  - replay-derived report aggregates
- Blocked/rejected/phantom included:
  - yes, according to each component metric
- Non-executed records contribute non-zero expected values:
  - yes to `ce_net`
- Non-executed records contribute zero realized values:
  - yes to realized-cost mean
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_replay_executor.py`
  - `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
- Consumers:
  - replay report: `CONSUMER_FOUND` through `replay_metrics.json`
  - cockpit: `CONSUMER_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_NOT_FOUND`
  - shadow comparison: `CONSUMER_NOT_FOUND`
- False-green risk:
  - engine rows may show `0.0` defaults when no records exist
- Ambiguities found:
  - rounded engine sums may not equal global sums exactly at floating precision
- External-audit questions:
  - should future reconciliation tests assert CE with tolerance

### `decision_match_rate`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `build_parity_diagnostics_payload`
- Exact code excerpt:
```python
decision_match_rate = (
    round_float64(decision_matches / decision_compared, 6)
    if decision_compared
    else 0.0
)
```
- Plain-text formula:
  - matched decisions divided by compared baseline records
- Inputs:
  - `decision_matches`
  - `decision_compared`
- Output field:
  - `ReplayParityDiagnosticsSummary.decision_match_rate`
- Units:
  - `ratio`
- Denominator:
  - `decision_compared`
- Scope:
  - `global`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - parity diagnostic report value
- Blocked/rejected/phantom included:
  - only if baseline state exists for those records
- Non-executed records contribute non-zero expected values:
  - not relevant
- Non-executed records contribute zero realized values:
  - not relevant
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_build_parity_diagnostics_payload_reports_ok_when_baselines_match`
- Consumers:
  - replay report: `CONSUMER_FOUND`
  - cockpit: `CONSUMER_NOT_FOUND` direct in inspected scope
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_FOUND` through export consumers
  - shadow comparison: `CONSUMER_FOUND`
- False-green risk:
  - `0.0` when no compared records can be misread without baseline-status context
- Ambiguities found:
  - baseline sufficiency must be read with `baseline_status`
- External-audit questions:
  - should decision parity displays require explicit baseline sufficiency badge

### `score_match_rate`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `build_parity_diagnostics_payload`
- Exact code excerpt:
```python
score_match_rate = (
    round_float64(score_matches / score_compared, 6) if score_compared else 0.0
)
```
- Plain-text formula:
  - score matches divided by compared baseline scores
- Inputs:
  - `score_matches`
  - `score_compared`
- Output field:
  - `ReplayParityDiagnosticsSummary.score_match_rate`
- Units:
  - `ratio`
- Denominator:
  - `score_compared`
- Scope:
  - `global`
- Gross/net semantics:
  - not applicable
- Expected/realized/simulated/report semantics:
  - parity diagnostic report value
- Blocked/rejected/phantom included:
  - if score baseline exists
- Non-executed records contribute non-zero expected values:
  - not relevant
- Non-executed records contribute zero realized values:
  - not relevant
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`
- Consumers:
  - replay report: `CONSUMER_NOT_FOUND` in markdown excerpt
  - cockpit: `CONSUMER_NOT_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_FOUND` through export consumers
  - shadow comparison: `CONSUMER_FOUND`
- False-green risk:
  - same baseline sufficiency issue as decision parity
- Ambiguities found:
  - none in formula; interpretation depends on tolerance policy
- External-audit questions:
  - should score parity always be shown together with tolerance configuration

### `mean_cost_gap`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `EXPECTED_REALIZED_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function/class:
  - `build_parity_diagnostics_payload`
- Exact code excerpt:
```python
if row.production_expected_cost is not None:
    cost_compared += 1
    cost_diffs.append(abs(row.production_expected_cost - record.expected_cost))

mean_cost_gap = (
    round_float64(sum(cost_diffs) / len(cost_diffs), 6) if cost_diffs else 0.0
)
```
- Plain-text formula:
  - mean absolute gap between production expected cost and replay expected cost
- Inputs:
  - `row.production_expected_cost`
  - `record.expected_cost`
- Output field:
  - `ReplayParityDiagnosticsSummary.mean_cost_gap`
- Units:
  - `fraction`
- Denominator:
  - `len(cost_diffs)`
- Scope:
  - `global`
- Gross/net semantics:
  - cost gap
- Expected/realized/simulated/report semantics:
  - expected-vs-expected parity diagnostic, not realized drift
- Blocked/rejected/phantom included:
  - only if baseline expected cost exists
- Non-executed records contribute non-zero expected values:
  - yes, if compared
- Non-executed records contribute zero realized values:
  - irrelevant to this metric
- Tests covering behavior:
  - `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`
- Consumers:
  - replay report: `CONSUMER_NOT_FOUND` directly in review markdown excerpt
  - cockpit: `CONSUMER_NOT_FOUND`
  - promotion: `CONSUMER_NOT_FOUND`
  - local lab: `CONSUMER_FOUND` through parity artifact consumers
  - shadow comparison: `CONSUMER_FOUND`
- False-green risk:
  - can be confused with realized cost drift
- Ambiguities found:
  - it is an ex-ante parity cost gap, not realized execution drift
- External-audit questions:
  - should parity cost gap naming explicitly include `expected`
