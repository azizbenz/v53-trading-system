# Wave 3 Slippage Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `EXPECTED_REALIZED_AMBIGUITY`

## 1. Ex-ante execution slippage model

Source file: `src/execution_backbone/slippage_model.py`  
Function: `predict_execution_slippage`

```python
predicted_slippage_bps = max(
    0.0,
    model.intercept_bps + model.sqrt_size_coefficient * math.sqrt(size_value),
)
return ExecutionSlippageEstimate(
    predicted_slippage_bps=predicted_slippage_bps,
    cost_addition=predicted_slippage_bps / 10_000.0,
    ...
)
```

Plain-text formula:
- `predicted_slippage_bps = max(0, intercept_bps + sqrt_size_coefficient * sqrt(size_value))`
- `cost_addition = predicted_slippage_bps / 10,000`

Inputs:
- `intercept_bps`
- `sqrt_size_coefficient`
- `size_value`

Outputs:
- `predicted_slippage_bps`
- `cost_addition`

Units:
- `predicted_slippage_bps`: bps
- `cost_addition`: fraction

Scope:
- per-candidate ex-ante slippage estimate

Tests:
- `tests/test_execution_backbone/test_slippage_model.py`
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_augments_expected_cost_from_slippage_model`
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_slippage_model_can_flip_path_to_no_trade`

## 2. Hybrid-router taker slippage formula

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`  
Function: `compute_expected_taker_slippage_bps`

```python
return 0.5 * spread_bps + lambda_impact_bps * math.sqrt(max(participation_ratio, 0.0))
```

Plain-text formula:
- `expected_taker_slippage_bps = 0.5 * spread_bps + lambda_impact_bps * sqrt(participation_ratio)`

Inputs:
- `spread_bps`
- `participation_ratio`
- `lambda_impact_bps`

Output:
- `expected_taker_slippage_bps`

Units:
- bps

Scope:
- execution routing / taker path economics

Ambiguity:
- This seam mixes spread and impact into a single taker-slippage proxy.

Classification:
- `AMBIGUITY_FOUND`

## 3. Replay prudent slippage seam

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `_expected_cost`

```python
row.slippage_bps * config.slippage_multiplier
```

Evidence:
- Replay slippage is an input field scaled by a multiplier.
- Sign convention is magnitude-only in this seam; buy/sell signed slippage is not represented separately.

Units:
- `row.slippage_bps`: bps
- output contribution: fraction after division by `10_000`

Non-executed records:
- still contribute to expected cost
- do not contribute realized cost if `execution_factor = 0`

## 4. Telemetry slippage extraction

Source file: `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`  
Function: `_extract_route_hint_slippage_bps`

```python
raw = route_hint_payload.get("slippage_bps")
if raw is None and isinstance(route_hint_payload.get("feature_values"), dict):
    raw = route_hint_payload["feature_values"].get("slippage_bps")
return float(raw) if raw is not None else None
```

Semantics:
- shadow telemetry / snapshot-batch sourced
- report-only extraction

## 5. Realized slippage

Evidence found:
- explicit realized slippage formula was not proven as a standalone named metric in replay or cockpit seams inspected in this pack
- live runtime instead records realized total cost components through cost meter and fill tracker

Classification:
- `CONSUMER_NOT_FOUND`
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`

External-audit questions:
- Is realized slippage expected to exist as a separate surfaced metric, or is it intentionally folded into `implicit_cost` / `total_cost`?
- Should replay retain only ex-ante slippage while live/shadow retains realized total-cost decomposition?
