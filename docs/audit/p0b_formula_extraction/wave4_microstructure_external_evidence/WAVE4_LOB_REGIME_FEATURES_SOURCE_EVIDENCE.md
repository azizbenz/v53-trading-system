# Wave 4 LOB Regime Features Source Evidence

## Source

- Source file: `src/data_backbone/microstructure/lob_regime_features.py`
- Artifact/runtime producer:
  - `src/complete_enablers/regime_detector_runtime.py`
- Dataset/training seam:
  - `src/local_replay_runtime/regime_detector_dataset_builder.py`

## Exact code excerpts

```python
LOB_REGIME_METHOD_VERSION = "lob_regime.live_microstructure.v2"
```

```python
if any(
    snapshot.timestamp_ns > eval_time_ns for snapshot in depth_events
) or any(
    trade.timestamp_ns > eval_time_ns for trade in trades
):
    raise ValueError("LOB regime feature inputs must not contain future events")
```

```python
return _window_rejection_snapshot(
    ...,
    status="stale",
    reason_codes=("LOB_REGIME_DEPTH_STALE",),
)
```

```python
regime_transition_risk: float = Field(default=0.0, ge=0.0, le=1.0)
regime_stability_score: float = Field(default=1.0, ge=0.0, le=1.0)
market_toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
expected_duration_bucket: RegimeDurationBucket = RegimeDurationBucket.PERSISTENT
```

```python
transition = _clip(float(raw_prediction.get("regime_transition_risk", 0.0)))
stability = _clip(float(raw_prediction.get("regime_stability_score", 1.0 - transition)))
toxicity = _clip(float(raw_prediction.get("market_toxicity_score", transition)))
bucket_raw = raw_prediction.get("expected_duration_bucket", RegimeDurationBucket.PERSISTENT.value)
```

## Feature list / allowed outputs

Canonical LOB regime feature families include:
- `spread_bps`
- `order_book_imbalance`
- `microprice_pressure`
- `depth_skew`
- `book_shape_skew`
- `liquidity_thinning_score`
- wall/spoofing family
- `ofi_short_window`
- `aggressive_trade_imbalance`
- `short_window_volatility`

Governed runtime regime outputs proven in `regime_detector_runtime.py`:
- `regime_transition_risk`
- `regime_stability_score`
- `market_toxicity_score`
- `expected_duration_bucket`

## Forbidden directional output scan

### Governed runtime file

- File scanned:
  - `src/complete_enablers/regime_detector_runtime.py`
- Result:
  - no runtime output field named:
    - `direction_up_300s_fee_safe`
    - `buy_probability`
    - `sell_probability`
    - `market_will_go_up`
    - `side`
    - `long`
    - `short`
    - `target_return`
    - `future_return`
    - `label`
    - `direct_trade_decision`

### Dataset / training seam

- File scanned:
  - `src/local_replay_runtime/regime_detector_dataset_builder.py`
- Result:
  - directional pressure-state labels exist in the training/data seam:

```python
if (
    snapshot.order_book_imbalance >= label_config.imbalance_flip_threshold
    and snapshot.microprice_pressure >= label_config.microprice_flip_threshold_bps
):
    return "bid"
```

This is evidence of dataset-label generation, not evidence of forbidden live runtime outputs.

## Runtime consumers

- `src/complete_enablers/regime_detector_runtime.py`
  - emits governed non-directional runtime regime outputs
- `src/execution_backbone/order_decider/hybrid_router.py`
  - consumes:
    - `market_toxicity_score`
    - `regime_transition_risk`
    - `regime_stability_score`
    - `short_window_volatility_z`
- `src/cockpit/state_feature_bridge.py`
  - artifact reader / cockpit bridge only

## Stale / missing / insufficient behavior

- LOB regime feature source:
  - insufficient data -> `LOB_REGIME_INSUFFICIENT_DEPTH_EVENTS`
  - stale depth -> `LOB_REGIME_DEPTH_STALE`
- Feature bridge cockpit seam:
  - source statuses:
    - `ok`
    - `missing`
    - `parse_error`

## Tests

- `tests/test_data_backbone/microstructure/test_lob_regime_features.py`
  - versioned feature-map assertions
  - insufficient-data assertions
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
  - `assert signal.regime_transition_risk == pytest.approx(0.82)`
  - `assert signal.reason_codes[0] == "REGIME_DIRECTIONAL_REF_FORBIDDEN"`

## Classification / external questions

- Classifications:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `REGIME_CONTEXT_INPUT`
  - `EXECUTION_GATE_CONSUMED`
  - `CONSUMED_VIA_ARTIFACT`
  - `AMBIGUITY_FOUND`
- External-audit questions:
  - Is the dataset-builder directional label seam sufficiently isolated from governed runtime, or should external audit require stronger directory-level separation or naming?
