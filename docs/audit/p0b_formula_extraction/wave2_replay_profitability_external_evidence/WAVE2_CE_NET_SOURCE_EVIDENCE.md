# Wave 2 CE Net Source Evidence

## A. Per-record CE source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Function:
  - `simulate_shadow_compatible_dtrs`
- Exact code excerpt:
```python
expected_cost=round(expected_cost, 6),
realized_cost=round(expected_cost * execution_factor, 6),
gross_return=gross_return,
ce_expected=round((row.expected_edge_bps / 10_000.0) - expected_cost, 6),
```
- Evidence:
  - `ce_expected` is built from expected edge and expected cost
  - it is not built from realized cost
  - it is emitted into every `DTRRecord`

## B. Blocked / rejected / phantom inclusion
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `AMBIGUITY_FOUND`
- Source file:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
- Exact code excerpts:
```python
if state in {
    DecisionState.HARD_BLOCKED,
    DecisionState.REJECTED_RANKING,
    DecisionState.EVALUATED,
    DecisionState.NOT_EVALUATED,
}:
    return 0.0
if state == DecisionState.PHANTOM:
    return 0.0
```
```python
ce_expected=round((row.expected_edge_bps / 10_000.0) - expected_cost, 6),
```
- Evidence:
  - execution factor becomes `0.0` for blocked / rejected / phantom
  - `ce_expected` is still populated independently of execution factor
- External-audit question:
  - is including non-executed expected CE in global replay CE a deliberate doctrine choice or only a current producer convention

## C. CE aggregation source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function:
  - `build_replay_metrics_summary`
- Exact code excerpts:
```python
ce_net=round(sum(record.ce_expected for record in group), 6),
```
```python
ce_net=round(sum(record.ce_expected for record in records), 6),
```
- Evidence:
  - pair, engine, and global CE all sum `record.ce_expected`
  - no realized-cost adjustment is applied here

## D. DTR schema evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/meta_minimal/dtr_core/dtr_record_builder.py`
- Exact code excerpt:
```python
# CE
ce_expected: float = 0.0
```
- Evidence:
  - CE is a first-class per-record field in the canonical DTR schema

## E. Cockpit row-level mapping evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/cockpit/state_decision_trace.py`
- Function:
  - `read_decision_trace`
- Exact code excerpt:
```python
expected_cost=_float(payload.get("expected_cost")),
ce_net=_float(payload.get("ce_expected")),
```
- Evidence:
  - the cockpit row field named `ce_net` is loaded from `ce_expected`
- External-audit question:
  - should operator-facing row labels distinguish expected CE from aggregate CE

## F. Replay report consumer evidence
- Classification:
  - `CONSUMER_FOUND`
- Source file:
  - `src/local_replay_runtime/replay_executor.py`
- Exact code excerpt:
```python
f"- ce_net: {metrics_summary.ce_net:.6f}",
```
- Evidence:
  - review markdown serializes the aggregated CE into the replay report

## G. Tests proving current behavior
- `tests/test_local_replay_runtime/test_replay_executor.py`
```python
assert summary.ce_net == 0.0005
```
- `tests/test_local_replay_runtime/test_shadow_execution_simulator.py`
```python
assert records[2].decision_state == "hard_blocked"
assert records[2].realized_cost == 0.0
```
- Combined evidence:
  - blocked records can exist with zero realized cost
  - replay CE aggregate still comes from per-record CE, not from realized-cost filtering

## External audit questions
1. Should replay `ce_net` remain an all-record expected CE aggregate, including blocked and phantom records?
2. Should replay report/cockpit explicitly rename this to `expected_ce_net`?
3. If a realized profitability verdict is needed, should it come from separate net-return accounting rather than `ce_net`?
