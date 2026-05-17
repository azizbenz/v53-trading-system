# Wave 4 VPIN / PIN / Toxicity Source Evidence

## VPIN source

- Source file: `src/data_backbone/microstructure/vpin.py`
- Function/class:
  - `compute_vpin`
  - `_build_equal_volume_buckets_with_trade_indices`
  - `_classify_bucket`
  - `VpinRecord`

### Exact code excerpts

```python
VPIN_METHOD_VERSION = "vpin.easley_lopez_ohara.v1"
```

```python
buy_fraction = _normal_cdf(delta_p / sigma_delta_p)
buy_volume = bucket.total_volume * buy_fraction
sell_volume = bucket.total_volume - buy_volume
```

```python
resolved_daily_volume = sum(trade.volume for trade in trades)
derived_input_warning = "derived_daily_volume_used"
```

```python
vpin = sum(abs(bucket.buy_volume - bucket.sell_volume) for bucket in bucket_rows[-resolved_window:]) / (
    resolved_window * bucket_volume
)
```

### Implemented formula in plain text

1. Build equal-volume buckets from ordered trades.
2. Within each bucket, estimate buy/sell split with bulk volume classification:
   - if `sigma_delta_p > 0`, use normal-CDF split from price change
   - if `sigma_delta_p <= 0`, use deterministic sign split or 50/50 for zero move
3. `VPIN = sum(|buy_volume - sell_volume|) / (window_buckets * bucket_volume)`
4. Output is clipped to `[0, 1]`.

### Inputs / output / window / stale behavior

- Input variables:
  - trade prices
  - trade volumes
  - trade timestamps
  - `buckets_per_day`
  - `window_buckets`
  - `daily_volume` or derived daily volume
  - `computed_at_ns`
- Output variable:
  - `VpinRecord.value`
- Units: fraction / score `0..1`
- Denominator:
  - `window_buckets * bucket_volume`
- Window:
  - equal-volume bucket window
- Timestamp convention:
  - trade timestamps
  - `computed_at_ns`
- Sparse / partial behavior:
  - `partial_window = resolved_window < window_buckets`
  - `low_sample_confidence` if partial, <5 buckets, or derived daily volume
  - `insufficient_variation = sigma_delta_p <= 0.0`

### Consumers

- Engine C:
  - `src/engines/engine_c/continuation_validator_c.py`
    - `if inputs.vpin is not None and inputs.vpin_max is not None and inputs.vpin > inputs.vpin_max`
    - reason code `engine_internal.c.vpin_toxic`
- Engine B:
  - `src/engines/engine_b/excess_detector_b.py`
    - `if inputs.vpin_current < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.vpin_toxic:`
    - toxic-flow fade reason `b.toxic_flow_fade`
- Toxicity classification:
  - Engine C uses VPIN as a toxic-flow veto seam
  - Engine B uses VPIN as a toxic-flow fade seam

### Tests

- `tests/test_data_backbone/microstructure/test_vpin.py`
  - `assert result.insufficient_variation is True`
- `tests/test_microstructure/test_paper_repro.py`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`

## PIN source

- Source file: `src/data_backbone/microstructure/pin.py`
- Function/class:
  - `compute_pin_from_estimate`
  - `PinRecord`

### Exact code excerpts

```python
PIN_METHOD_VERSION = "pin.easley_kiefer_ohara_paperman.v1"
```

```python
numerator = estimate.alpha * estimate.mu
denominator = numerator + estimate.epsilon_b + estimate.epsilon_s
pin_value = 0.0 if denominator <= 0.0 else numerator / denominator
```

```python
if numerator <= 0.0:
    parameter_warning = "zero_informed_flow_component"
```

### Implemented formula in plain text

PIN is computed from already-estimated parameters:
- `PIN = (alpha * mu) / (alpha * mu + epsilon_b + epsilon_s)`

This source file does not fit PIN parameters from raw events in the traced seam.

### Inputs / output / units / behavior

- Input variables:
  - `alpha`, `mu`, `epsilon_b`, `epsilon_s`
  - `pair`
  - `computed_at_ns`
  - window metadata and event count metadata
- Output variable:
  - `PinRecord.value`
- Units: fraction / score `0..1`
- Denominator:
  - `alpha * mu + epsilon_b + epsilon_s`
- Window:
  - metadata only; no raw-event rolling fit is implemented here
- Behavior:
  - `parameter_warning = "zero_informed_flow_component"` when numerator is zero
  - `low_sample_confidence` if `n_events_used < 5`

### Consumers / status

- Feature registry claims `meta_learning`
- Direct governed runtime consumer was not proven in this pass
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `FUTURE_RESERVED`
  - `CONSUMER_NOT_FOUND`

### Tests

- `tests/test_data_backbone/microstructure/test_pin.py`

## External-audit questions

1. Is PIN intentionally limited to a parameter-evaluation seam in V5.3, with fitting handled outside the governed runtime?
2. Should VPIN toxic-flow thresholds be treated as engine-local doctrine only, or should external audit require a shared canonical thresholding note?
