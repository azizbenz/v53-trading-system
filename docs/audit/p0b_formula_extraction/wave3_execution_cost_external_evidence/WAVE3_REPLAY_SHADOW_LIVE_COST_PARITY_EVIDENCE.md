# Wave 3 Replay / Shadow / Live Cost Parity Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `EXPECTED_REALIZED_AMBIGUITY`

## 1. Replay expected cost

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`

```python
return (
    row.spread_bps
    + row.slippage_bps * config.slippage_multiplier
    + row.latency_penalty_bps * config.latency_penalty_multiplier
) / 10_000.0
```

Semantics:
- expected
- replay global / per-record
- not live measured

## 2. Replay simulated realized cost

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`

```python
realized_cost=round(expected_cost * execution_factor, 6),
```

Semantics:
- simulated realized
- derived from replay expected cost
- not direct venue measurement

Missing behavior:
- hard-blocked, rejected, evaluated, phantom records resolve to `execution_factor = 0`, therefore `realized_cost = 0`

## 3. Replay-vs-production expected-cost parity diagnostics

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `build_parity_diagnostics_payload`

```python
if row.production_expected_cost is not None:
    cost_compared += 1
    cost_diffs.append(abs(row.production_expected_cost - record.expected_cost))
...
mean_cost_gap = (
    round_float64(sum(cost_diffs) / len(cost_diffs), 6) if cost_diffs else 0.0
)
...
if cost_compared and mean_cost_gap <= parity_policy.cost_tolerance
```

Plain-text formula:
- `mean_cost_gap = mean(abs(production_expected_cost - replay_expected_cost))`

Units:
- fraction

Semantics:
- parity diagnostic only
- expected-vs-expected comparison, not expected-vs-realized

Tests:
- `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_build_parity_diagnostics_payload_reports_ok_when_baselines_match`

## 4. Live/shadow realized total-cost seam

Source files:
- `src/execution_backbone/execution_runtime.py`
- `src/execution_backbone/execution_cost_meter/cost_aggregator.py`

```python
total = explicit_fee + implicit_cost + adverse_selection + partial_fill_cost + market_impact
surprise = total - expected_cost
```

Semantics:
- measured or reconstructed realized execution cost
- includes explicit fee, implicit cost, adverse selection, partial-fill cost, market impact

Scope:
- per-order / per-trade

## 5. Meta drift seam

Source file: `src/meta_minimal/cost_drift_monitor/monitor.py`

```python
mean_expected = sum(sample.expected_cost for sample in self._samples) / sample_count
mean_realised = sum(sample.realised_cost for sample in self._samples) / sample_count
bias_pct = (mean_realised - mean_expected) / mean_expected
alert = bias_pct > self._config.bias_alert_threshold
```

Semantics:
- realized-vs-expected drift monitor
- explicit denominator is mean expected cost

Tests:
- `tests/test_meta_minimal/test_cost_drift_monitor.py`

## 6. Parity gap summary

Evidence:
- Replay expected cost omits explicit fee and explicit impact terms unless already folded upstream.
- Live/shadow realized cost has explicit fee and explicit market-impact terms.
- Replay simulated realized cost is a scaled replay expected cost, not a measured fill-cost decomposition.

Classification:
- `POSSIBLE_MISMATCH_FOR_EXTERNAL_AUDIT`
- `EXPECTED_REALIZED_AMBIGUITY`

External-audit questions:
- Should replay expected cost be treated as a prudent lower-fidelity seam relative to live/shadow measured total cost?
- Is there a governed mapping between replay `production_expected_cost` and live `intent.expected_cost`?
