# Wave 4 Microstructure Anti-Leakage Evidence

This file summarizes family-level leakage controls. It does not certify sufficiency beyond the traced code paths.

## Family-level table

| Family | `computed_at_ns` | Uses only data `<= t` | Window type | Future-event handling | Provenance/hash | Tests | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Kyle lambda | Yes | Yes | rolling time + fixed buckets | rejects `computed_at_ns < latest trade ts` | `input_data_hash`, `method_version_hash` | `test_kyle_lambda.py` | `EVIDENCE_EXTRACTED` |
| OFI | Yes | Yes | event-count window | rejects `computed_at_ns < latest point ts`; ordered inputs | `input_data_hash`, `method_version_hash` | `test_order_flow_imbalance.py` | `EVIDENCE_EXTRACTED` |
| VPIN | Yes | Yes | equal-volume bucket window | rejects `computed_at_ns < latest trade ts` | `input_data_hash`, `method_version_hash` | `test_vpin.py` | `EVIDENCE_EXTRACTED` |
| PIN | Yes | N/A raw-event fit absent | metadata window only | no raw-event rolling fit in this seam | `input_data_hash`, `method_version_hash` | `test_pin.py` | `LEAKAGE_PROOF_MISSING` for raw-event fit |
| Amihud | Yes | Yes | rolling time window | rejects `computed_at_ns < latest bar ts` | `input_data_hash`, `method_version_hash` | `test_amihud_illiquidity.py` | `EVIDENCE_EXTRACTED` |
| Roll | Yes | Yes | rolling time window | rejects `computed_at_ns < latest trade ts` | `input_data_hash`, `method_version_hash` | `test_roll_spread.py` | `EVIDENCE_EXTRACTED` |
| Corwin-Schultz | Yes | Yes | fixed two-bar window | rejects `computed_at_ns < latest bar ts` | `input_data_hash`, `method_version_hash` | `test_corwin_schultz_spread.py` | `EVIDENCE_EXTRACTED` |
| Hawkes | Yes | Yes | event-count window | rejects `computed_at_ns < latest event ts` | `input_data_hash`, `method_version_hash` | `test_hawkes_intensity.py` | `EVIDENCE_EXTRACTED` |
| Realized kernel | Yes | Yes | ordered price sequence | rejects `computed_at_ns < latest point ts` | `input_data_hash`, `method_version_hash` | `test_realized_kernel_vol.py` | `EVIDENCE_EXTRACTED` |
| Queue pressure | Yes | Yes | single snapshot / top-k levels | rejects `computed_at_ns < point ts` | `input_data_hash`, `method_version_hash` | `test_queue_pressure.py` | `EVIDENCE_EXTRACTED` |
| Walls/spoofing | Yes | Yes | rolling time window | explicitly filters `timestamp_ns <= computed_at_ns` | `input_data_hash`, `method_version_hash` | `test_walls_and_spoofing.py` | `EVIDENCE_EXTRACTED` |
| LOB regime | Yes | Yes | rolling time window | explicit `future events` rejection | `input_data_hash`, `method_version_hash` | `test_lob_regime_features.py` | `EVIDENCE_EXTRACTED` |

## Key excerpts

### Kyle lambda

```python
if eval_time_ns < recent_trades[-1].timestamp_ns:
    raise ValueError("computed_at_ns must be >= latest trade timestamp")
```

### Realized kernel

```python
if eval_time_ns < points[-1].timestamp_ns:
    raise ValueError("computed_at_ns must be >= latest point timestamp")
```

### LOB regime

```python
if any(
    snapshot.timestamp_ns > eval_time_ns for snapshot in depth_events
) or any(
    trade.timestamp_ns > eval_time_ns for trade in trades
):
    raise ValueError("LOB regime feature inputs must not contain future events")
```

### Walls/spoofing

Windowing behavior was traced in the source summary and prior shell excerpts:
- depth/trade windows are bounded to `window_start_ns <= timestamp_ns <= computed_at_ns`

## Partial-window / stale / insufficient behavior

- OFI:
  - `partial_window`
  - `low_sample_confidence`
- VPIN:
  - `partial_window`
  - `low_sample_confidence`
  - `derived_input_warning`
- Roll:
  - `is_stale`
  - `stale_reason`
- LOB regime:
  - `data_status = insufficient_data | stale | ready`
  - explicit reason codes
- Walls/spoofing:
  - explicit insufficient snapshot

## Provenance behavior

All canonical estimator families inspected in this pack expose:
- `computed_at_ns`
- `method_version_hash`
- `input_data_hash`

That is strong evidence of provenance discipline. It is not, by itself, proof that every downstream artifact preserves the same hash chain.

## Remaining anti-leakage questions

1. `PIN` exposes only parameter-level provenance in the traced seam; raw-event fitting provenance was not found here.
2. Dataset-building code under `local_replay_runtime/regime_detector_dataset_builder.py` deliberately compares current and future snapshots for training labels. External audit should confirm that this seam is operationally isolated from governed runtime use.
