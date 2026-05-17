# Wave 3 Market Impact Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `IMPACT_SOURCE_NOT_PROVEN` for replay prudent expected-cost seam

## 1. Taker-path impact proxy

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`  
Function: `compute_expected_taker_slippage_bps`

```python
return 0.5 * spread_bps + lambda_impact_bps * math.sqrt(max(participation_ratio, 0.0))
```

Evidence:
- impact proxy increases with `sqrt(participation_ratio)`
- impact proxy increases with `lambda_impact_bps`
- low opposite-side depth raises `participation_ratio`, which raises taker slippage proxy

Inputs:
- `spread_bps`
- `participation_ratio`
- `lambda_impact_bps`

Outputs:
- `expected_taker_slippage_bps`

Units:
- bps

Scope:
- execution-route economic projection

## 2. Adverse-selection seam

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`  
Function: `compute_expected_adverse_selection_bps`

```python
return scale_bps * market_toxicity_score * (1.0 - regime_stability_score)
```

Evidence:
- adverse-selection proxy increases with toxicity
- adverse-selection proxy decreases with regime stability

Scope:
- route economics, not replay expected-cost seam

Tests:
- adverse selection meter tests in `tests/test_execution_backbone/test_execution_cost_meter.py`

## 3. Explicit realized market-impact seam

Source file: `src/execution_backbone/execution_runtime.py`  
Functions: `_record_fill_event`, `_record_trade_cost`

```python
context.market_impact_total += event.market_impact
...
compute_trade_cost(
    ...
    market_impact=context.market_impact_total,
    expected_cost=intent.expected_cost,
)
```

Source file: `src/execution_backbone/execution_cost_meter/cost_aggregator.py`

```python
total = explicit_fee + implicit_cost + adverse_selection + partial_fill_cost + market_impact
```

Evidence:
- Live/shadow runtime has an explicit realized `market_impact` component.
- That component is not merely implied by slippage; it is stored separately in `TradeCost`.

Tests:
- `tests/test_execution_backbone/test_execution_cost_meter.py::TestCostAggregator::test_market_impact_is_included_in_total_cost`

## 4. Replay prudent expected-cost seam

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
- No explicit market-impact term is present in replay expected cost.

Classification:
- `IMPACT_SOURCE_NOT_PROVEN`

External-audit questions:
- Is replay `slippage_bps` intentionally a folded spread+impact proxy?
- If not, how should replay expected-cost realism be compared against live/shadow realized cost where impact is explicit?
