# Wave 2 Cost Source Evidence

## Expected cost components
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function:
  - `_expected_cost`
- Exact code excerpt:
```python
return (
    row.spread_bps
    + row.slippage_bps * config.slippage_multiplier
    + row.latency_penalty_bps * config.latency_penalty_multiplier
) / 10_000.0
```
- Inputs:
  - `spread_bps`
  - `slippage_bps`
  - `latency_penalty_bps`
  - configured multipliers
- Output:
  - `expected_cost`
- Units:
  - `fraction`
- Denominator:
  - `10_000`
- Semantics:
  - expected
  - simulated replay cost

## Fee / impact / partial-fill evidence
- Classification:
  - `AMBIGUITY_FOUND`
  - `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`
- Evidence found:
  - no explicit fee term in `_expected_cost`
  - no explicit separate impact term in `_expected_cost`
  - partial fills are represented through execution factor, not a separate penalty field
- Exact code excerpt:
```python
if state == DecisionState.REDUCED:
    return row.fill_ratio
```
```python
realized_cost=round(expected_cost * execution_factor, 6),
```
- External-audit questions:
  - are fees folded into upstream `slippage_bps`
  - is impact intentionally absent from this replay seam
  - should partial-fill economics remain multiplicative only

## Realized cost source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function:
  - `simulate_shadow_compatible_dtrs`
- Exact code excerpt:
```python
realized_cost=round(expected_cost * execution_factor, 6),
```
- Semantics:
  - simulated realized replay cost
- Non-executed records:
  - can contribute zero realized cost
- Test evidence:
```python
assert records[1].realized_cost > 0.0
assert records[2].realized_cost == 0.0
```

## Replay expected and realized cost means
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `EXPECTED_REALIZED_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Exact code excerpts:
```python
expected_cost_mean=round(_mean(tuple(record.expected_cost for record in records)), 6),
realized_cost_mean=round(_mean(tuple(record.realized_cost for record in records)), 6),
```
- Denominator:
  - `len(records)` implicitly through `_mean`
- Scope:
  - global
  - pair and engine variants follow the same pattern
- Evidence:
  - these are all-record means
  - they are not filtered to executed-only records
- False-green risk:
  - zero realized cost on non-executed records can dilute the mean

## Cost drift evidence

### Point drift
- Source file:
  - `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
- Exact code excerpt:
```python
cost_drift=realized_cost - expected_cost,
net_return=net,
was_profitable=net > 0.0,
```
- Units:
  - `fraction`
- Semantics:
  - realized minus expected

### Normalized drift monitor
- Source file:
  - `src/meta_minimal/cost_drift_monitor/monitor.py`
- Exact code excerpt:
```python
mean_expected = sum(sample.expected_cost for sample in self._samples) / sample_count
mean_realised = sum(sample.realised_cost for sample in self._samples) / sample_count
bias_pct = (mean_realised - mean_expected) / mean_expected
```
- Units:
  - `ratio`
- Preconditions:
  - `expected_cost > 0`
  - enough samples
- Test evidence:
```python
assert result.bias_pct == pytest.approx(0.30)
assert result.reason == "insufficient_data"
```

## Consumer evidence
- Replay report:
  - `CONSUMER_FOUND` via `replay_executor._review_markdown`
```python
f"- expected_cost_mean: {metrics_summary.expected_cost_mean:.6f}",
f"- realized_cost_mean: {metrics_summary.realized_cost_mean:.6f}",
```
- Cockpit:
  - `CONSUMER_FOUND` via `state_replay_metrics.py`
  - `CONSUMER_FOUND` via `state_economic_sterilization.py`
- Local lab:
  - `CONSUMER_FOUND` via `_net_pnl(records)` in `artifact_ablation_study.py`
```python
return sum(
    record.gross_return - record.realized_cost
    for record in records
    if record.decision_state == "executed"
)
```

## External audit questions
1. Should replay expected and realized cost means be split into executed-only and all-record variants?
2. Are fees and impact intentionally absent, or merely folded into other replay inputs?
3. Is multiplicative realized cost on reduced fills the intended doctrine, or only a current simplification?
