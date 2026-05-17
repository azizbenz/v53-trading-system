# Microstructure Threshold Calibration Spec

## Purpose

Define the future calibration artifact contract for pair-specific microstructure thresholds without inventing thresholds now.

## Artifact path

`microstructure_thresholds/{pair}.json`

## Required fields

- `pair`
- `date_range`
- `regime_bucket`
- `vpin_quantiles`
- `normalized_kyle_quantiles`
- `raw_kyle_quantiles`
- `raw_ofi_quantiles`
- `normalized_ofi_quantiles`
- `recommended_thresholds`
- `sample_count`
- `train_window`
- `validation_window`
- `test_window`
- `method_version_hash`
- `input_data_hash`
- `calibration_status`

## Rules

- no global thresholds without pair/regime evidence
- no live threshold promotion without OOS validation
- thresholds should be per pair and optionally per regime
- normalized Kyle thresholds must reference the configured standard notional
- normalized OFI thresholds must reference the exact depth-adjusted seam used

## Suggested threshold payload

```json
{
  "pair": "BTCUSDT",
  "date_range": {"start": "2026-01-01", "end": "2026-03-31"},
  "regime_bucket": "trend_continuation",
  "vpin_quantiles": {"q50": 0.18, "q75": 0.24, "q90": 0.33},
  "normalized_kyle_quantiles": {"q50": 1.2, "q75": 2.1, "q90": 3.5},
  "raw_kyle_quantiles": {"q50": 0.0005, "q75": 0.0009, "q90": 0.0016},
  "raw_ofi_quantiles": {"q50": 8.0, "q75": 15.0, "q90": 29.0},
  "normalized_ofi_quantiles": {"q50": 0.06, "q75": 0.11, "q90": 0.20},
  "recommended_thresholds": {
    "engine_c_vpin_max": 0.35,
    "engine_c_raw_ofi_min": 10.0,
    "engine_c_normalized_ofi_min": 0.08,
    "engine_c_raw_kyle_max": 0.002,
    "engine_c_normalized_kyle_max_bps": 2.5
  },
  "sample_count": 18423,
  "train_window": {"start": "2026-01-01", "end": "2026-02-15"},
  "validation_window": {"start": "2026-02-16", "end": "2026-03-01"},
  "test_window": {"start": "2026-03-02", "end": "2026-03-31"},
  "method_version_hash": "sha256...",
  "input_data_hash": "sha256...",
  "calibration_status": "OOS_VALIDATED_PENDING_PROMOTION"
}
```

## Safe current doctrine

Until these artifacts exist:
- raw engine thresholds remain engine-local
- normalized seams are calibration/backtest/cockpit context
- no new live threshold promotion should be inferred
