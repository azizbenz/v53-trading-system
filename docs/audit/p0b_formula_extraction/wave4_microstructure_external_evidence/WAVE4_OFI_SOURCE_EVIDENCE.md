# Wave 4 OFI Source Evidence

## Source

- Source file: `src/data_backbone/microstructure/order_flow_imbalance.py`
- Function/class:
  - `compute_order_flow_imbalance`
  - `_event_contribution`
  - `OrderFlowImbalanceRecord`

## Exact code excerpts

```python
ORDER_FLOW_IMBALANCE_METHOD_VERSION = "order_flow_imbalance.cont_kukanov.v1"
```

```python
bid_up_or_same = 1.0 if current.bid_price >= previous.bid_price else 0.0
bid_down_or_same = 1.0 if current.bid_price <= previous.bid_price else 0.0
ask_down_or_same = 1.0 if current.ask_price <= previous.ask_price else 0.0
ask_up_or_same = 1.0 if current.ask_price >= previous.ask_price else 0.0
return (
    (bid_up_or_same * current.bid_size)
    - (bid_down_or_same * previous.bid_size)
    - (ask_down_or_same * current.ask_size)
    + (ask_up_or_same * previous.ask_size)
)
```

```python
value=sum(recent_contributions),
partial_window=resolved_window < window_events,
low_sample_confidence=resolved_window < 3,
...
input_data_hash=_hash_input(
    pair=pair,
    window_events=resolved_window,
```

## Formula in plain text

OFI is the sum of top-of-book event contributions over the resolved event window, using the implemented bid/ask update convention shown above.

## Inputs / output / units / scope

- Inputs:
  - top-of-book bid/ask prices and sizes
  - ordered event timestamps
  - `window_events`
  - `computed_at_ns`
- Output:
  - `OrderFlowImbalanceRecord.value`
- Units:
  - raw size imbalance
- Denominator:
  - none
- Scope:
  - estimator output over an event-count window

## Data <= t / invalid book / missing behavior

- Uses only ordered events up to `computed_at_ns`
- Invalid/crossed book points are rejected by validation
- Partial windows are explicit via `partial_window`
- Low-sample behavior is explicit via `low_sample_confidence`
- Missing values do not silently become safe zero; the estimator requires a valid point sequence

## Consumers

- Engine C continuation seam
- Engine A `ofi_flow_score` seam
- LOB regime `_ofi_short_window`
- feature-registry intent for meta-learning, not proven here as a governed runtime consumer

## Tests

- `tests/test_data_backbone/microstructure/test_order_flow_imbalance.py`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
- `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`

## Classification

- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `ENGINE_CONSUMED`
- `REGIME_CONTEXT_INPUT`
- `WINDOW_AMBIGUITY`

## External-audit questions

1. Should external audit require a normalized OFI seam for cross-pair comparisons, or is raw size OFI acceptable under current engine-local thresholds?
