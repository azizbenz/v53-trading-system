# Wave 4 Microstructure Semantic Safety Patch Report

## Scope

This patch is additive. It adds status metadata, doctrine constants, cockpit/runtime caveats, and tests. It does not rewrite estimator math and does not change engine strategy behavior.

## Files Modified

- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/queue_pressure.py`
- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/walls_and_spoofing.py`
- `src/data_backbone/microstructure/engine_input_provenance.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/templates/partials/_feature_bridge.html`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/__init__.py`
- `src/local_replay_runtime/regime_detector_dataset_builder.py`

## Semantic Safety Changes

### Feature bridge and cockpit

- `source_status=ok` now means artifact parsed, not runtime-consumed.
- Added additive bridge statuses:
  - `ARTIFACT_PRESENT_ONLY`
  - `NOT_PROVEN`
  - registry consumer hints per family
- System-flow feature stage stays yellow unless runtime consumption is actually proven.
- Cockpit feature bridge now states that artifact presence is not runtime-consumption proof.

### Engine C / D doctrine

- Added explicit doctrine constants for Engine C:
  - `CONTINUATION_BREAKOUT_MICROSTRUCTURE`
  - `FAKE_BREAKOUT_PROTECTION`
  - `TOXIC_FLOW_VETO`
- Added explicit doctrine constants for Engine D:
  - `REENTRY_SECOND_CHANCE`
  - `FIRST_EPISODE_LINKAGE`
  - `ANTI_REVENGE_CONDITIONING`
  - `REALIZED_VOL_REENTRY_CONTEXT`
- Shared-scoring mapping for C/D remains `PARTIAL_BY_DESIGN`.

### Kyle / OFI / queue pressure

- Kyle lambda records now surface:
  - `unit_status=UNNORMALIZED_LOCAL_OLS_SLOPE`
  - `cross_pair_comparable=false`
  - `normalized_kyle_lambda_available=false`
- OFI records now surface:
  - `unit_status=RAW_SIGNED_SIZE_IMBALANCE`
  - `cross_pair_comparable=false`
  - `normalization_status=ENGINE_LOCAL_THRESHOLDS`
- Queue-pressure records now surface:
  - `measurement_status=QUEUE_PRESSURE_INSUFFICIENT_DEPTH` when denominator is non-positive
  - explicit `reason_codes`

### Walls / spoofing

- Walls/spoofing snapshots now surface:
  - `real_wall_score_method=HEURISTIC_WEIGHTED_SCORE`
  - `spoof_suspicion_score_method=HEURISTIC_WEIGHTED_SCORE`
  - `calibration_status=CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM`

### Runtime/training regime boundary

- Added runtime constants:
  - `RUNTIME_REGIME_OUTPUT_MODE=NON_DIRECTIONAL_ONLY`
  - `RUNTIME_REGIME_OUTPUTS`
  - `DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN`
- Added dataset-builder constant:
  - `DATASET_BUILDER_LABEL_SCOPE=LOCAL_LAB_TRAINING_ONLY`

### Future / research estimators

- Registry metadata now explicitly marks non-proven runtime families as research/future by default where required by the audit.

## Anti-Leakage Documentation Status

The anti-leakage source evidence remains the primary proof file:
- `WAVE4_MICROSTRUCTURE_ANTI_LEAKAGE_EVIDENCE.md`

This patch adds one extra doctrinal boundary:
- dataset-builder future labels remain local-lab-only and are not runtime outputs.

## Side / Halal Safety

Preserved:
- no side creation from microstructure
- no short path
- no leverage path
- no fake-flat route
- regime runtime remains non-directional

## Tests Run

- targeted microstructure semantic tests
- targeted regime runtime and Engine C / D tests
- targeted cockpit tests
- broad Wave 4 validation band

Result:
- pass
