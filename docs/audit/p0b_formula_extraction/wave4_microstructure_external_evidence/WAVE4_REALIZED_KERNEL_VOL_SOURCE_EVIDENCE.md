# Wave 4 Realized Kernel Vol Source Evidence

## Source

- Source file: `src/data_backbone/microstructure/realized_kernel_vol.py`
- Function/class:
  - `compute_realized_kernel_vol`
  - `resolve_realized_kernel_bandwidth`
  - `parzen_kernel_weight`
  - `RealizedKernelVolRecord`

## Exact code excerpts

```python
REALIZED_KERNEL_METHOD_VERSION = "realized_kernel_vol.parzen.v1"
```

```python
resolved = ceil(bandwidth_c * (sample_size ** (3.0 / 5.0)))
return min(max(1, resolved), upper_bound)
```

```python
log_returns = [
    log(current.price) - log(previous.price)
    for previous, current in zip(points, points[1:])
]
```

```python
gamma_0 = _autocovariance(log_returns, 0)
kernel_variance = gamma_0
for lag in range(1, bandwidth + 1):
    gamma_h = _autocovariance(log_returns, lag)
    weight = parzen_kernel_weight((lag - 1) / bandwidth)
    kernel_variance += weight * (gamma_h + gamma_h)
...
value=sqrt(bounded_variance),
```

## Implemented formula in plain text

1. Construct log returns from ordered price points.
2. Resolve bandwidth:
   - `H = ceil(c * n^(3/5))`
   - bounded to `[1, n - 1]`
3. Compute realized-kernel variance:
   - `gamma_0 + sum_{h=1..H}(ParzenWeight((h-1)/H) * (gamma_h + gamma_h))`
4. Output realized-kernel volatility:
   - `sqrt(max(kernel_variance, 0.0))`

## Inputs / output / units / window / timestamps

- Input variables:
  - ordered price points `(timestamp_ns, price)`
  - `bucket_seconds`
  - `bandwidth_c`
  - `computed_at_ns`
- Output variable:
  - `RealizedKernelVolRecord.value`
- Units:
  - volatility in the native log-return scale of the sampled prices
- Denominator:
  - none; autocovariance sums are direct
- Window:
  - ordered event sequence over the supplied price points
- Timestamp convention:
  - point timestamps
  - `computed_at_ns`

## Data <= t / low-sample / stale behavior

- `computed_at_ns` must be `>= latest point timestamp`
- Uses only ordered points within the supplied history
- Low-sample behavior:
  - `low_sample_confidence = len(log_returns) < 10`
- Insufficient variation:
  - `insufficient_variation = bounded_variance <= 0.0`
- Provenance:
  - `method_version_hash`
  - `input_data_hash`

## Downstream consumers

### Engine A

```python
effective_trend_stability = (
    inputs.trend_stability
    if inputs.realized_kernel_vol_scale is None
    else inputs.realized_kernel_vol_scale
)
```

```python
if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
    return engine_inputs.realized_vol_current, ...
if engine_inputs.realized_kernel_vol_scale is not None and engine_inputs.realized_kernel_vol_scale > 0.0:
    return engine_inputs.realized_kernel_vol_scale, ...
```

### Engine C

```python
if realized_vol_at_break is not None and realized_vol_at_break > 0.0:
    return realized_vol_at_break, "realized_vol_at_break"
if realized_vol_current is not None and realized_vol_current > 0.0:
    return realized_vol_current, "realized_vol_current_fallback"
```

### Engine D

```python
if engine_inputs.realized_vol_post_close is not None and engine_inputs.realized_vol_post_close > 0.0:
    return engine_inputs.realized_vol_post_close, ...
if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
    return engine_inputs.realized_vol_current, ...
```

## Engine D re-entry evidence

- Source file:
  - `src/engines/engine_d/runtime_input_assembler_d.py`
  - `src/engines/engine_d/engine_d_runtime_support.py`
- Evidence:
  - canonical realized-kernel records are carried into `realized_vol_current` and `realized_vol_post_close`
  - runtime forecasting prefers `realized_vol_post_close`
  - this seam is tied to re-entry / first-episode / anti-revenge state, not A/B-style shared scoring physics

## Tests covering behavior

- `tests/test_data_backbone/microstructure/test_realized_kernel_vol.py`
  - `assert resolve_realized_kernel_bandwidth(sample_size) == expected`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
  - Engine A:
    - `assert engine_input.realized_kernel_vol_scale == pytest.approx(0.64)`
    - `assert engine_input.realized_vol_current == pytest.approx(0.08)`
  - Engine C:
    - `assert engine_input.realized_vol_current == pytest.approx(0.018)`
    - `assert engine_input.realized_vol_at_break == pytest.approx(0.02)`
  - Engine D:
    - `assert engine_input.realized_vol_current == pytest.approx(0.018)`
    - `assert engine_input.realized_vol_post_close == pytest.approx(0.015)`
- `tests/test_engines/test_engine_c/test_invalidation_mapper_c.py`
- `tests/test_engines/test_engine_d/test_invalidation_mapper_d.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`

## Classification / external questions

- Classifications:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `ENGINE_CONSUMED`
- External-audit questions:
  - Should external audit require an annualized/non-annualized declaration at the cockpit/report seam, given the canonical estimator keeps native volatility scale?
