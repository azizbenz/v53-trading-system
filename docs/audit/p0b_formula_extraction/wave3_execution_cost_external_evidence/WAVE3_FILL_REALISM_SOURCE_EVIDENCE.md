# Wave 3 Fill Realism Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `FILL_REALISM_NOT_PROVEN` for external realism calibration

## 1. Replay fill state machine

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Functions: `_state_and_reason`, `_execution_factor`

```python
if base_state in selected_states and expected_edge <= (
    expected_cost + config.economic_absurdity_buffer_bps / 10_000.0
):
    return DecisionState.PHANTOM, "economically_absurd"
if base_state in selected_states and row.fill_ratio <= config.phantom_fill_threshold:
    return DecisionState.PHANTOM, row.primary_reason or "no_fill"
if base_state in selected_states and row.fill_ratio < config.reduced_fill_threshold:
    return DecisionState.REDUCED, row.primary_reason or "partial_fill"
...
if state == DecisionState.PHANTOM:
    return 0.0
if state == DecisionState.REDUCED:
    return row.fill_ratio
return 1.0
```

Plain-text behavior:
- `PHANTOM` for economically absurd or near-no-fill selections
- `REDUCED` for partial fill
- `EXECUTED` for full replay-compatible fill
- `execution_factor = 0` for blocked/rejected/phantom
- `execution_factor = fill_ratio` for reduced
- `execution_factor = 1` for executed

Realized-cost consequence:
- `realized_cost = expected_cost * execution_factor`

Tests:
- `tests/test_local_replay_runtime/test_shadow_execution_simulator.py::test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states`

## 2. Fill aggregation seam

Source file: `src/execution_backbone/fill_tracker/fill_aggregator.py`  
Test evidence from `tests/test_execution_backbone/test_fill_tracker.py`

Proven assertions:
- partial fills aggregate weighted average price
- total fees sum across fills
- duplicate fill ids are idempotent
- conflicting fill metadata raises
- zero quantity fill is rejected

Representative evidence:
- `average_price == 50050.0` for two half-fills at `50000` and `50100`
- `total_fees == 50.1`

Scope:
- live/shadow measured fill aggregation

## 3. Partial-fill cost seam

Source file: `src/execution_backbone/execution_cost_meter/partial_fill_cost_meter.py`  
Test evidence from `tests/test_execution_backbone/test_execution_cost_meter.py::TestPartialFillCost`

Proven assertions:
- no variance for single fill
- positive price variance for fragmented fills
- residual unfilled cost positive when only a fraction fills
- empty fills produce zero fill ratio

Interpretation:
- live/shadow runtime has a separate partial-fill cost meter
- replay seam does not; replay instead uses `execution_factor`

Classification:
- `AMBIGUITY_FOUND`

## 4. Timeout behavior

Source seam:
- `src/execution_backbone/order_decider/timeout_policy_selector.py` was inspected earlier in session
- market timeout default: `5s`
- limit timeout default: `30s`
- cancel-on-timeout default enabled

Consumer seam:
- execution runtime tracks terminal `CANCELLED`, `EXPIRED`, `REJECTED`, `FILLED`
- timeout conversion or cancellation behavior is part of hybrid routing / runtime handling

Tests:
- `tests/test_execution_backbone/test_order_decider.py`
- integration execution tests

## 5. Maker/taker fill guarantee

Evidence status:
- No source in this pack proves maker fill is guaranteed.
- Hybrid router only computes `p_fill_proxy`.

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`

```python
return sigmoid(logit_fill)
```

Classification:
- `FILL_REALISM_NOT_PROVEN`
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`

External-audit questions:
- Is `p_fill_proxy` empirically calibrated enough for VPS non-HFT doctrine?
- Does replay `fill_ratio` originate from measured historical fill behavior, or from a separate synthetic heuristic?
