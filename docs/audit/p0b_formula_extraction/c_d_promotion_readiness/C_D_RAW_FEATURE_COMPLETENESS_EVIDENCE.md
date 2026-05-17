# C/D Raw Feature Completeness Evidence

## Engine C Raw Feature Export

Source: `src/engines/engine_c/engine_c_runtime.py`

```text
_ENGINE_C_FEATURE_WEIGHTS = {
  "breakout": 0.40,
  "continuation": 0.30,
  "context": 0.20,
  "ce_component": 0.10,
  "fake_breakout_risk": -0.10,
}
```

Source: `src/engines/engine_c/engine_c_runner_support.py`

```text
block_scores = {
  "breakout": breakout_score,
  "continuation": continuation_score,
  "context": context_score,
  "ce_component": conviction_result.ce_component,
  "fake_breakout_risk": fake_breakout_risk,
  "cost_preference": cost_metrics.cost_preference_score,
}
```

Finding:
- exported raw features are complete for the current runtime weights
- local engine internals are richer than exported raw scoring features

## Engine D Raw Feature Export

Source: `src/engines/engine_d/engine_d_runtime.py`

```text
_ENGINE_D_FEATURE_WEIGHTS = {
  "history": 0.25,
  "reformation": 0.30,
  "marginal_value": 0.25,
  "cost_preference": 0.20,
}
```

Source: `src/engines/engine_d/engine_d_runner_late_stages.py`

```text
block_scores = {
  "history": history_score,
  "reformation": reformation_score,
  "marginal_value": marginal_value_score,
  "cost_preference": cost_metrics.cost_preference_score,
}
```

Finding:
- exported raw features are complete for the current runtime weights
- local engine internals are richer than exported raw scoring features

## Completeness Classification

### Engine C

| Surface | Status |
|---|---|
| Runtime raw feature export keys | `PROVEN_PRESENT` |
| Runtime raw feature export consumed by scoring | `PROVEN_CONSUMED` |
| OFI / queue pressure / VPIN / kyle lambda local inputs | `PROVEN_PRESENT` |
| Local microstructure status as a single named field | `NOT_PROVEN` |
| `expected_total_cost` local field | `NOT_FOUND` |
| shared A/B physics export fields | `NOT_PROVEN` by doctrine |

### Engine D

| Surface | Status |
|---|---|
| Runtime raw feature export keys | `PROVEN_PRESENT` |
| Runtime raw feature export consumed by scoring | `PROVEN_CONSUMED` |
| First-episode / anti-revenge / realized-vol local inputs | `PROVEN_PRESENT` |
| Local re-entry window status as a single named field | `NOT_PROVEN` |
| `expected_total_cost` local field | `NOT_FOUND` |
| shared A/B physics export fields | `NOT_PROVEN` by doctrine |

## Test Coverage

- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_runtime_scoring_base_raw_score_matches_runner_score`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_scoring_candidate_marks_shared_physics_mapping_partial_for_engine_d`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_scoring_candidate_marks_shared_physics_mapping_partial_for_engine_c`

## Interpretation

- Raw feature completeness is good for the runtime export each engine actually uses.
- Missing requested field names are mostly naming mismatches or intentional non-exports, not proof that the engine is absent.
- Shared-physics feature completeness is intentionally partial and must stay that way until semantic equivalence is proven.

