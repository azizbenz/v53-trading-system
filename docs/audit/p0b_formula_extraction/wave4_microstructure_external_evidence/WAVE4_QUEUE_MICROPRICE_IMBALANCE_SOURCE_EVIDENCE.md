# Wave 4 Queue / Microprice / Imbalance Source Evidence

## Queue pressure

- Source file: `src/data_backbone/microstructure/queue_pressure.py`
- Function/class:
  - `compute_queue_pressure`
  - `QueuePressureRecord`

### Exact code excerpt

```python
bid_volume = sum(point.bid_sizes[:resolved_top_k])
ask_volume = sum(point.ask_sizes[:resolved_top_k])
denominator = bid_volume + ask_volume
value = 0.0 if denominator <= 0.0 else (bid_volume - ask_volume) / denominator
```

### Formula / units / behavior

- Formula:
  - top-k book imbalance `(bid_volume - ask_volume) / (bid_volume + ask_volume)`
- Units:
  - ratio in `[-1, 1]`
- Denominator:
  - `bid_volume + ask_volume`
- Window:
  - single snapshot, top-k depth window
- Zero-depth behavior:
  - returns `0.0`
  - `low_sample_confidence = True`
- Timestamp convention:
  - snapshot timestamp
  - `computed_at_ns`

### Consumers / tests

- Engine C direct consumer:
  - `src/engines/engine_c/continuation_validator_c.py`
    - `if inputs.queue_pressure is not None and inputs.queue_pressure < inputs.queue_min`
- Tests:
  - `tests/test_data_backbone/microstructure/test_queue_pressure.py`
  - `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
    - `assert engine_input.queue_pressure == pytest.approx(0.31)`

## LOB regime microprice / imbalance

- Source file: `src/data_backbone/microstructure/lob_regime_features.py`
- Function/class:
  - `_basic_book_bundle`
  - `_ofi_short_window`
  - `_aggressive_trade_imbalance`
  - `compute_lob_regime_features`

### Exact code excerpts

```python
order_book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth + _EPS)
```

```python
spread_bps=(latest.asks[0].price - latest.bids[0].price) / (mid + _EPS) * 10_000.0,
order_book_imbalance=order_book_imbalance,
depth_skew=order_book_imbalance,
microprice_pressure=(microprice - mid) / (mid + _EPS) * 10_000.0,
```

```python
liquidity_thinning_score = _clip(
    1.0 - ((bid_depth + ask_depth) / (historical_avg_depth + _EPS))
)
```

```python
buy_qty = sum(trade.quantity for trade in trades if trade.aggressor_side == "buy")
sell_qty = sum(trade.quantity for trade in trades if trade.aggressor_side == "sell")
```

### Formula / units / zero-depth / invalid-book behavior

- `spread_bps`
  - units: bps
- `order_book_imbalance`
  - units: ratio
- `microprice_pressure`
  - units: bps
- `depth_skew`
  - currently same scalar as order-book imbalance in this seam
- `liquidity_thinning_score`
  - units: score `0..1`
- `aggressive_trade_imbalance`
  - units: ratio
- Zero-depth behavior:
  - `_EPS` stabilized divisions prevent raw division errors
  - insufficient-data / stale paths are handled earlier in `_window_rejection_snapshot`
- Crossed / unsorted book behavior:
  - invalid depth is rejected before feature construction

## Consumers

- `src/complete_enablers/regime_detector_runtime.py`
  - consumes LOB regime feature snapshot as runtime regime context
- `src/execution_backbone/order_decider/hybrid_router_equations.py`
  - `sign_side * float(snap.order_book_imbalance)`
  - `sign_side * float(snap.microprice_pressure)`
  - `sign_side * float(snap.aggressive_trade_imbalance)`

## Tests

- `tests/test_data_backbone/microstructure/test_lob_regime_features.py`
  - `assert snapshot.as_feature_map()["spread_bps"] == pytest.approx(snapshot.spread_bps)`
  - versioned feature-map assertions
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
- `tests/test_execution_backbone/test_execution_runtime.py`

## Classification / external questions

- Classifications:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `ENGINE_CONSUMED`
  - `REGIME_CONTEXT_INPUT`
  - `EXECUTION_GATE_CONSUMED`
- External-audit questions:
  - Is `depth_skew = order_book_imbalance` an intentional alias seam, or only a compatibility duplication for feature-set stability?
