# Wave 4 Kyle Lambda Source Evidence

## Source

- Source file: `src/data_backbone/microstructure/kyle_lambda.py`
- Function/class:
  - `classify_trade_direction`
  - `build_kyle_intervals`
  - `_ols_slope`
  - `compute_kyle_lambda`
  - `KyleLambdaRecord`

## Exact code excerpts

```python
KYLE_LAMBDA_METHOD_VERSION = "kyle_lambda.rolling_ols.v1"
```

```python
sign = classify_trade_direction(
    trade,
    previous_trade=previous_trade,
    previous_sign=previous_sign,
)
bucket_signed_volume += sign * trade.volume
bucket_reference_price = trade.mid_price if trade.mid_price is not None else trade.price
```

```python
slope = _ols_slope(x_values, y_values)
...
if slope is None:
    slope = 0.0
    is_stale = True
    stale_reason = "zero_signed_volume_variance"
    insufficient_variation = True
elif slope <= 0.0:
    slope = 0.0
    is_stale = True
```

```python
input_data_hash=_hash_input(
    pair=pair,
    window_seconds=window_seconds,
    bucket_seconds=bucket_seconds,
    trades=recent_trades,
    eval_time_ns=eval_time_ns,
)
```

## Implemented formula in plain text

1. Trades are signed using Lee-Ready when `mid_price` is present, with tick-rule fallback.
2. Signed volume is bucketed into fixed-width time intervals.
3. Interval price change uses the interval `reference_price`, where the reference is `mid_price` when available, otherwise `trade.price`.
4. Kyle lambda is the OLS slope:
   - `lambda = cov(signed_volume, price_change) / var(signed_volume)`

## Inputs / output

- Input variables:
  - `trade.price`
  - `trade.mid_price`
  - `trade.volume`
  - `trade.timestamp_ns`
  - `pair`
  - `window_seconds`
  - `bucket_seconds`
  - `computed_at_ns`
- Output variable:
  - `KyleLambdaRecord.value`

## Units / denominator / window / timestamp convention

- Units: price-change per signed-volume unit; exact economic normalization remains `UNIT_AMBIGUITY` for external audit because the code does not rescale to bps or notional.
- Denominator: variance of interval signed volume.
- Window:
  - rolling time window via `window_seconds`
  - sub-bucket event aggregation via `bucket_seconds`
- Timestamp convention:
  - `computed_at_ns`
  - trade event timestamps

## Data <= t / stale / insufficient behavior

- Uses only data `<= computed_at_ns`:
  - `computed_at_ns` must be `>= latest trade timestamp`
- Zero-variance behavior:
  - returns `value = 0.0`
  - `is_stale = True`
  - `stale_reason = "zero_signed_volume_variance"`
- Non-positive slope behavior:
  - coerced to `0.0`
  - marked stale
- Missing values do not silently become safe live values; they surface through stale flags and reason fields.

## Downstream consumers

- `src/data_backbone/microstructure/engine_input_provenance.py`
  - Engine A `kyle_lambda_cost_uplift`
  - Engine C direct `kyle_lambda`
- `src/engines/engine_a/cost_feasibility_a.py`
  - `effective_expected_cost = inputs.expected_cost + inputs.kyle_lambda_cost_uplift`
- `src/engines/engine_c/continuation_validator_c.py`
  - `inputs.kyle_lambda > inputs.kyle_lambda_max`
- Feature-registry claimed consumer:
  - `execution_backbone`
  - direct governed execution consumer not proven in this pass

## Tests covering behavior

- `tests/test_data_backbone/microstructure/test_kyle_lambda.py`
  - stale path:
    - `assert result.is_stale is True`
    - `assert result.stale_reason == "zero_signed_volume_variance"`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
  - Engine A cost uplift:
    - `assert engine_input.kyle_lambda_cost_uplift == pytest.approx(0.0002)`
  - Engine C direct carry:
    - `assert engine_input.kyle_lambda == pytest.approx(0.0008)`
- `tests/test_microstructure/test_paper_repro.py`
  - reproduction anchor coverage

## Cockpit visibility / risk / external questions

- Cockpit visibility: not directly proven as a dedicated cockpit field; may be visible only via feature-bridge artifacts or engine why payloads.
- False-green risk: if surfaced only through artifact lineage, feature presence can be misread as runtime consumption.
- Classifications:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `ENGINE_CONSUMED`
  - `COST_GATE_CONSUMED`
  - `AMBIGUITY_FOUND`
- External-audit questions:
  - Is the unscaled OLS slope acceptable for all current consumers, or should external audit require a bps/notional normalization seam?
  - Is the feature-registry execution consumer intent still live, or now historical?
