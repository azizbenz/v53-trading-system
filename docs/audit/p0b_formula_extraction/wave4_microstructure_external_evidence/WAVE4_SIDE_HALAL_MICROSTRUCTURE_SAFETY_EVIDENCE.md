# Wave 4 Side / Halal Microstructure Safety Evidence

This file is evidence only. It does not certify live readiness.

## No side mutation in traced microstructure seams

### Engine C

- Tests:
  - `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`
  - `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- Evidence:
  - `assert result.signal_candidate.side == Side.BUY`

### Engine D

- Source:
  - `src/engines/engine_d/runtime_input_assembler_d.py`
  - `src/engines/engine_d/engine_d_runtime_support.py`
- Exact code excerpts:

```python
side=Side.BUY,
```

```python
side=Side.BUY,
confidence=max(0.0, min(1.0, engine_output.penalized_score)),
```

- Tests:
  - `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
    - `assert result.signal_candidate.side == Side.BUY`

## No directional regime output on governed runtime seam

- Source:
  - `src/complete_enablers/regime_detector_runtime.py`
- Proven runtime outputs:
  - `regime_transition_risk`
  - `regime_stability_score`
  - `market_toxicity_score`
  - `expected_duration_bucket`
- Directional live outputs were not found in the runtime producer.

## Dataset-label seam is not runtime side output

- Source:
  - `src/local_replay_runtime/regime_detector_dataset_builder.py`
- Directional states such as `"bid"` and `"ask"` appear here for label generation.
- This is evidence of a local-lab / dataset-building seam, not evidence of governed runtime side override.

## No short / leverage / fake flat evidence found

- No traced microstructure estimator produced a short side.
- No traced microstructure estimator introduced leverage sizing doctrine.
- No traced regime or microstructure seam emitted `NO_TRADE` as a fake flat order route.
- No hidden side mutation via hybrid router was found; hybrid router reuses upstream side sign:

```python
same_side_obi, same_side_micro, same_side_aggr = compute_same_side_signals(snap, sign_side=sign_side)
```

## Classification

- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `RUNTIME_CONSUMED`

## External-audit questions

1. Should the local-lab dataset-builder directional label seam be moved further away from runtime-named regime modules to reduce audit confusion?
