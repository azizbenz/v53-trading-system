# Wave 2 Reconciliation Source Evidence

## Producer-to-DTR consistency
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/backtest_artifact_import/export_dir_bridge_support.py`
- Function:
  - `_validate_metrics_consistency`
- Exact code excerpt:
```python
if replay_metrics.total_records != len(replay_dtr_records):
    raise ValueError(
        "governed export replay_metrics total_records must match replay_dtr count"
    )
expected_replay_metrics = build_replay_metrics_summary(
    replay_dtr_records,
    total_opportunities=replay_metrics.total_opportunities,
)
if replay_metrics != expected_replay_metrics:
    raise ValueError(
        "governed export replay_metrics must stay consistent with replay_dtr records"
    )
```
- Evidence:
  - replay metrics must be reproducible from DTRs
  - exporter/import bridge treats replay metrics as deterministic derived artifacts

## Pair and engine aggregate record-count reconciliation
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Exact code excerpt:
```python
if sum(item.record_count for item in replay_metrics.pair_aggregates) != replay_metrics.total_records:
    raise ValueError(
        "governed export replay_metrics pair_aggregates must sum to total_records"
    )
if sum(item.record_count for item in replay_metrics.engine_aggregates) != replay_metrics.total_records:
    raise ValueError(
        "governed export replay_metrics engine_aggregates must sum to total_records"
    )
```
- Evidence:
  - record-count reconciliation is explicitly enforced

## CE reconciliation
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `CONSUMER_NOT_FOUND`
  - `AMBIGUITY_FOUND`
- Evidence found:
  - pair and engine CE use the same field as global CE:
```python
ce_net=round(sum(record.ce_expected for record in group), 6),
```
```python
ce_net=round(sum(record.ce_expected for record in records), 6),
```
- Evidence not found:
  - no explicit assertion that `sum(pair.ce_net) == global.ce_net`
  - no explicit assertion that `sum(engine.ce_net) == global.ce_net`
- External-audit question:
  - should CE reconciliation be explicitly tested with tolerance because group values are rounded to 6 decimals

## Count ordering evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `AMBIGUITY_FOUND`
- Evidence found:
  - `selected_count` counts `{SELECTED, REDUCED, PHANTOM, EXECUTED}`
  - `executed_count` counts only `EXECUTED`
- Likely implication:
  - `executed_count <= selected_count <= total_records`
- Evidence not found:
  - no direct unit test asserting that inequality
- External-audit question:
  - should a direct reconciliation test pin `executed_count <= selected_count <= total_records`

## Exclusivity evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
- Evidence:
  - `hard_blocked_count`, `rejected_ranking_count`, and `phantom_count` are counted with exact equality against one `decision_state` field.
  - Since `decision_state` is singular in `DTRRecord`, those counts are mutually exclusive at record level.
- Exact schema excerpt:
```python
decision_state: DecisionState = DecisionState.NOT_EVALUATED
```
- External-audit question:
  - should a direct unit test assert mutual exclusivity over a mixed-state fixture

## Bounded block-rate evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/artifact_ablation_study.py`
- Exact code excerpt:
```python
return max(0.0, min(1.0, 1.0 - (executed_count / len(records))))
```
- Evidence:
  - ablation block/non-execution rate is clipped into `[0, 1]`

## Test evidence
- `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
```python
with pytest.raises(
    ValueError,
    match="governed export replay_metrics total_records must match replay_dtr count",
):
    discover_local_replay_export(export_dir)
```
```python
with pytest.raises(
    ValueError,
    match="governed export replay_metrics must stay consistent with replay_dtr records",
):
    discover_local_replay_export(export_dir)
```
- `tests/test_local_replay_runtime/test_replay_executor.py`
```python
assert summary.selected_count == 1
assert summary.hard_blocked_count == 1
assert summary.ce_net == 0.0005
```

## External audit questions
1. Should global CE equality with pair and engine CE be explicitly tested with tolerance?
2. Should direct tests assert `executed_count <= selected_count <= total_records`?
3. Should direct tests assert hard-blocked / ranking-rejected / phantom exclusivity on mixed fixtures?
