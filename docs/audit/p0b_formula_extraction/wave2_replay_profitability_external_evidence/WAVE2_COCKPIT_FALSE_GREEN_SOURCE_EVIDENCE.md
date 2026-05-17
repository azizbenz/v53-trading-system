# Wave 2 Cockpit False-Green Source Evidence

## Numeric defaults in replay snapshot
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/cockpit/state_replay_metrics.py`
- Exact code excerpt:
```python
total_records: int = 0
selected_count: int = 0
executed_count: int = 0
ce_net: float = 0.0
expected_cost_mean: float = 0.0
realized_cost_mean: float = 0.0
gross_return_mean: float = 0.0
gross_return_total: float = 0.0
drawdown_proxy: float = 0.0
```
- Evidence:
  - replay-facing numeric fields have placeholder defaults

## CE color logic
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/cockpit/templates/partials/_replay_metrics.html`
- Exact code excerpt:
```html
<span class="kpi-mega__label">CE net</span>
<span class="kpi-mega__value {% if vm.replay.ce_net >= 0 %}value-up{% else %}value-down{% endif %}">
    {{ "%.4f"|format(vm.replay.ce_net) }}
</span>
```
- Evidence:
  - positive-or-zero CE is colored up
  - no explicit guard against `total_records == 0`

## Exec-rate label and denominator evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `DENOMINATOR_AMBIGUITY`
- Source file:
  - `src/cockpit/templates/partials/_replay_metrics.html`
- Exact code excerpt:
```html
<span class="kpi-mega__label">Exec rate</span>
<span class="kpi-mega__value">{{ "%.1f%%"|format(vm.replay.exec_rate * 100) }}</span>
```
- Evidence:
  - label does not state denominator
  - denominator is only discoverable in Python code

## Zero-record exec-rate behavior
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `PLACEHOLDER_RISK`
- Source file:
  - `src/cockpit/state_replay_metrics.py`
- Exact code excerpt:
```python
if self.total_records == 0:
    return 0.0
return self.executed_count / self.total_records
```
- Evidence:
  - zero-record snapshot yields numeric `0.0`, not an unavailable state

## Stale replay handling evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source files:
  - `src/cockpit/state_economic_sterilization.py`
  - `src/cockpit/state_freshness.py`
- Exact code excerpts:
```python
stamp = source_stamp(path=source_path, stale_after_seconds=300.0)
```
```python
if stale_after_seconds is not None and age_seconds > stale_after_seconds:
    status = "stale"
    reason_codes = tuple((*reason_codes, "source_stale"))
```
- Evidence:
  - stale replay file detection exists
  - replay economics can inherit stale source status in sterilization view
- Ambiguity:
  - replay KPI partial itself only shows `vm.replay.source_status`; it does not visibly enforce a stale-economics color policy

## Thin-sample evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/cockpit/state_economic_sterilization.py`
- Exact code excerpt:
```python
if opportunities < 30:
    status = "insufficient_sample"
```
```python
if opportunities < 30:
    reason_codes.append("SAMPLE_TOO_SMALL")
```
- Evidence:
  - thin-sample restraint exists in sterilization monitor
  - equivalent replay KPI restraint is not enforced in the replay snapshot itself

## Report-not-yet-persisted evidence
- Classification:
  - `EVIDENCE_EXTRACTED`
- Source file:
  - `src/cockpit/state_decision_trace.py`
- Exact code excerpt:
```python
return DecisionTraceSnapshot(
    source_status="not_yet_persisted",
    ...
)
```
- Evidence:
  - some replay-adjacent surfaces already expose `not_yet_persisted`
- Ambiguity:
  - replay metrics snapshot uses `missing` / `parse_error` / `ok`, but not an explicit thin-sample or placeholder class

## Tests
- `tests/cockpit/test_state_economic_sterilization.py`
```python
assert snapshot.economic_sterilization_ratio == 0.8
assert snapshot.status == "insufficient_sample"
```
- `tests/cockpit/test_state_run_comparison.py`
```python
assert snapshot.sample_warning == "SAMPLE_TOO_SMALL"
```
- `tests/cockpit/test_state_decision_trace.py`
```python
assert snapshot.source_status == "not_yet_persisted"
```

## External audit questions
1. Should replay KPI state carry an explicit placeholder / insufficient-sample / stale status beyond numeric defaults?
2. Should `ce_net` be prevented from rendering as positive when `record_count == 0`?
3. Should exec-rate labels explicitly include denominator semantics on the display surface?
