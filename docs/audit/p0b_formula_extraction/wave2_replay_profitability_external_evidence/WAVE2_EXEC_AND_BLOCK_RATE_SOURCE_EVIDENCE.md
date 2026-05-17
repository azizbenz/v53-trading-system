# Wave 2 Exec and Block Rate Source Evidence

## Exec-rate source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `DENOMINATOR_AMBIGUITY`
  - `PLACEHOLDER_RISK`
- Source files:
  - `src/cockpit/state_replay_metrics.py`
  - `src/cockpit/state_run_comparison.py`
- Exact code excerpts:
```python
if self.total_records == 0:
    return 0.0
return self.executed_count / self.total_records
```
```python
total_records = int(payload.get("total_records", 0) or 0)
if total_records <= 0:
    return 0.0
return float(payload.get("executed_count", 0) or 0) / float(total_records)
```
- Evidence:
  - current denominator is `total_records`
  - zero-record behavior returns `0.0`
- Conflicting doctrine evidence:
  - current backtest spec documents `executed_count / max(selected_count, 1)`
- External-audit question:
  - is the implemented replay cockpit metric intentionally an opportunity-level rate rather than a selected-only execution success rate

## Selected / executed / blocked count source
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Exact code excerpts:
```python
selected_states = {
    DecisionState.SELECTED,
    DecisionState.REDUCED,
    DecisionState.PHANTOM,
    DecisionState.EXECUTED,
}
```
```python
selected_count=sum(
    1 for record in records if record.decision_state in selected_states
),
executed_count=sum(
    1 for record in records if record.decision_state == DecisionState.EXECUTED
),
hard_blocked_count=sum(
    1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED
),
rejected_ranking_count=sum(
    1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING
),
phantom_count=sum(
    1 for record in records if record.decision_state == DecisionState.PHANTOM
),
```
- Evidence:
  - `selected_count` includes phantom
  - `executed_count` is strict executed only
  - hard-blocked, ranking-rejected, and phantom counts are defined by exact state equality

## Block-rate proxy source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `AMBIGUITY_FOUND`
- Source file:
  - `src/local_replay_runtime/artifact_ablation_study.py`
- Exact code excerpt:
```python
if not records:
    return 1.0
executed_count = sum(1 for record in records if record.decision_state == "executed")
return max(0.0, min(1.0, 1.0 - (executed_count / len(records))))
```
- Evidence:
  - denominator is `len(records)`
  - metric is bounded in `[0, 1]`
  - metric is a non-execution rate proxy, not a pure hard-block rate

## Tests proving current behavior
- `tests/test_local_replay_runtime/test_replay_executor.py`
```python
assert summary.selected_count == 1
assert summary.hard_blocked_count == 1
```
- `tests/cockpit/test_state_economic_sterilization.py`
```python
assert snapshot.economic_sterilization_ratio == 0.8
assert snapshot.status == "insufficient_sample"
```
- `tests/cockpit/test_state_run_comparison.py`
```python
assert snapshot.sample_warning == "SAMPLE_TOO_SMALL"
```
- `tests/test_local_replay_runtime/test_artifact_ablation_study.py`
  - covers ablation block-rate and delta behavior

## Consumer evidence
- Exec-rate:
  - cockpit replay KPI: `CONSUMER_FOUND`
  - cockpit sterilization monitor: `CONSUMER_FOUND`
  - run comparison: `CONSUMER_FOUND`
- Block-rate proxy:
  - local lab ablation: `CONSUMER_FOUND`
  - proof summary: `CONSUMER_FOUND`
  - replay KPI cockpit: `CONSUMER_NOT_FOUND`

## False-green evidence
- `exec_rate` has no denominator label in `_replay_metrics.html`
```html
<span class="kpi-mega__label">Exec rate</span>
<span class="kpi-mega__value">{{ "%.1f%%"|format(vm.replay.exec_rate * 100) }}</span>
```
- `exec_rate` zero-record behavior returns `0.0`, not `None`
- `selected_count` includes phantom, which can surprise operator interpretation

## External audit questions
1. Should current cockpit `exec_rate` be renamed `exec_rate_total`?
2. Should a selected-only execution rate be introduced later as a separate metric?
3. Should ablation `block_rate` be renamed `non_execution_rate` or `block_rate_proxy`?
