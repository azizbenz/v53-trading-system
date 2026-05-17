# Wave 6 Anti-Leakage / Split Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LEAKAGE_PROOF_MISSING`, `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`

## 1. Feature timestamp discipline in regime dataset building

Source file: `src/local_replay_runtime/regime_detector_dataset_builder.py`

Exact code excerpt:

```python
def _snapshot_at(
    events: Sequence[LobSnapshotDerivedFeatureEvent],
    anchor_timestamp_ns: int,
) -> LobSnapshotDerivedFeatureEvent | None:
    eligible = [event for event in events if event.timestamp_ns <= anchor_timestamp_ns]
    if not eligible:
        return None
    return eligible[-1]
```

Implemented rule:

- features at anchor `t` are constructed only from events with `timestamp_ns <= t`
- future events are excluded from feature construction

## 2. Future-label boundary

Same source file, exact code excerpt:

```python
future_anchor_ns = anchor.timestamp_ns + int(config.future_window_ns * step)
future_snapshot = _snapshot_at(events, future_anchor_ns)
```

Plain-text meaning:

- future data is used only to build training labels after the anchor
- the feature snapshot and future label horizons are explicitly separated

## 3. Walk-forward purge and embargo

Source file: `src/calibration_methods/walkforward.py`

Exact code excerpt:

```python
embargo_start = validation_start - embargo_size
purge_start = validation_start - label_horizon_size
train_end_exclusive = min(embargo_start, purge_start)
```

Implemented rule:

- train rows end before both the embargo window and the label-horizon purge window
- this is stronger than a simple chronological split because it purges rows whose labels could overlap the validation region

## 4. Trainer split behavior

Source file: `src/calibration_methods/ml_trainer.py`

Evidence:

- request enforces `walk_forward_train_days == 180`
- request enforces `walk_forward_test_days == 30`
- request enforces `bagging_folds == 5`
- request enforces `early_stopping_rounds == 50`
- request enforces `max_depth == 6`
- time-based `_split_walk_forward(...)` produces train rows before validation rows

Source file: `src/calibration_methods/regime_detector_trainer.py`

Evidence:

- same 180d/30d/5-fold/50-ES/max-depth regime applies
- feature schema drift and feature-set-version drift are rejected

## 5. Human review gate

Source file: `src/local_replay_runtime/walk_forward_review.py`

Evidence:

- review readiness depends on:
  - `temporal_split_confirmed`
  - `no_future_data_leak_confirmed`
  - `feature_timestamp_alignment_confirmed`
  - `calibration_fit_window_confirmed`

Plain-text consequence:

- even with code-level split helpers, final audit still expects explicit review confirmation

## 6. What is proven vs not proven

Proven:

- time-series split exists
- purge and embargo exist
- feature timestamp `<= anchor` discipline exists in the regime dataset builder
- training rails fail closed on schema drift and missing aligned replay data

Not proven:

- a single unified anti-leakage artifact covering every ML/regime runtime seam end-to-end
- a repo-wide proof that every future training label is impossible to confuse with a governed runtime field

## 7. Tests

- `tests/test_calibration_methods/test_walkforward.py`
  - asserts train, embargo, and validation windows are disjoint
  - asserts `purged_train_count > 0` when label horizon exceeds embargo
- `tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py`
  - asserts future labels exist only when future windows are available
  - asserts fail-closed when future windows are absent
- `tests/test_calibration_methods/test_ml_trainer.py`
  - asserts `train_window.end_at < validation_window.start_at`
  - asserts deterministic results for identical seed/data
- `tests/test_calibration_methods/test_regime_detector_trainer.py`
  - asserts deterministic regime training
  - rejects schema and feature-set drift

## 8. External-audit questions

- Should the walk-forward human review confirmation be treated as sufficient governance evidence, or should a machine-verifiable anti-leakage artifact also be required?
- Is a random split forbidden by doctrine only, or is it structurally impossible in every training entry point?

