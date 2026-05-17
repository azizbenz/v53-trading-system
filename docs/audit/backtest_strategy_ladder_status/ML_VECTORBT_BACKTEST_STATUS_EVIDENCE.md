# ML / VectorBT Backtest Status Evidence

## Overall verdict

`RESEARCH_ONLY`

## LightGBM status

Source-proven ML training components exist:

- `src/calibration_methods/ml_trainer.py`
- `src/calibration_methods/regime_detector_trainer.py`
- `src/local_replay_runtime/ml_backtest_projection.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`
- `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py`

The key reading is conservative:

- both trainers are explicitly marked `LAB_ONLY`
- current training requests enforce bounded walk-forward windows
- current promotion doctrine is still non-sovereign and non-live-mutating

## Anti-leakage / walk-forward evidence

Source-level evidence found:

- `src/calibration_methods/walkforward.py` provides purged walk-forward helpers
- `tests/test_calibration_methods/test_walkforward.py` covers purge / embargo behavior
- `ml_trainer.py` and `regime_detector_trainer.py` use ordered walk-forward splits, not random train/test split

## Threshold / runtime doctrine evidence

- `src/complete_enablers/ml_confidence_enabler.py` contains bounded confidence interpretation with `0.55` / `0.45` thresholds
- Current live doctrine still forbids ML from creating trades directly

## VectorBT status

Audit search result:

- no `vectorbt` hit was found in the current source runner path
- no `from_signals` hit was found

Therefore VectorBT is `NOT_FOUND` in the current audited backtest path.

## Classification table

| Component | Classification | Evidence | Reading |
|---|---|---|---|
| LightGBM replay/backtest projection | `RESEARCH_ONLY` | `ml_backtest_projection.py`; LAB_ONLY trainers | Useful for Local IA Lab research, not promotion-safe live doctrine. |
| Purged walk-forward helper | `RESEARCH_ONLY` | `walkforward.py`; tests | Real anti-leakage helper exists, but it is not the same thing as a production Strategy Ladder runner. |
| VectorBT | `NOT_FOUND` | search result | No current VectorBT backtest path was found. |

## Conclusion

ML support exists as Local IA Lab research infrastructure. It is not the blocker that makes the current backtest coarse; the bigger blocker is that the Strategy Ladder execution chain itself is still incomplete.
