# Wave 3 Spread Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## 1. Cockpit live spread formula

Source file: `src/cockpit/state_data_quality.py`  
Function: `_compute_spread_bps`

```python
if bid is None or ask is None:
    return None
mid = (bid + ask) / 2.0
if mid <= 0:
    return None
return ((ask - bid) / mid) * 10000.0
```

Plain-text formula:
- `spread_bps = ((ask - bid) / mid) * 10,000`
- `mid = (bid + ask) / 2`

Inputs:
- `bid`
- `ask`

Output:
- `spread_bps`

Units:
- bps

Scope:
- cockpit-derived live data-quality view

Missing behavior:
- `None` if bid/ask missing
- `None` if `mid <= 0`

Consumers:
- cockpit data-quality card

Tests:
- `tests/cockpit/test_state_data_quality.py::test_data_quality_marks_fresh_snapshot_ok`
- `tests/cockpit/test_state_data_quality.py::test_data_quality_marks_stale_and_missing_depth`

## 2. Telemetry extraction spread fallback logic

Source file: `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`  
Function: `_extract_spread_bps`

```python
spread_from_feature = _extract_route_hint_feature_float(
    route_hint_payload,
    feature_key="spread_bps",
)
if spread_from_feature is not None:
    return spread_from_feature
...
if bid > 0.0 and ask >= bid:
    mid = (bid + ask) / 2.0
    if mid > 0.0:
        return ((ask - bid) / mid) * 10_000.0
...
if best_bid > 0.0 and best_ask >= best_bid:
    mid = (best_bid + best_ask) / 2.0
    if mid > 0.0:
        return ((best_ask - best_bid) / mid) * 10_000.0
```

Evidence:
- Spread can be sourced from route-hint feature values.
- If absent, it is recomputed from `bid/ask` or `bids[0]/asks[0]`.
- Crossed books are rejected by requiring `ask >= bid`.

Scope:
- shadow telemetry / local lab artifact extraction

Tests:
- indirect via telemetry artifact tests and cockpit live data-quality tests

## 3. Replay expected-cost spread input

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `_expected_cost`

```python
return (
    row.spread_bps
    + row.slippage_bps * config.slippage_multiplier
    + row.latency_penalty_bps * config.latency_penalty_multiplier
) / 10_000.0
```

Evidence:
- Replay prudent expected cost consumes `row.spread_bps` directly.

Scope:
- per-record replay expected-cost seam

Semantics:
- expected
- not live measured

## 4. Spread guard gate

Source file: `src/execution_backbone/test_spread_guard.py` was not opened directly in this turn, but runtime tests prove spread guard behavior through `ExecutionRuntime`.

Source file: `src/execution_backbone/execution_runtime.py` consumer behavior proven by:
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_blocks_submission_from_spread_guard_model`
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_fails_open_when_spread_guard_model_receives_invalid_spread`

Evidence from tests:
- `current_spread_bps = 15.0` with `max_spread_bps = 12.0` blocks submission
- `spread_bps = nan` causes fail-open path

Classification:
- `TEST_COVERED`
- `CONSUMER_FOUND`

External-audit questions:
- Is fail-open on invalid spread acceptable under VPS non-HFT doctrine?
- Should NaN or missing spread become explicit caution telemetry rather than silent runtime permissiveness?
