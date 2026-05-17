# Wave 4 Amihud / Roll / Corwin / Hawkes Source Evidence

## Amihud illiquidity

- Source file: `src/data_backbone/microstructure/amihud_illiquidity.py`
- Function/class:
  - `compute_amihud_illiquidity`
  - `AmihudIlliquidityRecord`

### Exact code excerpt

```python
ratios.append(
    abs(math.log(current.close_price) - math.log(previous.close_price))
    / current.dollar_volume
)
...
value=sum(ratios) / len(ratios),
partial_window=available_window_seconds < window_seconds,
low_sample_confidence=len(recent_bars) < 4,
```

### Formula / units / behavior

- Formula:
  - mean of `abs(log return) / dollar_volume`
- Units:
  - return-per-dollar-volume; exact economic unit remains `UNIT_AMBIGUITY`
- Window:
  - rolling time window via `window_seconds`
- Zero volume behavior:
  - bars with non-positive `dollar_volume` are skipped
- Timestamp discipline:
  - `computed_at_ns >= latest bar timestamp`
  - recent bars filtered to window ending at `computed_at_ns`

### Consumers / tests / classification

- Feature-registry claimed consumers:
  - `portfolio_minimal`
  - `scoring_backbone`
  - `interface_contracts.pair_catalog`
- Direct governed runtime consumer not proven in this pass
- Tests:
  - `tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## Roll spread

- Source file: `src/data_backbone/microstructure/roll_spread.py`
- Function/class:
  - `compute_roll_spread`
  - `RollSpreadRecord`

### Exact code excerpt

```python
covariance = _covariance_lag_one(price_changes)
spread = 0.0 if covariance >= 0.0 else 2.0 * ((-covariance) ** 0.5)
...
if covariance >= 0.0:
    stale_reason = "non_negative_lag_covariance"
```

### Formula / units / behavior

- Formula:
  - lag-one covariance of price changes
  - `spread = 2 * sqrt(-covariance)` when covariance is negative
- Units:
  - price units of the input trade prices
- Window:
  - rolling time window via `window_seconds`
- Negative-covariance requirement:
  - non-negative covariance forces `spread = 0.0` and stale flag
- Timestamp discipline:
  - `computed_at_ns >= latest trade timestamp`

### Consumers / tests / classification

- Feature-registry claimed consumer:
  - `execution_backbone.execution_cost_meter`
- Direct governed runtime consumer not proven in this pass
- Tests:
  - `tests/test_data_backbone/microstructure/test_roll_spread.py`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## Corwin-Schultz spread

- Source file: `src/data_backbone/microstructure/corwin_schultz_spread.py`
- Function/class:
  - `compute_corwin_schultz_spread`
  - `CorwinSchultzSpreadRecord`

### Exact code excerpt

```python
beta = (log_range_first ** 2) + (log_range_second ** 2)
gamma = log(two_day_high / two_day_low) ** 2
alpha = (
    ((sqrt(2.0 * beta) - sqrt(beta)) / _CS_DENOMINATOR)
    - sqrt(gamma / _CS_DENOMINATOR)
)
spread = 2.0 * (math.exp(alpha) - 1.0) / (1.0 + math.exp(alpha))
```

### Formula / units / behavior

- Formula:
  - standard two-bar Corwin-Schultz spread estimator
- Units:
  - fraction
- Window:
  - fixed two-bar lookback
- Invalid high-low behavior:
  - validator requires `high_price >= low_price`
- Low-sample behavior:
  - effectively always low-sample because the seam is fixed to two bars

### Consumers / tests / classification

- Feature-registry claimed consumers:
  - `interface_contracts.pair_catalog`
  - `meta_learning`
- Direct governed runtime consumer not proven in this pass
- Tests:
  - `tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `FUTURE_RESERVED`

## Hawkes intensity

- Source file: `src/data_backbone/microstructure/hawkes_intensity.py`
- Function/class:
  - `compute_hawkes_intensity`
  - `HawkesIntensityRecord`

### Exact code excerpt

```python
intensity = estimate.mu
for event in recent_events:
    dt_seconds = max((eval_time_ns - event.timestamp_ns) / 1_000_000_000.0, 0.0)
    intensity += estimate.alpha * exp(-estimate.beta * dt_seconds)

branching_ratio = estimate.alpha / estimate.beta
if branching_ratio >= 1.0:
    parameter_warning = "supercritical_branching_ratio"
elif branching_ratio >= 0.95:
    parameter_warning = "near_critical_branching_ratio"
```

### Formula / units / behavior

- Formula:
  - `lambda(t) = mu + sum(alpha * exp(-beta * dt))`
  - `branching_ratio = alpha / beta`
- Units:
  - intensity in event-rate units implied by the supplied estimate
- Time unit:
  - seconds
- Window:
  - event-count window via `window_events`
- Stability constraints:
  - warns on near-critical or supercritical branching ratios
  - warns on `slow_decay_relative_to_window`

### Consumers / tests / classification

- Feature-registry claimed consumers:
  - `engines.engine_c.continuation_validator_c`
  - `meta_learning`
- Direct governed runtime consumer not proven in this pass
- Tests:
  - `tests/test_data_backbone/microstructure/test_hawkes_intensity.py`
- Classification:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `FUTURE_RESERVED`
  - `CONSUMER_NOT_FOUND`

## External-audit questions

1. Are `Amihud` and `Roll` still intended for governed runtime use, or are they now primarily catalog / research seams?
2. Should Hawkes remain registry-listed for Engine C if no direct runtime seam is currently proven?
