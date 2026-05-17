# Wave 6 Dataset Builder / Training Label Boundary Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LOCAL_LAB_ONLY`, `LEAKAGE_RISK`

## 1. Regime training labels use future data by construction

Source file: `src/local_replay_runtime/regime_detector_dataset_builder.py`

Exact code excerpt:

```python
DATASET_BUILDER_LABEL_SCOPE = "LOCAL_LAB_TRAINING_ONLY"
...
eligible = [event for event in events if event.timestamp_ns <= anchor.timestamp_ns]
...
future_anchor_ns = anchor.timestamp_ns + int(config.future_window_ns * step)
future_snapshot = _snapshot_at(events, future_anchor_ns)
```

Implemented decision rule:

- features are snapped from events at or before the anchor timestamp
- labels are built from future windows after the anchor
- the module explicitly marks this scope as Local Lab training only

Input fields:

- ordered microstructure events
- anchor timestamp
- future window seconds / max future steps

Output fields:

- `transition_next_window`
- `duration_bucket`
- `toxicity_bucket`
- `future_steps_observed`
- `input_data_hash`
- `feature_hash`
- `label_config_hash`

## 2. Fail-closed behavior on missing future window

Same source file, exact code excerpt:

```python
if not samples:
    raise ValueError("No eligible regime-detector training samples could be built")
```

Plain-text meaning:

- the builder does not invent synthetic labels when future evidence is unavailable

## 3. Label contract makes training-only future semantics explicit

Source file: `src/interface_contracts/regime_detector_label_contracts.py`

Evidence:

- `REGIME_DETECTOR_LABEL_POLICY = "lob_future_regime_state.v1"`
- dataset sample carries `future_steps_observed`
- dataset contract pins stable `feature_set_version`, `feature_hash`, and `label_config_hash`

## 4. ML backtest projection boundary

Source file: `src/local_replay_runtime/ml_backtest_projection.py`

Exact code excerpt:

```python
projected_net_return_bps = gross_return_bps - route_cost_bps_total
...
if replay_dtr is not None and aligned:
    realized_net_return_bps = (gross_return - realized_cost) * 10_000.0
```

Boundary meaning:

- ML training targets are derived in Local Lab from replay and route-cost seams
- realized target is preferred when replay DTR alignment exists
- these are training dataset targets, not governed runtime outputs

## 5. Runtime isolation evidence

Observed runtime rails:

- `regime_detector_runtime.py` emits only non-directional regime outputs
- no inspected runtime contract exposes `buy_probability`, `sell_probability`, `direction_up_300s_fee_safe`, or similar directional training labels
- supplementary refs governance explicitly forbids those directional keys

Module naming confusion risk:

- dataset building lives under `src/local_replay_runtime/`, which is correct for Local Lab, but naming alone does not prove isolation
- the explicit constant `DATASET_BUILDER_LABEL_SCOPE = "LOCAL_LAB_TRAINING_ONLY"` reduces that ambiguity

## 6. Tests

- `tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py`
  - asserts future microstructure labels are emitted
  - asserts label policy is `lob_future_regime_state.v1`
  - asserts `future_steps_observed >= 1`
  - asserts fail-closed error `No eligible regime-detector training samples`
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
  - asserts `DATASET_BUILDER_LABEL_SCOPE == "LOCAL_LAB_TRAINING_ONLY"`
- `tests/test_local_replay_runtime/test_ml_backtest_projection.py`
  - asserts dataset source can become `local_dataset+replay_dtr`
- `tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py`
  - asserts `missing_replay_dtr_alignment` fail-closed path

## 7. External-audit questions

- Is the current `local_replay_runtime` module naming sufficiently explicit for auditors, or should a stronger Local-Lab-only namespace separation be introduced later?
- Should training-target policy names be surfaced more prominently in cockpit/report layers to avoid confusion with governed runtime outputs?

