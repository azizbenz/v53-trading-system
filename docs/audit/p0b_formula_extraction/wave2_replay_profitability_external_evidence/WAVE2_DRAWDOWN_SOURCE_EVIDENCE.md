# Wave 2 Drawdown Source Evidence

## Core source
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `GROSS_NET_AMBIGUITY`
- Source file:
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Function:
  - `_drawdown_proxy`
- Exact code excerpt:
```python
def _drawdown_proxy(records: tuple[DTRRecord, ...]) -> float:
    running = 0.0
    peak = 0.0
    worst = 0.0
    for record in records:
        running += record.gross_return
        peak = max(peak, running)
        worst = min(worst, running - peak)
    return abs(worst)
```

## Plain-text formula
- accumulate a running gross-return path
- track running peak
- track worst peak-to-trough loss
- return absolute magnitude

## Inputs
- `record.gross_return`

## Output
- `drawdown_proxy`

## Units
- `fraction`

## Denominator
- none

## Scope
- `global`

## Gross/net semantics
- gross-return path only
- no realized cost subtraction in the drawdown computation

## Expected/realized/simulated/report semantics
- replay-derived report value
- simulated path proxy

## Included states
- all DTR records are iterated
- blocked / rejected / phantom records only affect the path through their `gross_return`, often zero

## Non-executed evidence
- non-executed records often contribute zero `gross_return` because:
```python
gross_return = round((row.gross_return_bps / 10_000.0) * execution_factor, 6)
```
and blocked / phantom execution factor is `0.0`

## Report consumer evidence
- `src/local_replay_runtime/replay_executor.py`
```python
f"- drawdown_proxy: {metrics_summary.drawdown_proxy:.6f}",
```

## Cockpit consumer evidence
- `src/cockpit/state_replay_metrics.py`
```python
drawdown_proxy=float(payload.get("drawdown_proxy", 0.0)),
```
- `src/cockpit/templates/partials/_replay_metrics.html`
```html
<span class="kpi-mega__label">Drawdown Proxy</span>
<span class="kpi-mega__value value-info">{{ "%.4f"|format(vm.replay.drawdown_proxy) }}</span>
```

## Tests
- `tests/test_local_replay_runtime/test_replay_executor.py`
```python
assert summary.drawdown_proxy >= 0.0
```
- `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
  - replay metrics consistency checks cover serialized `drawdown_proxy` as part of the full payload

## False-green risk
- label includes `Proxy`, which is good evidence discipline
- no sample caveat is attached directly in the replay snapshot
- no freshness qualifier is attached directly in the replay KPI partial beyond `source_status`

## Ambiguities found
- no evidence that this is true max drawdown on net equity
- no evidence that capital path or position sizing path is included

## External audit questions
1. Is `drawdown_proxy` intended only as an operator diagnostic?
2. Should any promotion or economic gating logic be barred from using it until a true drawdown seam exists?
